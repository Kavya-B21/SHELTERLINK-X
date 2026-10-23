from datetime import datetime, timezone
from app.extensions import db
from app.models.shelter import Shelter
from app.models.request import ShelterRequest
from app.models.allocation import AllocationRecommendation, ConfirmedAllocation
from app.services.audit_service import AuditService
from app.utils.geo import haversine_distance, get_area_coordinates


class AllocationEngine:
    """
    Transparent, explainable multi-criteria decision engine for matching
    displaced survivor households to optimal emergency disaster shelters.
    """

    # Scoring weights (sum = 1.0)
    WEIGHT_DISTANCE = 0.35          # Closer shelters favored
    WEIGHT_CAPACITY_BUFFER = 0.25   # Shelters with ample headroom favored
    WEIGHT_FACILITIES = 0.20        # Shelters with surplus support amenities
    WEIGHT_PRESSURE_STABILITY = 0.20# Shelters with low projected congestion

    @classmethod
    def evaluate_and_rank_shelters(cls, request: ShelterRequest) -> list[dict]:
        """
        Evaluate all candidate shelters against request constraints and rank by suitability score.
        Returns a list of structured match candidates with explainable score breakdowns.
        """
        # Delete prior recommendations for this request to avoid stale states
        AllocationRecommendation.query.filter_by(request_id=request.id).delete()
        db.session.flush()

        shelters = Shelter.query.all()
        candidates = []

        # Resolve request coordinates
        req_lat, req_lon = request.latitude, request.longitude
        if req_lat is None or req_lon is None:
            req_lat, req_lon = get_area_coordinates(request.affected_area)

        for shelter in shelters:
            is_eligible = True
            unmet_reasons = []

            # 1. Operational status constraint
            if shelter.status in ('Inactive', 'Temporarily Closed'):
                is_eligible = False
                unmet_reasons.append(f"Shelter operational status is '{shelter.status}'")

            # 2. Capacity constraint (Family preservation rule: never split household!)
            if shelter.available_capacity < request.people_count:
                is_eligible = False
                unmet_reasons.append(
                    f"Insufficient available beds ({shelter.available_capacity} available vs {request.people_count} needed)"
                )

            # 3. Facility constraints
            if request.requires_accessibility and not shelter.has_accessibility_ramps:
                is_eligible = False
                unmet_reasons.append("Lacks wheelchair accessibility ramps")

            if request.requires_medical and not shelter.has_medical_support:
                is_eligible = False
                unmet_reasons.append("Lacks on-site emergency medical support")

            if request.requires_family_room and not shelter.has_family_rooms:
                is_eligible = False
                unmet_reasons.append("Lacks private family accommodation rooms")

            # Calculate distance
            dist_km = None
            if req_lat is not None and req_lon is not None and shelter.latitude and shelter.longitude:
                dist_km = haversine_distance(req_lat, req_lon, shelter.latitude, shelter.longitude)
            elif shelter.location_name.strip().lower() == request.affected_area.strip().lower():
                dist_km = 1.0  # Same operational sector estimate
            else:
                dist_km = 8.0  # Sector default estimate

            # Soft scoring components (0 to 100)
            # A. Distance score (closer is higher; 0km = 100, 25km+ = 0)
            if dist_km is not None:
                distance_score = max(0.0, 100.0 - (dist_km * 4.0))
            else:
                distance_score = 50.0  # Neutral baseline

            # B. Capacity buffer score: headroom remaining after placing household
            # Remaining ratio = (available - needed) / total_capacity
            remaining_after = max(0, shelter.available_capacity - request.people_count)
            cap_ratio = remaining_after / shelter.total_capacity if shelter.total_capacity > 0 else 0
            capacity_score = min(100.0, cap_ratio * 125.0)  # 80%+ remaining gets 100

            # C. Facility surplus score
            surplus_pts = 0
            surplus_total = 0
            for fac in [shelter.has_drinking_water, shelter.has_food_supply,
                        shelter.has_medical_support, shelter.has_sanitation,
                        shelter.has_power_backup, shelter.has_accessibility_ramps]:
                surplus_total += 1
                if fac:
                    surplus_pts += 1
            facility_score = (surplus_pts / surplus_total) * 100.0

            # D. Capacity pressure penalty: utilization percentage
            # High utilization (e.g. 90%) means high pressure -> lower stability score
            pressure_stability_score = max(0.0, 100.0 - shelter.utilization_percentage)
            pressure_penalty = shelter.utilization_percentage * 0.3  # Up to 30 penalty points

            # Weighted composite score
            composite_score = (
                cls.WEIGHT_DISTANCE * distance_score +
                cls.WEIGHT_CAPACITY_BUFFER * capacity_score +
                cls.WEIGHT_FACILITIES * facility_score +
                cls.WEIGHT_PRESSURE_STABILITY * pressure_stability_score
            )

            # Cap score at 0 if hard constraints violated
            final_score = round(composite_score, 1) if is_eligible else round(composite_score * 0.2, 1)

            # Generate natural language explanation
            explanation_parts = []
            if is_eligible:
                explanation_parts.append(f"Capacity Match: Verified space for all {request.people_count} household members ({shelter.available_capacity} free beds remaining).")
                if dist_km is not None:
                    explanation_parts.append(f"Proximity: ~{dist_km:.1f} km from affected sector.")
                
                matched_reqs = []
                if request.requires_accessibility:
                    matched_reqs.append("wheelchair access")
                if request.requires_medical:
                    matched_reqs.append("medical support")
                if request.requires_family_room:
                    matched_reqs.append("family rooms")
                if matched_reqs:
                    explanation_parts.append(f"Facility Verified: Successfully satisfies mandatory {', '.join(matched_reqs)}.")
                
                if shelter.utilization_percentage < 70:
                    explanation_parts.append("Pressure: Low current utilization with stable headroom.")
                elif shelter.utilization_percentage < 85:
                    explanation_parts.append("Pressure: Moderate occupancy; monitor incoming flows.")
                else:
                    explanation_parts.append("Pressure: High current utilization, approaching threshold.")
            else:
                explanation_parts.append(f"Ineligible: {'; '.join(unmet_reasons)}.")

            explanation = " ".join(explanation_parts)
            unmet_str = "; ".join(unmet_reasons) if unmet_reasons else None

            # Persist recommendation candidate
            rec = AllocationRecommendation(
                request_id=request.id,
                shelter_id=shelter.id,
                total_score=final_score,
                distance_km=dist_km,
                distance_score=distance_score,
                capacity_score=capacity_score,
                facility_score=facility_score,
                pressure_penalty=pressure_penalty,
                is_fully_eligible=is_eligible,
                explanation=explanation,
                unmet_criteria=unmet_str
            )
            db.session.add(rec)

            candidate_dict = {
                'recommendation_id': None, # will be populated after commit
                'shelter_id': shelter.id,
                'shelter_code': shelter.shelter_code,
                'shelter_name': shelter.name,
                'location_name': shelter.location_name,
                'total_capacity': shelter.total_capacity,
                'available_capacity': shelter.available_capacity,
                'utilization_percentage': shelter.utilization_percentage,
                'distance_km': dist_km,
                'is_eligible': is_eligible,
                'unmet_criteria': unmet_reasons,
                'total_score': final_score,
                'distance_score': round(distance_score, 1),
                'capacity_score': round(capacity_score, 1),
                'facility_score': round(facility_score, 1),
                'pressure_penalty': round(pressure_penalty, 1),
                'explanation': explanation,
                'has_accessibility_ramps': shelter.has_accessibility_ramps,
                'has_medical_support': shelter.has_medical_support,
                'has_family_rooms': shelter.has_family_rooms,
                'has_drinking_water': shelter.has_drinking_water,
                'has_food_supply': shelter.has_food_supply
            }
            candidates.append(candidate_dict)

        # Update request status to 'Recommended' if currently 'Submitted'
        if request.status in ('Submitted', 'Under Review'):
            request.status = 'Recommended'

        db.session.commit()

        # Sort: Eligible first, then descending total score, then ascending distance
        candidates.sort(key=lambda c: (1 if c['is_eligible'] else 0, c['total_score'], -(c['distance_km'] or 999)), reverse=True)
        return candidates

    @classmethod
    def confirm_allocation(cls, request_id: int, shelter_id: int, user,
                           allow_override: bool = False, override_reason: str = None) -> tuple[bool, str, ConfirmedAllocation | None]:
        """
        Transactionally allocate a household to a shelter.
        Atomically re-verifies available capacity, reserves space, updates request status,
        and generates an immutable audit record.
        """
        request = ShelterRequest.query.get(request_id)
        if not request:
            return False, "Survivor request not found.", None

        if request.status in ('Allocation Confirmed', 'Checked In', 'Completed'):
            return False, f"Request is already confirmed in status '{request.status}'.", None

        shelter = Shelter.query.with_for_update().get(shelter_id) if db.engine.name != 'sqlite' else Shelter.query.get(shelter_id)
        if not shelter:
            return False, "Selected shelter not found.", None

        # Revalidate shelter availability
        if shelter.status in ('Inactive', 'Temporarily Closed') and not allow_override:
            return False, f"Cannot allocate: Shelter is currently '{shelter.status}'.", None

        # Recheck capacity atomically
        if shelter.available_capacity < request.people_count and not allow_override:
            return False, (f"Capacity shortage detected during confirmation: "
                           f"Shelter '{shelter.name}' has only {shelter.available_capacity} available beds, "
                           f"but household requires {request.people_count}. Override authorization required."), None

        # Check existing confirmed allocation
        existing_alloc = ConfirmedAllocation.query.filter_by(request_id=request.id).first()
        if existing_alloc:
            return False, "An allocation is already recorded for this request.", None

        # Transactional update
        # We increase reserved_capacity for the shelter to hold space until check-in
        shelter.reserved_capacity += request.people_count
        shelter.update_status_based_on_capacity()

        # Update request
        request.assigned_shelter_id = shelter.id
        request.confirmed_by_user_id = user.id if user else None
        request.confirmed_at = datetime.now(timezone.utc)
        request.status = 'Allocation Confirmed'

        # Record confirmed allocation
        confirmed = ConfirmedAllocation(
            request_id=request.id,
            shelter_id=shelter.id,
            people_count=request.people_count,
            confirmed_by_user_id=user.id if user else None,
            confirmed_at=datetime.now(timezone.utc),
            check_in_status='Pending Check-In',
            is_override=allow_override,
            override_reason=override_reason
        )
        db.session.add(confirmed)
        db.session.commit()

        AuditService.log(
            action='ALLOCATION_CONFIRM',
            resource_type='ConfirmedAllocation',
            resource_id=request.request_code,
            details=(f"Allocated {request.people_count} pax ({request.household_alias}) to '{shelter.name}' ({shelter.shelter_code}). "
                     f"Override: {allow_override}. Reason: {override_reason or 'Direct algorithmic match confirmation'}"),
            user=user
        )

        return True, f"Allocation successfully confirmed for {request.household_alias} to {shelter.name}.", confirmed

    @classmethod
    def update_check_in_status(cls, confirmed_id: int, new_status: str, user) -> tuple[bool, str]:
        """
        Update check-in lifecycle ('Pending Check-In' -> 'Checked In' -> 'Departed / Checked Out' / 'Cancelled').
        Updates shelter reserved_capacity vs current_occupancy accordingly.
        """
        alloc = ConfirmedAllocation.query.get(confirmed_id)
        if not alloc:
            return False, "Allocation record not found."

        shelter = alloc.shelter
        req = alloc.request
        old_status = alloc.check_in_status

        if new_status == 'Checked In' and old_status != 'Checked In':
            # Move from reserved_capacity to current_occupancy
            shelter.reserved_capacity = max(0, shelter.reserved_capacity - alloc.people_count)
            shelter.current_occupancy += alloc.people_count
            alloc.check_in_status = 'Checked In'
            alloc.check_in_time = datetime.now(timezone.utc)
            req.status = 'Checked In'

        elif new_status == 'Departed / Checked Out' and old_status == 'Checked In':
            # Remove from current occupancy
            shelter.current_occupancy = max(0, shelter.current_occupancy - alloc.people_count)
            alloc.check_in_status = 'Departed / Checked Out'
            alloc.check_out_time = datetime.now(timezone.utc)
            req.status = 'Completed'

        elif new_status == 'Cancelled':
            if old_status == 'Checked In':
                shelter.current_occupancy = max(0, shelter.current_occupancy - alloc.people_count)
            else:
                shelter.reserved_capacity = max(0, shelter.reserved_capacity - alloc.people_count)
            alloc.check_in_status = 'Cancelled'
            req.status = 'Cancelled'

        shelter.update_status_based_on_capacity()
        db.session.commit()

        AuditService.log(
            action='CHECK_IN_STATUS_CHANGE',
            resource_type='ConfirmedAllocation',
            resource_id=req.request_code,
            details=f"Status changed from '{old_status}' to '{new_status}' for household {req.household_alias}",
            user=user
        )

        return True, f"Status successfully updated to '{new_status}'."

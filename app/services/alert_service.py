from datetime import datetime, timedelta, timezone
from app.extensions import db
from app.models.shelter import Shelter
from app.models.request import ShelterRequest
from app.models.alert import OperationalAlert
from app.services.forecasting_engine import ForecastingEngine


class AlertService:
    """
    Automated operational intelligence and alert generation service.
    Analyzes current telemetry, capacity buffers, and unallocated survivor demand.
    """

    @classmethod
    def evaluate_and_generate_alerts(cls) -> list[OperationalAlert]:
        """
        Scan system states and generate/update operational alerts.
        Prevents duplicate unresolved alerts of the same category and target.
        """
        generated = []
        now = datetime.now(timezone.utc)
        active_shelters = Shelter.query.filter(Shelter.status != 'Inactive').all()

        for s in active_shelters:
            # 1. Capacity Threshold Alert
            if s.utilization_percentage >= 95.0 or s.available_capacity == 0:
                cls._create_or_update_alert(
                    title=f"Critical Capacity: {s.name} at {s.utilization_percentage}%",
                    severity='CRITICAL',
                    category='CAPACITY',
                    shelter=s,
                    area=s.location_name,
                    message=f"Shelter '{s.name}' ({s.shelter_code}) has {s.available_capacity} available beds remaining. Occupancy is {s.current_occupancy}/{s.total_capacity}.",
                    action="Divert new arrivals to secondary regional shelters. Review pending reservations.",
                    generated_list=generated
                )
            elif s.utilization_percentage >= 85.0:
                cls._create_or_update_alert(
                    title=f"Approaching Capacity: {s.name} at {s.utilization_percentage}%",
                    severity='WARNING',
                    category='CAPACITY',
                    shelter=s,
                    area=s.location_name,
                    message=f"Shelter '{s.name}' is nearing operational threshold. Only {s.available_capacity} beds available.",
                    action="Monitor incoming survivor transfers and prepare overflow staging areas.",
                    generated_list=generated
                )

            # 2. Predicted Demand Surge
            forecast = ForecastingEngine.forecast_shelter_demand(s, horizon_hours=6)
            if forecast['projected_utilization_pct'] >= 95.0 and s.utilization_percentage < 85.0:
                cls._create_or_update_alert(
                    title=f"Predicted Demand Surge: {s.name}",
                    severity='WARNING',
                    category='DEMAND_SURGE',
                    shelter=s,
                    area=s.location_name,
                    message=f"Forecasting model anticipates +{forecast['forecasted_incoming']} incoming survivors in 6h, pushing utilization from {s.utilization_percentage}% to ~{forecast['projected_utilization_pct']}%.",
                    action="Pre-position additional bedding and request relief volunteer reinforcement.",
                    generated_list=generated
                )

            # 3. Essential Facility Deficit
            if not s.has_drinking_water or not s.has_sanitation:
                cls._create_or_update_alert(
                    title=f"Essential Facility Deficit: {s.name}",
                    severity='CRITICAL',
                    category='FACILITY_DEFICIT',
                    shelter=s,
                    area=s.location_name,
                    message=f"Critical sanitation or potable drinking water availability is reported offline at {s.name}.",
                    action="Coordinate with local municipal emergency utilities for immediate water bowser supply.",
                    generated_list=generated
                )

            # 4. Temporarily Closed Alert
            if s.status == 'Temporarily Closed':
                cls._create_or_update_alert(
                    title=f"Shelter Temporarily Closed: {s.name}",
                    severity='WARNING',
                    category='CAPACITY',
                    shelter=s,
                    area=s.location_name,
                    message=f"Shelter {s.shelter_code} is offline or undergoing structural evaluation.",
                    action="Verify status with on-site manager before routing survivor transport.",
                    generated_list=generated
                )

        # 5. Unmatched Urgent Requests
        urgent_pending = ShelterRequest.query.filter(
            ShelterRequest.status.in_(['Submitted', 'Under Review']),
            ShelterRequest.priority_level == 'Urgent'
        ).all()

        if urgent_pending:
            cls._create_or_update_alert(
                title=f"{len(urgent_pending)} Urgent Unallocated Survivor Requests",
                severity='CRITICAL',
                category='UNMATCHED_REQUEST',
                shelter=None,
                area='All Operational Sectors',
                message=f"There are {len(urgent_pending)} urgent priority household requests awaiting shelter confirmation.",
                action="Review the Smart Allocation Recommendations page immediately to assign available beds.",
                generated_list=generated
            )

        db.session.commit()
        return generated

    @classmethod
    def _create_or_update_alert(cls, title: str, severity: str, category: str,
                               shelter: Shelter | None, area: str, message: str,
                               action: str, generated_list: list):
        """Helper to create alert if not already active and unacknowledged."""
        existing = OperationalAlert.query.filter_by(
            title=title,
            category=category,
            is_acknowledged=False
        ).first()

        if not existing:
            alert = OperationalAlert(
                title=title,
                severity=severity,
                category=category,
                shelter_id=shelter.id if shelter else None,
                affected_area=area,
                message=message,
                suggested_action=action
            )
            db.session.add(alert)
            generated_list.append(alert)
        else:
            existing.message = message
            existing.suggested_action = action
            generated_list.append(existing)

    @classmethod
    def acknowledge_alert(cls, alert_id: int, user) -> bool:
        alert = OperationalAlert.query.get(alert_id)
        if not alert:
            return False
        alert.is_acknowledged = True
        alert.acknowledged_by_id = user.id if user else None
        alert.acknowledged_at = datetime.now(timezone.utc)
        db.session.commit()
        return True

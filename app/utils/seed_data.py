from datetime import datetime, timedelta, timezone
import random
from app.extensions import db
from app.models.user import User
from app.models.shelter import Shelter
from app.models.history import ShelterHistory
from app.models.request import ShelterRequest
from app.models.allocation import ConfirmedAllocation
from app.models.alert import OperationalAlert
from app.services.alert_service import AlertService


def seed_database():
    """
    Seed idempotent demonstration dataset with realistic disaster scenarios.
    Checks existence before inserting to prevent duplicates on repeated runs.
    """
    # 1. Seed Demonstration Users
    demo_users = [
        {
            'username': 'admin',
            'email': 'admin@shelterlink.org',
            'password': 'Admin@12345',
            'full_name': 'Chief Relief Administrator',
            'role': 'admin'
        },
        {
            'username': 'coordinator',
            'email': 'coordinator@shelterlink.org',
            'password': 'Coord@12345',
            'full_name': 'Regional Disaster Coordinator',
            'role': 'coordinator'
        },
        {
            'username': 'manager',
            'email': 'manager@shelterlink.org',
            'password': 'Manager@12345',
            'full_name': 'Shelter Operations Manager',
            'role': 'manager'
        },
        {
            'username': 'viewer',
            'email': 'viewer@shelterlink.org',
            'password': 'Viewer@12345',
            'full_name': 'Public Agency Observer',
            'role': 'viewer'
        }
    ]

    for u_data in demo_users:
        if not User.query.filter_by(username=u_data['username']).first():
            user = User(
                username=u_data['username'],
                email=u_data['email'],
                full_name=u_data['full_name'],
                role=u_data['role'],
                is_active=True
            )
            user.set_password(u_data['password'])
            db.session.add(user)

    db.session.commit()

    # 2. Seed Demonstration Shelters
    shelters_spec = [
        {
            'shelter_code': 'SHELTER-001',
            'name': 'St. Jude Community Relief Hub',
            'location_name': 'North Coastal Sector',
            'lat': 13.0827, 'lon': 80.2707,
            'total': 250, 'occ': 85, 'res': 10,
            'status': 'Active',
            'access': True, 'water': True, 'food': True, 'med': True, 'san': True, 'fam': True, 'power': True,
            'contact': 'Capt. Michael Vance', 'phone': '+91-9876543210'
        },
        {
            'shelter_code': 'SHELTER-002',
            'name': 'East River High School Gymnasium',
            'location_name': 'East River Basin',
            'lat': 13.0500, 'lon': 80.2500,
            'total': 200, 'occ': 175, 'res': 15,  # 95% utilization - Approaching capacity / critical
            'status': 'Approaching Capacity',
            'access': True, 'water': True, 'food': True, 'med': False, 'san': True, 'fam': False, 'power': True,
            'contact': 'Sarah Jenkins, Principal', 'phone': '+91-9876543211'
        },
        {
            'shelter_code': 'SHELTER-003',
            'name': 'Central City Indoor Sports Arena',
            'location_name': 'Central Metro Sector',
            'lat': 13.0600, 'lon': 80.2300,
            'total': 500, 'occ': 120, 'res': 30,  # Ample headroom
            'status': 'Active',
            'access': True, 'water': True, 'food': True, 'med': True, 'san': True, 'fam': True, 'power': True,
            'contact': 'David Kumar', 'phone': '+91-9876543212'
        },
        {
            'shelter_code': 'SHELTER-004',
            'name': 'South Valley Municipal Hall',
            'location_name': 'South Hillside Zone',
            'lat': 13.0000, 'lon': 80.2000,
            'total': 100, 'occ': 100, 'res': 0,  # 100% full! Zero capacity
            'status': 'Full',
            'access': False, 'water': True, 'food': True, 'med': False, 'san': True, 'fam': True, 'power': False,
            'contact': 'Rajesh Sharma', 'phone': '+91-9876543213'
        },
        {
            'shelter_code': 'SHELTER-005',
            'name': 'West Industrial Training Pavilion',
            'location_name': 'West Industrial District',
            'lat': 13.0400, 'lon': 80.1700,
            'total': 150, 'occ': 0, 'res': 0,  # Temporarily closed for structural audit
            'status': 'Temporarily Closed',
            'access': False, 'water': False, 'food': False, 'med': False, 'san': False, 'fam': False, 'power': False,
            'contact': 'Eng. Robert Chen', 'phone': '+91-9876543214'
        },
        {
            'shelter_code': 'SHELTER-006',
            'name': 'Harbor View Relief Enclave',
            'location_name': 'Harbor Port District',
            'lat': 13.1000, 'lon': 80.2900,
            'total': 180, 'occ': 110, 'res': 10,
            'status': 'Active',
            'access': False, 'water': True, 'food': True, 'med': True, 'san': True, 'fam': False, 'power': True,
            'contact': 'Officer Meera Patel', 'phone': '+91-9876543215'
        },
        {
            'shelter_code': 'SHELTER-007',
            'name': 'Highland Methodist Cultural Center',
            'location_name': 'Suburban Highland Area',
            'lat': 12.9800, 'lon': 80.1500,
            'total': 120, 'occ': 45, 'res': 5,
            'status': 'Active',
            'access': True, 'water': True, 'food': True, 'med': False, 'san': True, 'fam': True, 'power': True,
            'contact': 'Rev. Thomas John', 'phone': '+91-9876543216'
        }
    ]

    for s_info in shelters_spec:
        existing = Shelter.query.filter_by(shelter_code=s_info['shelter_code']).first()
        if not existing:
            shelter = Shelter(
                shelter_code=s_info['shelter_code'],
                name=s_info['name'],
                location_name=s_info['location_name'],
                latitude=s_info['lat'],
                longitude=s_info['lon'],
                total_capacity=s_info['total'],
                current_occupancy=s_info['occ'],
                reserved_capacity=s_info['res'],
                status=s_info['status'],
                has_accessibility_ramps=s_info['access'],
                has_drinking_water=s_info['water'],
                has_food_supply=s_info['food'],
                has_medical_support=s_info['med'],
                has_sanitation=s_info['san'],
                has_family_rooms=s_info['fam'],
                has_power_backup=s_info['power'],
                contact_person=s_info['contact'],
                contact_phone=s_info['phone'],
                last_updated_by='System Seed'
            )
            shelter.update_status_based_on_capacity()
            db.session.add(shelter)

    db.session.commit()

    # 3. Seed Historical Telemetry Observations for ML Training
    # Only seed if table has fewer than 100 rows
    if ShelterHistory.query.count() < 100:
        shelters = Shelter.query.filter(Shelter.status != 'Temporarily Closed').all()
        now = datetime.now(timezone.utc)
        random.seed(42)

        # Generate 14 days of hourly observations (336 hours per shelter)
        history_records = []
        for shelter in shelters:
            base_occ = max(10, int(shelter.total_capacity * 0.35))
            current_sim_occ = base_occ

            for h_ago in range(336, 0, -1):
                obs_time = now - timedelta(hours=h_ago)
                hour = obs_time.hour
                day_of_week = obs_time.weekday()

                # Diurnal pattern: Higher arrivals in afternoon/evening (12-20)
                diurnal_weight = 1.6 if (12 <= hour <= 20) else (0.5 if (1 <= hour <= 6) else 1.0)
                
                # Storm spike event at 48 hours ago
                storm_factor = 2.5 if (36 <= h_ago <= 72) else 1.0

                expected_inflow = int(random.poisson(3.0 * diurnal_weight * storm_factor) if hasattr(random, 'poisson') 
                                      else max(0, int(random.gauss(3.0 * diurnal_weight * storm_factor, 1.5))))
                
                # Departures usually happen in the morning (8-11)
                departure_weight = 1.4 if (8 <= hour <= 11) else 0.4
                expected_outflow = max(0, int(random.gauss(1.5 * departure_weight, 1.0)))

                # Update running occupancy
                current_sim_occ = max(5, min(shelter.total_capacity, current_sim_occ + expected_inflow - expected_outflow))

                status = 'Active'
                if (current_sim_occ / shelter.total_capacity) >= 0.95:
                    status = 'Full'
                elif (current_sim_occ / shelter.total_capacity) >= 0.85:
                    status = 'Approaching Capacity'

                history_records.append(ShelterHistory(
                    shelter_id=shelter.id,
                    timestamp=obs_time,
                    total_capacity=shelter.total_capacity,
                    current_occupancy=current_sim_occ,
                    incoming_requests=expected_inflow,
                    departures=expected_outflow,
                    affected_area=shelter.location_name,
                    shelter_status=status,
                    is_synthetic=True,
                    notes='Synthetic emergency telemetry observation'
                ))

        db.session.bulk_save_objects(history_records)
        db.session.commit()

    # 4. Seed Representative Survivor Requests
    if ShelterRequest.query.count() == 0:
        sample_requests = [
            {
                'code': 'REQ-2026-001',
                'alias': 'Household Alpha-1',
                'pax': 4,
                'area': 'North Coastal Sector',
                'lat': 13.0850, 'lon': 80.2720,
                'type': 'Family Unit',
                'access': True,  # Needs wheelchair ramps
                'med': True,     # Needs medical support
                'fam': True,     # Needs family room
                'priority': 'Urgent',
                'status': 'Submitted',
                'notes': 'Family with elderly grandparent using wheelchair; insulin storage required.'
            },
            {
                'code': 'REQ-2026-002',
                'alias': 'Household Beta-4',
                'pax': 2,
                'area': 'East River Basin',
                'lat': 13.0520, 'lon': 80.2510,
                'type': 'Standard',
                'access': False,
                'med': False,
                'fam': False,
                'priority': 'Standard',
                'status': 'Submitted',
                'notes': 'Displaced due to stormwater drainage overflow.'
            },
            {
                'code': 'REQ-2026-003',
                'alias': 'Household Gamma-7',
                'pax': 6,
                'area': 'South Hillside Zone',
                'lat': 13.0020, 'lon': 80.2050,
                'type': 'Family Unit',
                'access': False,
                'med': False,
                'fam': True,
                'priority': 'High',
                'status': 'Submitted',
                'notes': 'Large family group with 4 young children. Needs adjacent bedding.'
            },
            {
                'code': 'REQ-2026-004',
                'alias': 'Household Delta-9',
                'pax': 1,
                'area': 'Harbor Port District',
                'lat': 13.0980, 'lon': 80.2880,
                'type': 'Standard',
                'access': False,
                'med': True,
                'fam': False,
                'priority': 'High',
                'status': 'Under Review',
                'notes': 'Individual with minor injury requiring dressing check.'
            },
            {
                'code': 'REQ-2026-005',
                'alias': 'Household Epsilon-2',
                'pax': 3,
                'area': 'Central Metro Sector',
                'lat': 13.0610, 'lon': 80.2310,
                'type': 'Standard',
                'access': False,
                'med': False,
                'fam': False,
                'priority': 'Standard',
                'status': 'Allocation Confirmed',
                'assigned_shelter_code': 'SHELTER-003',
                'notes': 'Pre-allocated to Central City Sports Arena.'
            },
            {
                'code': 'REQ-2026-006',
                'alias': 'Household Omega-X',
                'pax': 12,  # Edge case: Very large group, tests capacity headroom
                'area': 'Suburban Highland Area',
                'lat': 12.9810, 'lon': 80.1520,
                'type': 'Family Unit',
                'access': True,
                'med': False,
                'fam': True,
                'priority': 'Urgent',
                'status': 'Submitted',
                'notes': 'Joint extended family requiring contiguous space and ramps.'
            }
        ]

        coord_user = User.query.filter_by(username='coordinator').first()

        for req_data in sample_requests:
            assigned_id = None
            confirmed_at = None
            confirmed_by_id = None

            if req_data.get('assigned_shelter_code'):
                sh = Shelter.query.filter_by(shelter_code=req_data['assigned_shelter_code']).first()
                if sh:
                    assigned_id = sh.id
                    confirmed_at = datetime.now(timezone.utc)
                    confirmed_by_id = coord_user.id if coord_user else None

            req = ShelterRequest(
                request_code=req_data['code'],
                household_alias=req_data['alias'],
                people_count=req_data['pax'],
                affected_area=req_data['area'],
                latitude=req_data['lat'],
                longitude=req_data['lon'],
                accommodation_type=req_data['type'],
                requires_accessibility=req_data['access'],
                requires_medical=req_data['med'],
                requires_family_room=req_data['fam'],
                priority_level=req_data['priority'],
                status=req_data['status'],
                assigned_shelter_id=assigned_id,
                confirmed_by_user_id=confirmed_by_id,
                confirmed_at=confirmed_at,
                notes=req_data['notes']
            )
            db.session.add(req)
            db.session.flush()

            if assigned_id:
                conf = ConfirmedAllocation(
                    request_id=req.id,
                    shelter_id=assigned_id,
                    people_count=req.people_count,
                    confirmed_by_user_id=confirmed_by_id,
                    confirmed_at=confirmed_at,
                    check_in_status='Pending Check-In',
                    notes='Seed confirmed allocation'
                )
                db.session.add(conf)

        db.session.commit()

    # 5. Generate initial operational alerts
    AlertService.evaluate_and_generate_alerts()
    print("Database successfully seeded with idempotent demonstration dataset.")

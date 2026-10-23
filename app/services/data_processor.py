import io
import csv
from datetime import datetime, timezone
import pandas as pd
from app.extensions import db
from app.models.shelter import Shelter
from app.models.history import ShelterHistory
from app.models.request import ShelterRequest
from app.services.audit_service import AuditService


class DataProcessor:
    """
    Data Engineering pipeline for ingesting, validating, cleaning,
    normalizing, and exporting disaster shelter telemetry and requests.
    """

    # Required columns for CSV types
    SCHEMA_SHELTERS = [
        'shelter_code', 'name', 'location_name', 'total_capacity',
        'current_occupancy', 'status'
    ]
    SCHEMA_HISTORY = [
        'shelter_code', 'timestamp', 'total_capacity', 'current_occupancy',
        'incoming_requests', 'departures', 'affected_area', 'shelter_status'
    ]
    SCHEMA_REQUESTS = [
        'request_code', 'household_alias', 'people_count', 'affected_area',
        'accommodation_type', 'priority_level'
    ]

    @classmethod
    def parse_bool(cls, val, default=False) -> bool:
        if val is None or pd.isna(val):
            return default
        s = str(val).strip().lower()
        return s in ('true', '1', 'yes', 'y', 't')

    @classmethod
    def import_shelters_csv(cls, file_stream, user=None) -> dict:
        """
        Validate and ingest shelters CSV with detailed row-by-row error reporting.
        """
        report = {
            'total_rows': 0,
            'success_count': 0,
            'rejected_count': 0,
            'duplicate_count': 0,
            'rejections': [],  # list of {line: int, reason: str, data: dict}
            'quality_warnings': []
        }

        try:
            content = file_stream.read()
            if isinstance(content, bytes):
                content = content.decode('utf-8', errors='replace')
            df = pd.read_csv(io.StringIO(content))
        except Exception as e:
            report['rejections'].append({'line': 0, 'reason': f"CSV parsing failed: {str(e)}", 'data': None})
            return report

        # Verify header schema
        missing_headers = [c for c in cls.SCHEMA_SHELTERS if c not in df.columns]
        if missing_headers:
            report['rejections'].append({
                'line': 1,
                'reason': f"Missing mandatory schema columns: {', '.join(missing_headers)}",
                'data': None
            })
            return report

        report['total_rows'] = len(df)
        seen_in_batch = set()

        for idx, row in df.iterrows():
            line_no = idx + 2  # 1-indexed header + row index
            row_dict = row.to_dict()

            code = str(row.get('shelter_code', '')).strip().upper()
            name = str(row.get('name', '')).strip()
            location = str(row.get('location_name', '')).strip()

            if not code or code == 'NAN':
                report['rejected_count'] += 1
                report['rejections'].append({'line': line_no, 'reason': "Missing or blank shelter_code", 'data': row_dict})
                continue

            if code in seen_in_batch:
                report['duplicate_count'] += 1
                report['rejected_count'] += 1
                report['rejections'].append({'line': line_no, 'reason': f"Duplicate shelter_code '{code}' within uploaded file", 'data': row_dict})
                continue
            seen_in_batch.add(code)

            if not name or name == 'NAN':
                report['rejected_count'] += 1
                report['rejections'].append({'line': line_no, 'reason': "Missing shelter name", 'data': row_dict})
                continue

            # Numeric validation
            try:
                tot_cap = int(row.get('total_capacity', 0))
                cur_occ = int(row.get('current_occupancy', 0))
                res_cap = int(row.get('reserved_capacity', 0)) if 'reserved_capacity' in row and not pd.isna(row['reserved_capacity']) else 0
            except (ValueError, TypeError):
                report['rejected_count'] += 1
                report['rejections'].append({'line': line_no, 'reason': "Non-integer capacity or occupancy values", 'data': row_dict})
                continue

            if tot_cap <= 0:
                report['rejected_count'] += 1
                report['rejections'].append({'line': line_no, 'reason': f"Total capacity must be > 0 (found {tot_cap})", 'data': row_dict})
                continue

            if cur_occ < 0 or res_cap < 0:
                report['rejected_count'] += 1
                report['rejections'].append({'line': line_no, 'reason': "Occupancy and reservations cannot be negative", 'data': row_dict})
                continue

            if (cur_occ + res_cap) > tot_cap:
                report['rejected_count'] += 1
                report['rejections'].append({'line': line_no, 'reason': f"Occupancy ({cur_occ}) + reserved ({res_cap}) exceeds total capacity ({tot_cap})", 'data': row_dict})
                continue

            # Coordinates
            lat = row.get('latitude')
            lon = row.get('longitude')
            try:
                lat = float(lat) if pd.notna(lat) and lat != '' else None
                lon = float(lon) if pd.notna(lon) and lon != '' else None
            except (ValueError, TypeError):
                lat, lon = None, None
                report['quality_warnings'].append(f"Line {line_no}: Invalid coordinates converted to NULL.")

            # Status normalization
            raw_status = str(row.get('status', 'Active')).strip()
            valid_statuses = {'Active', 'Approaching Capacity', 'Full', 'Temporarily Closed', 'Inactive'}
            status = raw_status if raw_status in valid_statuses else 'Active'

            # Upsert or update existing
            existing = Shelter.query.filter_by(shelter_code=code).first()
            if existing:
                existing.name = name
                existing.location_name = location
                existing.total_capacity = tot_cap
                existing.current_occupancy = cur_occ
                existing.reserved_capacity = res_cap
                existing.status = status
                existing.latitude = lat
                existing.longitude = lon
                existing.has_accessibility_ramps = cls.parse_bool(row.get('has_accessibility_ramps'))
                existing.has_drinking_water = cls.parse_bool(row.get('has_drinking_water', True))
                existing.has_food_supply = cls.parse_bool(row.get('has_food_supply', True))
                existing.has_medical_support = cls.parse_bool(row.get('has_medical_support'))
                existing.has_sanitation = cls.parse_bool(row.get('has_sanitation', True))
                existing.has_family_rooms = cls.parse_bool(row.get('has_family_rooms'))
                existing.has_power_backup = cls.parse_bool(row.get('has_power_backup'))
                existing.update_status_based_on_capacity()
                report['duplicate_count'] += 1
            else:
                shelter = Shelter(
                    shelter_code=code,
                    name=name,
                    location_name=location,
                    latitude=lat,
                    longitude=lon,
                    total_capacity=tot_cap,
                    current_occupancy=cur_occ,
                    reserved_capacity=res_cap,
                    status=status,
                    has_accessibility_ramps=cls.parse_bool(row.get('has_accessibility_ramps')),
                    has_drinking_water=cls.parse_bool(row.get('has_drinking_water', True)),
                    has_food_supply=cls.parse_bool(row.get('has_food_supply', True)),
                    has_medical_support=cls.parse_bool(row.get('has_medical_support')),
                    has_sanitation=cls.parse_bool(row.get('has_sanitation', True)),
                    has_family_rooms=cls.parse_bool(row.get('has_family_rooms')),
                    has_power_backup=cls.parse_bool(row.get('has_power_backup')),
                    last_updated_by=user.username if user else 'CSV Ingest'
                )
                shelter.update_status_based_on_capacity()
                db.session.add(shelter)

            report['success_count'] += 1

        db.session.commit()

        AuditService.log(
            action='DATA_IMPORT',
            resource_type='Shelter',
            resource_id='BULK_CSV',
            details=f"Imported Shelters CSV: {report['success_count']} success, {report['rejected_count']} rejected.",
            user=user
        )

        return report

    @classmethod
    def import_history_csv(cls, file_stream, user=None) -> dict:
        """
        Validate and ingest historical telemetry observations CSV.
        """
        report = {
            'total_rows': 0,
            'success_count': 0,
            'rejected_count': 0,
            'duplicate_count': 0,
            'rejections': [],
            'quality_warnings': []
        }

        try:
            content = file_stream.read()
            if isinstance(content, bytes):
                content = content.decode('utf-8', errors='replace')
            df = pd.read_csv(io.StringIO(content))
        except Exception as e:
            report['rejections'].append({'line': 0, 'reason': f"CSV parsing error: {str(e)}", 'data': None})
            return report

        missing_headers = [c for c in cls.SCHEMA_HISTORY if c not in df.columns]
        if missing_headers:
            report['rejections'].append({
                'line': 1,
                'reason': f"Missing schema columns: {', '.join(missing_headers)}",
                'data': None
            })
            return report

        report['total_rows'] = len(df)
        shelter_map = {s.shelter_code: s.id for s in Shelter.query.all()}

        for idx, row in df.iterrows():
            line_no = idx + 2
            row_dict = row.to_dict()

            code = str(row.get('shelter_code', '')).strip().upper()
            if code not in shelter_map:
                report['rejected_count'] += 1
                report['rejections'].append({
                    'line': line_no,
                    'reason': f"Shelter with code '{code}' does not exist in database.",
                    'data': row_dict
                })
                continue

            # Parse timestamp
            ts_str = str(row.get('timestamp', '')).strip()
            try:
                ts = pd.to_datetime(ts_str).to_pydatetime()
            except Exception:
                report['rejected_count'] += 1
                report['rejections'].append({'line': line_no, 'reason': f"Invalid timestamp format: '{ts_str}'", 'data': row_dict})
                continue

            try:
                tot_cap = int(row.get('total_capacity', 100))
                cur_occ = int(row.get('current_occupancy', 0))
                incoming = int(row.get('incoming_requests', 0))
                departures = int(row.get('departures', 0))
            except (ValueError, TypeError):
                report['rejected_count'] += 1
                report['rejections'].append({'line': line_no, 'reason': "Non-integer numeric columns", 'data': row_dict})
                continue

            if tot_cap <= 0 or cur_occ < 0 or incoming < 0 or departures < 0:
                report['rejected_count'] += 1
                report['rejections'].append({'line': line_no, 'reason': "Negative counts or non-positive capacity", 'data': row_dict})
                continue

            history_rec = ShelterHistory(
                shelter_id=shelter_map[code],
                timestamp=ts,
                total_capacity=tot_cap,
                current_occupancy=cur_occ,
                incoming_requests=incoming,
                departures=departures,
                affected_area=str(row.get('affected_area', 'General Sector')).strip(),
                shelter_status=str(row.get('shelter_status', 'Active')).strip(),
                is_synthetic=True,
                notes='Imported via Historical Telemetry CSV Pipeline'
            )
            db.session.add(history_rec)
            report['success_count'] += 1

        db.session.commit()

        AuditService.log(
            action='DATA_IMPORT',
            resource_type='ShelterHistory',
            resource_id='BULK_CSV',
            details=f"Imported Telemetry CSV: {report['success_count']} rows inserted, {report['rejected_count']} rejected.",
            user=user
        )

        return report

    @classmethod
    def get_data_quality_summary(cls) -> dict:
        """
        Compute real data-quality metrics across all database tables.
        """
        shelters = Shelter.query.all()
        history_count = ShelterHistory.query.count()
        request_count = ShelterRequest.query.count()

        total_shelters = len(shelters)
        missing_coords_count = sum(1 for s in shelters if s.latitude is None or s.longitude is None)
        high_util_count = sum(1 for s in shelters if s.utilization_percentage >= 85.0)
        overbooked_count = sum(1 for s in shelters if (s.current_occupancy + s.reserved_capacity) > s.total_capacity)

        # Requests missing coords
        unassigned_requests = ShelterRequest.query.filter(ShelterRequest.assigned_shelter_id.is_(None)).count()
        urgent_unassigned = ShelterRequest.query.filter(
            ShelterRequest.assigned_shelter_id.is_(None),
            ShelterRequest.priority_level == 'Urgent'
        ).count()

        return {
            'total_shelters': total_shelters,
            'missing_coords_rate': round((missing_coords_count / total_shelters * 100), 1) if total_shelters else 0,
            'missing_coords_count': missing_coords_count,
            'overbooked_inconsistencies': overbooked_count,
            'high_capacity_shelters': high_util_count,
            'telemetry_observation_count': history_count,
            'survivor_requests_total': request_count,
            'unassigned_requests_count': unassigned_requests,
            'urgent_unassigned_count': urgent_unassigned,
            'overall_quality_score': max(0, 100 - (missing_coords_count * 2 + overbooked_count * 20))
        }

    @classmethod
    def export_csv(cls, report_type: str) -> str:
        """Generate downloadable CSV string for authorized reporting."""
        output = io.StringIO()
        writer = csv.writer(output)

        if report_type == 'shelters':
            writer.writerow([
                'shelter_code', 'name', 'location_name', 'latitude', 'longitude',
                'total_capacity', 'current_occupancy', 'reserved_capacity',
                'available_capacity', 'utilization_pct', 'status',
                'accessibility', 'drinking_water', 'medical_support', 'updated_at'
            ])
            for s in Shelter.query.all():
                writer.writerow([
                    s.shelter_code, s.name, s.location_name, s.latitude, s.longitude,
                    s.total_capacity, s.current_occupancy, s.reserved_capacity,
                    s.available_capacity, s.utilization_percentage, s.status,
                    s.has_accessibility_ramps, s.has_drinking_water, s.has_medical_support,
                    s.updated_at.isoformat() if s.updated_at else ''
                ])

        elif report_type == 'requests':
            writer.writerow([
                'request_code', 'household_alias', 'people_count', 'affected_area',
                'accommodation_type', 'accessibility_req', 'medical_req',
                'priority', 'status', 'assigned_shelter', 'created_at', 'confirmed_at'
            ])
            for r in ShelterRequest.query.all():
                writer.writerow([
                    r.request_code, r.household_alias, r.people_count, r.affected_area,
                    r.accommodation_type, r.requires_accessibility, r.requires_medical,
                    r.priority_level, r.status,
                    r.assigned_shelter.name if r.assigned_shelter else 'Unassigned',
                    r.created_at.isoformat() if r.created_at else '',
                    r.confirmed_at.isoformat() if r.confirmed_at else ''
                ])

        elif report_type == 'history':
            writer.writerow([
                'shelter_code', 'timestamp', 'total_capacity', 'current_occupancy',
                'incoming_requests', 'departures', 'affected_area', 'shelter_status', 'is_synthetic'
            ])
            for h in ShelterHistory.query.order_by(ShelterHistory.timestamp.asc()).all():
                writer.writerow([
                    h.shelter.shelter_code if h.shelter else '',
                    h.timestamp.isoformat() if h.timestamp else '',
                    h.total_capacity, h.current_occupancy, h.incoming_requests,
                    h.departures, h.affected_area, h.shelter_status, h.is_synthetic
                ])

        elif report_type == 'audit':
            writer.writerow([
                'timestamp', 'username', 'action', 'resource_type', 'resource_id', 'details', 'ip_address'
            ])
            from app.models.audit import AuditLog
            for a in AuditLog.query.order_by(AuditLog.created_at.desc()).limit(1000).all():
                writer.writerow([
                    a.created_at.isoformat() if a.created_at else '',
                    a.username, a.action, a.resource_type, a.resource_id,
                    a.details, a.ip_address
                ])

        return output.getvalue()

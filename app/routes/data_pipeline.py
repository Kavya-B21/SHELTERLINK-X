import io
from flask import Blueprint, render_template, request, flash, redirect, url_for, Response, send_file
from app.services.data_processor import DataProcessor
from app.utils.decorators import login_required, role_required, get_current_user

data_bp = Blueprint('data_pipeline', __name__, url_prefix='/data')


@data_bp.route('/import', methods=['GET', 'POST'])
@login_required
@role_required('admin', 'coordinator')
def import_data():
    report = None
    import_type = request.form.get('import_type', 'shelters')

    if request.method == 'POST':
        if 'csv_file' not in request.files:
            flash('No file part selected.', 'danger')
            return redirect(request.url)

        file = request.files['csv_file']
        if file.filename == '':
            flash('No file selected.', 'danger')
            return redirect(request.url)

        if not file.filename.lower().endswith('.csv'):
            flash('Invalid file format. Only .csv files are supported.', 'danger')
            return redirect(request.url)

        user = get_current_user()

        if import_type == 'shelters':
            report = DataProcessor.import_shelters_csv(file.stream, user=user)
        elif import_type == 'history':
            report = DataProcessor.import_history_csv(file.stream, user=user)
        else:
            flash('Unsupported import type.', 'danger')
            return redirect(request.url)

        if report['rejected_count'] == 0:
            flash(f"Data ingestion successful: {report['success_count']} rows processed.", 'success')
        else:
            flash(f"Data ingestion completed with issues: {report['success_count']} succeeded, {report['rejected_count']} rejected.", 'warning')

    return render_template('data_pipeline/import.html', report=report, import_type=import_type)


@data_bp.route('/quality')
@login_required
def quality():
    summary = DataProcessor.get_data_quality_summary()
    return render_template('data_pipeline/quality.html', summary=summary)


@data_bp.route('/template/<template_type>')
@login_required
def download_template(template_type: str):
    """Serve sample CSV templates with correct headers and example rows."""
    if template_type == 'shelters':
        csv_content = (
            "shelter_code,name,location_name,latitude,longitude,total_capacity,current_occupancy,reserved_capacity,status,has_accessibility_ramps,has_drinking_water,has_food_supply,has_medical_support,has_sanitation,has_family_rooms,has_power_backup\n"
            "SHELTER-EXAMPLE-1,North Community Pavilion,North Coastal Sector,13.0850,80.2720,200,45,5,Active,True,True,True,True,True,True,True\n"
            "SHELTER-EXAMPLE-2,Riverfront Stadium Shelter,East River Basin,13.0510,80.2520,150,135,10,Approaching Capacity,False,True,True,False,True,False,False\n"
        )
        filename = "shelters_template.csv"
    elif template_type == 'history':
        csv_content = (
            "shelter_code,timestamp,total_capacity,current_occupancy,incoming_requests,departures,affected_area,shelter_status\n"
            "SHELTER-001,2026-10-12 14:00:00,250,85,6,2,North Coastal Sector,Active\n"
            "SHELTER-001,2026-10-12 15:00:00,250,89,8,4,North Coastal Sector,Active\n"
            "SHELTER-002,2026-10-12 14:00:00,200,160,12,1,East River Basin,Approaching Capacity\n"
        )
        filename = "telemetry_history_template.csv"
    elif template_type == 'requests':
        csv_content = (
            "request_code,household_alias,people_count,affected_area,latitude,longitude,accommodation_type,requires_accessibility,requires_medical,requires_family_room,priority_level\n"
            "REQ-SAMPLE-01,Household Phoenix-4,4,North Coastal Sector,13.0840,80.2710,Family Unit,True,True,True,Urgent\n"
            "REQ-SAMPLE-02,Household Falcon-2,2,East River Basin,13.0530,80.2505,Standard,False,False,False,Standard\n"
        )
        filename = "survivor_requests_template.csv"
    else:
        return Response("Template not found", status=404)

    return Response(
        csv_content,
        mimetype="text/csv",
        headers={"Content-Disposition": f"attachment;filename={filename}"}
    )

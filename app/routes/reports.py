from datetime import datetime, timezone
from flask import Blueprint, render_template, Response, flash, redirect, url_for
from app.services.data_processor import DataProcessor
from app.utils.decorators import login_required

reports_bp = Blueprint('reports', __name__, url_prefix='/reports')


@reports_bp.route('/', strict_slashes=False)
@reports_bp.route('', strict_slashes=False)
@login_required
def index():
    return render_template('reports/index.html')


@reports_bp.route('/export/<report_type>')
@login_required
def export_csv(report_type: str):
    if report_type not in ('shelters', 'requests', 'history', 'audit'):
        flash('Invalid report type requested.', 'danger')
        return redirect(url_for('reports.index'))

    csv_data = DataProcessor.export_csv(report_type)
    filename = f"shelterlink_{report_type}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"

    return Response(
        csv_data,
        mimetype="text/csv",
        headers={"Content-Disposition": f"attachment;filename={filename}"}
    )

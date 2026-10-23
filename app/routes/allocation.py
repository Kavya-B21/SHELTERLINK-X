from flask import Blueprint, render_template, request, redirect, url_for, flash, abort
from app.models.request import ShelterRequest
from app.models.allocation import ConfirmedAllocation
from app.services.allocation_engine import AllocationEngine
from app.utils.decorators import login_required, role_required, get_current_user

allocation_bp = Blueprint('allocation', __name__, url_prefix='/allocation')


@allocation_bp.route('/match/<int:request_id>')
@login_required
def recommend(request_id: int):
    req_obj = ShelterRequest.query.get(request_id)
    if not req_obj:
        abort(404)

    # Run allocation engine
    candidates = AllocationEngine.evaluate_and_rank_shelters(req_obj)
    eligible_candidates = [c for c in candidates if c['is_eligible']]
    ineligible_candidates = [c for c in candidates if not c['is_eligible']]

    return render_template(
        'allocation/recommend.html',
        request_item=req_obj,
        eligible_candidates=eligible_candidates,
        ineligible_candidates=ineligible_candidates,
        total_evaluated=len(candidates)
    )


@allocation_bp.route('/confirm', methods=['POST'])
@login_required
@role_required('admin', 'coordinator')
def confirm():
    try:
        request_id = int(request.form.get('request_id'))
        shelter_id = int(request.form.get('shelter_id'))
    except (ValueError, TypeError):
        flash('Invalid request or shelter parameter.', 'danger')
        return redirect(url_for('requests.index'))

    allow_override = request.form.get('allow_override') == '1'
    override_reason = request.form.get('override_reason', '').strip()

    user = get_current_user()
    success, msg, confirmed = AllocationEngine.confirm_allocation(
        request_id=request_id,
        shelter_id=shelter_id,
        user=user,
        allow_override=allow_override,
        override_reason=override_reason
    )

    if success:
        flash(msg, 'success')
        return redirect(url_for('allocation.confirmed_list'))
    else:
        flash(msg, 'danger')
        return redirect(url_for('allocation.recommend', request_id=request_id))


@allocation_bp.route('/confirmed-list')
@login_required
def confirmed_list():
    allocations = ConfirmedAllocation.query.order_by(
        ConfirmedAllocation.confirmed_at.desc()
    ).all()
    return render_template('allocation/confirmed.html', allocations=allocations)


@allocation_bp.route('/status-update/<int:confirmed_id>', methods=['POST'])
@login_required
@role_required('admin', 'coordinator', 'manager')
def update_status(confirmed_id: int):
    new_status = request.form.get('new_status', '').strip()
    user = get_current_user()

    success, msg = AllocationEngine.update_check_in_status(
        confirmed_id=confirmed_id,
        new_status=new_status,
        user=user
    )

    if success:
        flash(msg, 'success')
    else:
        flash(msg, 'danger')

    return redirect(url_for('allocation.confirmed_list'))

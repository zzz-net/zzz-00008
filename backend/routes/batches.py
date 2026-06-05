from flask import Blueprint, request, jsonify, g
from ..validators import validate_batch_data
from ..services.batch_service import (
    get_batches, get_batch_detail, create_batch, confirm_batch, return_batch
)

bp = Blueprint('batches', __name__, url_prefix='/api/batches')


def get_current_user():
    return getattr(g, 'current_user', 'cs_demo')


@bp.route('', methods=['GET'])
def list_batches():
    status = request.args.get('status')
    batches = get_batches(status=status)
    return jsonify({'success': True, 'data': batches})


@bp.route('/<int:batch_id>', methods=['GET'])
def get_batch(batch_id):
    result, error = get_batch_detail(batch_id)
    if error:
        return jsonify({'success': False, 'error': error}), 404
    return jsonify({'success': True, 'data': result})


@bp.route('', methods=['POST'])
def create_batch_route():
    data = request.get_json()
    if not data:
        return jsonify({'success': False, 'error': '请求体不能为空'}), 400

    valid, error = validate_batch_data(data)
    if not valid:
        return jsonify({'success': False, 'error': error}), 400

    result, error = create_batch(data, get_current_user())
    if error:
        return jsonify({'success': False, 'error': error}), 400
    return jsonify({'success': True, 'data': result}), 201


@bp.route('/<int:batch_id>/confirm', methods=['POST'])
def confirm_batch_route(batch_id):
    data = request.get_json() or {}
    receiver_person = data.get('receiver_person') or get_current_user()
    if not receiver_person:
        return jsonify({'success': False, 'error': '缺少接班人信息'}), 400

    result, error = confirm_batch(batch_id, receiver_person)
    if error:
        return jsonify({'success': False, 'error': error}), 400
    return jsonify({'success': True, 'data': result})


@bp.route('/<int:batch_id>/return', methods=['POST'])
def return_batch_route(batch_id):
    data = request.get_json() or {}
    receiver_person = data.get('receiver_person') or get_current_user()
    reason = data.get('reason', '')

    if not receiver_person:
        return jsonify({'success': False, 'error': '缺少退回人信息'}), 400

    result, error = return_batch(batch_id, receiver_person, reason)
    if error:
        return jsonify({'success': False, 'error': error}), 400
    return jsonify({'success': True, 'data': result})

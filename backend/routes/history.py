from flask import Blueprint, request, jsonify
from ..models import StatusHistory

bp = Blueprint('history', __name__, url_prefix='/api/history')


@bp.route('', methods=['GET'])
def list_history():
    entity_type = request.args.get('entity_type')
    entity_id = request.args.get('entity_id', type=int)
    limit = request.args.get('limit', type=int, default=100)

    query = StatusHistory.query

    if entity_type:
        query = query.filter(StatusHistory.entity_type == entity_type)
    if entity_id is not None:
        query = query.filter(StatusHistory.entity_id == entity_id)

    items = query.order_by(StatusHistory.created_at.desc()).limit(limit).all()
    return jsonify({'success': True, 'data': [h.to_dict() for h in items]})

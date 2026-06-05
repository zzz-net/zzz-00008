from flask import Blueprint, request, jsonify, g
from ..models import Ticket
from ..validators import validate_ticket_data
from ..services.ticket_service import (
    get_tickets, create_ticket, update_ticket, close_ticket,
    get_open_tickets_for_handover
)

bp = Blueprint('tickets', __name__, url_prefix='/api/tickets')


def get_current_role():
    return getattr(g, 'current_role', 'cs')


def get_current_user():
    return getattr(g, 'current_user', 'cs_demo')


@bp.route('', methods=['GET'])
def list_tickets():
    status = request.args.get('status')
    severity = request.args.get('severity')
    assignee = request.args.get('assignee')
    page = int(request.args.get('page', 1))
    page_size = int(request.args.get('page_size', 20))

    result = get_tickets(status=status, severity=severity, assignee=assignee,
                         page=page, page_size=page_size)
    return jsonify({'success': True, 'data': result})


@bp.route('/open-for-handover', methods=['GET'])
def list_open_for_handover():
    tickets = get_open_tickets_for_handover()
    return jsonify({'success': True, 'data': tickets})


@bp.route('/<int:ticket_id>', methods=['GET'])
def get_ticket(ticket_id):
    ticket = Ticket.query.get(ticket_id)
    if not ticket:
        return jsonify({'success': False, 'error': '升级单不存在'}), 404
    return jsonify({'success': True, 'data': ticket.to_dict()})


@bp.route('', methods=['POST'])
def create_ticket_route():
    data = request.get_json()
    if not data:
        return jsonify({'success': False, 'error': '请求体不能为空'}), 400

    valid, error = validate_ticket_data(data)
    if not valid:
        return jsonify({'success': False, 'error': error}), 400

    result = create_ticket(data, get_current_user())
    return jsonify({'success': True, 'data': result}), 201


@bp.route('/<int:ticket_id>', methods=['PUT'])
def update_ticket_route(ticket_id):
    data = request.get_json() or {}
    result, error = update_ticket(ticket_id, data, get_current_user())
    if error:
        return jsonify({'success': False, 'error': error}), 400
    return jsonify({'success': True, 'data': result})


@bp.route('/<int:ticket_id>/close', methods=['POST'])
def close_ticket_route(ticket_id):
    try:
        data = request.get_json(silent=True) or {}
    except Exception:
        data = {}
    result, error = close_ticket(ticket_id, get_current_user(), get_current_role())
    if error:
        return jsonify({'success': False, 'error': error}), 403
    return jsonify({'success': True, 'data': result})

from flask import Blueprint, jsonify
from sqlalchemy import func
from ..models import db, Ticket, HandoverBatch, StatusHistory
from ..services.ticket_service import check_overdue_tickets

bp = Blueprint('dashboard', __name__, url_prefix='/api/dashboard')


@bp.route('/stats', methods=['GET'])
def get_stats():
    check_overdue_tickets()

    total_tickets = Ticket.query.count()

    status_map = dict(
        db.session.query(Ticket.status, func.count(Ticket.id))
        .group_by(Ticket.status)
        .all()
    )

    severity_counts = dict(
        db.session.query(Ticket.severity, func.count(Ticket.id))
        .group_by(Ticket.severity)
        .all()
    )

    batch_counts = dict(
        db.session.query(HandoverBatch.status, func.count(HandoverBatch.id))
        .group_by(HandoverBatch.status)
        .all()
    )

    recent_history = StatusHistory.query.order_by(StatusHistory.created_at.desc()).limit(20).all()

    return jsonify({
        'success': True,
        'data': {
            'tickets': {
                'total': total_tickets,
                'by_status': {
                    'open': status_map.get('open', 0),
                    'in_progress': status_map.get('in_progress', 0),
                    'closed': status_map.get('closed', 0),
                    'overdue': status_map.get('overdue', 0)
                },
                'by_severity': {
                    'low': severity_counts.get('low', 0),
                    'medium': severity_counts.get('medium', 0),
                    'high': severity_counts.get('high', 0),
                    'critical': severity_counts.get('critical', 0)
                }
            },
            'batches': {
                'total': HandoverBatch.query.count(),
                'pending': batch_counts.get('pending', 0),
                'confirmed': batch_counts.get('confirmed', 0),
                'returned': batch_counts.get('returned', 0)
            },
            'recent_activity': [h.to_dict() for h in recent_history]
        }
    })

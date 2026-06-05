from datetime import datetime
from sqlalchemy import and_, or_
from ..models import db, Ticket, HandoverBatch, BatchTicket
from .history_service import add_history


def check_overdue_tickets():
    now = datetime.utcnow()
    overdue = Ticket.query.filter(
        and_(
            Ticket.deadline < now,
            Ticket.status.in_(['open', 'in_progress'])
        )
    ).all()

    for ticket in overdue:
        old_status = ticket.status
        ticket.status = 'overdue'
        add_history('ticket', ticket.id, old_status, 'overdue', 'system', '系统自动标记为逾期')

    db.session.commit()


def get_tickets(status=None, severity=None, assignee=None, page=1, page_size=20):
    check_overdue_tickets()

    query = Ticket.query

    if status:
        query = query.filter(Ticket.status == status)
    if severity:
        query = query.filter(Ticket.severity == severity)
    if assignee:
        query = query.filter(Ticket.assignee == assignee)

    total = query.count()
    items = query.order_by(Ticket.created_at.desc()) \
        .offset((page - 1) * page_size) \
        .limit(page_size) \
        .all()

    return {
        'items': [t.to_dict() for t in items],
        'total': total,
        'page': page,
        'page_size': page_size
    }


def create_ticket(data, created_by):
    from datetime import datetime as dt
    deadline_str = str(data['deadline']).replace('Z', '+00:00')
    deadline = dt.fromisoformat(deadline_str)

    now = dt.utcnow()
    initial_status = 'overdue' if deadline < now else 'open'

    ticket = Ticket(
        customer_name=data['customer_name'],
        severity=data['severity'],
        assignee=data['assignee'],
        deadline=deadline,
        progress=data.get('progress', ''),
        status=initial_status,
        created_by=created_by
    )
    db.session.add(ticket)
    db.session.flush()

    add_history('ticket', ticket.id, None, initial_status, created_by, '创建升级单')
    db.session.commit()

    return ticket.to_dict()


def update_ticket(ticket_id, data, operator):
    ticket = Ticket.query.get(ticket_id)
    if not ticket:
        return None, '升级单不存在'

    old_status = ticket.status

    if 'progress' in data:
        ticket.progress = data['progress']
    if 'assignee' in data:
        ticket.assignee = data['assignee']
    if 'deadline' in data:
        from datetime import datetime as dt
        deadline_str = str(data['deadline']).replace('Z', '+00:00')
        ticket.deadline = dt.fromisoformat(deadline_str)
        if ticket.deadline < dt.utcnow() and ticket.status in ['open', 'in_progress']:
            ticket.status = 'overdue'

    if 'status' in data and data['status'] != old_status:
        if data['status'] == 'closed' and ticket.severity in ['high', 'critical'] and ticket.status == 'overdue':
            return None, '权限不足：普通客服不能关闭逾期的高危升级单，请联系主管处理'

        if data['status'] not in ['open', 'in_progress', 'closed', 'overdue']:
            return None, '无效的状态值'

        ticket.status = data['status']
        add_history('ticket', ticket_id, old_status, data['status'], operator,
                    data.get('reason', '状态变更'))

    db.session.commit()
    return ticket.to_dict(), None


def close_ticket(ticket_id, operator, role):
    ticket = Ticket.query.get(ticket_id)
    if not ticket:
        return None, '升级单不存在'

    if ticket.status == 'closed':
        return None, '升级单已经是关闭状态'

    if role == 'cs' and ticket.severity in ['high', 'critical'] and ticket.status == 'overdue':
        return None, '权限不足：普通客服不能关闭逾期的高危升级单，请联系主管处理'

    old_status = ticket.status
    ticket.status = 'closed'
    add_history('ticket', ticket_id, old_status, 'closed', operator, '关闭升级单')
    db.session.commit()

    return ticket.to_dict(), None


def get_open_tickets_for_handover():
    check_overdue_tickets()

    subq = db.session.query(BatchTicket.ticket_id).join(
        HandoverBatch, HandoverBatch.id == BatchTicket.batch_id
    ).filter(HandoverBatch.status == 'pending')

    tickets = Ticket.query.filter(
        and_(
            Ticket.status.in_(['open', 'in_progress', 'overdue']),
            Ticket.id.not_in(subq)
        )
    ).order_by(Ticket.severity.desc(), Ticket.created_at.desc()).all()

    return [t.to_dict() for t in tickets]


def is_ticket_in_pending_batch(ticket_id, exclude_batch_id=None):
    query = db.session.query(BatchTicket).join(
        HandoverBatch, HandoverBatch.id == BatchTicket.batch_id
    ).filter(
        BatchTicket.ticket_id == ticket_id,
        HandoverBatch.status == 'pending'
    )
    if exclude_batch_id is not None:
        query = query.filter(HandoverBatch.id != exclude_batch_id)
    count = query.count()
    return count > 0

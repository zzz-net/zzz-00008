from datetime import datetime
from sqlalchemy import and_
from ..models import db, HandoverBatch, Ticket, BatchTicket
from .history_service import add_history
from .ticket_service import is_ticket_in_pending_batch


def get_batches(status=None):
    query = HandoverBatch.query.order_by(HandoverBatch.created_at.desc())
    if status:
        query = query.filter(HandoverBatch.status == status)
    batches = query.all()
    return [b.to_dict() for b in batches]


def get_batch_detail(batch_id):
    batch = HandoverBatch.query.get(batch_id)
    if not batch:
        return None, '交接批次不存在', 404

    result = batch.to_dict()
    result['tickets'] = [t.to_dict() for t in batch.tickets]
    return result, None, 200


def create_batch(data, operator):
    ticket_ids = data['ticket_ids']

    invalid_tickets = []
    for tid in ticket_ids:
        ticket = Ticket.query.get(tid)
        if not ticket:
            invalid_tickets.append(f'工单 {tid} 不存在')
        elif ticket.status == 'closed':
            invalid_tickets.append(f'工单 {tid} 已关闭，不能加入交接')
        elif is_ticket_in_pending_batch(tid):
            invalid_tickets.append(f'工单 {tid} 已在另一个待确认的交接批次中')

    if invalid_tickets:
        return None, '；'.join(invalid_tickets), 400

    batch = HandoverBatch(
        name=data['name'],
        description=data.get('description', ''),
        handover_person=data['handover_person'],
        status='pending'
    )

    for tid in ticket_ids:
        ticket = Ticket.query.get(tid)
        batch.tickets.append(ticket)

    db.session.add(batch)
    db.session.flush()

    add_history('batch', batch.id, None, 'pending', operator, f'创建交接批次，包含 {len(ticket_ids)} 个工单')
    db.session.commit()

    return batch.to_dict(), None, 201


def confirm_batch(batch_id, receiver_person, role):
    if role != 'receiver':
        return None, '权限不足：只有接班人角色可以确认交接批次', 403

    batch = HandoverBatch.query.get(batch_id)
    if not batch:
        return None, '交接批次不存在', 404

    if batch.status == 'confirmed':
        return None, '该交接批次已经确认过，不能重复确认', 400

    if batch.status == 'returned':
        return None, '该交接批次已被退回，需要重新创建交接', 400

    if batch.status != 'pending':
        return None, f'当前批次状态为 {batch.status}，无法确认', 400

    old_status = batch.status
    batch.status = 'confirmed'
    batch.receiver_person = receiver_person
    batch.confirmed_at = datetime.utcnow()

    add_history('batch', batch_id, old_status, 'confirmed', receiver_person, '确认接收交接')
    db.session.commit()

    result = batch.to_dict()
    result['tickets'] = [t.to_dict() for t in batch.tickets]
    return result, None, 200


def return_batch(batch_id, receiver_person, reason, role):
    if role != 'receiver':
        return None, '权限不足：只有接班人角色可以退回交接批次', 403

    batch = HandoverBatch.query.get(batch_id)
    if not batch:
        return None, '交接批次不存在', 404

    if batch.status == 'returned':
        return None, '该交接批次已经被退回，不能重复退回', 400

    if batch.status == 'confirmed':
        return None, '该交接批次已确认，无法退回', 400

    if batch.status != 'pending':
        return None, f'当前批次状态为 {batch.status}，无法退回', 400

    old_status = batch.status
    batch.status = 'returned'
    batch.receiver_person = receiver_person

    add_history('batch', batch_id, old_status, 'returned', receiver_person,
                reason or '退回交接批次')
    db.session.commit()

    result = batch.to_dict()
    result['tickets'] = [t.to_dict() for t in batch.tickets]
    return result, None, 200

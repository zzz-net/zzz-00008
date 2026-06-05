from datetime import datetime
from sqlalchemy import and_
from ..models import db, HandoverBatch, Ticket, BatchTicket, DutyShift
from .history_service import add_history
from .ticket_service import is_ticket_in_pending_batch, get_batch_using_ticket


def get_batches(status=None, is_revoked=None):
    query = HandoverBatch.query.order_by(HandoverBatch.created_at.desc())
    if status:
        query = query.filter(HandoverBatch.status == status)
    if is_revoked is not None:
        if is_revoked:
            query = query.filter(HandoverBatch.revoked_at.isnot(None))
        else:
            query = query.filter(HandoverBatch.revoked_at.is_(None))
    batches = query.all()
    return [b.to_dict() for b in batches]


def get_batch_detail(batch_id):
    batch = HandoverBatch.query.get(batch_id)
    if not batch:
        return None, '交接批次不存在', 404

    result = batch.to_dict()
    result['tickets'] = [t.to_dict() for t in batch.tickets]
    return result, None, 200


def _check_edit_permission(batch, operator, role, permissions):
    if operator == batch.handover_person:
        return True
    if 'create_batches' in permissions:
        return True
    return False


def _validate_tickets_for_batch(ticket_ids, exclude_batch_id=None):
    invalid_tickets = []
    for tid in ticket_ids:
        ticket = Ticket.query.get(tid)
        if not ticket:
            invalid_tickets.append(f'工单 {tid} 不存在')
        elif ticket.status == 'closed':
            invalid_tickets.append(f'工单 {tid} 已关闭，不能加入交接')
        elif is_ticket_in_pending_batch(tid, exclude_batch_id):
            invalid_tickets.append(f'工单 {tid} 已在另一个待确认的交接批次中')
    return invalid_tickets


def create_batch(data, operator):
    ticket_ids = data['ticket_ids']

    invalid_tickets = _validate_tickets_for_batch(ticket_ids)
    if invalid_tickets:
        return None, '；'.join(invalid_tickets), 400

    shift_id = data.get('shift_id')
    shift = None
    if shift_id:
        shift = DutyShift.query.get(shift_id)
        if not shift:
            return None, '指定的班次不存在', 404
        if not shift.is_active:
            return None, f'班次「{shift.name}」已停用，不能用于交接', 400

    batch = HandoverBatch(
        name=data['name'],
        description=data.get('description', ''),
        handover_person=data['handover_person'],
        status='pending',
        shift_id=shift_id
    )

    for tid in ticket_ids:
        ticket = Ticket.query.get(tid)
        batch.tickets.append(ticket)

    db.session.add(batch)
    db.session.flush()

    shift_msg = f'，关联班次: {shift.name}' if shift else ''
    add_history('batch', batch.id, None, 'pending', operator,
                f'创建交接批次，包含 {len(ticket_ids)} 个工单{shift_msg}')
    db.session.commit()

    return batch.to_dict(), None, 201


def update_batch(batch_id, data, operator, role, permissions):
    batch = HandoverBatch.query.get(batch_id)
    if not batch:
        return None, '交接批次不存在', 404

    if batch.status != 'returned':
        return None, f'当前批次状态为 {batch.status}，只有已退回的批次可以修改', 400

    if not _check_edit_permission(batch, operator, role, permissions):
        return None, '权限不足：只有交班人或有创建交接权限的角色可以修改已退回批次', 403

    if 'name' in data and data['name']:
        batch.name = data['name']
    if 'description' in data:
        batch.description = data.get('description', '')

    if 'ticket_ids' in data:
        ticket_ids = data['ticket_ids']
        if not isinstance(ticket_ids, list) or len(ticket_ids) == 0:
            return None, 'ticket_ids 必须是非空列表', 400

        invalid_tickets = _validate_tickets_for_batch(ticket_ids, exclude_batch_id=batch_id)
        if invalid_tickets:
            return None, '；'.join(invalid_tickets), 400

        batch.tickets.clear()
        for tid in ticket_ids:
            ticket = Ticket.query.get(tid)
            batch.tickets.append(ticket)

    old_ticket_count = len(batch.tickets)
    add_history('batch', batch_id, 'returned', 'returned', operator,
                f'修改已退回批次信息，包含 {old_ticket_count} 个工单')
    db.session.commit()

    result = batch.to_dict()
    result['tickets'] = [t.to_dict() for t in batch.tickets]
    return result, None, 200


def resubmit_batch(batch_id, operator, role, permissions):
    batch = HandoverBatch.query.get(batch_id)
    if not batch:
        return None, '交接批次不存在', 404

    if batch.status != 'returned':
        return None, f'当前批次状态为 {batch.status}，只有已退回的批次可以重新提交', 400

    if not _check_edit_permission(batch, operator, role, permissions):
        return None, '权限不足：只有交班人或有创建交接权限的角色可以重新提交已退回批次', 403

    ticket_ids = [t.id for t in batch.tickets]
    invalid_tickets = _validate_tickets_for_batch(ticket_ids, exclude_batch_id=batch_id)
    if invalid_tickets:
        return None, '；'.join(invalid_tickets), 400

    old_status = batch.status
    batch.status = 'pending'
    batch.receiver_person = None

    add_history('batch', batch_id, old_status, 'pending', operator,
                f'重新提交已退回的交接批次，包含 {len(ticket_ids)} 个工单')
    db.session.commit()

    result = batch.to_dict()
    result['tickets'] = [t.to_dict() for t in batch.tickets]
    return result, None, 200


def confirm_batch(batch_id, receiver_person, role, current_user):
    if role != 'receiver':
        return None, '权限不足：只有接班人角色可以确认交接批次', 403

    batch = HandoverBatch.query.get(batch_id)
    if not batch:
        return None, '交接批次不存在', 404

    if batch.status == 'confirmed':
        return None, '该交接批次已经确认过，不能重复确认', 400

    if batch.status != 'pending':
        return None, f'当前批次状态为 {batch.status}，无法确认', 400

    if batch.shift_id and batch.shift:
        if receiver_person and receiver_person != batch.shift.duty_person:
            return None, f'该批次关联班次「{batch.shift.name}」，接班人必须是值班人「{batch.shift.duty_person}」', 400

    old_status = batch.status
    batch.status = 'confirmed'
    effective_receiver = receiver_person
    if batch.shift_id and batch.shift and not effective_receiver:
        effective_receiver = batch.shift.duty_person
    batch.receiver_person = effective_receiver
    batch.receiver_person_display = effective_receiver
    batch.original_confirmer = current_user
    batch.confirmed_at = datetime.utcnow()

    add_history('batch', batch_id, old_status, 'confirmed', current_user, '确认接收交接')
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


def revoke_batch(batch_id, current_user, reason, role):
    if role != 'receiver':
        return None, '权限不足：只有接班人角色可以撤销已确认的交接批次', 403

    batch = HandoverBatch.query.get(batch_id)
    if not batch:
        return None, '交接批次不存在', 404

    if batch.status == 'pending':
        return None, '当前批次状态为待确认，无需撤销', 400

    if batch.status == 'returned':
        return None, '当前批次状态为已退回，不能撤销', 400

    if batch.status != 'confirmed':
        return None, f'当前批次状态为 {batch.status}，只有已确认的批次可以撤销', 400

    if not batch.original_confirmer:
        return None, '该批次缺少原确认人记录，无法撤销', 400

    if batch.original_confirmer != current_user:
        return None, f'权限不足：该批次由「{batch.original_confirmer}」确认，只有原确认人可以撤销', 403

    ticket_ids = [t.id for t in batch.tickets]
    occupied_tickets = []
    for tid in ticket_ids:
        using_batch = get_batch_using_ticket(tid, exclude_batch_id=batch_id)
        if using_batch:
            occupied_tickets.append(
                f'工单 {tid} 已被新批次「{using_batch.name}」(ID: {using_batch.id}) 占用，不能撤销'
            )

    if occupied_tickets:
        return None, '；'.join(occupied_tickets), 409

    old_status = batch.status
    new_status = 'pending'

    batch.status = new_status
    batch.receiver_person = None
    batch.confirmed_at = None
    batch.revoked_at = datetime.utcnow()
    batch.revoked_by = current_user
    batch.revoke_reason = reason
    batch.revoke_old_status = old_status
    batch.revoke_new_status = new_status

    add_history('batch', batch_id, old_status, new_status, current_user,
                f'撤销已确认的交接批次，原因：{reason or "未填写"}')
    db.session.commit()

    result = batch.to_dict()
    result['tickets'] = [t.to_dict() for t in batch.tickets]
    result['affected_tickets'] = [t.to_dict() for t in batch.tickets]
    return result, None, 200

from datetime import datetime, timedelta
from sqlalchemy import and_, or_
from ..models import db, DutyShift, HandoverBatch
from .history_service import add_history


def _parse_dt(s):
    if isinstance(s, datetime):
        return s
    return datetime.fromisoformat(str(s).replace('Z', '+00:00'))


def _check_time_overlap(duty_person, start_time, end_time, exclude_id=None):
    query = DutyShift.query.filter(
        DutyShift.duty_person == duty_person,
        DutyShift.is_active == True
    )
    if exclude_id is not None:
        query = query.filter(DutyShift.id != exclude_id)

    overlaps = []
    for s in query.all():
        if start_time < s.end_time and end_time > s.start_time:
            overlaps.append(f'{s.name} (ID: {s.id}, {s.start_time.strftime("%Y-%m-%d %H:%M")} ~ {s.end_time.strftime("%Y-%m-%d %H:%M")})')
    return overlaps


def _check_shift_referenced_by_active_batches(shift_id):
    batches = HandoverBatch.query.filter(
        HandoverBatch.shift_id == shift_id,
        HandoverBatch.status.in_(['pending', 'confirmed'])
    ).all()
    refs = []
    for b in batches:
        refs.append(f'{b.name} (ID: {b.id}, 状态: {b.status})')
    return refs


def get_shifts(date=None, is_active=None, duty_person=None):
    query = DutyShift.query.order_by(DutyShift.start_time.desc())

    if date is not None:
        try:
            if isinstance(date, str):
                date = date[:10]
                start_of_day = datetime.strptime(date, '%Y-%m-%d')
            elif isinstance(date, datetime):
                start_of_day = date.replace(hour=0, minute=0, second=0, microsecond=0)
            else:
                start_of_day = date
            end_of_day = start_of_day + timedelta(days=1)
            query = query.filter(
                or_(
                    and_(DutyShift.start_time >= start_of_day, DutyShift.start_time < end_of_day),
                    and_(DutyShift.end_time > start_of_day, DutyShift.end_time <= end_of_day),
                    and_(DutyShift.start_time <= start_of_day, DutyShift.end_time >= end_of_day)
                )
            )
        except (ValueError, TypeError):
            pass

    if is_active is not None:
        query = query.filter(DutyShift.is_active == is_active)

    if duty_person:
        query = query.filter(DutyShift.duty_person.like(f'%{duty_person}%'))

    shifts = query.all()
    return [s.to_dict() for s in shifts]


def get_shift_detail(shift_id):
    shift = DutyShift.query.get(shift_id)
    if not shift:
        return None, '班次不存在', 404
    return shift.to_dict(), None, 200


def get_active_shifts_for_receiver(at_time=None):
    if at_time is None:
        at_time = datetime.utcnow()
    query = DutyShift.query.filter(
        DutyShift.is_active == True,
        DutyShift.start_time <= at_time,
        DutyShift.end_time >= at_time
    ).order_by(DutyShift.start_time.asc())
    shifts = query.all()
    return [s.to_dict() for s in shifts]


def create_shift(data, operator):
    start_dt = _parse_dt(data['start_time'])
    end_dt = _parse_dt(data['end_time'])
    duty_person = str(data['duty_person']).strip()

    overlaps = _check_time_overlap(duty_person, start_dt, end_dt)
    if overlaps:
        return None, f'值班人时间冲突：与以下班次重叠 - {"；".join(overlaps)}', 409

    allowed = data.get('allowed_severities', ['low', 'medium', 'high', 'critical'])
    allowed_str = ','.join(allowed) if isinstance(allowed, list) else str(allowed)

    shift = DutyShift(
        name=str(data['name']).strip(),
        duty_person=duty_person,
        start_time=start_dt,
        end_time=end_dt,
        allowed_severities=allowed_str,
        is_active=data.get('is_active', True),
        created_by=operator
    )

    db.session.add(shift)
    db.session.flush()
    add_history('shift', shift.id, None, 'active' if shift.is_active else 'inactive', operator,
                f'创建班次：{shift.name}，值班人：{shift.duty_person}，时间：{start_dt.strftime("%Y-%m-%d %H:%M")} ~ {end_dt.strftime("%Y-%m-%d %H:%M")}')
    db.session.commit()
    return shift.to_dict(), None, 201


def update_shift(shift_id, data, operator):
    shift = DutyShift.query.get(shift_id)
    if not shift:
        return None, '班次不存在', 404

    old_state = {
        'name': shift.name,
        'duty_person': shift.duty_person,
        'start_time': shift.start_time,
        'end_time': shift.end_time,
        'allowed_severities': shift.allowed_severities,
        'is_active': shift.is_active
    }

    if 'name' in data:
        shift.name = str(data['name']).strip()

    duty_person = shift.duty_person
    if 'duty_person' in data:
        duty_person = str(data['duty_person']).strip()
        shift.duty_person = duty_person

    start_dt = shift.start_time
    if 'start_time' in data and data['start_time']:
        start_dt = _parse_dt(data['start_time'])
        shift.start_time = start_dt

    end_dt = shift.end_time
    if 'end_time' in data and data['end_time']:
        end_dt = _parse_dt(data['end_time'])
        shift.end_time = end_dt

    if 'allowed_severities' in data:
        allowed = data['allowed_severities']
        shift.allowed_severities = ','.join(allowed) if isinstance(allowed, list) else str(allowed)

    if 'is_active' in data:
        new_active = bool(data['is_active'])
        if shift.is_active and not new_active:
            refs = _check_shift_referenced_by_active_batches(shift_id)
            if refs:
                db.session.rollback()
                return None, f'班次已被以下未完成的交接批次引用，不能停用：{"；".join(refs)}', 409
        shift.is_active = new_active

    if shift.end_time <= shift.start_time:
        db.session.rollback()
        return None, '结束时间必须晚于开始时间', 400

    if shift.is_active:
        overlaps = _check_time_overlap(shift.duty_person, shift.start_time, shift.end_time, exclude_id=shift_id)
        if overlaps:
            db.session.rollback()
            return None, f'值班人时间冲突：与以下班次重叠 - {"；".join(overlaps)}', 409

    changes = []
    if old_state['name'] != shift.name:
        changes.append(f'名称: {old_state["name"]} → {shift.name}')
    if old_state['duty_person'] != shift.duty_person:
        changes.append(f'值班人: {old_state["duty_person"]} → {shift.duty_person}')
    if old_state['start_time'] != shift.start_time:
        changes.append(f'开始: {old_state["start_time"].strftime("%Y-%m-%d %H:%M")} → {shift.start_time.strftime("%Y-%m-%d %H:%M")}')
    if old_state['end_time'] != shift.end_time:
        changes.append(f'结束: {old_state["end_time"].strftime("%Y-%m-%d %H:%M")} → {shift.end_time.strftime("%Y-%m-%d %H:%M")}')
    if old_state['allowed_severities'] != shift.allowed_severities:
        changes.append(f'可接收级别: {old_state["allowed_severities"]} → {shift.allowed_severities}')
    if old_state['is_active'] != shift.is_active:
        changes.append(f'状态: {"启用" if old_state["is_active"] else "停用"} → {"启用" if shift.is_active else "停用"}')

    if changes:
        new_status = 'active' if shift.is_active else 'inactive'
        old_status = 'active' if old_state['is_active'] else 'inactive'
        add_history('shift', shift_id, old_status, new_status, operator, f'编辑班次：{"；".join(changes)}')

    db.session.commit()
    return shift.to_dict(), None, 200


def disable_shift(shift_id, operator):
    shift = DutyShift.query.get(shift_id)
    if not shift:
        return None, '班次不存在', 404

    if not shift.is_active:
        return None, '该班次已经是停用状态', 400

    refs = _check_shift_referenced_by_active_batches(shift_id)
    if refs:
        return None, f'班次已被以下未完成的交接批次引用，不能停用：{"；".join(refs)}', 409

    shift.is_active = False
    add_history('shift', shift_id, 'active', 'inactive', operator, f'停用班次：{shift.name}')
    db.session.commit()
    return shift.to_dict(), None, 200

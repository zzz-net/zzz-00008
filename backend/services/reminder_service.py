from datetime import datetime, timedelta
from sqlalchemy import and_, or_
from ..models import db, DutyReminder, DutyReminderConfirmation, DutyShift
from .history_service import add_history


def _parse_dt(s):
    if isinstance(s, datetime):
        return s
    return datetime.fromisoformat(str(s).replace('Z', '+00:00'))


def _check_duplicate(title, shift_id, effective_start, effective_end, exclude_id=None):
    query = DutyReminder.query.filter(
        DutyReminder.title == title,
        DutyReminder.is_active == True
    )
    if shift_id:
        query = query.filter(DutyReminder.shift_id == shift_id)
    else:
        query = query.filter(DutyReminder.shift_id.is_(None))

    query = query.filter(
        DutyReminder.effective_start < effective_end,
        DutyReminder.effective_end > effective_start
    )
    if exclude_id is not None:
        query = query.filter(DutyReminder.id != exclude_id)
    return query.first() is not None


def get_reminders(date=None, shift_id=None, is_active=None, for_user=None):
    query = DutyReminder.query.order_by(DutyReminder.effective_start.desc())

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
                    and_(DutyReminder.shift_date >= start_of_day, DutyReminder.shift_date < end_of_day),
                    and_(DutyReminder.effective_start < end_of_day, DutyReminder.effective_end > start_of_day)
                )
            )
        except (ValueError, TypeError):
            pass

    if shift_id is not None:
        query = query.filter(DutyReminder.shift_id == shift_id)

    if is_active is not None:
        query = query.filter(DutyReminder.is_active == is_active)

    if for_user:
        query = query.join(DutyShift, DutyReminder.shift_id == DutyShift.id).filter(
            DutyShift.duty_person == for_user
        )

    reminders = query.all()
    result = []
    for r in reminders:
        data = r.to_dict()
        data['confirmations'] = [c.to_dict() for c in r.confirmations]
        result.append(data)
    return result


def get_my_pending_reminders(username, at_time=None):
    if at_time is None:
        at_time = datetime.utcnow()

    shift_ids = [s.id for s in DutyShift.query.filter(
        DutyShift.duty_person == username,
        DutyShift.is_active == True,
        DutyShift.start_time <= at_time + timedelta(hours=24),
        DutyShift.end_time >= at_time - timedelta(hours=1)
    ).all()]

    query = DutyReminder.query.filter(
        DutyReminder.is_active == True,
        DutyReminder.effective_start <= at_time,
        DutyReminder.effective_end >= at_time
    )

    query = query.filter(
        or_(
            DutyReminder.shift_id.in_(shift_ids),
            and_(
                DutyReminder.shift_id.is_(None),
                DutyReminder.shift_date >= at_time - timedelta(hours=1),
                DutyReminder.shift_date <= at_time + timedelta(hours=24)
            )
        )
    )

    confirmed_ids = {c.reminder_id for c in DutyReminderConfirmation.query.filter_by(confirmed_by=username).all()}
    reminders = [r for r in query.all() if r.id not in confirmed_ids]

    result = []
    for r in reminders:
        data = r.to_dict()
        data['confirmations'] = [c.to_dict() for c in r.confirmations]
        result.append(data)
    return result


def get_reminder_detail(reminder_id):
    reminder = DutyReminder.query.get(reminder_id)
    if not reminder:
        return None, '提醒不存在', 404
    data = reminder.to_dict(include_confirmations=True)
    return data, None, 200


def create_reminder(data, operator):
    title = str(data['title']).strip()
    content = str(data['content']).strip()
    effective_start = _parse_dt(data['effective_start'])
    effective_end = _parse_dt(data['effective_end'])

    shift_id = data.get('shift_id')
    if shift_id is not None and shift_id != '':
        shift_id = int(shift_id)
        shift = DutyShift.query.get(shift_id)
        if not shift:
            return None, '关联的班次不存在', 400
    else:
        shift_id = None

    shift_date = data.get('shift_date')
    if shift_date:
        shift_date = _parse_dt(shift_date)

    if _check_duplicate(title, shift_id, effective_start, effective_end):
        return None, '同一班次同一时间段已存在相同标题的提醒', 409

    reminder = DutyReminder(
        title=title,
        content=content,
        shift_id=shift_id,
        shift_date=shift_date,
        effective_start=effective_start,
        effective_end=effective_end,
        is_active=data.get('is_active', True),
        created_by=operator
    )

    db.session.add(reminder)
    db.session.flush()
    shift_name = reminder.shift.name if reminder.shift else '未指定班次'
    add_history(
        'reminder', reminder.id, None,
        'active' if reminder.is_active else 'inactive',
        operator,
        f'创建提醒：{title}（{shift_name}），有效期：{effective_start.strftime("%Y-%m-%d %H:%M")} ~ {effective_end.strftime("%Y-%m-%d %H:%M")}'
    )
    db.session.commit()
    return reminder.to_dict(include_confirmations=True), None, 201


def update_reminder(reminder_id, data, operator):
    reminder = DutyReminder.query.get(reminder_id)
    if not reminder:
        return None, '提醒不存在', 404

    old_state = {
        'title': reminder.title,
        'content': reminder.content,
        'shift_id': reminder.shift_id,
        'shift_date': reminder.shift_date,
        'effective_start': reminder.effective_start,
        'effective_end': reminder.effective_end,
        'is_active': reminder.is_active
    }

    if 'title' in data:
        reminder.title = str(data['title']).strip()

    if 'content' in data:
        reminder.content = str(data['content']).strip()

    shift_id = old_state['shift_id']
    if 'shift_id' in data:
        if data['shift_id'] is not None and data['shift_id'] != '':
            new_shift_id = int(data['shift_id'])
            shift = DutyShift.query.get(new_shift_id)
            if not shift:
                db.session.rollback()
                return None, '关联的班次不存在', 400
            shift_id = new_shift_id
            reminder.shift_id = shift_id
        else:
            shift_id = None
            reminder.shift_id = None

    if 'shift_date' in data:
        if data['shift_date']:
            reminder.shift_date = _parse_dt(data['shift_date'])
        else:
            reminder.shift_date = None

    effective_start = old_state['effective_start']
    if 'effective_start' in data and data['effective_start']:
        effective_start = _parse_dt(data['effective_start'])
        reminder.effective_start = effective_start

    effective_end = old_state['effective_end']
    if 'effective_end' in data and data['effective_end']:
        effective_end = _parse_dt(data['effective_end'])
        reminder.effective_end = effective_end

    if 'is_active' in data:
        reminder.is_active = bool(data['is_active'])

    if reminder.effective_end <= reminder.effective_start:
        db.session.rollback()
        return None, '结束时间必须晚于开始时间', 400

    if reminder.is_active and _check_duplicate(reminder.title, reminder.shift_id, reminder.effective_start, reminder.effective_end, exclude_id=reminder_id):
        db.session.rollback()
        return None, '同一班次同一时间段已存在相同标题的提醒', 409

    changes = []
    if old_state['title'] != reminder.title:
        changes.append(f'标题: {old_state["title"]} → {reminder.title}')
    if old_state['content'] != reminder.content:
        changes.append(f'内容已更新')
    if old_state['shift_id'] != reminder.shift_id:
        old_shift = DutyShift.query.get(old_state['shift_id']) if old_state['shift_id'] else None
        new_shift = reminder.shift
        changes.append(f'关联班次: {old_shift.name if old_shift else "无"} → {new_shift.name if new_shift else "无"}')
    if old_state['effective_start'] != reminder.effective_start:
        changes.append(f'开始时间: {old_state["effective_start"].strftime("%Y-%m-%d %H:%M")} → {reminder.effective_start.strftime("%Y-%m-%d %H:%M")}')
    if old_state['effective_end'] != reminder.effective_end:
        changes.append(f'结束时间: {old_state["effective_end"].strftime("%Y-%m-%d %H:%M")} → {reminder.effective_end.strftime("%Y-%m-%d %H:%M")}')
    if old_state['is_active'] != reminder.is_active:
        changes.append(f'状态: {"启用" if old_state["is_active"] else "停用"} → {"启用" if reminder.is_active else "停用"}')

    if changes:
        new_status = 'active' if reminder.is_active else 'inactive'
        old_status = 'active' if old_state['is_active'] else 'inactive'
        add_history('reminder', reminder_id, old_status, new_status, operator, f'编辑提醒：{"；".join(changes)}')

    db.session.commit()
    return reminder.to_dict(include_confirmations=True), None, 200


def disable_reminder(reminder_id, operator):
    reminder = DutyReminder.query.get(reminder_id)
    if not reminder:
        return None, '提醒不存在', 404

    if not reminder.is_active:
        return None, '该提醒已经是停用状态', 400

    reminder.is_active = False
    add_history('reminder', reminder_id, 'active', 'inactive', operator, f'停用提醒：{reminder.title}')
    db.session.commit()
    return reminder.to_dict(include_confirmations=True), None, 200


def confirm_reminder(reminder_id, operator):
    reminder = DutyReminder.query.get(reminder_id)
    if not reminder:
        return None, '提醒不存在', 404

    if not reminder.is_active:
        return None, '提醒已停用，无法确认', 400

    now = datetime.utcnow()
    if now < reminder.effective_start or now > reminder.effective_end:
        return None, '提醒已过期，无法确认', 400

    existing = DutyReminderConfirmation.query.filter_by(
        reminder_id=reminder_id,
        confirmed_by=operator
    ).first()
    if existing:
        return None, '您已确认过该提醒', 400

    confirmation = DutyReminderConfirmation(
        reminder_id=reminder_id,
        confirmed_by=operator
    )
    db.session.add(confirmation)
    add_history(
        'reminder', reminder_id, None, 'confirmed',
        operator,
        f'值班人确认提醒：{reminder.title}'
    )
    db.session.commit()
    return confirmation.to_dict(), None, 200

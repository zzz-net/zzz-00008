import csv
import io
import json
from datetime import datetime
from flask import Blueprint, request, jsonify, g, make_response
from ..validators import validate_reminder_data
from ..services.reminder_service import (
    get_reminders, get_reminder_detail, create_reminder,
    update_reminder, disable_reminder, confirm_reminder, get_my_pending_reminders, _parse_dt
)
from ..models import db, DutyShift, DutyReminder
from ..routes.auth import ROLES

bp = Blueprint('reminders', __name__, url_prefix='/api/reminders')

MANAGE_PERMISSION = 'manage_reminders'
VIEW_PERMISSION = 'view_reminders'
CONFIRM_PERMISSION = 'confirm_reminders'


def get_current_role():
    return getattr(g, 'current_role', 'cs')


def get_current_user():
    return getattr(g, 'current_user', 'cs_demo')


def get_current_user_name():
    from ..routes.auth import USERS
    user_info = USERS.get(get_current_user(), {'name': get_current_user()})
    return user_info['name']


def has_permission(perm):
    role = get_current_role()
    role_info = next((r for r in ROLES if r['role'] == role), None)
    if not role_info:
        return False
    return perm in role_info.get('permissions', [])


@bp.route('', methods=['GET'])
def list_reminders():
    if not has_permission(VIEW_PERMISSION) and not has_permission(MANAGE_PERMISSION):
        return jsonify({'success': False, 'error': '权限不足'}), 403

    date = request.args.get('date')
    shift_id_str = request.args.get('shift_id')
    shift_id = int(shift_id_str) if shift_id_str else None
    is_active_str = request.args.get('is_active')
    is_active = None
    if is_active_str is not None:
        is_active = is_active_str.lower() in ('true', '1', 'yes')

    reminders = get_reminders(date=date, shift_id=shift_id, is_active=is_active)
    return jsonify({'success': True, 'data': reminders})


@bp.route('/my-pending', methods=['GET'])
def my_pending():
    if not has_permission(CONFIRM_PERMISSION):
        return jsonify({'success': False, 'error': '权限不足'}), 403
    username = get_current_user_name()
    reminders = get_my_pending_reminders(username)
    return jsonify({'success': True, 'data': reminders})


@bp.route('/for-shift/<int:shift_id>', methods=['GET'])
def reminders_for_shift(shift_id):
    if not has_permission(VIEW_PERMISSION) and not has_permission(MANAGE_PERMISSION):
        return jsonify({'success': False, 'error': '权限不足'}), 403
    reminders = get_reminders(shift_id=shift_id, is_active=True)
    return jsonify({'success': True, 'data': reminders})


@bp.route('/<int:reminder_id>', methods=['GET'])
def get_reminder(reminder_id):
    if not has_permission(VIEW_PERMISSION) and not has_permission(MANAGE_PERMISSION):
        return jsonify({'success': False, 'error': '权限不足'}), 403
    result, error, status_code = get_reminder_detail(reminder_id)
    if error:
        return jsonify({'success': False, 'error': error}), status_code
    return jsonify({'success': True, 'data': result}), status_code


@bp.route('', methods=['POST'])
def create_reminder_route():
    if not has_permission(MANAGE_PERMISSION):
        return jsonify({'success': False, 'error': '权限不足：只有管理员可以创建提醒'}), 403

    data = request.get_json()
    if not data:
        return jsonify({'success': False, 'error': '请求体不能为空'}), 400

    valid, error = validate_reminder_data(data)
    if not valid:
        return jsonify({'success': False, 'error': error}), 400

    result, error, status_code = create_reminder(data, get_current_user())
    if error:
        return jsonify({'success': False, 'error': error}), status_code
    return jsonify({'success': True, 'data': result}), status_code


@bp.route('/<int:reminder_id>', methods=['PUT'])
def update_reminder_route(reminder_id):
    if not has_permission(MANAGE_PERMISSION):
        return jsonify({'success': False, 'error': '权限不足：只有管理员可以编辑提醒'}), 403

    data = request.get_json()
    if not data:
        return jsonify({'success': False, 'error': '请求体不能为空'}), 400

    valid, error = validate_reminder_data(data, for_update=True)
    if not valid:
        return jsonify({'success': False, 'error': error}), 400

    result, error, status_code = update_reminder(reminder_id, data, get_current_user())
    if error:
        return jsonify({'success': False, 'error': error}), status_code
    return jsonify({'success': True, 'data': result}), status_code


@bp.route('/<int:reminder_id>/disable', methods=['POST'])
def disable_reminder_route(reminder_id):
    if not has_permission(MANAGE_PERMISSION):
        return jsonify({'success': False, 'error': '权限不足：只有管理员可以停用提醒'}), 403

    result, error, status_code = disable_reminder(reminder_id, get_current_user())
    if error:
        return jsonify({'success': False, 'error': error}), status_code
    return jsonify({'success': True, 'data': result}), status_code


@bp.route('/<int:reminder_id>/confirm', methods=['POST'])
def confirm_reminder_route(reminder_id):
    if not has_permission(CONFIRM_PERMISSION):
        return jsonify({'success': False, 'error': '权限不足'}), 403

    result, error, status_code = confirm_reminder(reminder_id, get_current_user_name())
    if error:
        return jsonify({'success': False, 'error': error}), status_code
    return jsonify({'success': True, 'data': result}), status_code


@bp.route('/export', methods=['GET'])
def export_reminders():
    if not has_permission(VIEW_PERMISSION) and not has_permission(MANAGE_PERMISSION):
        return jsonify({'success': False, 'error': '权限不足'}), 403

    date = request.args.get('date')
    fmt = request.args.get('format', 'csv')
    reminders = get_reminders(date=date)

    def reminder_to_row(r):
        confirm_list = r.get('confirmations', [])
        confirmed_by = ','.join([c['confirmed_by'] for c in confirm_list])
        confirmed_times = ','.join([
            c.get('confirmed_at', '').replace('T', ' ')[:19] for c in confirm_list])
        return {
            'ID': r['id'],
            '提醒标题': r['title'],
            '提醒内容': r['content'],
            '关联班次名称': r.get('shift_name') or '',
            '班次日期': r.get('shift_date', '').replace('T', ' ')[:10] if r.get('shift_date') else '',
            '生效开始时间': r['effective_start'].replace('T', ' ')[:19] if r.get('effective_start') else '',
            '生效结束时间': r['effective_end'].replace('T', ' ')[:19] if r.get('effective_end') else '',
            '是否启用': '是' if r.get('is_active') else '否',
            '确认人': confirmed_by,
            '确认时间': confirmed_times,
            '创建人': r.get('created_by', ''),
            '创建时间': r.get('created_at', '').replace('T', ' ')[:19] if r.get('created_at') else '',
            '更新时间': r.get('updated_at', '').replace('T', ' ')[:19] if r.get('updated_at') else ''
        }

    rows = [reminder_to_row(r) for r in reminders]
    fieldnames = [
        'ID', '提醒标题', '提醒内容', '关联班次名称', '班次日期',
        '生效开始时间', '生效结束时间', '是否启用',
        '确认人', '确认时间', '创建人', '创建时间', '更新时间'
    ]

    if fmt == 'json':
        output = json.dumps(rows, ensure_ascii=False, indent=2)
        response = make_response(output)
        response.headers['Content-Type'] = 'application/json; charset=utf-8'
        response.headers['Content-Disposition'] = 'attachment; filename=reminders.json'
        return response

    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(rows)
    response = make_response(output.getvalue())
    response.headers['Content-Type'] = 'text/csv; charset=utf-8-sig'
    response.headers['Content-Disposition'] = 'attachment; filename=reminders.csv'
    return response


@bp.route('/import', methods=['POST'])
def import_reminders():
    if not has_permission(MANAGE_PERMISSION):
        return jsonify({'success': False, 'error': '权限不足：只有管理员可以导入提醒'}), 403

    if 'file' not in request.files:
        return jsonify({'success': False, 'error': '未找到上传的文件'}), 400

    file = request.files['file']
    if not file.filename:
        return jsonify({'success': False, 'error': '文件名不能为空'}), 400

    content = file.read().decode('utf-8-sig')
    try:
        reader = csv.DictReader(io.StringIO(content))
    except Exception as e:
        return jsonify({'success': False, 'error': f'CSV 解析失败: {str(e)}'}), 400

    required_cols = {'提醒标题', '提醒内容', '生效开始时间', '生效结束时间'}
    headers = set(reader.fieldnames or [])
    missing = required_cols - headers
    if missing:
        return jsonify({'success': False, 'error': f'缺少必需列: {", ".join(sorted(missing))}'}), 400

    shift_name_map = {}
    for s in DutyShift.query.all():
        shift_name_map[s.name] = s.id

    rows = []
    errors = []
    for idx, row in enumerate(reader, start=2):
        title = (row.get('提醒标题') or '').strip()
        content = (row.get('提醒内容') or '').strip()
        start_str = (row.get('生效开始时间') or '').strip()
        end_str = (row.get('生效结束时间') or '').strip()
        shift_name = (row.get('关联班次名称') or '').strip()
        shift_date_str = (row.get('班次日期') or '').strip()
        active_str = (row.get('是否启用') or '是').strip()

        row_errors = []
        if not title:
            row_errors.append('提醒标题为空')
        if not content:
            row_errors.append('提醒内容为空')
        if not start_str:
            row_errors.append('生效开始时间为空')
        if not end_str:
            row_errors.append('生效结束时间为空')

        start_dt = None
        end_dt = None
        try:
            if start_str:
                start_dt = datetime.fromisoformat(start_str.replace(' ', 'T'))
        except Exception:
            row_errors.append(f'生效开始时间格式错误: {start_str}')
        try:
            if end_str:
                end_dt = datetime.fromisoformat(end_str.replace(' ', 'T'))
        except Exception:
            row_errors.append(f'生效结束时间格式错误: {end_str}')

        if start_dt and end_dt and end_dt <= start_dt:
            row_errors.append('结束时间必须晚于开始时间')

        shift_date = None
        if shift_date_str:
            try:
                shift_date = datetime.fromisoformat(shift_date_str.replace(' ', 'T'))
            except Exception:
                row_errors.append(f'班次日期格式错误: {shift_date_str}')

        shift_id = None
        if shift_name:
            if shift_name not in shift_name_map:
                row_errors.append(f'无效班次: {shift_name}')
            else:
                shift_id = shift_name_map[shift_name]

        is_active = active_str not in ('否', 'false', '0', 'no', 'FALSE', 'NO')

        if row_errors:
            errors.append(f'第 {idx} 行: {"; ".join(row_errors)}')
            continue

        rows.append({
            'title': title,
            'content': content,
            'shift_id': shift_id,
            'shift_date': shift_date.isoformat() if shift_date else None,
            'effective_start': start_dt.isoformat(),
            'effective_end': end_dt.isoformat(),
            'is_active': is_active,
            'line_no': idx
        })

    if errors:
        return jsonify({
            'success': False,
            'error': '数据校验失败，未导入任何记录',
            'details': errors
        }), 400

    operator = get_current_user()
    imported = 0
    skipped = []
    conflict_errors = []

    existing_titles = {(r.title, r.shift_id, r.effective_start, r.effective_end) for r in DutyReminder.query.all()}

    try:
        for r in rows:
            start_dt = _parse_dt(r['effective_start'])
            end_dt = _parse_dt(r['effective_end'])

            overlap = False
            for (et, es, es_start, es_end) in existing_titles:
                pass

            from ..services.reminder_service import _check_duplicate
            if _check_duplicate(r['title'], r['shift_id'], start_dt, end_dt):
                skipped.append(f'第 {r["line_no"]} 行: 标题「{r["title"]}」在该班次和时间段已存在，跳过')
                continue

            reminder = DutyReminder(
                title=r['title'],
                content=r['content'],
                shift_id=r['shift_id'],
                shift_date=_parse_dt(r['shift_date']) if r['shift_date'] else None,
                effective_start=start_dt,
                effective_end=end_dt,
                is_active=r['is_active'],
                created_by=operator
            )
            db.session.add(reminder)
            db.session.flush()
            from ..services.history_service import add_history
            shift_label = reminder.shift.name if reminder.shift else '未指定班次'
            add_history(
                'reminder', reminder.id, None,
                'active' if reminder.is_active else 'inactive',
                operator,
                f'CSV 导入创建提醒：{reminder.title}（{shift_label}）'
            )
            imported += 1

        if conflict_errors:
            db.session.rollback()
            return jsonify({
                'success': False,
                'error': '存在冲突，已回滚所有导入',
                'details': conflict_errors
            }), 409

        db.session.commit()
        return jsonify({
            'success': True,
            'data': {
                'imported': imported,
                'skipped': skipped,
                'total': len(rows)
            },
            'message': f'成功导入 {imported} 条，跳过 {len(skipped)} 条'
        })

    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': f'导入失败，已回滚: {str(e)}'}), 500

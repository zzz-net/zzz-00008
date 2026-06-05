import csv
import io
import json
from datetime import datetime
from flask import Blueprint, request, jsonify, g, make_response
from ..validators import validate_shift_data
from ..services.shift_service import (
    get_shifts, get_shift_detail, create_shift, update_shift, disable_shift,
    get_active_shifts_for_receiver, _check_time_overlap, _parse_dt
)
from ..services.history_service import add_history
from ..models import db, DutyShift
from ..routes.auth import ROLES

bp = Blueprint('shifts', __name__, url_prefix='/api/shifts')

SHIFT_MANAGE_PERMISSION = 'manage_shifts'


def get_current_role():
    return getattr(g, 'current_role', 'cs')


def get_current_user():
    return getattr(g, 'current_user', 'cs_demo')


def has_shift_permission():
    role = get_current_role()
    role_info = next((r for r in ROLES if r['role'] == role), None)
    if not role_info:
        return False
    return SHIFT_MANAGE_PERMISSION in role_info.get('permissions', [])


@bp.route('', methods=['GET'])
def list_shifts():
    date = request.args.get('date')
    is_active_str = request.args.get('is_active')
    is_active = None
    if is_active_str is not None:
        is_active = is_active_str.lower() in ('true', '1', 'yes')
    shifts = get_shifts(date=date, is_active=is_active)
    return jsonify({'success': True, 'data': shifts})


@bp.route('/active', methods=['GET'])
def list_active_shifts():
    shifts = get_active_shifts_for_receiver()
    return jsonify({'success': True, 'data': shifts})


@bp.route('/<int:shift_id>', methods=['GET'])
def get_shift(shift_id):
    result, error, status_code = get_shift_detail(shift_id)
    if error:
        return jsonify({'success': False, 'error': error}), status_code
    return jsonify({'success': True, 'data': result}), status_code


@bp.route('', methods=['POST'])
def create_shift_route():
    if not has_shift_permission():
        return jsonify({'success': False, 'error': '权限不足：只有管理员角色可以管理排班'}), 403

    data = request.get_json()
    if not data:
        return jsonify({'success': False, 'error': '请求体不能为空'}), 400

    valid, error = validate_shift_data(data)
    if not valid:
        return jsonify({'success': False, 'error': error}), 400

    result, error, status_code = create_shift(data, get_current_user())
    if error:
        return jsonify({'success': False, 'error': error}), status_code
    return jsonify({'success': True, 'data': result}), status_code


@bp.route('/<int:shift_id>', methods=['PUT'])
def update_shift_route(shift_id):
    if not has_shift_permission():
        return jsonify({'success': False, 'error': '权限不足：只有管理员角色可以管理排班'}), 403

    data = request.get_json()
    if not data:
        return jsonify({'success': False, 'error': '请求体不能为空'}), 400

    valid, error = validate_shift_data(data, for_update=True)
    if not valid:
        return jsonify({'success': False, 'error': error}), 400

    result, error, status_code = update_shift(shift_id, data, get_current_user())
    if error:
        return jsonify({'success': False, 'error': error}), status_code
    return jsonify({'success': True, 'data': result}), status_code


@bp.route('/<int:shift_id>/disable', methods=['POST'])
def disable_shift_route(shift_id):
    if not has_shift_permission():
        return jsonify({'success': False, 'error': '权限不足：只有管理员角色可以管理排班'}), 403

    result, error, status_code = disable_shift(shift_id, get_current_user())
    if error:
        return jsonify({'success': False, 'error': error}), status_code
    return jsonify({'success': True, 'data': result}), status_code


@bp.route('/export', methods=['GET'])
def export_shifts():
    date = request.args.get('date')
    fmt = request.args.get('format', 'csv')
    shifts = get_shifts(date=date)

    def shift_to_row(s):
        return {
            'ID': s['id'],
            '班次名称': s['name'],
            '值班人': s['duty_person'],
            '开始时间': s['start_time'].replace('T', ' ')[:19] if s.get('start_time') else '',
            '结束时间': s['end_time'].replace('T', ' ')[:19] if s.get('end_time') else '',
            '可接收严重级别': ','.join(s.get('allowed_severities', [])),
            '是否启用': '是' if s.get('is_active') else '否',
            '创建人': s.get('created_by', ''),
            '创建时间': s.get('created_at', '').replace('T', ' ')[:19] if s.get('created_at') else '',
            '更新时间': s.get('updated_at', '').replace('T', ' ')[:19] if s.get('updated_at') else ''
        }

    rows = [shift_to_row(s) for s in shifts]
    fieldnames = ['ID', '班次名称', '值班人', '开始时间', '结束时间', '可接收严重级别', '是否启用', '创建人', '创建时间', '更新时间']

    if fmt == 'json':
        output = json.dumps(rows, ensure_ascii=False, indent=2)
        response = make_response(output)
        response.headers['Content-Type'] = 'application/json; charset=utf-8'
        response.headers['Content-Disposition'] = 'attachment; filename=shifts.json'
        return response

    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(rows)
    response = make_response(output.getvalue())
    response.headers['Content-Type'] = 'text/csv; charset=utf-8-sig'
    response.headers['Content-Disposition'] = 'attachment; filename=shifts.csv'
    return response


@bp.route('/import', methods=['POST'])
def import_shifts():
    if not has_shift_permission():
        return jsonify({'success': False, 'error': '权限不足：只有管理员角色可以管理排班'}), 403

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

    required_cols = {'班次名称', '值班人', '开始时间', '结束时间'}
    headers = set(reader.fieldnames or [])
    missing = required_cols - headers
    if missing:
        return jsonify({'success': False, 'error': f'缺少必需列: {", ".join(sorted(missing))}'}), 400

    valid_severities = {'low', 'medium', 'high', 'critical'}
    rows = []
    errors = []
    for idx, row in enumerate(reader, start=2):
        name = (row.get('班次名称') or '').strip()
        duty_person = (row.get('值班人') or '').strip()
        start_str = (row.get('开始时间') or '').strip()
        end_str = (row.get('结束时间') or '').strip()
        sev_str = (row.get('可接收严重级别') or 'low,medium,high,critical').strip()
        active_str = (row.get('是否启用') or '是').strip()

        row_errors = []
        if not name:
            row_errors.append('班次名称为空')
        if not duty_person:
            row_errors.append('值班人为空')
        if not start_str:
            row_errors.append('开始时间为空')
        if not end_str:
            row_errors.append('结束时间为空')

        start_dt = None
        end_dt = None
        try:
            if start_str:
                start_dt = datetime.fromisoformat(start_str.replace(' ', 'T'))
        except Exception:
            row_errors.append(f'开始时间格式错误: {start_str}')
        try:
            if end_str:
                end_dt = datetime.fromisoformat(end_str.replace(' ', 'T'))
        except Exception:
            row_errors.append(f'结束时间格式错误: {end_str}')

        if start_dt and end_dt and end_dt <= start_dt:
            row_errors.append('结束时间必须晚于开始时间')

        sevs = [s.strip() for s in sev_str.split(',') if s.strip()]
        invalid_sevs = [s for s in sevs if s not in valid_severities]
        if invalid_sevs:
            row_errors.append(f'无效的严重级别: {", ".join(invalid_sevs)}')
        if not sevs:
            sevs = ['low', 'medium', 'high', 'critical']

        is_active = active_str not in ('否', 'false', '0', 'no', 'FALSE', 'NO')

        if row_errors:
            errors.append(f'第 {idx} 行: {"; ".join(row_errors)}')
            continue

        rows.append({
            'name': name,
            'duty_person': duty_person,
            'start_time': start_dt.isoformat(),
            'end_time': end_dt.isoformat(),
            'allowed_severities': sevs,
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

    existing_names = {s.name: s.id for s in DutyShift.query.all()}

    try:
        for r in rows:
            if r['name'] in existing_names:
                skipped.append(f'第 {r["line_no"]} 行: 班次名称「{r["name"]}」已存在，跳过')
                continue

            start_dt = _parse_dt(r['start_time'])
            end_dt = _parse_dt(r['end_time'])
            overlaps = _check_time_overlap(r['duty_person'], start_dt, end_dt)
            if overlaps:
                conflict_errors.append(f'第 {r["line_no"]} 行: 值班人 {r["duty_person"]} 时间冲突 - {"；".join(overlaps)}')
                continue

            allowed_str = ','.join(r['allowed_severities'])
            shift = DutyShift(
                name=r['name'],
                duty_person=r['duty_person'],
                start_time=start_dt,
                end_time=end_dt,
                allowed_severities=allowed_str,
                is_active=r['is_active'],
                created_by=operator
            )
            db.session.add(shift)
            db.session.flush()
            add_history(
                'shift', shift.id, None,
                'active' if shift.is_active else 'inactive',
                operator,
                f'CSV 导入创建班次：{shift.name}，值班人：{shift.duty_person}'
            )
            imported += 1
            existing_names[r['name']] = shift.id

        if conflict_errors:
            db.session.rollback()
            return jsonify({
                'success': False,
                'error': '存在时间冲突，已回滚所有导入',
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

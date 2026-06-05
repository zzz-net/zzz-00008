import csv
import io
import json
from datetime import datetime
from flask import Blueprint, request, jsonify, g, make_response
from ..validators import validate_plan_data
from ..services.plan_service import (
    get_plans, get_plan_detail, get_plan_versions,
    create_plan, update_plan, disable_plan, enable_plan,
    reference_plan_on_ticket, match_plans_for_ticket
)
from ..services.history_service import add_history
from ..models import db, UpgradePlan
from ..routes.auth import ROLES

bp = Blueprint('plans', __name__, url_prefix='/api/plans')

PLAN_MANAGE_PERMISSION = 'manage_plans'
PLAN_VIEW_PERMISSION = 'view_plans'
PLAN_REFERENCE_PERMISSION = 'reference_plans'


def get_current_role():
    return getattr(g, 'current_role', 'cs')


def get_current_user():
    return getattr(g, 'current_user', 'cs_demo')


def _has_permission(permission: str) -> bool:
    role = get_current_role()
    role_info = next((r for r in ROLES if r['role'] == role), None)
    if not role_info:
        return False
    return permission in role_info.get('permissions', [])


def _severity_label_to_key(label: str) -> str | None:
    mapping = {
        '低危': 'low', '低': 'low', 'low': 'low',
        '中危': 'medium', '中': 'medium', 'medium': 'medium',
        '高危': 'high', '高': 'high', 'high': 'high',
        '严重': 'critical', '致命': 'critical', 'critical': 'critical'
    }
    return mapping.get(str(label).strip().lower())


def _severity_key_to_label(key: str) -> str:
    mapping = {'low': '低危', 'medium': '中危', 'high': '高危', 'critical': '严重'}
    return mapping.get(key, key)


@bp.route('', methods=['GET'])
def list_plans():
    if not _has_permission(PLAN_VIEW_PERMISSION):
        return jsonify({'success': False, 'error': '权限不足：无法查看预案库'}), 403

    severity = request.args.get('severity')
    is_active_str = request.args.get('is_active')
    keyword = request.args.get('keyword')
    customer_name = request.args.get('customer_name')
    title = request.args.get('title')
    only_latest_str = request.args.get('only_latest', 'true')

    is_active = None
    if is_active_str is not None:
        is_active = is_active_str.lower() in ('true', '1', 'yes')

    only_latest = only_latest_str.lower() in ('true', '1', 'yes')

    plans = get_plans(
        severity=severity,
        is_active=is_active,
        keyword=keyword,
        customer_name=customer_name,
        title=title,
        only_latest=only_latest
    )
    return jsonify({'success': True, 'data': plans})


@bp.route('/match', methods=['GET'])
def match_plans():
    if not _has_permission(PLAN_VIEW_PERMISSION):
        return jsonify({'success': False, 'error': '权限不足：无法查看预案库'}), 403

    customer_name = request.args.get('customer_name')
    severity = request.args.get('severity')
    progress = request.args.get('progress')

    plans = match_plans_for_ticket(
        customer_name=customer_name,
        severity=severity,
        progress=progress
    )
    return jsonify({'success': True, 'data': plans})


@bp.route('/<int:plan_id>', methods=['GET'])
def get_plan(plan_id):
    if not _has_permission(PLAN_VIEW_PERMISSION):
        return jsonify({'success': False, 'error': '权限不足：无法查看预案库'}), 403

    result, error, status_code = get_plan_detail(plan_id)
    if error:
        return jsonify({'success': False, 'error': error}), status_code
    return jsonify({'success': True, 'data': result}), status_code


@bp.route('/group/<plan_group_id>/versions', methods=['GET'])
def list_plan_versions(plan_group_id):
    if not _has_permission(PLAN_VIEW_PERMISSION):
        return jsonify({'success': False, 'error': '权限不足：无法查看预案库'}), 403

    versions = get_plan_versions(plan_group_id)
    return jsonify({'success': True, 'data': versions})


@bp.route('', methods=['POST'])
def create_plan_route():
    if not _has_permission(PLAN_MANAGE_PERMISSION):
        return jsonify({'success': False, 'error': '权限不足：只有管理员角色可以维护预案库'}), 403

    data = request.get_json()
    if not data:
        return jsonify({'success': False, 'error': '请求体不能为空'}), 400

    valid, error = validate_plan_data(data)
    if not valid:
        return jsonify({'success': False, 'error': error}), 400

    result, error, status_code = create_plan(data, get_current_user())
    if error:
        return jsonify({'success': False, 'error': error}), status_code
    return jsonify({'success': True, 'data': result}), status_code


@bp.route('/<int:plan_id>', methods=['PUT'])
def update_plan_route(plan_id):
    if not _has_permission(PLAN_MANAGE_PERMISSION):
        return jsonify({'success': False, 'error': '权限不足：只有管理员角色可以维护预案库'}), 403

    data = request.get_json()
    if not data:
        return jsonify({'success': False, 'error': '请求体不能为空'}), 400

    valid, error = validate_plan_data(data, for_update=True)
    if not valid:
        return jsonify({'success': False, 'error': error}), 400

    result, error, status_code = update_plan(plan_id, data, get_current_user())
    if error:
        return jsonify({'success': False, 'error': error}), status_code
    return jsonify({'success': True, 'data': result}), status_code


@bp.route('/<int:plan_id>/disable', methods=['POST'])
def disable_plan_route(plan_id):
    if not _has_permission(PLAN_MANAGE_PERMISSION):
        return jsonify({'success': False, 'error': '权限不足：只有管理员角色可以维护预案库'}), 403

    result, error, status_code = disable_plan(plan_id, get_current_user())
    if error:
        return jsonify({'success': False, 'error': error}), status_code
    return jsonify({'success': True, 'data': result}), status_code


@bp.route('/<int:plan_id>/enable', methods=['POST'])
def enable_plan_route(plan_id):
    if not _has_permission(PLAN_MANAGE_PERMISSION):
        return jsonify({'success': False, 'error': '权限不足：只有管理员角色可以维护预案库'}), 403

    result, error, status_code = enable_plan(plan_id, get_current_user())
    if error:
        return jsonify({'success': False, 'error': error}), status_code
    return jsonify({'success': True, 'data': result}), status_code


@bp.route('/<int:plan_id>/reference/<int:ticket_id>', methods=['POST'])
def reference_plan_route(plan_id, ticket_id):
    if not _has_permission(PLAN_REFERENCE_PERMISSION):
        return jsonify({'success': False, 'error': '权限不足：无法引用预案'}), 403

    result, error, status_code = reference_plan_on_ticket(ticket_id, plan_id, get_current_user())
    if error:
        return jsonify({'success': False, 'error': error}), status_code
    return jsonify({'success': True, 'data': result}), status_code


@bp.route('/export', methods=['GET'])
def export_plans():
    if not _has_permission(PLAN_MANAGE_PERMISSION):
        return jsonify({'success': False, 'error': '权限不足：只有管理员角色可以导出预案'}), 403

    severity = request.args.get('severity')
    is_active_str = request.args.get('is_active')
    fmt = request.args.get('format', 'csv')

    is_active = None
    if is_active_str is not None:
        is_active = is_active_str.lower() in ('true', '1', 'yes')

    plans = get_plans(severity=severity, is_active=is_active, only_latest=False)

    def plan_to_row(p):
        return {
            '预案标题': p['title'],
            '适用严重级别': _severity_key_to_label(p['applicable_severity']),
            '关键词': '、'.join(p.get('keywords', [])),
            '处理步骤': p.get('steps', ''),
            '负责人建议': p.get('assignee_suggestion', ''),
            '是否启用': '是' if p.get('is_active') else '否',
            '版本号': p.get('version', 1),
            '创建人': p.get('created_by', ''),
            '创建时间': p.get('created_at', '').replace('T', ' ')[:19] if p.get('created_at') else '',
            '更新时间': p.get('updated_at', '').replace('T', ' ')[:19] if p.get('updated_at') else ''
        }

    rows = [plan_to_row(p) for p in plans]
    fieldnames = [
        '预案标题', '适用严重级别', '关键词', '处理步骤', '负责人建议',
        '是否启用', '版本号', '创建人', '创建时间', '更新时间'
    ]

    if fmt == 'json':
        output = json.dumps(rows, ensure_ascii=False, indent=2)
        response = make_response(output)
        response.headers['Content-Type'] = 'application/json; charset=utf-8'
        response.headers['Content-Disposition'] = 'attachment; filename=upgrade_plans.json'
        return response

    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(rows)
    response = make_response(output.getvalue())
    response.headers['Content-Type'] = 'text/csv; charset=utf-8-sig'
    response.headers['Content-Disposition'] = 'attachment; filename=upgrade_plans.csv'
    return response


@bp.route('/import', methods=['POST'])
def import_plans():
    if not _has_permission(PLAN_MANAGE_PERMISSION):
        return jsonify({'success': False, 'error': '权限不足：只有管理员角色可以导入预案'}), 403

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

    required_cols = {'预案标题', '适用严重级别', '关键词', '处理步骤'}
    headers = set(reader.fieldnames or [])
    missing = required_cols - headers
    if missing:
        return jsonify({'success': False, 'error': f'缺少必需列: {", ".join(sorted(missing))}'}), 400

    valid_severities = {'low', 'medium', 'high', 'critical'}
    rows = []
    errors = []

    for idx, row in enumerate(reader, start=2):
        title = (row.get('预案标题') or '').strip()
        severity_label = (row.get('适用严重级别') or '').strip()
        kw_raw = (row.get('关键词') or '').strip()
        steps = (row.get('处理步骤') or '').strip()
        assignee = (row.get('负责人建议') or '').strip()
        active_str = (row.get('是否启用') or '是').strip()

        row_errors = []
        if not title:
            row_errors.append('预案标题为空')
        if not severity_label:
            row_errors.append('适用严重级别为空')
        if not kw_raw:
            row_errors.append('关键词为空')
        if not steps:
            row_errors.append('处理步骤为空')

        severity_key = _severity_label_to_key(severity_label) if severity_label else None
        if severity_label and not severity_key:
            row_errors.append(f'无效的严重级别: {severity_label}（应为：低危/中危/高危/严重）')
        if severity_key and severity_key not in valid_severities:
            row_errors.append(f'无效的严重级别: {severity_label}')

        keywords = []
        if kw_raw:
            separators = ['、', ',', '，', ';', '；', '/', '|']
            tmp = kw_raw
            for sep in separators[1:]:
                tmp = tmp.replace(sep, separators[0])
            keywords = [k.strip() for k in tmp.split('、') if k.strip()]
            if not keywords:
                row_errors.append('关键词解析后为空')

        is_active = active_str not in ('否', 'false', '0', 'no', 'FALSE', 'NO')

        if row_errors:
            errors.append(f'第 {idx} 行：{"；".join(row_errors)}')
            continue

        rows.append({
            'title': title,
            'applicable_severity': severity_key,
            'keywords': keywords,
            'steps': steps,
            'assignee_suggestion': assignee or None,
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

    try:
        existing_groups_to_check = set()
        existing_severity_kws = {}

        all_active_latest = UpgradePlan.query.filter(
            UpgradePlan.is_active.is_(True),
            UpgradePlan.is_latest.is_(True)
        ).all()
        for p in all_active_latest:
            key = p.applicable_severity
            if key not in existing_severity_kws:
                existing_severity_kws[key] = {}
            kws = tuple(sorted([k.strip().lower() for k in (p.keywords or '').split(',') if k.strip()]))
            existing_severity_kws[key][kws] = p.title

        for r in rows:
            kw_tuple = tuple(sorted([k.strip().lower() for k in r['keywords']]))
            existing_title = existing_severity_kws.get(r['applicable_severity'], {}).get(kw_tuple)
            if existing_title:
                skipped.append(f'第 {r["line_no"]} 行：级别「{r["applicable_severity"]}」下关键词组合已存在（预案：{existing_title}），跳过')
                continue

            plan_group_id = f"plan_{__import__('uuid').uuid4().hex[:12]}"
            plan = UpgradePlan(
                plan_group_id=plan_group_id,
                title=r['title'],
                applicable_severity=r['applicable_severity'],
                keywords=','.join(r['keywords']),
                steps=r['steps'],
                assignee_suggestion=r['assignee_suggestion'],
                is_active=r['is_active'],
                version=1,
                is_latest=True,
                created_by=operator
            )
            db.session.add(plan)
            db.session.flush()

            add_history(
                'plan', plan.id, None,
                'active' if plan.is_active else 'inactive',
                operator,
                f'CSV 导入创建预案：{plan.title}（级别：{plan.applicable_severity}，v1）'
            )
            imported += 1

            if r['is_active']:
                key = r['applicable_severity']
                if key not in existing_severity_kws:
                    existing_severity_kws[key] = {}
                existing_severity_kws[key][kw_tuple] = r['title']

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

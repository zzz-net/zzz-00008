import uuid
from datetime import datetime
from sqlalchemy import and_, or_
from ..models import db, UpgradePlan
from .history_service import add_history


def _generate_plan_group_id() -> str:
    return f"plan_{uuid.uuid4().hex[:12]}"


def _normalize_keywords(keywords: list[str]) -> list[str]:
    return sorted(list({kw.strip().lower() for kw in keywords if kw and kw.strip()}))


def _keywords_str_to_list(kw_str: str) -> list[str]:
    if not kw_str:
        return []
    return [k.strip() for k in kw_str.split(',') if k.strip()]


def _check_keyword_conflict(
    severity: str,
    keywords: list[str],
    exclude_group_id: str | None = None
) -> list[str]:
    normalized = _normalize_keywords(keywords)
    if not normalized:
        return []

    active_plans = UpgradePlan.query.filter(
        UpgradePlan.applicable_severity == severity,
        UpgradePlan.is_active.is_(True),
        UpgradePlan.is_latest.is_(True)
    ).all()

    conflicts = []
    for plan in active_plans:
        if exclude_group_id and plan.plan_group_id == exclude_group_id:
            continue
        plan_kws = _normalize_keywords(_keywords_str_to_list(plan.keywords))
        if plan_kws and set(plan_kws) == set(normalized):
            conflicts.append(
                f"同级别（{severity}）下已存在启用预案「{plan.title}」(v{plan.version})使用完全相同的关键词"
            )
    return conflicts


def get_plans(
    severity: str | None = None,
    is_active: bool | None = None,
    keyword: str | None = None,
    customer_name: str | None = None,
    title: str | None = None,
    only_latest: bool = True
) -> list[dict]:
    query = UpgradePlan.query

    if only_latest:
        query = query.filter(UpgradePlan.is_latest.is_(True))

    if severity is not None:
        query = query.filter(UpgradePlan.applicable_severity == severity)

    if is_active is not None:
        query = query.filter(UpgradePlan.is_active.is_(is_active))

    if keyword:
        kw_lower = keyword.lower().strip()
        query = query.filter(UpgradePlan.keywords.like(f'%{kw_lower}%'))

    if title:
        query = query.filter(UpgradePlan.title.like(f'%{title}%'))

    if customer_name:
        cn_lower = customer_name.lower().strip()
        query = query.filter(
            or_(
                UpgradePlan.title.like(f'%{cn_lower}%'),
                UpgradePlan.keywords.like(f'%{cn_lower}%')
            )
        )

    plans = query.order_by(UpgradePlan.updated_at.desc()).all()
    return [p.to_dict() for p in plans]


def get_plan_detail(plan_id: int) -> tuple[dict | None, str | None, int]:
    plan = UpgradePlan.query.get(plan_id)
    if not plan:
        return None, '预案不存在', 404
    return plan.to_dict(), None, 200


def get_plan_versions(plan_group_id: str) -> list[dict]:
    versions = UpgradePlan.query.filter(
        UpgradePlan.plan_group_id == plan_group_id
    ).order_by(UpgradePlan.version.desc()).all()
    return [v.to_dict() for v in versions]


def create_plan(data: dict, operator: str) -> tuple[dict | None, str | None, int]:
    normalized_kws = _normalize_keywords(data['keywords'])
    if not normalized_kws:
        return None, '关键词不能为空或全部为空字符串', 400

    conflicts = _check_keyword_conflict(data['applicable_severity'], normalized_kws)
    if conflicts:
        return None, '; '.join(conflicts), 409

    plan_group_id = _generate_plan_group_id()
    plan = UpgradePlan(
        plan_group_id=plan_group_id,
        title=data['title'].strip(),
        applicable_severity=data['applicable_severity'],
        keywords=','.join(normalized_kws),
        steps=data['steps'].strip(),
        assignee_suggestion=(data.get('assignee_suggestion') or '').strip() or None,
        is_active=data.get('is_active', True),
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
        f'创建预案：{plan.title}（级别：{plan.applicable_severity}，v1）'
    )
    db.session.commit()
    return plan.to_dict(), None, 201


def update_plan(plan_id: int, data: dict, operator: str) -> tuple[dict | None, str | None, int]:
    old_plan = UpgradePlan.query.get(plan_id)
    if not old_plan:
        return None, '预案不存在', 404
    if not old_plan.is_latest:
        return None, '只能编辑最新版本的预案', 400

    new_title = data.get('title', old_plan.title).strip()
    new_severity = data.get('applicable_severity', old_plan.applicable_severity)
    if 'keywords' in data:
        new_kws = _normalize_keywords(data['keywords'])
    else:
        new_kws = _normalize_keywords(_keywords_str_to_list(old_plan.keywords))
    new_steps = data.get('steps', old_plan.steps).strip()
    new_assignee = data.get('assignee_suggestion')
    if new_assignee is not None:
        new_assignee = new_assignee.strip() or None
    new_is_active = data.get('is_active', old_plan.is_active)

    if not new_kws:
        return None, '关键词不能为空或全部为空字符串', 400

    conflicts = _check_keyword_conflict(
        new_severity, new_kws, exclude_group_id=old_plan.plan_group_id
    )
    if conflicts:
        return None, '; '.join(conflicts), 409

    old_plan.is_latest = False
    db.session.flush()

    new_version = old_plan.version + 1
    new_plan = UpgradePlan(
        plan_group_id=old_plan.plan_group_id,
        title=new_title,
        applicable_severity=new_severity,
        keywords=','.join(new_kws),
        steps=new_steps,
        assignee_suggestion=new_assignee,
        is_active=new_is_active,
        version=new_version,
        is_latest=True,
        created_by=operator
    )
    db.session.add(new_plan)
    db.session.flush()

    add_history(
        'plan', new_plan.id,
        f'v{old_plan.version}', f'v{new_version}',
        operator,
        f'编辑预案，生成新版本：{new_title}（级别：{new_severity}，v{new_version}）'
    )
    db.session.commit()
    return new_plan.to_dict(), None, 200


def disable_plan(plan_id: int, operator: str) -> tuple[dict | None, str | None, int]:
    plan = UpgradePlan.query.get(plan_id)
    if not plan:
        return None, '预案不存在', 404
    if not plan.is_latest:
        return None, '只能停用最新版本的预案', 400
    if not plan.is_active:
        return None, '预案已经是停用状态', 400

    plan.is_active = False
    db.session.flush()

    add_history(
        'plan', plan.id, 'active', 'inactive',
        operator,
        f'停用预案：{plan.title}（v{plan.version}）'
    )
    db.session.commit()
    return plan.to_dict(), None, 200


def enable_plan(plan_id: int, operator: str) -> tuple[dict | None, str | None, int]:
    plan = UpgradePlan.query.get(plan_id)
    if not plan:
        return None, '预案不存在', 404
    if not plan.is_latest:
        return None, '只能启用最新版本的预案', 400
    if plan.is_active:
        return None, '预案已经是启用状态', 400

    kws = _normalize_keywords(_keywords_str_to_list(plan.keywords))
    conflicts = _check_keyword_conflict(
        plan.applicable_severity, kws, exclude_group_id=plan.plan_group_id
    )
    if conflicts:
        return None, '; '.join(conflicts), 409

    plan.is_active = True
    db.session.flush()

    add_history(
        'plan', plan.id, 'inactive', 'active',
        operator,
        f'启用预案：{plan.title}（v{plan.version}）'
    )
    db.session.commit()
    return plan.to_dict(), None, 200


def reference_plan_on_ticket(
    ticket_id: int,
    plan_id: int,
    operator: str
) -> tuple[dict | None, str | None, int]:
    from ..models import Ticket

    ticket = Ticket.query.get(ticket_id)
    if not ticket:
        return None, '升级单不存在', 404

    plan = UpgradePlan.query.get(plan_id)
    if not plan:
        return None, '预案不存在', 404
    if not plan.is_active:
        return None, '只能引用启用状态的预案', 400
    if not plan.is_latest:
        return None, '只能引用最新版本的预案', 400

    add_history(
        'ticket', ticket_id, None, 'plan_referenced',
        operator,
        f'引用预案：{plan.title}（v{plan.version}，ID:{plan.id}，级别：{plan.applicable_severity}）'
    )
    db.session.commit()

    return {
        'plan': plan.to_dict(),
        'referenced_at': datetime.utcnow().isoformat(),
        'operator': operator
    }, None, 200


def match_plans_for_ticket(
    customer_name: str | None = None,
    severity: str | None = None,
    progress: str | None = None
) -> list[dict]:
    query = UpgradePlan.query.filter(
        UpgradePlan.is_active.is_(True),
        UpgradePlan.is_latest.is_(True)
    )

    if severity:
        query = query.filter(UpgradePlan.applicable_severity == severity)

    plans = query.all()
    results = []

    search_terms = []
    if customer_name:
        search_terms.append(customer_name.lower())
    if progress:
        search_terms.append(progress.lower())
    combined_search = ' '.join(search_terms)

    for plan in plans:
        kws = _keywords_str_to_list(plan.keywords)
        score = 0
        matched_kws = []
        for kw in kws:
            kw_lower = kw.lower()
            if combined_search and (kw_lower in combined_search or kw_lower in customer_name.lower() if customer_name else False):
                score += 10
                matched_kws.append(kw)
            elif customer_name and kw_lower in customer_name.lower():
                score += 5
                matched_kws.append(kw)

        if severity and plan.applicable_severity == severity:
            score += 3

        if score > 0 or (severity and plan.applicable_severity == severity):
            plan_dict = plan.to_dict()
            plan_dict['match_score'] = score
            plan_dict['matched_keywords'] = matched_kws
            results.append(plan_dict)

    results.sort(key=lambda p: (-p['match_score'], p['applicable_severity']))
    return results

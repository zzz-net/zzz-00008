from datetime import datetime
from typing import Tuple, Optional


def validate_ticket_data(data: dict) -> Tuple[bool, Optional[str]]:
    required_fields = ['customer_name', 'severity', 'assignee', 'deadline']
    for field in required_fields:
        if field not in data or not str(data[field]).strip():
            return False, f'缺少必填字段: {field}'

    valid_severities = ['low', 'medium', 'high', 'critical']
    if data['severity'] not in valid_severities:
        return False, f'严重级别必须是: {", ".join(valid_severities)}'

    try:
        datetime.fromisoformat(str(data['deadline']).replace('Z', '+00:00'))
    except (ValueError, TypeError):
        return False, '截止时间格式不正确，请使用 ISO 格式 (YYYY-MM-DDTHH:MM:SS)'

    return True, None


def validate_batch_data(data: dict) -> Tuple[bool, Optional[str]]:
    required_fields = ['name', 'ticket_ids', 'handover_person']
    for field in required_fields:
        if field not in data:
            return False, f'缺少必填字段: {field}'

    if not isinstance(data['ticket_ids'], list) or len(data['ticket_ids']) == 0:
        return False, 'ticket_ids 必须是非空列表'

    if not all(isinstance(tid, int) for tid in data['ticket_ids']):
        return False, 'ticket_ids 中的元素必须是整数'

    return True, None


def validate_shift_data(data: dict, for_update: bool = False) -> Tuple[bool, Optional[str]]:
    if not for_update:
        required_fields = ['name', 'duty_person', 'start_time', 'end_time']
        for field in required_fields:
            if field not in data or not str(data[field]).strip():
                return False, f'缺少必填字段: {field}'

    if 'name' in data and not str(data['name']).strip():
        return False, '班次名称不能为空'

    if 'duty_person' in data and not str(data['duty_person']).strip():
        return False, '值班人不能为空'

    valid_severities = ['low', 'medium', 'high', 'critical']
    if 'allowed_severities' in data:
        sevs = data['allowed_severities']
        if not isinstance(sevs, list) or len(sevs) == 0:
            return False, 'allowed_severities 必须是非空列表'
        for s in sevs:
            if s not in valid_severities:
                return False, f'严重级别必须是: {", ".join(valid_severities)}'

    start_dt = None
    end_dt = None
    try:
        if 'start_time' in data and data['start_time']:
            start_dt = datetime.fromisoformat(str(data['start_time']).replace('Z', '+00:00'))
        if 'end_time' in data and data['end_time']:
            end_dt = datetime.fromisoformat(str(data['end_time']).replace('Z', '+00:00'))
    except (ValueError, TypeError):
        return False, '时间格式不正确，请使用 ISO 格式 (YYYY-MM-DDTHH:MM:SS)'

    if start_dt and end_dt and end_dt <= start_dt:
        return False, '结束时间必须晚于开始时间'

    return True, None


def validate_reminder_data(data: dict, for_update: bool = False) -> Tuple[bool, Optional[str]]:
    if not for_update:
        required_fields = ['title', 'content', 'effective_start', 'effective_end']
        for field in required_fields:
            if field not in data or not str(data[field]).strip():
                return False, f'缺少必填字段: {field}'

    if 'title' in data and not str(data['title']).strip():
        return False, '提醒标题不能为空'

    if 'content' in data and not str(data['content']).strip():
        return False, '提醒内容不能为空'

    start_dt = None
    end_dt = None
    try:
        if 'effective_start' in data and data['effective_start']:
            start_dt = datetime.fromisoformat(str(data['effective_start']).replace('Z', '+00:00'))
        if 'effective_end' in data and data['effective_end']:
            end_dt = datetime.fromisoformat(str(data['effective_end']).replace('Z', '+00:00'))
    except (ValueError, TypeError):
        return False, '有效时间格式不正确，请使用 ISO 格式 (YYYY-MM-DDTHH:MM:SS)'

    if start_dt and end_dt and end_dt <= start_dt:
        return False, '结束时间必须晚于开始时间'

    shift_date = None
    if 'shift_date' in data and data['shift_date']:
        try:
            shift_date = datetime.fromisoformat(str(data['shift_date']).replace('Z', '+00:00'))
        except (ValueError, TypeError):
            return False, '班次日期格式不正确'

    if 'shift_id' in data and data['shift_id'] is not None:
        try:
            int(data['shift_id'])
        except (ValueError, TypeError):
            return False, '关联班次 ID 格式不正确'

    return True, None


def validate_plan_data(data: dict, for_update: bool = False) -> Tuple[bool, Optional[str]]:
    if not for_update:
        required_fields = ['title', 'applicable_severity', 'keywords', 'steps']
        for field in required_fields:
            if field not in data:
                return False, f'缺少必填字段: {field}'
            if field == 'keywords':
                if not isinstance(data[field], list) or len(data[field]) == 0:
                    return False, '关键词必须是非空列表'
            elif not str(data[field]).strip():
                return False, f'缺少必填字段: {field}'

    if 'title' in data and not str(data['title']).strip():
        return False, '预案标题不能为空'

    valid_severities = ['low', 'medium', 'high', 'critical']
    if 'applicable_severity' in data and data['applicable_severity'] not in valid_severities:
        return False, f'适用严重级别必须是: {", ".join(valid_severities)}'

    if 'keywords' in data:
        if not isinstance(data['keywords'], list):
            return False, '关键词必须是列表'
        if len(data['keywords']) == 0:
            return False, '至少需要一个关键词'
        for kw in data['keywords']:
            if not isinstance(kw, str) or not kw.strip():
                return False, '关键词不能包含空字符串'

    if 'steps' in data and not str(data['steps']).strip():
        return False, '处理步骤不能为空'

    return True, None

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

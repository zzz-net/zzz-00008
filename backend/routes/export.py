import csv
import io
import json
from flask import Blueprint, request, jsonify, make_response
from ..models import Ticket, HandoverBatch
from ..services.ticket_service import check_overdue_tickets

bp = Blueprint('export', __name__, url_prefix='/api/export')


def ticket_to_row(ticket):
    return {
        'ID': ticket.id,
        '客户名称': ticket.customer_name,
        '严重级别': ticket.severity,
        '责任人': ticket.assignee,
        '截止时间': ticket.deadline.strftime('%Y-%m-%d %H:%M:%S') if ticket.deadline else '',
        '进展': ticket.progress or '',
        '状态': ticket.status,
        '创建人': ticket.created_by,
        '创建时间': ticket.created_at.strftime('%Y-%m-%d %H:%M:%S') if ticket.created_at else '',
        '更新时间': ticket.updated_at.strftime('%Y-%m-%d %H:%M:%S') if ticket.updated_at else ''
    }


def batch_to_row(batch):
    return {
        'ID': batch.id,
        '批次名称': batch.name,
        '描述': batch.description or '',
        '状态': batch.status,
        '交班人': batch.handover_person,
        '接班人': batch.receiver_person or '',
        '接班人显示名': batch.receiver_person_display or '',
        '原确认人': batch.original_confirmer or '',
        '工单数量': len(batch.tickets),
        '创建时间': batch.created_at.strftime('%Y-%m-%d %H:%M:%S') if batch.created_at else '',
        '确认时间': batch.confirmed_at.strftime('%Y-%m-%d %H:%M:%S') if batch.confirmed_at else '',
        '是否已撤销': '是' if batch.revoked_at else '否',
        '撤销人': batch.revoked_by or '',
        '撤销时间': batch.revoked_at.strftime('%Y-%m-%d %H:%M:%S') if batch.revoked_at else '',
        '撤销原因': batch.revoke_reason or '',
        '撤销前状态': batch.revoke_old_status or '',
        '撤销后状态': batch.revoke_new_status or '',
        '关联工单ID': ','.join([str(t.id) for t in batch.tickets])
    }


@bp.route('/tickets', methods=['GET'])
def export_tickets():
    check_overdue_tickets()

    fmt = request.args.get('format', 'csv')
    status = request.args.get('status')
    severity = request.args.get('severity')

    query = Ticket.query
    if status:
        query = query.filter(Ticket.status == status)
    if severity:
        query = query.filter(Ticket.severity == severity)

    tickets = query.order_by(Ticket.created_at.desc()).all()
    data = [ticket_to_row(t) for t in tickets]

    if fmt == 'json':
        output = json.dumps(data, ensure_ascii=False, indent=2)
        response = make_response(output)
        response.headers['Content-Type'] = 'application/json; charset=utf-8'
        response.headers['Content-Disposition'] = 'attachment; filename=tickets.json'
        return response

    output = io.StringIO()
    fieldnames = ['ID', '客户名称', '严重级别', '责任人', '截止时间', '进展', '状态', '创建人', '创建时间', '更新时间']
    writer = csv.DictWriter(output, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(data)

    response = make_response(output.getvalue())
    response.headers['Content-Type'] = 'text/csv; charset=utf-8-sig'
    response.headers['Content-Disposition'] = 'attachment; filename=tickets.csv'
    return response


@bp.route('/batches', methods=['GET'])
def export_batches():
    fmt = request.args.get('format', 'csv')
    status = request.args.get('status')
    is_revoked_str = request.args.get('is_revoked')

    query = HandoverBatch.query
    if status:
        query = query.filter(HandoverBatch.status == status)
    if is_revoked_str is not None:
        is_revoked = is_revoked_str.lower() == 'true'
        if is_revoked:
            query = query.filter(HandoverBatch.revoked_at.isnot(None))
        else:
            query = query.filter(HandoverBatch.revoked_at.is_(None))

    batches = query.order_by(HandoverBatch.created_at.desc()).all()
    data = [batch_to_row(b) for b in batches]

    if fmt == 'json':
        output = json.dumps(data, ensure_ascii=False, indent=2)
        response = make_response(output)
        response.headers['Content-Type'] = 'application/json; charset=utf-8'
        response.headers['Content-Disposition'] = 'attachment; filename=batches.json'
        return response

    output = io.StringIO()
    fieldnames = ['ID', '批次名称', '描述', '状态', '交班人', '接班人', '接班人显示名', '原确认人', '工单数量', '创建时间', '确认时间',
                  '是否已撤销', '撤销人', '撤销时间', '撤销原因', '撤销前状态', '撤销后状态', '关联工单ID']
    writer = csv.DictWriter(output, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(data)

    response = make_response(output.getvalue())
    response.headers['Content-Type'] = 'text/csv; charset=utf-8-sig'
    response.headers['Content-Disposition'] = 'attachment; filename=batches.csv'
    return response

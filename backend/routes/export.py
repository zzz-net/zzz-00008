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
        '工单数量': len(batch.tickets),
        '创建时间': batch.created_at.strftime('%Y-%m-%d %H:%M:%S') if batch.created_at else '',
        '确认时间': batch.confirmed_at.strftime('%Y-%m-%d %H:%M:%S') if batch.confirmed_at else ''
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

    query = HandoverBatch.query
    if status:
        query = query.filter(HandoverBatch.status == status)

    batches = query.order_by(HandoverBatch.created_at.desc()).all()
    data = [batch_to_row(b) for b in batches]

    if fmt == 'json':
        output = json.dumps(data, ensure_ascii=False, indent=2)
        response = make_response(output)
        response.headers['Content-Type'] = 'application/json; charset=utf-8'
        response.headers['Content-Disposition'] = 'attachment; filename=batches.json'
        return response

    output = io.StringIO()
    fieldnames = ['ID', '批次名称', '描述', '状态', '交班人', '接班人', '工单数量', '创建时间', '确认时间']
    writer = csv.DictWriter(output, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(data)

    response = make_response(output.getvalue())
    response.headers['Content-Type'] = 'text/csv; charset=utf-8-sig'
    response.headers['Content-Disposition'] = 'attachment; filename=batches.csv'
    return response

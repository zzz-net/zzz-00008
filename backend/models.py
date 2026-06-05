from datetime import datetime
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


class Ticket(db.Model):
    __tablename__ = 'ticket'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    customer_name = db.Column(db.String(200), nullable=False)
    severity = db.Column(db.String(20), nullable=False)
    assignee = db.Column(db.String(100), nullable=False)
    deadline = db.Column(db.DateTime, nullable=False)
    progress = db.Column(db.Text)
    status = db.Column(db.String(20), nullable=False, default='open')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by = db.Column(db.String(100), nullable=False)

    def to_dict(self):
        return {
            'id': self.id,
            'customer_name': self.customer_name,
            'severity': self.severity,
            'assignee': self.assignee,
            'deadline': self.deadline.isoformat() if self.deadline else None,
            'progress': self.progress,
            'status': self.status,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'created_by': self.created_by
        }


class HandoverBatch(db.Model):
    __tablename__ = 'handover_batch'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    status = db.Column(db.String(20), nullable=False, default='pending')
    handover_person = db.Column(db.String(100), nullable=False)
    receiver_person = db.Column(db.String(100))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    confirmed_at = db.Column(db.DateTime)

    tickets = db.relationship('Ticket', secondary='batch_ticket',
                              backref=db.backref('batches', lazy='dynamic'))

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'status': self.status,
            'handover_person': self.handover_person,
            'receiver_person': self.receiver_person,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'confirmed_at': self.confirmed_at.isoformat() if self.confirmed_at else None,
            'ticket_ids': [t.id for t in self.tickets]
        }


class BatchTicket(db.Model):
    __tablename__ = 'batch_ticket'

    batch_id = db.Column(db.Integer, db.ForeignKey('handover_batch.id', ondelete='CASCADE'), primary_key=True)
    ticket_id = db.Column(db.Integer, db.ForeignKey('ticket.id', ondelete='CASCADE'), primary_key=True)


class StatusHistory(db.Model):
    __tablename__ = 'status_history'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    entity_type = db.Column(db.String(20), nullable=False)
    entity_id = db.Column(db.Integer, nullable=False)
    old_status = db.Column(db.String(20))
    new_status = db.Column(db.String(20), nullable=False)
    operator = db.Column(db.String(100), nullable=False)
    reason = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'entity_type': self.entity_type,
            'entity_id': self.entity_id,
            'old_status': self.old_status,
            'new_status': self.new_status,
            'operator': self.operator,
            'reason': self.reason,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

from datetime import datetime
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


class DutyShift(db.Model):
    __tablename__ = 'duty_shift'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(200), nullable=False)
    duty_person = db.Column(db.String(100), nullable=False)
    start_time = db.Column(db.DateTime, nullable=False)
    end_time = db.Column(db.DateTime, nullable=False)
    allowed_severities = db.Column(db.String(200), nullable=False, default='low,medium,high,critical')
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by = db.Column(db.String(100), nullable=False)

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'duty_person': self.duty_person,
            'start_time': self.start_time.isoformat() if self.start_time else None,
            'end_time': self.end_time.isoformat() if self.end_time else None,
            'allowed_severities': self.allowed_severities.split(',') if self.allowed_severities else [],
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'created_by': self.created_by
        }


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
    receiver_person_display = db.Column(db.String(100))
    original_confirmer = db.Column(db.String(100))
    shift_id = db.Column(db.Integer, db.ForeignKey('duty_shift.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    confirmed_at = db.Column(db.DateTime)
    revoked_at = db.Column(db.DateTime)
    revoked_by = db.Column(db.String(100))
    revoke_reason = db.Column(db.Text)
    revoke_old_status = db.Column(db.String(20))
    revoke_new_status = db.Column(db.String(20))

    shift = db.relationship('DutyShift', backref=db.backref('batches', lazy='dynamic'))
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
            'receiver_person_display': self.receiver_person_display,
            'original_confirmer': self.original_confirmer,
            'shift_id': self.shift_id,
            'shift_name': self.shift.name if self.shift else None,
            'shift_duty_person': self.shift.duty_person if self.shift else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'confirmed_at': self.confirmed_at.isoformat() if self.confirmed_at else None,
            'revoked_at': self.revoked_at.isoformat() if self.revoked_at else None,
            'revoked_by': self.revoked_by,
            'revoke_reason': self.revoke_reason,
            'revoke_old_status': self.revoke_old_status,
            'revoke_new_status': self.revoke_new_status,
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


class DutyReminder(db.Model):
    __tablename__ = 'duty_reminder'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    title = db.Column(db.String(200), nullable=False)
    content = db.Column(db.Text, nullable=False)
    shift_id = db.Column(db.Integer, db.ForeignKey('duty_shift.id'), nullable=True)
    shift_date = db.Column(db.DateTime, nullable=True)
    effective_start = db.Column(db.DateTime, nullable=False)
    effective_end = db.Column(db.DateTime, nullable=False)
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by = db.Column(db.String(100), nullable=False)

    shift = db.relationship('DutyShift', backref=db.backref('reminders', lazy='dynamic'))
    confirmations = db.relationship(
        'DutyReminderConfirmation',
        backref='reminder',
        lazy='dynamic',
        cascade='all, delete-orphan'
    )

    def to_dict(self, include_confirmations=False):
        data = {
            'id': self.id,
            'title': self.title,
            'content': self.content,
            'shift_id': self.shift_id,
            'shift_name': self.shift.name if self.shift else None,
            'shift_duty_person': self.shift.duty_person if self.shift else None,
            'shift_date': self.shift_date.isoformat() if self.shift_date else None,
            'effective_start': self.effective_start.isoformat() if self.effective_start else None,
            'effective_end': self.effective_end.isoformat() if self.effective_end else None,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'created_by': self.created_by,
        }
        if include_confirmations:
            data['confirmations'] = [c.to_dict() for c in self.confirmations]
        return data


class DutyReminderConfirmation(db.Model):
    __tablename__ = 'duty_reminder_confirmation'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    reminder_id = db.Column(db.Integer, db.ForeignKey('duty_reminder.id', ondelete='CASCADE'), nullable=False)
    confirmed_by = db.Column(db.String(100), nullable=False)
    confirmed_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'reminder_id': self.reminder_id,
            'confirmed_by': self.confirmed_by,
            'confirmed_at': self.confirmed_at.isoformat() if self.confirmed_at else None
        }

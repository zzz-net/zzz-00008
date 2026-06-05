import os
from datetime import datetime, timedelta
from flask import Flask, send_from_directory, jsonify, request
from flask_cors import CORS

from .models import db, Ticket
from .routes.tickets import bp as tickets_bp
from .routes.batches import bp as batches_bp
from .routes.history import bp as history_bp
from .routes.export import bp as export_bp
from .routes.auth import bp as auth_bp
from .routes.dashboard import bp as dashboard_bp
from .routes.shifts import bp as shifts_bp
from .routes.reminders import bp as reminders_bp
from .routes.plans import bp as plans_bp


def create_app():
    dist_path = os.path.join(os.path.dirname(__file__), '..', 'dist')
    app = Flask(__name__, static_folder=dist_path, static_url_path='')
    app.secret_key = 'dev-secret-key-change-in-production'

    db_path = os.path.join(os.path.dirname(__file__), 'data.db')
    app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['JSON_AS_ASCII'] = False

    CORS(app, supports_credentials=True)

    db.init_app(app)

    app.register_blueprint(auth_bp)
    app.register_blueprint(tickets_bp)
    app.register_blueprint(batches_bp)
    app.register_blueprint(history_bp)
    app.register_blueprint(export_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(shifts_bp)
    app.register_blueprint(reminders_bp)
    app.register_blueprint(plans_bp)

    with app.app_context():
        db.create_all()
        init_sample_data()

    @app.errorhandler(404)
    def not_found(e):
        if request.path.startswith('/api/'):
            return jsonify({'error': 'Not Found'}), 404
        return send_from_directory(dist_path, 'index.html')

    return app


def init_sample_data():
    from .services.ticket_service import check_overdue_tickets

    if Ticket.query.count() == 0:
        now = datetime.utcnow()
        sample_tickets = [
            Ticket(
                customer_name='示例客户A',
                severity='high',
                assignee='张三',
                deadline=now + timedelta(days=2),
                progress='已联系客户，等待反馈',
                status='open',
                created_by='cs_demo'
            ),
            Ticket(
                customer_name='示例客户B',
                severity='critical',
                assignee='李四',
                deadline=now - timedelta(days=1),
                progress='紧急问题正在排查',
                status='overdue',
                created_by='cs_demo'
            ),
            Ticket(
                customer_name='示例客户C',
                severity='medium',
                assignee='王五',
                deadline=now + timedelta(days=5),
                progress='初步方案已确定',
                status='in_progress',
                created_by='cs_demo'
            )
        ]
        db.session.add_all(sample_tickets)
        db.session.commit()

    check_overdue_tickets()


if __name__ == '__main__':
    app = create_app()
    app.run(host='0.0.0.0', port=5000, debug=False)

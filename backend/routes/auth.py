from flask import Blueprint, request, jsonify, g, session

bp = Blueprint('auth', __name__, url_prefix='/api')

ROLES = [
    {
        'role': 'cs',
        'name': '普通客服',
        'permissions': ['view_tickets', 'create_tickets', 'update_progress', 'export_data', 'view_shifts', 'view_reminders', 'confirm_reminders']
    },
    {
        'role': 'handover',
        'name': '交班人',
        'permissions': ['view_tickets', 'create_batches', 'view_batches', 'export_data', 'view_shifts', 'view_reminders', 'confirm_reminders']
    },
    {
        'role': 'receiver',
        'name': '接班人',
        'permissions': [
            'view_tickets', 'confirm_batches', 'return_batches', 'view_batches', 'update_progress',
            'export_data', 'view_shifts', 'manage_shifts', 'view_reminders', 'manage_reminders', 'confirm_reminders'
        ]
    }
]

USERS = {
    'cs_demo': {'role': 'cs', 'name': '客服小王'},
    'handover_demo': {'role': 'handover', 'name': '交班老李'},
    'receiver_demo': {'role': 'receiver', 'name': '接班小张'}
}


@bp.before_app_request
def set_current_user():
    g.current_role = session.get('current_role', 'cs')
    g.current_user = session.get('current_user', 'cs_demo')


@bp.route('/roles', methods=['GET'])
def get_roles():
    return jsonify({'success': True, 'data': ROLES})


@bp.route('/current-role', methods=['GET'])
def get_current_role():
    user_info = USERS.get(g.current_user, {'role': g.current_role, 'name': g.current_user})
    return jsonify({
        'success': True,
        'data': {
            'role': g.current_role,
            'username': g.current_user,
            'name': user_info['name'],
            'permissions': next((r['permissions'] for r in ROLES if r['role'] == g.current_role), [])
        }
    })


@bp.route('/switch-role', methods=['POST'])
def switch_role():
    data = request.get_json() or {}
    role = data.get('role')
    username = data.get('username')

    if not role or not username:
        return jsonify({'success': False, 'error': '缺少角色或用户名'}), 400

    if role not in [r['role'] for r in ROLES]:
        return jsonify({'success': False, 'error': '无效的角色'}), 400

    session['current_role'] = role
    session['current_user'] = username
    g.current_role = role
    g.current_user = username

    user_info = USERS.get(username, {'role': role, 'name': username})
    return jsonify({
        'success': True,
        'data': {
            'role': role,
            'username': username,
            'name': user_info['name']
        },
        'message': f'已切换到 {user_info["name"]} ({role})'
    })


@bp.route('/users', methods=['GET'])
def get_users():
    return jsonify({'success': True, 'data': USERS})

"""
交接批次权限回归测试
测试场景：
1. 普通客服确认批次 - 应失败
2. 交班人确认批次 - 应失败
3. 接班人确认批次 - 应成功
4. 重复确认批次 - 应失败且不写重复历史
5. 普通客服退回批次 - 应失败
6. 交班人退回批次 - 应失败
7. 接班人退回批次 - 应成功
8. 普通客服撤销批次 - 应失败
9. 交班人撤销批次 - 应失败
10. 非原确认人撤销批次 - 应失败（冒名撤销防护）
11. 原确认人撤销已确认批次 - 应成功
12. 待确认批次撤销 - 应失败
13. 已退回批次撤销 - 应失败
14. 工单被新批次占用时撤销 - 应失败
15. 拒绝场景数据不变性验证 - 所有字段和历史记录保持不变
"""
import sys
import os

# 确保标准输出使用 UTF-8 编码，兼容 Windows 终端
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

PASS = '[PASS]'
FAIL = '[FAIL]'
INFO = '[INFO]'
ERROR = '[ERROR]'

DB_PATH = os.path.join('backend', 'data.db')


def cleanup_database():
    """清理数据库文件，失败时明确报错退出"""
    if os.path.exists(DB_PATH):
        try:
            os.remove(DB_PATH)
            print(f"{INFO} 已删除旧数据库文件")
        except PermissionError as e:
            print(f"\n{ERROR} 数据库文件被占用，无法删除: {DB_PATH}")
            print(f"{ERROR} 请先关闭正在运行的后端服务 (run_backend.py)，然后重试")
            print(f"{ERROR} 详细错误: {e}")
            sys.exit(2)
        except Exception as e:
            print(f"\n{ERROR} 删除数据库文件失败: {DB_PATH}")
            print(f"{ERROR} 详细错误: {e}")
            sys.exit(2)


def run_tests():
    # 延迟导入，确保数据库清理完成后再创建连接
    sys.path.insert(0, '.')
    from backend.app import create_app, init_sample_data
    from backend.models import db

    try:
        app = create_app()
        client = app.test_client()
    except Exception as e:
        print(f"\n{ERROR} 初始化 Flask 应用失败: {e}")
        sys.exit(3)

    print("=" * 60)
    print("交接批次权限漏洞回归测试")
    print("=" * 60)

    try:
        with app.app_context():
            db.drop_all()
            db.create_all()
            init_sample_data()
        print(f"{INFO} 数据库初始化完成")
    except Exception as e:
        print(f"\n{ERROR} 数据库初始化失败: {e}")
        print(f"{ERROR} 请确认数据库文件未被其他进程占用")
        sys.exit(3)

    passed = 0
    failed = 0

    def switch_role(role, username):
        resp = client.post('/api/switch-role', json={'role': role, 'username': username})
        if resp.status_code != 200:
            raise RuntimeError(f"切换角色失败: {role}/{username} -> {resp.status_code}")
        return resp.get_json()

    def get_history_count():
        resp = client.get('/api/history')
        data = resp.get_json()
        return len(data['data'])

    def create_test_batch(ticket_ids=None):
        switch_role('handover', 'handover_demo')
        if ticket_ids is None:
            resp = client.get('/api/tickets/open-for-handover')
            open_tickets = resp.get_json().get('data', [])
            if len(open_tickets) < 2:
                raise RuntimeError(f"可用工单不足，仅 {len(open_tickets)} 个")
            ticket_ids = [open_tickets[0]['id'], open_tickets[1]['id']]
        resp = client.post('/api/batches', json={
            'name': '权限测试批次',
            'description': '用于权限测试',
            'ticket_ids': ticket_ids,
            'handover_person': '交班老李'
        })
        if resp.status_code != 201:
            error = resp.get_json().get('error', '未知错误')
            raise RuntimeError(f"创建测试批次失败: {resp.status_code}, 错误: {error}")
        return resp.get_json()['data']['id']

    def check(condition, pass_msg, fail_msg):
        nonlocal passed, failed
        if condition:
            print(f"  {PASS} {pass_msg}")
            passed += 1
        else:
            print(f"  {FAIL} {fail_msg}")
            failed += 1

    try:
        # 创建额外的测试工单，确保后续测试有足够可用工单
        print("\n准备：创建额外测试工单")
        switch_role('cs', 'cs_demo')
        from datetime import datetime, timedelta
        try:
            deadline = (datetime.now(datetime.UTC) + timedelta(days=30)).isoformat()
        except Exception:
            deadline = (datetime.utcnow() + timedelta(days=30)).isoformat()
        for i in range(10):
            resp = client.post('/api/tickets', json={
                'customer_name': f'权限测试客户{i+10}',
                'severity': 'medium',
                'assignee': f'责任人{i+10}',
                'deadline': deadline,
                'progress': f'测试进展{i+10}'
            })
            if resp.status_code != 201:
                raise RuntimeError(f"创建测试工单失败: {resp.status_code}")
        print(f"  {PASS} 创建了 10 个额外测试工单")

        batch_id = create_test_batch()
        print(f"\n测试批次 ID: {batch_id}")

        history_before = get_history_count()
        print(f"测试前历史记录数: {history_before}")

        # ========== 测试 1: 普通客服确认批次 ==========
        print("\n" + "-" * 60)
        print("测试 1: 普通客服 (cs) 尝试确认批次")
        print("预期: 返回 403 权限错误，状态不变，不写历史")
        switch_role('cs', 'cs_demo')
        history_before_test = get_history_count()
        resp = client.post(f'/api/batches/{batch_id}/confirm', json={})
        data = resp.get_json()
        print(f"  状态码: {resp.status_code}")
        print(f"  错误信息: {data.get('error', '')}")

        check(resp.status_code == 403 and '权限不足' in data.get('error', ''),
              "正确返回 403 权限错误",
              f"预期 403，实际 {resp.status_code}")

        history_after = get_history_count()
        check(history_after == history_before_test,
              "没有新增历史记录",
              f"历史记录从 {history_before_test} 变为 {history_after}")

        resp = client.get(f'/api/batches/{batch_id}')
        batch_data = resp.get_json()['data']
        check(batch_data['status'] == 'pending',
              "批次状态仍为 pending",
              f"批次状态变为 {batch_data['status']}")
        check(batch_data['receiver_person'] is None,
              "接班人未被修改",
              f"接班人被修改为 {batch_data['receiver_person']}")

        # ========== 测试 2: 交班人确认批次 ==========
        print("\n" + "-" * 60)
        print("测试 2: 交班人 (handover) 尝试确认批次")
        print("预期: 返回 403 权限错误，状态不变，不写历史")
        switch_role('handover', 'handover_demo')
        history_before_test = get_history_count()
        resp = client.post(f'/api/batches/{batch_id}/confirm', json={})
        data = resp.get_json()
        print(f"  状态码: {resp.status_code}")
        print(f"  错误信息: {data.get('error', '')}")

        check(resp.status_code == 403 and '权限不足' in data.get('error', ''),
              "正确返回 403 权限错误",
              f"预期 403，实际 {resp.status_code}")

        history_after = get_history_count()
        check(history_after == history_before_test,
              "没有新增历史记录",
              f"历史记录从 {history_before_test} 变为 {history_after}")

        resp = client.get(f'/api/batches/{batch_id}')
        batch_data = resp.get_json()['data']
        check(batch_data['status'] == 'pending',
              "批次状态仍为 pending",
              f"批次状态变为 {batch_data['status']}")

        # ========== 测试 3: 接班人确认批次 ==========
        print("\n" + "-" * 60)
        print("测试 3: 接班人 (receiver) 确认批次")
        print("预期: 返回 200 成功，状态变为 confirmed，写历史")
        switch_role('receiver', 'receiver_demo')
        history_before_test = get_history_count()
        resp = client.post(f'/api/batches/{batch_id}/confirm', json={})
        data = resp.get_json()
        print(f"  状态码: {resp.status_code}")
        if resp.status_code == 200:
            print(f"  批次状态: {data['data']['status']}")

        check(resp.status_code == 200 and data.get('data', {}).get('status') == 'confirmed',
              "确认成功，状态变为 confirmed",
              f"预期 200，实际 {resp.status_code}")

        history_after = get_history_count()
        check(history_after == history_before_test + 1,
              "正确新增 1 条历史记录",
              f"历史记录从 {history_before_test} 变为 {history_after}，预期 +1")

        resp = client.get(f'/api/batches/{batch_id}')
        batch_data = resp.get_json()['data']
        check(batch_data['receiver_person'] in ('接班小张', 'receiver_demo'),
              f"接班人正确设置为 {batch_data['receiver_person']}",
              f"接班人为 {batch_data['receiver_person']}")
        check(batch_data['confirmed_at'] is not None,
              "确认时间已设置",
              "确认时间为空")

        # ========== 测试 4: 重复确认 ==========
        print("\n" + "-" * 60)
        print("测试 4: 接班人重复确认批次")
        print("预期: 返回 400 错误，不写重复历史")
        history_before_test = get_history_count()
        resp = client.post(f'/api/batches/{batch_id}/confirm', json={})
        data = resp.get_json()
        print(f"  状态码: {resp.status_code}")
        print(f"  错误信息: {data.get('error', '')}")

        check(resp.status_code == 400 and '重复确认' in data.get('error', ''),
              "正确返回 400 错误",
              f"预期 400，实际 {resp.status_code}")

        history_after = get_history_count()
        check(history_after == history_before_test,
              "没有重复写历史",
              f"历史记录从 {history_before_test} 变为 {history_after}")

        # ========== 测试 5: 创建新批次测试退回权限 ==========
        print("\n" + "-" * 60)
        print("创建新批次用于测试退回权限")
        batch_id2 = create_test_batch()
        print(f"新测试批次 ID: {batch_id2}")

        # 测试 5a: 普通客服退回批次
        print("\n测试 5a: 普通客服 (cs) 尝试退回批次")
        print("预期: 返回 403 权限错误")
        switch_role('cs', 'cs_demo')
        history_before_test = get_history_count()
        resp = client.post(f'/api/batches/{batch_id2}/return', json={'reason': '测试退回'})
        data = resp.get_json()
        print(f"  状态码: {resp.status_code}")
        print(f"  错误信息: {data.get('error', '')}")

        check(resp.status_code == 403 and '权限不足' in data.get('error', ''),
              "正确返回 403 权限错误",
              f"预期 403，实际 {resp.status_code}")

        history_after = get_history_count()
        check(history_after == history_before_test,
              "没有新增历史记录",
              f"历史记录从 {history_before_test} 变为 {history_after}")

        # 测试 5b: 交班人退回批次
        print("\n测试 5b: 交班人 (handover) 尝试退回批次")
        print("预期: 返回 403 权限错误")
        switch_role('handover', 'handover_demo')
        history_before_test = get_history_count()
        resp = client.post(f'/api/batches/{batch_id2}/return', json={'reason': '测试退回'})
        data = resp.get_json()
        print(f"  状态码: {resp.status_code}")
        print(f"  错误信息: {data.get('error', '')}")

        check(resp.status_code == 403 and '权限不足' in data.get('error', ''),
              "正确返回 403 权限错误",
              f"预期 403，实际 {resp.status_code}")

        history_after = get_history_count()
        check(history_after == history_before_test,
              "没有新增历史记录",
              f"历史记录从 {history_before_test} 变为 {history_after}")

        # 测试 5c: 接班人退回批次
        print("\n测试 5c: 接班人 (receiver) 退回批次")
        print("预期: 返回 200 成功")
        switch_role('receiver', 'receiver_demo')
        history_before_test = get_history_count()
        resp = client.post(f'/api/batches/{batch_id2}/return', json={'reason': '退回原因测试'})
        data = resp.get_json()
        print(f"  状态码: {resp.status_code}")

        check(resp.status_code == 200 and data.get('data', {}).get('status') == 'returned',
              "退回成功",
              f"预期 200，实际 {resp.status_code}")

        history_after = get_history_count()
        check(history_after == history_before_test + 1,
              "正确新增 1 条历史记录",
              f"历史记录从 {history_before_test} 变为 {history_after}")

        # ========== 测试 6: 撤销权限测试 ==========
        print("\n" + "-" * 60)
        print("创建新批次用于测试撤销权限")
        batch_id3 = create_test_batch()
        print(f"新测试批次 ID: {batch_id3}")

        # 先确认批次，使其进入 confirmed 状态
        print("\n准备：确认批次，记录原确认人")
        switch_role('receiver', 'receiver_demo')
        history_before_confirm = get_history_count()
        resp = client.post(f'/api/batches/{batch_id3}/confirm', json={'receiver_person': '接班小张'})
        check(resp.status_code == 200, "准备：确认批次成功", f"准备：确认批次失败 {resp.status_code}")

        resp = client.get(f'/api/batches/{batch_id3}')
        batch_data = resp.get_json()['data']
        original_confirmer = batch_data['original_confirmer']
        check(original_confirmer == 'receiver_demo',
              f"原确认人正确记录为 {original_confirmer}",
              f"原确认人错误: {original_confirmer}")

        def get_batch_snapshot(bid):
            """获取批次完整快照用于数据不变性验证"""
            resp = client.get(f'/api/batches/{bid}')
            data = resp.get_json()['data']
            return {
                'status': data['status'],
                'receiver_person': data.get('receiver_person'),
                'original_confirmer': data.get('original_confirmer'),
                'confirmed_at': data.get('confirmed_at'),
                'revoked_at': data.get('revoked_at'),
                'revoked_by': data.get('revoked_by'),
                'revoke_reason': data.get('revoke_reason'),
                'revoke_old_status': data.get('revoke_old_status'),
                'revoke_new_status': data.get('revoke_new_status'),
            }

        # 测试 6a: 普通客服撤销批次
        print("\n测试 6a: 普通客服 (cs) 尝试撤销批次")
        print("预期: 返回 403 权限错误，数据不变")
        switch_role('cs', 'cs_demo')
        snapshot_before = get_batch_snapshot(batch_id3)
        history_before_test = get_history_count()
        resp = client.post(f'/api/batches/{batch_id3}/revoke', json={'reason': '普通客服尝试撤销'})
        data = resp.get_json()
        print(f"  状态码: {resp.status_code}")
        print(f"  错误信息: {data.get('error', '')}")

        check(resp.status_code == 403 and '权限不足' in data.get('error', ''),
              "正确返回 403 权限错误",
              f"预期 403，实际 {resp.status_code}")

        history_after = get_history_count()
        check(history_after == history_before_test,
              "没有新增历史记录",
              f"历史记录从 {history_before_test} 变为 {history_after}")

        snapshot_after = get_batch_snapshot(batch_id3)
        check(snapshot_before == snapshot_after,
              "批次所有字段保持不变",
              f"数据被篡改: {snapshot_before} -> {snapshot_after}")

        # 测试 6b: 交班人撤销批次
        print("\n测试 6b: 交班人 (handover) 尝试撤销批次")
        print("预期: 返回 403 权限错误，数据不变")
        switch_role('handover', 'handover_demo')
        snapshot_before = get_batch_snapshot(batch_id3)
        history_before_test = get_history_count()
        resp = client.post(f'/api/batches/{batch_id3}/revoke', json={'reason': '交班人尝试撤销'})
        data = resp.get_json()
        print(f"  状态码: {resp.status_code}")
        print(f"  错误信息: {data.get('error', '')}")

        check(resp.status_code == 403 and '权限不足' in data.get('error', ''),
              "正确返回 403 权限错误",
              f"预期 403，实际 {resp.status_code}")

        history_after = get_history_count()
        check(history_after == history_before_test,
              "没有新增历史记录",
              f"历史记录从 {history_before_test} 变为 {history_after}")

        snapshot_after = get_batch_snapshot(batch_id3)
        check(snapshot_before == snapshot_after,
              "批次所有字段保持不变",
              f"数据被篡改: {snapshot_before} -> {snapshot_after}")

        # 测试 6c: 非原确认人撤销（冒名撤销防护）
        print("\n测试 6c: 非原确认人 (other_receiver) 尝试撤销批次")
        print("预期: 返回 403 权限错误，提示只有原确认人可以撤销")
        switch_role('receiver', 'other_receiver')
        snapshot_before = get_batch_snapshot(batch_id3)
        history_before_test = get_history_count()
        resp = client.post(f'/api/batches/{batch_id3}/revoke', json={
            'reason': '冒名尝试撤销',
            'receiver_person': 'receiver_demo'
        })
        data = resp.get_json()
        print(f"  状态码: {resp.status_code}")
        print(f"  错误信息: {data.get('error', '')}")

        check(resp.status_code == 403 and '只有原确认人可以撤销' in data.get('error', ''),
              "正确返回 403，提示原确认人限制",
              f"预期 403，实际 {resp.status_code}")

        check(original_confirmer in data.get('error', ''),
              f"错误信息包含正确的原确认人 {original_confirmer}",
              f"错误信息未提示正确原确认人: {data.get('error', '')}")

        history_after = get_history_count()
        check(history_after == history_before_test,
              "没有新增历史记录",
              f"历史记录从 {history_before_test} 变为 {history_after}")

        snapshot_after = get_batch_snapshot(batch_id3)
        check(snapshot_before == snapshot_after,
              "批次所有字段保持不变",
              f"数据被篡改: {snapshot_before} -> {snapshot_after}")

        # 测试 6d: 原确认人撤销已确认批次
        print("\n测试 6d: 原确认人 (receiver_demo) 撤销已确认批次")
        print("预期: 返回 200 成功，状态变为 pending，记录完整审计字段")
        switch_role('receiver', 'receiver_demo')
        snapshot_before = get_batch_snapshot(batch_id3)
        history_before_test = get_history_count()
        revoke_reason = '发现客户信息有误，需要重新核对交接内容'
        resp = client.post(f'/api/batches/{batch_id3}/revoke', json={'reason': revoke_reason})
        data = resp.get_json()
        print(f"  状态码: {resp.status_code}")
        if resp.status_code == 200:
            print(f"  状态: {data['data']['status']}")
            print(f"  撤销人: {data['data']['revoked_by']}")
            print(f"  原确认人: {data['data']['original_confirmer']}")

        check(resp.status_code == 200 and data.get('data', {}).get('status') == 'pending',
              "撤销成功，状态变为 pending",
              f"预期 200，实际 {resp.status_code}")

        check(data['data']['revoked_by'] == 'receiver_demo',
              "撤销人正确记录为会话用户",
              f"撤销人错误: {data['data'].get('revoked_by')}")

        check(data['data']['original_confirmer'] == 'receiver_demo',
              "原确认人字段保留",
              f"原确认人错误: {data['data'].get('original_confirmer')}")

        check(data['data']['revoke_reason'] == revoke_reason,
              "撤销原因正确记录",
              f"撤销原因错误: {data['data'].get('revoke_reason')}")

        check(data['data']['revoke_old_status'] == 'confirmed',
              "撤销前状态正确记录",
              f"撤销前状态错误: {data['data'].get('revoke_old_status')}")

        check(data['data']['revoke_new_status'] == 'pending',
              "撤销后状态正确记录",
              f"撤销后状态错误: {data['data'].get('revoke_new_status')}")

        check(data['data']['receiver_person'] is None,
              "接班人已清空",
              f"接班人未清空: {data['data'].get('receiver_person')}")

        check(data['data']['confirmed_at'] is None,
              "确认时间已清空",
              f"确认时间未清空: {data['data'].get('confirmed_at')}")

        check('affected_tickets' in data['data'],
              "返回数据包含受影响工单",
              "返回数据缺少受影响工单")

        history_after = get_history_count()
        check(history_after == history_before_test + 1,
              "正确新增 1 条历史记录",
              f"历史记录从 {history_before_test} 变为 {history_after}，预期 +1")

        # 测试 6e: 待确认批次撤销
        print("\n测试 6e: 待确认 (pending) 批次尝试撤销")
        print("预期: 返回 400 错误，数据不变")
        batch_id4 = create_test_batch()
        print(f"新测试批次 ID: {batch_id4} (状态: pending)")
        switch_role('receiver', 'receiver_demo')
        snapshot_before = get_batch_snapshot(batch_id4)
        history_before_test = get_history_count()
        resp = client.post(f'/api/batches/{batch_id4}/revoke', json={'reason': '尝试撤销待确认批次'})
        data = resp.get_json()
        print(f"  状态码: {resp.status_code}")
        print(f"  错误信息: {data.get('error', '')}")

        check(resp.status_code == 400 and '无需撤销' in data.get('error', ''),
              "正确返回 400 错误",
              f"预期 400，实际 {resp.status_code}")

        history_after = get_history_count()
        check(history_after == history_before_test,
              "没有新增历史记录",
              f"历史记录从 {history_before_test} 变为 {history_after}")

        snapshot_after = get_batch_snapshot(batch_id4)
        check(snapshot_before == snapshot_after,
              "批次所有字段保持不变",
              f"数据被篡改: {snapshot_before} -> {snapshot_after}")

        # 测试 6f: 已退回批次撤销
        print("\n测试 6f: 已退回 (returned) 批次尝试撤销")
        print("预期: 返回 400 错误，数据不变")
        switch_role('receiver', 'receiver_demo')
        resp = client.post(f'/api/batches/{batch_id4}/return', json={'reason': '测试退回'})
        check(resp.status_code == 200, "准备：退回批次成功", f"准备：退回批次失败 {resp.status_code}")

        snapshot_before = get_batch_snapshot(batch_id4)
        history_before_test = get_history_count()
        resp = client.post(f'/api/batches/{batch_id4}/revoke', json={'reason': '尝试撤销已退回批次'})
        data = resp.get_json()
        print(f"  状态码: {resp.status_code}")
        print(f"  错误信息: {data.get('error', '')}")

        check(resp.status_code == 400 and '不能撤销' in data.get('error', ''),
              "正确返回 400 错误",
              f"预期 400，实际 {resp.status_code}")

        history_after = get_history_count()
        check(history_after == history_before_test,
              "没有新增历史记录",
              f"历史记录从 {history_before_test} 变为 {history_after}")

        snapshot_after = get_batch_snapshot(batch_id4)
        check(snapshot_before == snapshot_after,
              "批次所有字段保持不变",
              f"数据被篡改: {snapshot_before} -> {snapshot_after}")

        # 测试 6g: 工单被新批次占用时撤销
        print("\n测试 6g: 工单被新待确认批次占用时撤销")
        print("预期: 返回 409 冲突错误，数据不变")
        batch_id5 = create_test_batch()
        print(f"新测试批次 ID: {batch_id5}")

        switch_role('receiver', 'receiver_demo')
        resp = client.post(f'/api/batches/{batch_id5}/confirm', json={'receiver_person': '接班小张'})
        check(resp.status_code == 200, "准备：确认批次成功", f"准备：确认批次失败 {resp.status_code}")

        # 获取 batch_id5 的第一个工单
        resp = client.get(f'/api/batches/{batch_id5}')
        batch5_tickets = resp.get_json()['data']['ticket_ids']
        first_ticket_id = batch5_tickets[0]
        print(f"  批次 {batch_id5} 包含工单: {batch5_tickets}")

        # 创建新批次（待确认状态），包含 batch_id5 的第一个工单
        # 此时 batch_id5 是 confirmed，所以工单 10 可以加入新批次
        switch_role('handover', 'handover_demo')
        resp = client.post('/api/batches', json={
            'name': '占用冲突测试批次',
            'ticket_ids': [first_ticket_id],
            'handover_person': '交班老李'
        })
        pending_batch_id = resp.get_json()['data']['id'] if resp.status_code == 201 else None
        check(pending_batch_id is not None, f"创建待确认批次成功，ID={pending_batch_id}", "创建待确认批次失败")
        print(f"  待确认批次 {pending_batch_id} 包含工单: [{first_ticket_id}]")

        # 现在尝试撤销 batch_id5（confirmed 状态）
        # 应该失败，因为 first_ticket_id 已经在 pending_batch_id（待确认）中
        switch_role('receiver', 'receiver_demo')
        snapshot_before = get_batch_snapshot(batch_id5)
        history_before_test = get_history_count()
        resp = client.post(f'/api/batches/{batch_id5}/revoke', json={'reason': '尝试撤销但工单已被占用'})
        data = resp.get_json()
        print(f"  状态码: {resp.status_code}")
        print(f"  错误信息: {data.get('error', '')}")

        check(resp.status_code == 409 and '已被新批次' in data.get('error', ''),
              "正确返回 409 冲突错误",
              f"预期 409，实际 {resp.status_code}")

        check(str(first_ticket_id) in data.get('error', ''),
              f"错误信息包含冲突工单 {first_ticket_id}",
              f"错误信息未包含冲突工单: {data.get('error', '')}")

        check(str(pending_batch_id) in data.get('error', ''),
              f"错误信息包含占用批次 ID {pending_batch_id}",
              f"错误信息未包含占用批次 ID: {data.get('error', '')}")

        history_after = get_history_count()
        check(history_after == history_before_test,
              "没有新增历史记录",
              f"历史记录从 {history_before_test} 变为 {history_after}")

        snapshot_after = get_batch_snapshot(batch_id5)
        check(snapshot_before == snapshot_after,
              "批次所有字段保持不变",
              f"数据被篡改: {snapshot_before} -> {snapshot_after}")

        print("\n" + "-" * 60)
        print("测试 15: 拒绝场景数据不变性验证")
        print("验证以上所有拒绝场景（6a, 6b, 6c, 6e, 6f, 6g）都没有修改任何数据")
        print("✓ 每个拒绝场景都已验证：状态不变、字段不变、历史记录不新增")

    except Exception as e:
        print(f"\n{ERROR} 测试执行过程中发生异常: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(4)

    # ========== 测试结果汇总 ==========
    print("\n" + "=" * 60)
    print(f"测试结果: {passed} 通过, {failed} 失败")
    print("=" * 60)

    if failed == 0:
        print(f"\n{INFO} 所有测试全部通过！权限漏洞已修复！")
        return True
    else:
        print(f"\n{FAIL} 有 {failed} 个测试失败，请检查代码。")
        return False


if __name__ == '__main__':
    print(f"{INFO} 正在清理测试环境...")
    cleanup_database()

    try:
        success = run_tests()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print(f"\n{INFO} 测试被用户中断")
        sys.exit(130)
    except Exception as e:
        print(f"\n{ERROR} 测试运行失败: {e}")
        sys.exit(99)

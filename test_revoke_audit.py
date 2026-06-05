"""
交接批次撤销 - 可审计异常复核流程回归测试
覆盖：冒名撤销、冲突占用、数据不变性、跨重启一致性、导出字段
"""
import sys
import os
import json
import copy

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
    if os.path.exists(DB_PATH):
        try:
            os.remove(DB_PATH)
            print(f"{INFO} 已删除旧数据库文件")
        except PermissionError as e:
            print(f"\n{ERROR} 数据库文件被占用，无法删除: {DB_PATH}")
            print(f"{ERROR} 请先关闭正在运行的后端服务 (run_backend.py)，然后重试")
            sys.exit(2)
        except Exception as e:
            print(f"\n{ERROR} 删除数据库文件失败: {DB_PATH}")
            sys.exit(2)


def get_batch_snapshot(batch_id, app):
    """获取批次的完整数据快照，用于验证数据不变性"""
    with app.app_context():
        from backend.models import HandoverBatch, StatusHistory
        batch = HandoverBatch.query.get(batch_id)
        if not batch:
            return None
        snapshot = {
            'status': batch.status,
            'receiver_person': batch.receiver_person,
            'original_confirmer': batch.original_confirmer,
            'confirmed_at': batch.confirmed_at,
            'revoked_at': batch.revoked_at,
            'revoked_by': batch.revoked_by,
            'revoke_reason': batch.revoke_reason,
            'revoke_old_status': batch.revoke_old_status,
            'revoke_new_status': batch.revoke_new_status,
            'ticket_ids': sorted([t.id for t in batch.tickets]),
        }
        history_count = StatusHistory.query.filter_by(
            entity_type='batch', entity_id=batch_id
        ).count()
        return snapshot, history_count


def run_tests():
    sys.path.insert(0, '.')
    from backend.app import create_app, init_sample_data
    from backend.models import db

    try:
        app = create_app()
        client = app.test_client()
    except Exception as e:
        print(f"\n{ERROR} 初始化 Flask 应用失败: {e}")
        sys.exit(3)

    print("测试交接批次撤销 - 可审计异常复核流程...")
    print("=" * 70)

    try:
        with app.app_context():
            db.drop_all()
            db.create_all()
            init_sample_data()
        print(f"{INFO} 数据库初始化完成")
    except Exception as e:
        print(f"\n{ERROR} 数据库初始化失败: {e}")
        sys.exit(3)

    passed = 0
    failed = 0
    errors = []

    def check(condition, pass_msg, fail_msg):
        nonlocal passed, failed
        if condition:
            print(f"   {PASS} {pass_msg}")
            passed += 1
        else:
            print(f"   {FAIL} {fail_msg}")
            errors.append(fail_msg)
            failed += 1

    try:
        from datetime import datetime, timedelta
        try:
            deadline = (datetime.now(datetime.UTC) + timedelta(days=3)).isoformat()
        except Exception:
            deadline = (datetime.utcnow() + timedelta(days=3)).isoformat()

        print("\n=== 测试准备：创建测试数据 ===")

        client.post('/api/switch-role', json={'role': 'cs', 'username': 'cs_demo'})
        for i in range(5):
            resp = client.post('/api/tickets', json={
                'customer_name': f'审计测试客户{i+1}',
                'severity': 'high' if i < 3 else 'medium',
                'assignee': f'责任人{i+1}',
                'deadline': deadline,
                'progress': f'测试进展{i+1}'
            })
            check(resp.status_code == 201, f"创建测试工单 {i+1} 成功", f"创建测试工单 {i+1} 失败")

        client.post('/api/switch-role', json={'role': 'handover', 'username': 'handover_demo'})
        resp = client.post('/api/batches', json={
            'name': '审计测试批次-撤销复核',
            'description': '用于测试可审计撤销流程的批次',
            'ticket_ids': [1, 2, 3],
            'handover_person': '交班老李'
        })
        batch_id = resp.get_json()['data']['id'] if resp.status_code == 201 else None
        check(resp.status_code == 201 and batch_id, f"创建测试批次成功，ID={batch_id}", "创建测试批次失败")

        print("\n" + "=" * 70)
        print("=== 第一部分：安全校验 - 原确认人绑定会话 ===")
        print("=" * 70)

        print("\n1.1 确认批次，记录原确认人（会话用户）")
        client.post('/api/switch-role', json={'role': 'receiver', 'username': 'receiver_demo'})
        resp = client.post(f'/api/batches/{batch_id}/confirm', json={'receiver_person': '接班小张'})
        data = resp.get_json()
        check(resp.status_code == 200, "确认批次成功", "确认批次失败")
        check(data['data']['original_confirmer'] == 'receiver_demo',
              "原确认人正确记录为会话用户 'receiver_demo'",
              f"原确认人记录错误: {data['data'].get('original_confirmer')}")
        check(data['data']['receiver_person'] == '接班小张',
              "接班人显示名称正确记录为 '接班小张'",
              f"接班人显示名称记录错误: {data['data'].get('receiver_person')}")

        print("\n1.2 冒名撤销测试 - 请求体伪造 receiver_person 为原确认人显示名，但登录用户不同")
        snapshot_before, history_before = get_batch_snapshot(batch_id, app)
        client.post('/api/switch-role', json={'role': 'receiver', 'username': 'other_receiver'})
        resp = client.post(f'/api/batches/{batch_id}/revoke', json={
            'receiver_person': 'receiver_demo',
            'reason': '冒名尝试撤销'
        })
        check(resp.status_code == 403, "冒名撤销正确返回 403",
              f"冒名撤销校验失败: {resp.status_code}")
        check('只有原确认人可以撤销' in resp.get_json().get('error', ''),
              "错误信息包含原确认人提示",
              f"错误信息不正确: {resp.get_json().get('error')}")
        check('receiver_demo' in resp.get_json().get('error', ''),
              "错误信息提示正确的原确认人",
              f"错误信息未提示正确原确认人: {resp.get_json().get('error')}")

        snapshot_after, history_after = get_batch_snapshot(batch_id, app)
        check(snapshot_before == snapshot_after, "冒名撤销失败后数据保持不变",
              "冒名撤销失败后数据被篡改")
        check(history_before == history_after, "冒名撤销失败后历史记录保持不变",
              "冒名撤销失败后新增了历史记录")

        print("\n1.3 冒名撤销测试 - 登录用户为原确认人，即使不传 receiver_person 也应成功（先不撤销，为后续测试保留状态）")
        client.post('/api/switch-role', json={'role': 'receiver', 'username': 'receiver_demo'})
        resp = client.get(f'/api/batches/{batch_id}')
        data = resp.get_json()['data']
        check(data['original_confirmer'] == 'receiver_demo',
              "原确认人字段持久化正确",
              f"原确认人字段丢失或错误: {data.get('original_confirmer')}")

        print("\n" + "=" * 70)
        print("=== 第二部分：拒绝条件 - 数据不变性保证 ===")
        print("=" * 70)

        print("\n2.1 待确认批次撤销测试 - 应拒绝且数据不变")
        client.post('/api/switch-role', json={'role': 'handover', 'username': 'handover_demo'})
        resp = client.post('/api/batches', json={
            'name': '测试批次-待确认撤销',
            'ticket_ids': [4, 5],
            'handover_person': '交班老李'
        })
        pending_batch_id = resp.get_json()['data']['id'] if resp.status_code == 201 else None
        check(resp.status_code == 201, "创建待确认批次成功", "创建待确认批次失败")

        snapshot_before, history_before = get_batch_snapshot(pending_batch_id, app)
        client.post('/api/switch-role', json={'role': 'receiver', 'username': 'receiver_demo'})
        resp = client.post(f'/api/batches/{pending_batch_id}/revoke', json={
            'reason': '尝试撤销待确认批次'
        })
        check(resp.status_code == 400 and '无需撤销' in resp.get_json().get('error', ''),
              "待确认批次撤销正确返回 400",
              f"待确认批次撤销校验失败: {resp.status_code}")
        snapshot_after, history_after = get_batch_snapshot(pending_batch_id, app)
        check(snapshot_before == snapshot_after, "待确认批次撤销失败后数据保持不变",
              "待确认批次撤销失败后数据被篡改")
        check(history_before == history_after, "待确认批次撤销失败后历史记录保持不变",
              "待确认批次撤销失败后新增了历史记录")

        print("\n2.2 已退回批次撤销测试 - 应拒绝且数据不变")
        client.post('/api/switch-role', json={'role': 'receiver', 'username': 'receiver_demo'})
        resp = client.post(f'/api/batches/{pending_batch_id}/return', json={
            'receiver_person': '接班小张',
            'reason': '测试退回'
        })
        check(resp.status_code == 200, "退回批次成功", "退回批次失败")

        snapshot_before, history_before = get_batch_snapshot(pending_batch_id, app)
        resp = client.post(f'/api/batches/{pending_batch_id}/revoke', json={
            'reason': '尝试撤销已退回批次'
        })
        check(resp.status_code == 400 and '不能撤销' in resp.get_json().get('error', ''),
              "已退回批次撤销正确返回 400",
              f"已退回批次撤销校验失败: {resp.status_code}")
        snapshot_after, history_after = get_batch_snapshot(pending_batch_id, app)
        check(snapshot_before == snapshot_after, "已退回批次撤销失败后数据保持不变",
              "已退回批次撤销失败后数据被篡改")
        check(history_before == history_after, "已退回批次撤销失败后历史记录保持不变",
              "已退回批次撤销失败后新增了历史记录")

        print("\n2.3 工单被新批次占用时撤销测试 - 应拒绝且数据不变")
        snapshot_before, history_before = get_batch_snapshot(batch_id, app)

        client.post('/api/switch-role', json={'role': 'handover', 'username': 'handover_demo'})
        resp = client.post('/api/batches', json={
            'name': '测试批次-占用冲突2',
            'ticket_ids': [1, 4],
            'handover_person': '交班老李'
        })
        new_batch_id = resp.get_json()['data']['id'] if resp.status_code == 201 else None
        check(resp.status_code == 201, f"创建新批次成功，ID={new_batch_id}", "创建新批次失败")

        client.post('/api/switch-role', json={'role': 'receiver', 'username': 'receiver_demo'})
        resp = client.post(f'/api/batches/{batch_id}/revoke', json={
            'reason': '尝试撤销但工单已被占用'
        })
        check(resp.status_code == 409 and '已被新批次' in resp.get_json().get('error', ''),
              "工单被占用时撤销正确返回 409",
              f"工单占用冲突校验失败: {resp.status_code}")

        snapshot_after, history_after = get_batch_snapshot(batch_id, app)
        check(snapshot_before == snapshot_after, "工单占用时撤销失败后数据保持不变",
              "工单占用时撤销失败后数据被篡改")
        check(history_before == history_after, "工单占用时撤销失败后历史记录保持不变",
              "工单占用时撤销失败后新增了历史记录")

        print("\n2.4 清理新批次，释放工单 1 以便后续测试")
        client.post('/api/switch-role', json={'role': 'handover', 'username': 'handover_demo'})
        with app.app_context():
            from backend.models import HandoverBatch
            batch_to_delete = HandoverBatch.query.get(new_batch_id)
            if batch_to_delete:
                db.session.delete(batch_to_delete)
                db.session.commit()
        check(True, "新批次已删除", "新批次删除失败")

        print("\n" + "=" * 70)
        print("=== 第三部分：撤销成功 - 完整复核字段记录 ===")
        print("=" * 70)

        print("\n3.1 执行撤销，验证所有复核字段")
        revoke_reason = '审计测试：发现客户信息有误，需要重新确认交接内容'
        snapshot_before, history_before = get_batch_snapshot(batch_id, app)

        import time
        time.sleep(0.5)

        client.post('/api/switch-role', json={'role': 'receiver', 'username': 'receiver_demo'})
        resp = client.post(f'/api/batches/{batch_id}/revoke', json={
            'reason': revoke_reason
        })
        data = resp.get_json()
        check(resp.status_code == 200, "撤销成功", f"撤销失败: {resp.status_code}")

        check(data['data']['original_confirmer'] == 'receiver_demo',
              "撤销后原确认人字段保留（会话用户）",
              f"撤销后原确认人字段丢失或错误: {data['data'].get('original_confirmer')}")
        check(data['data']['revoked_by'] == 'receiver_demo',
              "撤销人正确记录（使用会话用户）",
              f"撤销人记录错误: {data['data'].get('revoked_by')}")
        check(data['data']['revoke_reason'] == revoke_reason,
              "撤销原因正确记录",
              f"撤销原因记录错误: {data['data'].get('revoke_reason')}")
        check(data['data']['revoked_at'] is not None,
              "撤销时间正确记录",
              "撤销时间未记录")
        check(data['data']['revoke_old_status'] == 'confirmed',
              "撤销前状态正确记录为 confirmed",
              f"撤销前状态记录错误: {data['data'].get('revoke_old_status')}")
        check(data['data']['revoke_new_status'] == 'pending',
              "撤销后状态正确记录为 pending",
              f"撤销后状态记录错误: {data['data'].get('revoke_new_status')}")
        check(data['data']['status'] == 'pending',
              "批次实际状态已变为 pending",
              f"批次状态未变更: {data['data'].get('status')}")
        check(data['data']['receiver_person'] is None,
              "接班人已清空",
              "接班人未清空")
        check(data['data']['confirmed_at'] is None,
              "确认时间已清空",
              "确认时间未清空")
        check('affected_tickets' in data['data'],
              "返回数据包含受影响工单",
              "返回数据缺少受影响工单")
        check(len(data['data']['affected_tickets']) == 3,
              "受影响工单数量正确",
              f"受影响工单数量错误: {len(data['data'].get('affected_tickets', []))}")

        time.sleep(0.5)
        snapshot_after, history_after = get_batch_snapshot(batch_id, app)
        check(history_after == history_before + 1,
              "撤销操作新增了一条历史记录",
              f"历史记录数量不正确: {history_before} -> {history_after}")

        print("\n3.2 验证历史记录完整")
        resp = client.get(f'/api/history?entity_type=batch&entity_id={batch_id}')
        history = resp.get_json()['data'] if resp.status_code == 200 else []
        revoke_log = next((h for h in history if h['old_status'] == 'confirmed' and h['new_status'] == 'pending'), None)
        check(revoke_log is not None, "撤销历史记录存在", "撤销历史记录不存在")
        if revoke_log:
            check(revoke_log['operator'] == 'receiver_demo',
                  "历史记录操作人为会话用户",
                  f"历史记录操作人错误: {revoke_log['operator']}")
            check(revoke_reason in (revoke_log.get('reason') or ''),
                  "历史记录包含撤销原因",
                  f"历史记录原因错误: {revoke_log.get('reason')}")

        print("\n" + "=" * 70)
        print("=== 第四部分：列表筛选 - 已撤销批次筛选 ===")
        print("=" * 70)

        print("\n4.1 筛选已撤销批次")
        resp = client.get('/api/batches?is_revoked=true')
        data = resp.get_json()['data']
        check(resp.status_code == 200, "获取已撤销批次列表成功", "获取已撤销批次列表失败")
        revoked_ids = [b['id'] for b in data]
        check(batch_id in revoked_ids, "已撤销批次在筛选结果中",
              f"已撤销批次未在筛选结果中，筛选结果: {revoked_ids}")
        check(pending_batch_id not in revoked_ids, "未撤销批次不在筛选结果中",
              "未撤销批次出现在已撤销筛选结果中")

        print("\n4.2 筛选未撤销批次")
        resp = client.get('/api/batches?is_revoked=false')
        data = resp.get_json()['data']
        check(resp.status_code == 200, "获取未撤销批次列表成功", "获取未撤销批次列表失败")
        not_revoked_ids = [b['id'] for b in data]
        check(batch_id not in not_revoked_ids, "已撤销批次不在未撤销筛选结果中",
              "已撤销批次出现在未撤销筛选结果中")
        check(pending_batch_id in not_revoked_ids, "未撤销批次在筛选结果中",
              f"未撤销批次未在筛选结果中，筛选结果: {not_revoked_ids}")

        print("\n" + "=" * 70)
        print("=== 第五部分：导出字段 - 完整复核信息导出 ===")
        print("=" * 70)

        print("\n5.1 JSON 导出包含完整复核字段")
        resp = client.get('/api/export/batches?format=json')
        check(resp.status_code == 200 and 'json' in resp.content_type, "JSON 导出成功", "JSON 导出失败")

        exported_data = json.loads(resp.data.decode('utf-8'))
        target_batch = next((b for b in exported_data if b['ID'] == batch_id), None)
        check(target_batch is not None, "导出数据包含目标批次", "导出数据不包含目标批次")
        if target_batch:
            check('原确认人' in target_batch, "JSON 导出包含原确认人字段", "JSON 导出缺少原确认人字段")
            check(target_batch['原确认人'] == 'receiver_demo', "JSON 导出原确认人正确",
                  f"JSON 导出原确认人错误: {target_batch.get('原确认人')}")
            check('撤销前状态' in target_batch, "JSON 导出包含撤销前状态字段",
                  "JSON 导出缺少撤销前状态字段")
            check(target_batch['撤销前状态'] == 'confirmed', "JSON 导出撤销前状态正确",
                  f"JSON 导出撤销前状态错误: {target_batch.get('撤销前状态')}")
            check('撤销后状态' in target_batch, "JSON 导出包含撤销后状态字段",
                  "JSON 导出缺少撤销后状态字段")
            check(target_batch['撤销后状态'] == 'pending', "JSON 导出撤销后状态正确",
                  f"JSON 导出撤销后状态错误: {target_batch.get('撤销后状态')}")
            check('关联工单ID' in target_batch, "JSON 导出包含关联工单ID字段",
                  "JSON 导出缺少关联工单ID字段")
            check('1,2,3' in target_batch['关联工单ID'], "JSON 导出关联工单ID正确",
                  f"JSON 导出关联工单ID错误: {target_batch.get('关联工单ID')}")

        print("\n5.2 CSV 导出包含完整复核字段")
        resp = client.get('/api/export/batches?format=csv')
        check(resp.status_code == 200 and 'csv' in resp.content_type, "CSV 导出成功", "CSV 导出失败")

        csv_content = resp.data.decode('utf-8-sig')
        check('原确认人' in csv_content, "CSV 包含原确认人列", "CSV 缺少原确认人列")
        check('撤销前状态' in csv_content, "CSV 包含撤销前状态列", "CSV 缺少撤销前状态列")
        check('撤销后状态' in csv_content, "CSV 包含撤销后状态列", "CSV 缺少撤销后状态列")
        check('关联工单ID' in csv_content, "CSV 包含关联工单ID列", "CSV 缺少关联工单ID列")
        check('receiver_demo' in csv_content, "CSV 包含原确认人内容", "CSV 缺少原确认人内容")
        check(revoke_reason in csv_content, "CSV 包含撤销原因内容", "CSV 缺少撤销原因内容")

        print("\n5.3 带筛选条件的导出")
        resp = client.get('/api/export/batches?format=json&is_revoked=true')
        exported_filtered = json.loads(resp.data.decode('utf-8'))
        check(all(b.get('是否已撤销') == '是' for b in exported_filtered),
              "带 is_revoked=true 筛选的导出只包含已撤销批次",
              "带筛选的导出包含未撤销批次")
        check(len(exported_filtered) >= 1, "筛选导出至少有一条记录",
              f"筛选导出记录数不足: {len(exported_filtered)}")

        print("\n" + "=" * 70)
        print("=== 第六部分：跨重启一致性 ===")
        print("=" * 70)

        print("\n6.1 保存当前状态快照")
        state_before = {}
        with app.app_context():
            from backend.models import HandoverBatch, StatusHistory
            batch_before = HandoverBatch.query.get(batch_id)
            state_before['batch'] = {
                'status': batch_before.status,
                'original_confirmer': batch_before.original_confirmer,
                'revoked_at': batch_before.revoked_at.isoformat() if batch_before.revoked_at else None,
                'revoked_by': batch_before.revoked_by,
                'revoke_reason': batch_before.revoke_reason,
                'revoke_old_status': batch_before.revoke_old_status,
                'revoke_new_status': batch_before.revoke_new_status,
            }
            state_before['history_count'] = StatusHistory.query.filter_by(
                entity_type='batch', entity_id=batch_id
            ).count()

            resp = client.get('/api/export/batches?format=json')
            state_before['export'] = json.loads(resp.data.decode('utf-8'))

        print("\n6.2 模拟服务重启（重新初始化 app）")
        del app
        del client
        import gc
        gc.collect()

        app2 = create_app()
        client2 = app2.test_client()

        print("\n6.3 验证重启后批次状态一致")
        with app2.app_context():
            from backend.models import HandoverBatch, StatusHistory
            batch_after = HandoverBatch.query.get(batch_id)
            state_after = {
                'status': batch_after.status,
                'original_confirmer': batch_after.original_confirmer,
                'revoked_at': batch_after.revoked_at.isoformat() if batch_after.revoked_at else None,
                'revoked_by': batch_after.revoked_by,
                'revoke_reason': batch_after.revoke_reason,
                'revoke_old_status': batch_after.revoke_old_status,
                'revoke_new_status': batch_after.revoke_new_status,
            }
            history_count_after = StatusHistory.query.filter_by(
                entity_type='batch', entity_id=batch_id
            ).count()

        check(state_before['batch'] == state_after, "重启后批次状态完全一致",
              "重启后批次状态不一致")
        check(state_before['history_count'] == history_count_after,
              "重启后历史记录数量一致",
              f"重启后历史记录数量不一致: {state_before['history_count']} -> {history_count_after}")

        print("\n6.4 验证重启后API返回状态一致")
        resp = client2.get(f'/api/batches/{batch_id}')
        api_data = resp.get_json()['data'] if resp.status_code == 200 else None
        check(api_data is not None, "API 获取批次详情成功", "API 获取批次详情失败")
        if api_data:
            check(api_data['original_confirmer'] == state_before['batch']['original_confirmer'],
                  "API 返回原确认人正确", "API 返回原确认人错误")
            check(api_data['revoke_old_status'] == state_before['batch']['revoke_old_status'],
                  "API 返回撤销前状态正确", "API 返回撤销前状态错误")
            check(api_data['revoke_new_status'] == state_before['batch']['revoke_new_status'],
                  "API 返回撤销后状态正确", "API 返回撤销后状态错误")

        print("\n6.5 验证重启后导出结果一致")
        resp = client2.get('/api/export/batches?format=json')
        exported_after = json.loads(resp.data.decode('utf-8'))
        check(len(state_before['export']) == len(exported_after),
              "重启后导出记录数一致",
              f"重启后导出记录数不一致: {len(state_before['export'])} -> {len(exported_after)}")

        target_after = next((b for b in exported_after if b['ID'] == batch_id), None)
        check(target_after is not None and target_after.get('原确认人') == 'receiver_demo',
              "重启后导出原确认人一致", "重启后导出原确认人不一致")
        check(target_after.get('撤销前状态') == 'confirmed',
              "重启后导出撤销前状态一致", "重启后导出撤销前状态不一致")
        check(target_after.get('撤销后状态') == 'pending',
              "重启后导出撤销后状态一致", "重启后导出撤销后状态不一致")

        print("\n6.6 验证重启后筛选功能正常")
        resp = client2.get('/api/batches?is_revoked=true')
        filtered_after = resp.get_json()['data']
        revoked_ids_after = [b['id'] for b in filtered_after]
        check(batch_id in revoked_ids_after, "重启后已撤销筛选正常工作",
              "重启后已撤销筛选结果不正确")

        print("\n" + "=" * 70)
        print("=== 第七部分：再确认再撤销 - 原确认人更新 ===")
        print("=" * 70)

        print("\n7.1 用不同用户重新确认批次")
        client2.post('/api/switch-role', json={'role': 'receiver', 'username': 'other_receiver'})
        resp = client2.post(f'/api/batches/{batch_id}/confirm', json={'receiver_person': '接班小王'})
        check(resp.status_code == 200, "新用户确认批次成功", "新用户确认批次失败")
        check(resp.get_json()['data']['original_confirmer'] == 'other_receiver',
              "重新确认后原确认人更新为新会话用户",
              f"重新确认后原确认人未更新: {resp.get_json()['data'].get('original_confirmer')}")
        check(resp.get_json()['data']['receiver_person_display'] == '接班小王',
              "重新确认后接班人显示名正确",
              f"重新确认后接班人显示名错误: {resp.get_json()['data'].get('receiver_person_display')}")

        print("\n7.2 原确认人（已更换）不能再撤销")
        client2.post('/api/switch-role', json={'role': 'receiver', 'username': 'receiver_demo'})
        resp = client2.post(f'/api/batches/{batch_id}/revoke', json={
            'reason': '原确认人尝试撤销已被他人重新确认的批次'
        })
        check(resp.status_code == 403 and 'other_receiver' in resp.get_json().get('error', ''),
              "原确认人已更换后，旧确认人不能撤销（错误信息提示新确认人）",
              f"重新确认后的撤销权限校验失败: {resp.status_code}")

        print("\n7.3 新确认人可以撤销")
        client2.post('/api/switch-role', json={'role': 'receiver', 'username': 'other_receiver'})
        resp = client2.post(f'/api/batches/{batch_id}/revoke', json={
            'reason': '新确认人撤销自己确认的批次'
        })
        check(resp.status_code == 200, "新确认人撤销成功", "新确认人撤销失败")
        check(resp.get_json()['data']['revoked_by'] == 'other_receiver',
              "新撤销人正确记录为会话用户",
              f"撤销人记录错误: {resp.get_json()['data'].get('revoked_by')}")

    except Exception as e:
        print(f"\n{ERROR} 测试执行过程中发生异常: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(4)

    print("\n" + "=" * 70)
    print(f"测试结果: {passed} 通过, {failed} 失败")
    print("=" * 70)

    if failed == 0:
        print(f"\n{INFO} 所有可审计异常复核流程测试全部通过！")
        return True
    else:
        print(f"\n{FAIL} 有 {failed} 个测试失败:")
        for err in errors:
            print(f"  - {err}")
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
        import traceback
        traceback.print_exc()
        sys.exit(99)

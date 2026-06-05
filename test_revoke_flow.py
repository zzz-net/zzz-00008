"""
交接批次撤销功能回归测试
覆盖：权限校验、冲突检测、跨重启一致性、导出信息
"""
import sys
import os
import json

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

    print("测试交接批次撤销功能...")
    print("=" * 60)

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
        for i in range(4):
            resp = client.post('/api/tickets', json={
                'customer_name': f'测试客户{i+1}',
                'severity': 'high' if i < 2 else 'medium',
                'assignee': f'责任人{i+1}',
                'deadline': deadline,
                'progress': f'测试进展{i+1}'
            })
            check(resp.status_code == 201, f"创建测试工单 {i+1} 成功", f"创建测试工单 {i+1} 失败")

        client.post('/api/switch-role', json={'role': 'handover', 'username': 'handover_demo'})
        resp = client.post('/api/batches', json={
            'name': '测试批次-撤销测试',
            'description': '用于测试撤销功能的批次',
            'ticket_ids': [1, 2],
            'handover_person': '交班老李'
        })
        batch_id = resp.get_json()['data']['id'] if resp.status_code == 201 else None
        check(resp.status_code == 201 and batch_id, f"创建测试批次成功，ID={batch_id}", "创建测试批次失败")

        print("\n=== 1. 权限测试 ===")

        print("\n1.1 普通客服角色尝试撤销")
        client.post('/api/switch-role', json={'role': 'cs', 'username': 'cs_demo'})
        resp = client.post(f'/api/batches/{batch_id}/revoke', json={
            'receiver_person': 'cs_demo',
            'reason': '测试撤销'
        })
        check(resp.status_code == 403, "普通客服撤销正确返回 403",
              f"普通客服撤销权限校验失败: {resp.status_code}")

        print("\n1.2 交班人角色尝试撤销")
        client.post('/api/switch-role', json={'role': 'handover', 'username': 'handover_demo'})
        resp = client.post(f'/api/batches/{batch_id}/revoke', json={
            'receiver_person': 'handover_demo',
            'reason': '测试撤销'
        })
        check(resp.status_code == 403, "交班人撤销正确返回 403",
              f"交班人撤销权限校验失败: {resp.status_code}")

        print("\n1.3 先确认批次，再测试接班人权限")
        client.post('/api/switch-role', json={'role': 'receiver', 'username': 'receiver_demo'})
        resp = client.post(f'/api/batches/{batch_id}/confirm', json={'receiver_person': '接班小张'})
        check(resp.status_code == 200, "确认批次成功", "确认批次失败")

        print("\n1.4 非确认者的接班人尝试撤销")
        client.post('/api/switch-role', json={'role': 'receiver', 'username': 'other_receiver'})
        resp = client.post(f'/api/batches/{batch_id}/revoke', json={
            'receiver_person': 'other_receiver',
            'reason': '测试撤销'
        })
        check(resp.status_code == 403 and '只能撤销自己作为接班人确认的批次' in resp.get_json().get('error', ''),
              "非确认者撤销正确返回 403",
              f"非确认者撤销权限校验失败: {resp.status_code}")

        print("\n1.5 缺少撤销原因")
        client.post('/api/switch-role', json={'role': 'receiver', 'username': 'receiver_demo'})
        resp = client.post(f'/api/batches/{batch_id}/revoke', json={
            'receiver_person': '接班小张',
            'reason': ''
        })
        check(resp.status_code == 400 and '请填写撤销原因' in resp.get_json().get('error', ''),
              "缺少撤销原因正确返回 400",
              f"缺少撤销原因校验失败: {resp.status_code}")

        print("\n=== 2. 状态冲突测试 ===")

        print("\n2.1 撤销成功 - 已确认批次")
        client.post('/api/switch-role', json={'role': 'receiver', 'username': 'receiver_demo'})
        resp = client.post(f'/api/batches/{batch_id}/revoke', json={
            'receiver_person': '接班小张',
            'reason': '发现交接错误，需要重新核对'
        })
        data = resp.get_json()
        check(resp.status_code == 200 and data.get('success') and data['data']['status'] == 'pending',
              "已确认批次撤销成功",
              f"已确认批次撤销失败: {resp.status_code}")
        check(data['data']['revoked_by'] == '接班小张', "撤销人正确记录", "撤销人记录错误")
        check(data['data']['revoke_reason'] == '发现交接错误，需要重新核对', "撤销原因正确记录", "撤销原因记录错误")
        check(data['data']['revoked_at'] is not None, "撤销时间正确记录", "撤销时间记录错误")
        check(data['data']['receiver_person'] is None, "撤销后接班人已清空", "撤销后接班人未清空")
        check(data['data']['confirmed_at'] is None, "撤销后确认时间已清空", "撤销后确认时间未清空")

        print("\n2.2 待确认批次尝试撤销")
        resp = client.post(f'/api/batches/{batch_id}/revoke', json={
            'receiver_person': '接班小张',
            'reason': '测试撤销'
        })
        check(resp.status_code == 400 and '无需撤销' in resp.get_json().get('error', ''),
              "待确认批次撤销正确返回 400",
              f"待确认批次撤销校验失败: {resp.status_code}")

        print("\n2.3 已退回批次尝试撤销")
        client.post('/api/switch-role', json={'role': 'receiver', 'username': 'receiver_demo'})
        resp = client.post(f'/api/batches/{batch_id}/return', json={
            'receiver_person': '接班小张',
            'reason': '测试退回'
        })
        check(resp.status_code == 200, "退回批次成功", "退回批次失败")

        resp = client.post(f'/api/batches/{batch_id}/revoke', json={
            'receiver_person': '接班小张',
            'reason': '测试撤销'
        })
        check(resp.status_code == 400 and '不能撤销' in resp.get_json().get('error', ''),
              "已退回批次撤销正确返回 400",
              f"已退回批次撤销校验失败: {resp.status_code}")

        print("\n=== 3. 工单占用冲突测试 ===")

        print("\n3.1 准备：重新提交批次并确认")
        client.post('/api/switch-role', json={'role': 'handover', 'username': 'handover_demo'})
        resp = client.post(f'/api/batches/{batch_id}/resubmit')
        check(resp.status_code == 200, "重新提交批次成功", "重新提交批次失败")

        client.post('/api/switch-role', json={'role': 'receiver', 'username': 'receiver_demo'})
        resp = client.post(f'/api/batches/{batch_id}/confirm', json={'receiver_person': '接班小张'})
        check(resp.status_code == 200, "确认批次成功", "确认批次失败")

        print("\n3.2 创建新批次，直接添加工单 1（与原批次的工单冲突）")
        client.post('/api/switch-role', json={'role': 'handover', 'username': 'handover_demo'})
        resp = client.post('/api/batches', json={
            'name': '测试批次-占用冲突',
            'ticket_ids': [1, 3],
            'handover_person': '交班老李'
        })
        new_batch_id = resp.get_json()['data']['id'] if resp.status_code == 201 else None
        check(resp.status_code == 201, f"创建新批次成功，ID={new_batch_id}", "创建新批次失败")

        print("\n3.3 尝试撤销原批次，工单 1 已被新批次占用")
        client.post('/api/switch-role', json={'role': 'receiver', 'username': 'receiver_demo'})
        resp = client.post(f'/api/batches/{batch_id}/revoke', json={
            'receiver_person': '接班小张',
            'reason': '测试工单占用冲突'
        })
        data = resp.get_json()
        check(resp.status_code == 409 and '已被新批次' in data.get('error', ''),
              "工单被占用时撤销正确返回 409",
              f"工单占用冲突校验失败: {resp.status_code}")

        print("\n3.4 先删除新批次，释放工单 1")
        client.post('/api/switch-role', json={'role': 'handover', 'username': 'handover_demo'})
        from backend.models import db, HandoverBatch
        with app.app_context():
            batch_to_delete = HandoverBatch.query.get(new_batch_id)
            if batch_to_delete:
                db.session.delete(batch_to_delete)
                db.session.commit()
        check(True, "新批次已删除", "新批次删除失败")

        print("\n3.5 撤销原批次（工单1已被释放），使其回到待确认状态")
        client.post('/api/switch-role', json={'role': 'receiver', 'username': 'receiver_demo'})
        resp = client.post(f'/api/batches/{batch_id}/revoke', json={
            'receiver_person': '接班小张',
            'reason': '测试工单释放'
        })
        check(resp.status_code == 200, "撤销原批次成功", "撤销原批次失败")

        print("\n=== 4. 操作日志测试 ===")

        print("\n4.1 确认批次，为日志测试做准备")
        client.post('/api/switch-role', json={'role': 'receiver', 'username': 'receiver_demo'})

        import time
        time.sleep(1.1)

        resp = client.post(f'/api/batches/{batch_id}/confirm', json={'receiver_person': '接班小张'})
        check(resp.status_code == 200, "确认批次成功", "确认批次失败")

        time.sleep(1.1)

        print("\n4.2 撤销批次，检查日志")
        revoke_reason = '发现客户信息有误，需要重新确认-日志测试'

        resp = client.post(f'/api/batches/{batch_id}/revoke', json={
            'receiver_person': '接班小张',
            'reason': revoke_reason
        })
        check(resp.status_code == 200, "撤销批次成功", "撤销批次失败")

        time.sleep(0.5)

        resp = client.get(f'/api/history?entity_type=batch&entity_id={batch_id}')
        history = resp.get_json()['data'] if resp.status_code == 200 else []

        revoke_log = next((h for h in history if h['old_status'] == 'confirmed' and h['new_status'] == 'pending' and revoke_reason in (h.get('reason') or '')), None)
        check(revoke_log is not None, "撤销操作日志已记录", "撤销操作日志未记录")
        if revoke_log:
            check(revoke_log['operator'] == '接班小张', "日志操作人正确", f"日志操作人错误: {revoke_log['operator']}")
            check(revoke_log['old_status'] == 'confirmed', "日志旧状态正确", f"日志旧状态错误: {revoke_log['old_status']}")
            check(revoke_log['new_status'] == 'pending', "日志新状态正确", f"日志新状态错误: {revoke_log['new_status']}")
            expected_log_reason = f'撤销已确认的交接批次，原因：{revoke_reason}'
            check(revoke_log.get('reason') == expected_log_reason,
                  f"日志原因正确",
                  f"日志原因错误，期望: {expected_log_reason}, 实际: {revoke_log.get('reason')}")
            check(revoke_log.get('created_at') is not None, "日志时间正确记录", "日志时间未记录")

        print("\n=== 5. 导出信息测试 ===")

        print("\n5.1 JSON 导出包含撤销信息")
        resp = client.get('/api/export/batches?format=json')
        check(resp.status_code == 200 and 'json' in resp.content_type, "JSON 导出成功", "JSON 导出失败")

        exported_data = json.loads(resp.data.decode('utf-8'))
        target_batch = next((b for b in exported_data if b['ID'] == batch_id), None)
        check(target_batch is not None, "导出数据包含目标批次", "导出数据不包含目标批次")
        if target_batch:
            check(target_batch.get('是否已撤销') == '是', "导出包含是否已撤销字段", "导出缺少是否已撤销字段")
            check(target_batch.get('撤销人') == '接班小张', "导出撤销人正确", "导出撤销人错误")
            check(target_batch.get('撤销时间') != '', "导出撤销时间正确", "导出撤销时间为空")
            check(target_batch.get('撤销原因') == revoke_reason, "导出撤销原因正确", "导出撤销原因错误")

        print("\n5.2 CSV 导出包含撤销信息")
        resp = client.get('/api/export/batches?format=csv')
        check(resp.status_code == 200 and 'csv' in resp.content_type, "CSV 导出成功", "CSV 导出失败")

        csv_content = resp.data.decode('utf-8-sig')
        check('是否已撤销' in csv_content, "CSV 包含是否已撤销列", "CSV 缺少是否已撤销列")
        check('撤销人' in csv_content, "CSV 包含撤销人列", "CSV 缺少撤销人列")
        check('撤销时间' in csv_content, "CSV 包含撤销时间列", "CSV 缺少撤销时间列")
        check('撤销原因' in csv_content, "CSV 包含撤销原因列", "CSV 缺少撤销原因列")
        check(revoke_reason in csv_content, "CSV 包含撤销原因内容", "CSV 缺少撤销原因内容")

        print("\n=== 6. 跨重启一致性测试 ===")

        print("\n6.1 保存当前状态到变量")
        with app.app_context():
            from backend.models import HandoverBatch, StatusHistory
            batch_before = HandoverBatch.query.get(batch_id)
            batch_data_before = {
                'status': batch_before.status,
                'revoked_at': batch_before.revoked_at.isoformat() if batch_before.revoked_at else None,
                'revoked_by': batch_before.revoked_by,
                'revoke_reason': batch_before.revoke_reason,
                'receiver_person': batch_before.receiver_person,
                'confirmed_at': batch_before.confirmed_at.isoformat() if batch_before.confirmed_at else None,
            }
            history_count_before = StatusHistory.query.filter_by(
                entity_type='batch', entity_id=batch_id
            ).count()

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
            batch_data_after = {
                'status': batch_after.status,
                'revoked_at': batch_after.revoked_at.isoformat() if batch_after.revoked_at else None,
                'revoked_by': batch_after.revoked_by,
                'revoke_reason': batch_after.revoke_reason,
                'receiver_person': batch_after.receiver_person,
                'confirmed_at': batch_after.confirmed_at.isoformat() if batch_after.confirmed_at else None,
            }
            history_count_after = StatusHistory.query.filter_by(
                entity_type='batch', entity_id=batch_id
            ).count()

        check(batch_data_before == batch_data_after, "重启后批次状态一致", "重启后批次状态不一致")
        check(history_count_before == history_count_after, "重启后历史记录数量一致", "重启后历史记录数量不一致")

        print("\n6.4 验证重启后API返回状态一致")
        resp = client2.get(f'/api/batches/{batch_id}')
        api_data = resp.get_json()['data'] if resp.status_code == 200 else None
        check(api_data is not None, "API 获取批次详情成功", "API 获取批次详情失败")
        if api_data:
            check(api_data['status'] == batch_data_before['status'], "API 返回状态正确", "API 返回状态错误")
            check(api_data['revoked_by'] == batch_data_before['revoked_by'], "API 返回撤销人正确", "API 返回撤销人错误")
            check(api_data['revoke_reason'] == batch_data_before['revoke_reason'], "API 返回撤销原因正确", "API 返回撤销原因错误")

        print("\n6.5 验证重启后导出结果一致")
        resp = client2.get('/api/export/batches?format=json')
        exported_after = json.loads(resp.data.decode('utf-8'))
        target_after = next((b for b in exported_after if b['ID'] == batch_id), None)
        check(target_after is not None and target_after.get('是否已撤销') == '是',
              "重启后导出撤销状态一致", "重启后导出撤销状态不一致")

        print("\n6.6 验证撤销后工单可继续交接")
        client2.post('/api/switch-role', json={'role': 'handover', 'username': 'handover_demo'})
        resp = client2.post('/api/batches', json={
            'name': '测试批次-撤销后交接',
            'ticket_ids': [1, 2],
            'handover_person': '交班老李'
        })
        check(resp.status_code == 400 and '已在另一个待确认的交接批次中' in resp.get_json().get('error', ''),
              "撤销后的工单在原批次（待确认）中，不能重复加入新批次",
              "撤销后工单状态校验失败")

    except Exception as e:
        print(f"\n{ERROR} 测试执行过程中发生异常: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(4)

    print("\n" + "=" * 60)
    print(f"测试结果: {passed} 通过, {failed} 失败")
    print("=" * 60)

    if failed == 0:
        print(f"\n{INFO} 所有撤销功能回归测试全部通过！")
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

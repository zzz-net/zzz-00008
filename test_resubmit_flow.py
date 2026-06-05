"""
交接批次退回后整改再提交 回归测试
测试场景：
1. 权限测试 - 普通客服/接班人尝试编辑/重新提交退回批次 - 应失败
2. 权限测试 - 交班人或有创建权限角色编辑/重新提交 - 应成功
3. 冲突测试 - 工单已关闭/已被其他批次占用 - 应失败
4. 完整流程 - 编辑退回批次 -> 重新提交 -> 状态回到 pending -> 确认
5. 重启数据持久化 - 重启后批次状态、工单关系、历史记录仍正确
"""
import sys
import os
import json
import time

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
    """清理数据库文件"""
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


def create_test_env():
    """创建测试环境并返回 app 和 client"""
    sys.path.insert(0, '.')
    from backend.app import create_app, init_sample_data
    from backend.models import db

    app = create_app()
    with app.app_context():
        db.drop_all()
        db.create_all()
        init_sample_data()
    return app, app.test_client()


def run_tests():
    try:
        app, client = create_test_env()
    except Exception as e:
        print(f"\n{ERROR} 初始化 Flask 应用失败: {e}")
        sys.exit(3)

    print("=" * 70)
    print("交接批次退回后整改再提交 回归测试")
    print("=" * 70)

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
        resp = client.post('/api/batches', json={
            'name': '测试批次',
            'description': '初始描述',
            'ticket_ids': ticket_ids or [1, 3],
            'handover_person': 'handover_demo'
        })
        if resp.status_code != 201:
            raise RuntimeError(f"创建测试批次失败: {resp.status_code} - {resp.get_json()}")
        return resp.get_json()['data']['id']

    def return_batch(batch_id, reason='测试退回'):
        switch_role('receiver', 'receiver_demo')
        resp = client.post(f'/api/batches/{batch_id}/return', json={
            'receiver_person': 'receiver_demo',
            'reason': reason
        })
        if resp.status_code != 200:
            raise RuntimeError(f"退回批次失败: {resp.status_code} - {resp.get_json()}")
        return resp.get_json()

    def check(condition, pass_msg, fail_msg):
        nonlocal passed, failed
        if condition:
            print(f"  {PASS} {pass_msg}")
            passed += 1
        else:
            print(f"  {FAIL} {fail_msg}")
            failed += 1

    try:
        # ========== 准备测试数据 ==========
        print(f"\n{INFO} 准备测试数据...")
        batch_id = create_test_batch()
        print(f"测试批次 ID: {batch_id}")

        # 退回批次
        return_batch(batch_id, '退回原因：需要补充更多信息')
        print(f"批次已退回，当前状态: returned")

        history_count_start = get_history_count()
        print(f"测试开始前历史记录数: {history_count_start}")

        # ========== 测试 1: 普通客服 (cs) 尝试编辑退回批次 ==========
        print("\n" + "-" * 70)
        print("测试 1: 普通客服 (cs) 尝试编辑退回批次")
        print("预期: 返回 403 权限错误，状态不变")
        switch_role('cs', 'cs_demo')
        history_before = get_history_count()
        resp = client.put(f'/api/batches/{batch_id}', json={
            'name': '被篡改的名称',
            'description': '恶意修改',
            'ticket_ids': [1]
        })
        data = resp.get_json()
        print(f"  状态码: {resp.status_code}")
        print(f"  错误信息: {data.get('error', '')}")

        check(resp.status_code == 403 and '权限不足' in data.get('error', ''),
              "正确返回 403 权限错误",
              f"预期 403，实际 {resp.status_code}")

        check(get_history_count() == history_before,
              "没有新增历史记录",
              "不应新增历史记录")

        resp = client.get(f'/api/batches/{batch_id}')
        batch_data = resp.get_json()['data']
        check(batch_data['status'] == 'returned',
              "批次状态仍为 returned",
              f"批次状态变为 {batch_data['status']}")
        check(batch_data['name'] == '测试批次',
              "批次名称未被修改",
              f"批次名称被修改为 {batch_data['name']}")

        # ========== 测试 2: 普通客服 (cs) 尝试重新提交退回批次 ==========
        print("\n" + "-" * 70)
        print("测试 2: 普通客服 (cs) 尝试重新提交退回批次")
        print("预期: 返回 403 权限错误，状态不变")
        history_before = get_history_count()
        resp = client.post(f'/api/batches/{batch_id}/resubmit')
        data = resp.get_json()
        print(f"  状态码: {resp.status_code}")
        print(f"  错误信息: {data.get('error', '')}")

        check(resp.status_code == 403 and '权限不足' in data.get('error', ''),
              "正确返回 403 权限错误",
              f"预期 403，实际 {resp.status_code}")

        check(get_history_count() == history_before,
              "没有新增历史记录",
              "不应新增历史记录")

        resp = client.get(f'/api/batches/{batch_id}')
        batch_data = resp.get_json()['data']
        check(batch_data['status'] == 'returned',
              "批次状态仍为 returned",
              f"批次状态变为 {batch_data['status']}")

        # ========== 测试 3: 接班人 (receiver) 尝试编辑退回批次 ==========
        print("\n" + "-" * 70)
        print("测试 3: 接班人 (receiver) 尝试编辑退回批次")
        print("预期: 返回 403 权限错误，状态不变")
        switch_role('receiver', 'receiver_demo')
        history_before = get_history_count()
        resp = client.put(f'/api/batches/{batch_id}', json={
            'name': '被篡改的名称',
            'ticket_ids': [1]
        })
        data = resp.get_json()
        print(f"  状态码: {resp.status_code}")
        print(f"  错误信息: {data.get('error', '')}")

        check(resp.status_code == 403 and '权限不足' in data.get('error', ''),
              "正确返回 403 权限错误",
              f"预期 403，实际 {resp.status_code}")

        check(get_history_count() == history_before,
              "没有新增历史记录",
              "不应新增历史记录")

        # ========== 测试 4: 接班人 (receiver) 尝试重新提交退回批次 ==========
        print("\n" + "-" * 70)
        print("测试 4: 接班人 (receiver) 尝试重新提交退回批次")
        print("预期: 返回 403 权限错误，状态不变")
        history_before = get_history_count()
        resp = client.post(f'/api/batches/{batch_id}/resubmit')
        data = resp.get_json()
        print(f"  状态码: {resp.status_code}")
        print(f"  错误信息: {data.get('error', '')}")

        check(resp.status_code == 403 and '权限不足' in data.get('error', ''),
              "正确返回 403 权限错误",
              f"预期 403，实际 {resp.status_code}")

        check(get_history_count() == history_before,
              "没有新增历史记录",
              "不应新增历史记录")

        # ========== 测试 5: 交班人 (handover) 编辑退回批次 ==========
        print("\n" + "-" * 70)
        print("测试 5: 交班人 (handover) 编辑退回批次 - 修改名称、描述和工单")
        print("预期: 返回 200 成功，信息更新，写历史")
        switch_role('handover', 'handover_demo')
        history_before = get_history_count()
        resp = client.put(f'/api/batches/{batch_id}', json={
            'name': '测试批次-已整改',
            'description': '已补充完整信息，调整了工单清单',
            'ticket_ids': [1, 2, 3]
        })
        data = resp.get_json()
        print(f"  状态码: {resp.status_code}")
        if resp.status_code == 200:
            print(f"  批次名称: {data['data']['name']}")
            print(f"  工单数量: {len(data['data']['ticket_ids'])}")

        check(resp.status_code == 200 and data.get('success'),
              "编辑成功",
              f"预期 200，实际 {resp.status_code}")

        check(get_history_count() == history_before + 1,
              "正确新增 1 条历史记录",
              f"历史记录数变化不正确")

        resp = client.get(f'/api/batches/{batch_id}')
        batch_data = resp.get_json()['data']
        check(batch_data['status'] == 'returned',
              "批次状态仍为 returned（编辑不改变状态）",
              f"批次状态变为 {batch_data['status']}")
        check(batch_data['name'] == '测试批次-已整改',
              "批次名称已更新",
              f"批次名称为 {batch_data['name']}")
        check(batch_data['description'] == '已补充完整信息，调整了工单清单',
              "批次描述已更新",
              f"批次描述为 {batch_data['description']}")
        check(set(batch_data['ticket_ids']) == {1, 2, 3},
              "工单列表已更新",
              f"工单列表为 {batch_data['ticket_ids']}")

        # ========== 测试 6: 重新提交包含已关闭工单的批次 - 应失败 ==========
        print("\n" + "-" * 70)
        print("测试 6: 重新提交包含已关闭工单的批次")
        print("预期: 返回 400 错误，提示工单已关闭")

        switch_role('handover', 'handover_demo')
        resp = client.post('/api/tickets/1/close')
        print(f"  关闭工单 1，状态码: {resp.status_code}")

        history_before = get_history_count()
        resp = client.post(f'/api/batches/{batch_id}/resubmit')
        data = resp.get_json()
        print(f"  状态码: {resp.status_code}")
        print(f"  错误信息: {data.get('error', '')}")

        check(resp.status_code == 400 and '已关闭' in data.get('error', ''),
              "正确返回 400 错误，提示工单已关闭",
              f"预期 400，实际 {resp.status_code}")

        check(get_history_count() == history_before,
              "没有新增历史记录",
              "不应新增历史记录")

        resp = client.get(f'/api/batches/{batch_id}')
        batch_data = resp.get_json()['data']
        check(batch_data['status'] == 'returned',
              "批次状态仍为 returned",
              f"批次状态变为 {batch_data['status']}")

        # ========== 测试 7: 编辑时移除关闭工单，再重新提交 ==========
        print("\n" + "-" * 70)
        print("测试 7: 编辑移除已关闭工单后重新提交")
        print("预期: 返回 200 成功，状态变为 pending")
        time.sleep(1.1)
        history_before = get_history_count()
        resp = client.put(f'/api/batches/{batch_id}', json={
            'ticket_ids': [2, 3]
        })
        print(f"  编辑移除工单 1，状态码: {resp.status_code}")

        time.sleep(1.1)
        resp = client.post(f'/api/batches/{batch_id}/resubmit')
        data = resp.get_json()
        print(f"  状态码: {resp.status_code}")
        if resp.status_code == 200:
            print(f"  批次状态: {data['data']['status']}")

        check(resp.status_code == 200 and data.get('data', {}).get('status') == 'pending',
              "重新提交成功，状态变为 pending",
              f"预期 200，实际 {resp.status_code}")

        history_after = get_history_count()
        check(history_after == history_before + 2,
              f"正确新增 2 条历史记录（编辑+重新提交），从 {history_before} 到 {history_after}",
              f"历史记录从 {history_before} 变为 {history_after}，预期 +2")

        resp = client.get(f'/api/batches/{batch_id}')
        batch_data = resp.get_json()['data']
        check(batch_data['status'] == 'pending',
              "批次状态为 pending",
              f"批次状态为 {batch_data['status']}")
        check(batch_data['receiver_person'] is None,
              "接班人已清空",
              f"接班人为 {batch_data['receiver_person']}")
        check(set(batch_data['ticket_ids']) == {2, 3},
              "工单列表正确",
              f"工单列表为 {batch_data['ticket_ids']}")

        # ========== 测试 8: 确认重新提交后的批次 ==========
        print("\n" + "-" * 70)
        print("测试 8: 接班人确认重新提交后的批次")
        print("预期: 返回 200 成功，状态变为 confirmed")
        switch_role('receiver', 'receiver_demo')
        history_before = get_history_count()
        resp = client.post(f'/api/batches/{batch_id}/confirm', json={
            'receiver_person': 'receiver_demo'
        })
        data = resp.get_json()
        print(f"  状态码: {resp.status_code}")

        check(resp.status_code == 200 and data.get('data', {}).get('status') == 'confirmed',
              "确认成功，状态变为 confirmed",
              f"预期 200，实际 {resp.status_code}")

        check(get_history_count() == history_before + 1,
              "正确新增 1 条历史记录",
              f"历史记录数变化不正确")

        # ========== 测试 9: 冲突测试 - 工单在其他待确认批次中 ==========
        print("\n" + "-" * 70)
        print("测试 9: 冲突测试 - 工单被其他待确认批次占用")
        print("预期: 返回 400 错误，提示工单在其他批次中")

        batch_id2 = create_test_batch([3])
        return_batch(batch_id2, '退回另一个批次')

        batch_id3 = create_test_batch([3])
        print(f"  创建另一个待确认批次 {batch_id3}，包含工单 3")

        switch_role('handover', 'handover_demo')
        time.sleep(1.1)
        history_before = get_history_count()
        resp = client.post(f'/api/batches/{batch_id2}/resubmit')
        data = resp.get_json()
        print(f"  状态码: {resp.status_code}")
        print(f"  错误信息: {data.get('error', '')}")

        check(resp.status_code == 400 and '已在另一个待确认' in data.get('error', ''),
              "正确返回 400 错误，提示工单冲突",
              f"预期 400，实际 {resp.status_code}")

        check(get_history_count() == history_before,
              "没有新增历史记录",
              "不应新增历史记录")

        resp = client.get(f'/api/batches/{batch_id2}')
        batch_data2 = resp.get_json()['data']
        check(batch_data2['status'] == 'returned',
              "批次状态仍为 returned",
              f"批次状态变为 {batch_data2['status']}")

        # ========== 测试 10: 导出数据验证最新状态 ==========
        print("\n" + "-" * 70)
        print("测试 10: 导出批次数据验证最新状态")
        print("预期: 导出数据反映最新状态")
        resp = client.get('/api/export/batches?format=json')
        export_data = json.loads(resp.data.decode('utf-8'))
        print(f"  导出版本数: {len(export_data)}")

        exported_batch = next((b for b in export_data if b['ID'] == batch_id), None)
        check(exported_batch is not None and exported_batch['状态'] == 'confirmed',
              f"导出批次 {batch_id} 状态为 confirmed",
              f"导出状态不正确")

        exported_batch2 = next((b for b in export_data if b['ID'] == batch_id2), None)
        check(exported_batch2 is not None and exported_batch2['状态'] == 'returned',
              f"导出批次 {batch_id2} 状态为 returned",
              f"导出状态不正确: {exported_batch2['状态'] if exported_batch2 else 'None'}")

        # ========== 测试 11: 跨重启数据持久化 ==========
        print("\n" + "-" * 70)
        print("测试 11: 跨重启数据持久化验证")
        print("预期: 重启后批次状态、工单关系、历史记录仍正确")

        state_before = {
            'batch1': {
                'id': batch_id,
                'status': 'confirmed',
                'ticket_ids': set(batch_data['ticket_ids']),
                'name': batch_data['name'],
                'description': batch_data['description'],
            },
            'batch2': {
                'id': batch_id2,
                'status': 'returned',
            },
            'batch3': {
                'id': batch_id3,
                'status': 'pending',
            },
            'history_count': get_history_count()
        }

        print(f"  保存当前状态: 批次 {batch_id}={state_before['batch1']['status']}, "
              f"批次 {batch_id2}={state_before['batch2']['status']}, "
              f"批次 {batch_id3}={state_before['batch3']['status']}, "
              f"历史记录数={state_before['history_count']}")

        del app
        del client
        import gc
        gc.collect()

        print(f"  模拟服务重启，重新创建应用...")
        sys.path.insert(0, '.')
        from backend.app import create_app
        from backend.models import db

        app2 = create_app()
        client2 = app2.test_client()

        with app2.app_context():
            db.session.remove()

        switch_role2 = lambda r, u: client2.post('/api/switch-role', json={'role': r, 'username': u})
        switch_role2('handover', 'handover_demo')

        resp = client2.get(f'/api/batches/{batch_id}')
        batch1_after = resp.get_json()['data']
        print(f"  重启后批次 {batch_id} 状态: {batch1_after['status']}")

        check(batch1_after['status'] == state_before['batch1']['status'],
              f"批次 {batch_id} 状态正确: {batch1_after['status']}",
              f"批次 {batch_id} 状态应为 {state_before['batch1']['status']}，实际 {batch1_after['status']}")

        check(batch1_after['name'] == state_before['batch1']['name'],
              "批次名称保留",
              f"批次名称应为 {state_before['batch1']['name']}")

        check(batch1_after['description'] == state_before['batch1']['description'],
              "批次描述保留",
              "批次描述不匹配")

        check(set(batch1_after['ticket_ids']) == state_before['batch1']['ticket_ids'],
              "工单关系保留",
              f"工单列表应为 {state_before['batch1']['ticket_ids']}")

        resp = client2.get(f'/api/batches/{batch_id2}')
        batch2_after = resp.get_json()['data']
        print(f"  重启后批次 {batch_id2} 状态: {batch2_after['status']}")

        check(batch2_after['status'] == state_before['batch2']['status'],
              f"批次 {batch_id2} 状态正确: {batch2_after['status']}",
              f"批次 {batch_id2} 状态应为 {state_before['batch2']['status']}")

        resp = client2.get(f'/api/batches/{batch_id3}')
        batch3_after = resp.get_json()['data']
        print(f"  重启后批次 {batch_id3} 状态: {batch3_after['status']}")

        check(batch3_after['status'] == state_before['batch3']['status'],
              f"批次 {batch_id3} 状态正确: {batch3_after['status']}",
              f"批次 {batch_id3} 状态应为 {state_before['batch3']['status']}")

        resp = client2.get('/api/history')
        history_after = len(resp.get_json()['data'])
        print(f"  重启后历史记录数: {history_after}")

        check(history_after == state_before['history_count'],
              f"历史记录数正确: {history_after}",
              f"历史记录数应为 {state_before['history_count']}，实际 {history_after}")

        resp = client2.get('/api/export/batches?format=json')
        export_after = json.loads(resp.data.decode('utf-8'))
        export_batch1 = next((b for b in export_after if b['ID'] == batch_id), None)
        check(export_batch1 is not None and export_batch1['状态'] == 'confirmed',
              "导出数据重启后仍正确",
              "导出数据不正确")

    except Exception as e:
        print(f"\n{ERROR} 测试执行过程中发生异常: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(4)

    print("\n" + "=" * 70)
    print(f"测试结果: {passed} 通过, {failed} 失败")
    print("=" * 70)

    if failed == 0:
        print(f"\n{INFO} 所有测试全部通过！退回后整改再提交流程完整！")
        return True
    else:
        print(f"\n{FAIL} 有 {failed} 个测试失败，请检查代码。")
        return False


if __name__ == '__main__':
    print(f"{INFO} 正在清理测试环境...")
    cleanup_database()

    try:
        success = run_tests()
        cleanup_database()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print(f"\n{INFO} 测试被用户中断")
        sys.exit(130)
    except Exception as e:
        print(f"\n{ERROR} 测试运行失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(99)

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

    def create_test_batch():
        switch_role('handover', 'handover_demo')
        resp = client.post('/api/batches', json={
            'name': '权限测试批次',
            'description': '用于权限测试',
            'ticket_ids': [2, 3],
            'handover_person': '交班老李'
        })
        if resp.status_code != 201:
            raise RuntimeError(f"创建测试批次失败: {resp.status_code}")
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

"""
交接批次权限回归测试
测试场景：
1. 普通客服确认批次 - 应失败
2. 交班人确认批次 - 应失败
3. 接班人确认批次 - 应成功
4. 重复确认批次 - 应失败且不写重复历史
5. 普通客服退回批次 - 应失败
6. 交班人退回批次 - 应失败
"""
import sys
sys.path.insert(0, '.')

from backend.app import create_app
from backend.models import db

app = create_app()
client = app.test_client()


def switch_role(role, username):
    resp = client.post('/api/switch-role', json={'role': role, 'username': username})
    assert resp.status_code == 200
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
    assert resp.status_code == 201
    return resp.get_json()['data']['id']


def run_tests():
    print("=" * 60)
    print("交接批次权限漏洞回归测试")
    print("=" * 60)

    with app.app_context():
        db.drop_all()
        db.create_all()
        from backend.app import init_sample_data
        init_sample_data()

    passed = 0
    failed = 0

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

    if resp.status_code == 403 and '权限不足' in data.get('error', ''):
        print("  ✅ PASS: 正确返回 403 权限错误")
        passed += 1
    else:
        print(f"  ❌ FAIL: 预期 403，实际 {resp.status_code}")
        failed += 1

    history_after = get_history_count()
    if history_after == history_before_test:
        print("  ✅ PASS: 没有新增历史记录")
        passed += 1
    else:
        print(f"  ❌ FAIL: 历史记录从 {history_before_test} 变为 {history_after}")
        failed += 1

    resp = client.get(f'/api/batches/{batch_id}')
    batch_data = resp.get_json()['data']
    if batch_data['status'] == 'pending':
        print("  ✅ PASS: 批次状态仍为 pending")
        passed += 1
    else:
        print(f"  ❌ FAIL: 批次状态变为 {batch_data['status']}")
        failed += 1
    if batch_data['receiver_person'] is None:
        print("  ✅ PASS: 接班人未被修改")
        passed += 1
    else:
        print(f"  ❌ FAIL: 接班人被修改为 {batch_data['receiver_person']}")
        failed += 1

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

    if resp.status_code == 403 and '权限不足' in data.get('error', ''):
        print("  ✅ PASS: 正确返回 403 权限错误")
        passed += 1
    else:
        print(f"  ❌ FAIL: 预期 403，实际 {resp.status_code}")
        failed += 1

    history_after = get_history_count()
    if history_after == history_before_test:
        print("  ✅ PASS: 没有新增历史记录")
        passed += 1
    else:
        print(f"  ❌ FAIL: 历史记录从 {history_before_test} 变为 {history_after}")
        failed += 1

    resp = client.get(f'/api/batches/{batch_id}')
    batch_data = resp.get_json()['data']
    if batch_data['status'] == 'pending':
        print("  ✅ PASS: 批次状态仍为 pending")
        passed += 1
    else:
        print(f"  ❌ FAIL: 批次状态变为 {batch_data['status']}")
        failed += 1

    # ========== 测试 3: 接班人确认批次 ==========
    print("\n" + "-" * 60)
    print("测试 3: 接班人 (receiver) 确认批次")
    print("预期: 返回 200 成功，状态变为 confirmed，写历史")
    switch_role('receiver', 'receiver_demo')
    history_before_test = get_history_count()
    resp = client.post(f'/api/batches/{batch_id}/confirm', json={})
    data = resp.get_json()
    print(f"  状态码: {resp.status_code}")
    print(f"  批次状态: {data['data']['status']}")

    if resp.status_code == 200 and data['data']['status'] == 'confirmed':
        print("  ✅ PASS: 确认成功，状态变为 confirmed")
        passed += 1
    else:
        print(f"  ❌ FAIL: 预期 200，实际 {resp.status_code}")
        failed += 1

    history_after = get_history_count()
    if history_after == history_before_test + 1:
        print("  ✅ PASS: 正确新增 1 条历史记录")
        passed += 1
    else:
        print(f"  ❌ FAIL: 历史记录从 {history_before_test} 变为 {history_after}，预期 +1")
        failed += 1

    resp = client.get(f'/api/batches/{batch_id}')
    batch_data = resp.get_json()['data']
    if batch_data['receiver_person'] in ('接班小张', 'receiver_demo'):
        print(f"  ✅ PASS: 接班人正确设置为 {batch_data['receiver_person']}")
        passed += 1
    else:
        print(f"  ❌ FAIL: 接班人为 {batch_data['receiver_person']}")
        failed += 1
    if batch_data['confirmed_at'] is not None:
        print("  ✅ PASS: 确认时间已设置")
        passed += 1
    else:
        print("  ❌ FAIL: 确认时间为空")
        failed += 1

    # ========== 测试 4: 重复确认 ==========
    print("\n" + "-" * 60)
    print("测试 4: 接班人重复确认批次")
    print("预期: 返回 400 错误，不写重复历史")
    history_before_test = get_history_count()
    resp = client.post(f'/api/batches/{batch_id}/confirm', json={})
    data = resp.get_json()
    print(f"  状态码: {resp.status_code}")
    print(f"  错误信息: {data.get('error', '')}")

    if resp.status_code == 400 and '重复确认' in data.get('error', ''):
        print("  ✅ PASS: 正确返回 400 错误")
        passed += 1
    else:
        print(f"  ❌ FAIL: 预期 400，实际 {resp.status_code}")
        failed += 1

    history_after = get_history_count()
    if history_after == history_before_test:
        print("  ✅ PASS: 没有重复写历史")
        passed += 1
    else:
        print(f"  ❌ FAIL: 历史记录从 {history_before_test} 变为 {history_after}")
        failed += 1

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

    if resp.status_code == 403 and '权限不足' in data.get('error', ''):
        print("  ✅ PASS: 正确返回 403 权限错误")
        passed += 1
    else:
        print(f"  ❌ FAIL: 预期 403，实际 {resp.status_code}")
        failed += 1

    history_after = get_history_count()
    if history_after == history_before_test:
        print("  ✅ PASS: 没有新增历史记录")
        passed += 1
    else:
        print(f"  ❌ FAIL: 历史记录从 {history_before_test} 变为 {history_after}")
        failed += 1

    # 测试 5b: 交班人退回批次
    print("\n测试 5b: 交班人 (handover) 尝试退回批次")
    print("预期: 返回 403 权限错误")
    switch_role('handover', 'handover_demo')
    history_before_test = get_history_count()
    resp = client.post(f'/api/batches/{batch_id2}/return', json={'reason': '测试退回'})
    data = resp.get_json()
    print(f"  状态码: {resp.status_code}")
    print(f"  错误信息: {data.get('error', '')}")

    if resp.status_code == 403 and '权限不足' in data.get('error', ''):
        print("  ✅ PASS: 正确返回 403 权限错误")
        passed += 1
    else:
        print(f"  ❌ FAIL: 预期 403，实际 {resp.status_code}")
        failed += 1

    history_after = get_history_count()
    if history_after == history_before_test:
        print("  ✅ PASS: 没有新增历史记录")
        passed += 1
    else:
        print(f"  ❌ FAIL: 历史记录从 {history_before_test} 变为 {history_after}")
        failed += 1

    # 测试 5c: 接班人退回批次
    print("\n测试 5c: 接班人 (receiver) 退回批次")
    print("预期: 返回 200 成功")
    switch_role('receiver', 'receiver_demo')
    history_before_test = get_history_count()
    resp = client.post(f'/api/batches/{batch_id2}/return', json={'reason': '退回原因测试'})
    data = resp.get_json()
    print(f"  状态码: {resp.status_code}")

    if resp.status_code == 200 and data['data']['status'] == 'returned':
        print("  ✅ PASS: 退回成功")
        passed += 1
    else:
        print(f"  ❌ FAIL: 预期 200，实际 {resp.status_code}")
        failed += 1

    history_after = get_history_count()
    if history_after == history_before_test + 1:
        print("  ✅ PASS: 正确新增 1 条历史记录")
        passed += 1
    else:
        print(f"  ❌ FAIL: 历史记录从 {history_before_test} 变为 {history_after}")
        failed += 1

    # ========== 测试结果汇总 ==========
    print("\n" + "=" * 60)
    print(f"测试结果: {passed} 通过, {failed} 失败")
    print("=" * 60)

    if failed == 0:
        print("\n🎉 所有测试全部通过！权限漏洞已修复！")
    else:
        print(f"\n⚠️  有 {failed} 个测试失败，请检查代码。")

    return failed == 0


if __name__ == '__main__':
    import os
    try:
        if os.path.exists('backend/data.db'):
            os.remove('backend/data.db')
    except:
        pass
    success = run_tests()
    sys.exit(0 if success else 1)

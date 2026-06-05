"""
值班排班模块回归测试
覆盖场景：
1. 跨重启数据保留
2. 同一值班人时间重叠冲突拒绝
3. 停用被未完成批次引用的班次拒绝
4. 权限拒绝：cs/handover 角色不能新建/编辑/停用排班
5. CSV 导入导出一致性
6. 跨天班次按日期查询
7. 接班人必须匹配班次值班人
"""
import sys
import os
import io
import csv

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
            print(f"{ERROR} 详细错误: {e}")
            sys.exit(2)
        except Exception as e:
            print(f"\n{ERROR} 删除数据库文件失败: {DB_PATH}")
            print(f"{ERROR} 详细错误: {e}")
            sys.exit(2)


def run_tests():
    sys.path.insert(0, '.')
    from backend.app import create_app, init_sample_data
    from backend.models import db

    print(f"{INFO} 正在清理测试环境...")
    cleanup_database()

    try:
        app = create_app()
        client = app.test_client()
    except Exception as e:
        print(f"\n{ERROR} 初始化 Flask 应用失败: {e}")
        sys.exit(3)

    print("=" * 60)
    print("值班排班模块回归测试")
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

    def check(condition, pass_msg, fail_msg):
        nonlocal passed, failed
        if condition:
            print(f"  {PASS} {pass_msg}")
            passed += 1
        else:
            print(f"  {FAIL} {fail_msg}")
            failed += 1

    switch_role('receiver', 'receiver_demo')

    print("\n--- 场景 1：权限拒绝（cs/handover 不能管理排班）---")

    switch_role('cs', 'cs_demo')
    resp = client.post('/api/shifts', json={
        'name': '越权测试班次',
        'duty_person': '测试员',
        'start_time': '2025-03-01T09:00:00',
        'end_time': '2025-03-01T17:00:00',
        'allowed_severities': ['low'],
    })
    check(resp.status_code == 403,
          f"普通客服创建班次返回 403 (实际: {resp.status_code})",
          f"普通客服越权创建班次应返回 403，实际: {resp.status_code}, {resp.get_json()}")

    switch_role('handover', 'handover_demo')
    resp = client.post('/api/shifts', json={
        'name': '越权测试班次2',
        'duty_person': '测试员',
        'start_time': '2025-03-01T09:00:00',
        'end_time': '2025-03-01T17:00:00',
    })
    check(resp.status_code == 403,
          f"交班人创建班次返回 403 (实际: {resp.status_code})",
          f"交班人越权创建班次应返回 403，实际: {resp.status_code}, {resp.get_json()}")

    switch_role('receiver', 'receiver_demo')
    resp = client.post('/api/shifts', json={
        'name': '正常测试班次',
        'duty_person': '张值班',
        'start_time': '2025-03-01T09:00:00',
        'end_time': '2025-03-01T17:00:00',
        'allowed_severities': ['low', 'medium'],
    })
    check(resp.status_code == 201,
          f"接班人创建班次返回 201 (实际: {resp.status_code})",
          f"接班人创建班次应返回 201，实际: {resp.status_code}, {resp.get_json()}")

    shift_id_1 = resp.get_json()['data']['id']

    switch_role('cs', 'cs_demo')
    resp = client.put(f'/api/shifts/{shift_id_1}', json={'name': '越权修改'})
    check(resp.status_code == 403,
          f"普通客服编辑班次返回 403 (实际: {resp.status_code})",
          f"普通客服越权编辑应返回 403，实际: {resp.status_code}")

    switch_role('cs', 'cs_demo')
    resp = client.post(f'/api/shifts/{shift_id_1}/disable')
    check(resp.status_code == 403,
          f"普通客服停用班次返回 403 (实际: {resp.status_code})",
          f"普通客服越权停用应返回 403，实际: {resp.status_code}")

    switch_role('handover', 'handover_demo')
    resp = client.post(f'/api/shifts/{shift_id_1}/disable')
    check(resp.status_code == 403,
          f"交班人停用班次返回 403 (实际: {resp.status_code})",
          f"交班人越权停用应返回 403，实际: {resp.status_code}")

    switch_role('cs', 'cs_demo')
    resp = client.post('/api/shifts/import', data={}, content_type='multipart/form-data')
    check(resp.status_code == 403,
          f"普通客服导入 CSV 返回 403 (实际: {resp.status_code})",
          f"普通客服越权导入应返回 403，实际: {resp.status_code}")

    print("\n--- 场景 2：时间重叠冲突拒绝 ---")

    switch_role('receiver', 'receiver_demo')

    resp = client.post('/api/shifts', json={
        'name': '张值班-早班',
        'duty_person': '张值班',
        'start_time': '2025-03-02T08:00:00',
        'end_time': '2025-03-02T16:00:00',
    })
    check(resp.status_code == 201,
          f"创建张值班早班成功 (实际: {resp.status_code})",
          f"创建张值班早班应成功，实际: {resp.status_code}, {resp.get_json()}")

    resp = client.post('/api/shifts', json={
        'name': '张值班-重叠晚班',
        'duty_person': '张值班',
        'start_time': '2025-03-02T12:00:00',
        'end_time': '2025-03-02T20:00:00',
    })
    check(resp.status_code == 409,
          f"同一值班人时间重叠返回 409 (实际: {resp.status_code})",
          f"同一值班人时间重叠应返回 409，实际: {resp.status_code}, {resp.get_json()}")

    resp = client.post('/api/shifts', json={
        'name': '李值班-早班',
        'duty_person': '李值班',
        'start_time': '2025-03-02T08:00:00',
        'end_time': '2025-03-02T16:00:00',
    })
    check(resp.status_code == 201,
          f"不同值班人同时间段成功 (实际: {resp.status_code})",
          f"不同值班人同时间段应成功，实际: {resp.status_code}, {resp.get_json()}")

    print("\n--- 场景 3：停用被未完成批次引用的班次拒绝 ---")

    switch_role('receiver', 'receiver_demo')
    resp = client.post('/api/shifts', json={
        'name': '被引用班次',
        'duty_person': '被引用值班人',
        'start_time': '2025-03-10T08:00:00',
        'end_time': '2025-03-10T20:00:00',
    })
    check(resp.status_code == 201,
          f"创建被引用班次成功 (实际: {resp.status_code})",
          f"创建被引用班次失败: {resp.status_code}, {resp.get_json()}")
    referenced_shift_id = resp.get_json()['data']['id']

    switch_role('handover', 'handover_demo')
    resp = client.get('/api/tickets/open-for-handover')
    open_tickets = resp.get_json().get('data', [])
    if len(open_tickets) < 1:
        print(f"  {INFO} 无可用工单，跳过批次创建引用测试")
    else:
        ticket_id = open_tickets[0]['id']
        resp = client.post('/api/batches', json={
            'name': '引用班次的批次',
            'description': '测试停用冲突',
            'ticket_ids': [ticket_id],
            'handover_person': '交班老王',
            'shift_id': referenced_shift_id,
        })
        check(resp.status_code == 201,
              f"创建关联班次的批次成功 (实际: {resp.status_code})",
              f"创建关联班次的批次失败: {resp.status_code}, {resp.get_json()}")

        switch_role('receiver', 'receiver_demo')
        resp = client.post(f'/api/shifts/{referenced_shift_id}/disable')
        check(resp.status_code == 409,
              f"停用被引用班次返回 409 (实际: {resp.status_code})",
              f"停用被引用班次应返回 409，实际: {resp.status_code}, {resp.get_json()}")

    print("\n--- 场景 4：跨天班次按日期查询 ---")

    switch_role('receiver', 'receiver_demo')
    resp = client.post('/api/shifts', json={
        'name': '跨天支援班',
        'duty_person': '跨天值班',
        'start_time': '2025-03-05T22:00:00',
        'end_time': '2025-03-06T06:00:00',
    })
    check(resp.status_code == 201,
          f"创建跨天班次成功 (实际: {resp.status_code})",
          f"创建跨天班次失败: {resp.status_code}, {resp.get_json()}")

    resp = client.get('/api/shifts?date=2025-03-05')
    names_day1 = [s['name'] for s in resp.get_json().get('data', [])]
    check('跨天支援班' in names_day1,
          "按 2025-03-05 可查到跨天班次",
          f"按 2025-03-05 查不到跨天班次，实际: {names_day1}")

    resp = client.get('/api/shifts?date=2025-03-06')
    names_day2 = [s['name'] for s in resp.get_json().get('data', [])]
    check('跨天支援班' in names_day2,
          "按 2025-03-06 可查到跨天班次",
          f"按 2025-03-06 查不到跨天班次，实际: {names_day2}")

    resp = client.get('/api/shifts?date=2025-03-07')
    names_day3 = [s['name'] for s in resp.get_json().get('data', [])]
    check('跨天支援班' not in names_day3,
          "按 2025-03-07 查不到跨天班次",
          f"按 2025-03-07 不应查到跨天班次，实际: {names_day3}")

    print("\n--- 场景 5：接班人必须匹配班次值班人 ---")

    switch_role('receiver', 'receiver_demo')
    resp = client.post('/api/shifts', json={
        'name': '确认人校验班次',
        'duty_person': '指定确认人',
        'start_time': '2025-03-15T08:00:00',
        'end_time': '2025-03-15T20:00:00',
    })
    confirm_shift_id = resp.get_json()['data']['id']

    switch_role('handover', 'handover_demo')
    resp = client.get('/api/tickets/open-for-handover')
    open_tickets = resp.get_json().get('data', [])
    if len(open_tickets) < 2:
        print(f"  {INFO} 可用工单不足，跳过接班人校验测试")
    else:
        ticket_ids = [t['id'] for t in open_tickets[:2]]
        resp = client.post('/api/batches', json={
            'name': '确认人校验批次',
            'ticket_ids': ticket_ids,
            'handover_person': '交班老李',
            'shift_id': confirm_shift_id,
        })
        confirm_batch_id = resp.get_json()['data']['id']

        switch_role('receiver', 'receiver_demo')
        resp = client.post(f'/api/batches/{confirm_batch_id}/confirm', json={
            'receiver_person': '非指定确认人',
        })
        check(resp.status_code == 400,
              f"非班次值班人确认返回 400 (实际: {resp.status_code})",
              f"非班次值班人确认应返回 400，实际: {resp.status_code}, {resp.get_json()}")

        resp = client.post(f'/api/batches/{confirm_batch_id}/confirm', json={
            'receiver_person': '指定确认人',
        })
        check(resp.status_code == 200,
              f"班次值班人本人确认成功 (实际: {resp.status_code})",
              f"班次值班人本人确认应成功，实际: {resp.status_code}, {resp.get_json()}")

    print("\n--- 场景 6：CSV 导入导出一致性 ---")

    switch_role('receiver', 'receiver_demo')

    before_count = len(client.get('/api/shifts').get_json().get('data', []))

    csv_content = (
        "班次名称,值班人,开始时间,结束时间,可接收严重级别,是否启用\n"
        "导入早班,导入甲,2025-04-01 08:00,2025-04-01 16:00,\"low,medium\",1\n"
        "导入晚班,导入乙,2025-04-01 16:00,2025-04-02 00:00,\"high,critical\",1\n"
    )
    data = {'file': (io.BytesIO(csv_content.encode('utf-8')), 'shifts.csv')}
    resp = client.post('/api/shifts/import', data=data, content_type='multipart/form-data')
    check(resp.status_code == 200,
          f"CSV 导入成功 (实际: {resp.status_code})",
          f"CSV 导入失败: {resp.status_code}, {resp.get_json()}")

    resp = client.get('/api/shifts')
    after_list = resp.get_json().get('data', [])
    imported_names = [s['name'] for s in after_list]
    check('导入早班' in imported_names and '导入晚班' in imported_names,
          "导入后列表中包含两条新班次",
          f"导入后列表应含两条新班次，实际班次: {imported_names}")

    bad_csv = (
        "班次名称,值班人,开始时间,结束时间,可接收严重级别,是否启用\n"
        "好班次,导入丙,2025-04-02 08:00,2025-04-02 16:00,,1\n"
        "坏班次,导入甲,2025-04-01 10:00,2025-04-01 14:00,,1\n"
    )
    bad_count_before = len(client.get('/api/shifts').get_json().get('data', []))
    data = {'file': (io.BytesIO(bad_csv.encode('utf-8')), 'bad_shifts.csv')}
    resp = client.post('/api/shifts/import', data=data, content_type='multipart/form-data')
    bad_count_after = len(client.get('/api/shifts').get_json().get('data', []))
    check(resp.status_code == 409 and bad_count_before == bad_count_after,
          f"含冲突行导入返回 409 且全部回滚（行数不变: {bad_count_before}）",
          f"含冲突行导入应回滚，状态码: {resp.status_code}, 行数: {bad_count_before} -> {bad_count_after}")

    resp = client.get('/api/shifts/export')
    check(resp.status_code == 200 and 'text/csv' in resp.content_type,
          f"CSV 导出成功 (实际: {resp.status_code}, type: {resp.content_type})",
          f"CSV 导出失败: {resp.status_code}")

    print("\n--- 场景 7：跨重启数据保留 ---")

    shifts_before = sorted(client.get('/api/shifts').get_json().get('data', []), key=lambda s: s['id'])

    del client
    del app
    import gc
    gc.collect()

    app2 = create_app()
    client2 = app2.test_client()

    with app2.app_context():
        from backend.models import db as db2
        db2.create_all()

    client2.post('/api/switch-role', json={'role': 'receiver', 'username': 'receiver_demo'})
    shifts_after = sorted(client2.get('/api/shifts').get_json().get('data', []), key=lambda s: s['id'])

    check(len(shifts_before) == len(shifts_after),
          f"跨重启后班次数量一致 ({len(shifts_before)})",
          f"跨重启后班次数量不一致: 前 {len(shifts_before)}, 后 {len(shifts_after)}")

    ids_before = [s['id'] for s in shifts_before]
    ids_after = [s['id'] for s in shifts_after]
    check(ids_before == ids_after,
          "跨重启后班次 ID 完全一致",
          f"跨重启后班次 ID 不一致: 前 {ids_before}, 后 {ids_after}")

    names_before = [s['name'] for s in shifts_before]
    names_after = [s['name'] for s in shifts_after]
    check(names_before == names_after,
          "跨重启后班次名称完全一致",
          f"跨重启后班次名称不一致: 前 {names_before}, 后 {names_after}")

    print("\n" + "=" * 60)
    print(f"测试结果: {passed} 通过, {failed} 失败")
    print("=" * 60)

    if failed > 0:
        print(f"\n{ERROR} 存在失败的测试用例，请检查")
        sys.exit(1)
    else:
        print(f"\n{INFO} 所有测试全部通过！值班排班模块功能正常！")


if __name__ == '__main__':
    run_tests()

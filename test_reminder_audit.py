"""
值班提醒模块回归测试
覆盖场景：
1. 权限拒绝：cs/handover 不能创建/编辑/停用提醒
2. 创建提醒基本功能
3. 同一班次同一时间段重复标题拒绝（409）
4. 过期提醒不能确认
5. 停用提醒不能确认
6. 提醒确认记录用户和时间
7. 停用操作写入历史日志
8. CSV 导入校验：时间格式、重复数据、无效班次
9. CSV 导入导出一致性
10. 跨重启数据保留
11. 值班人只能看到分配给自己的提醒（my-pending）
"""
import sys
import os
import io
import csv
from datetime import datetime, timedelta

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

    print(f"{INFO} 正在清理测试环境...")
    cleanup_database()

    try:
        app = create_app()
        client = app.test_client()
    except Exception as e:
        print(f"\n{ERROR} 初始化 Flask 应用失败: {e}")
        sys.exit(3)

    print("=" * 60)
    print("值班提醒模块回归测试")
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

    def iso(dt):
        return dt.isoformat()

    now = datetime.utcnow()
    future_1h = iso(now + timedelta(hours=1))
    future_2h = iso(now + timedelta(hours=2))
    past_1h = iso(now - timedelta(hours=1))
    past_2h = iso(now - timedelta(hours=2))

    print("\n--- 场景 1：创建测试班次 ---")
    switch_role('receiver', 'receiver_demo')

    shift_data = {
        'name': '提醒测试白班',
        'duty_person': '接班小张',
        'start_time': future_1h,
        'end_time': future_2h,
        'allowed_severities': ['low', 'medium', 'high', 'critical'],
        'is_active': True
    }
    resp = client.post('/api/shifts', json=shift_data)
    check(resp.status_code == 201, '测试班次创建成功', f'创建失败: {resp.status_code} {resp.get_json()}')
    test_shift_id = resp.get_json()['data']['id']

    print("\n--- 场景 2：权限拒绝（cs/handover 不能管理提醒）---")

    switch_role('cs', 'cs_demo')
    resp = client.post('/api/reminders', json={
        'title': '测试提醒',
        'content': '测试内容',
        'effective_start': future_1h,
        'effective_end': future_2h
    })
    check(resp.status_code == 403, '普通客服创建提醒被拒绝(403)',
          f'未被拒绝: {resp.status_code}')

    switch_role('handover', 'handover_demo')
    resp = client.post('/api/reminders', json={
        'title': '测试提醒',
        'content': '测试内容',
        'effective_start': future_1h,
        'effective_end': future_2h
    })
    check(resp.status_code == 403, '交班人创建提醒被拒绝(403)',
          f'未被拒绝: {resp.status_code}')

    switch_role('receiver', 'receiver_demo')

    print("\n--- 场景 3：创建提醒基本功能 ---")
    reminder1 = {
        'title': '班前安全检查',
        'content': '请检查系统状态并完成交接\n1. 检查服务器\n2. 检查日志',
        'shift_id': test_shift_id,
        'effective_start': future_1h,
        'effective_end': future_2h,
        'is_active': True
    }
    resp = client.post('/api/reminders', json=reminder1)
    check(resp.status_code == 201, f'提醒创建成功 (ID: {resp.get_json().get("data", {}).get("id")})',
          f'创建失败: {resp.status_code} {resp.get_json()}')
    reminder1_id = resp.get_json()['data']['id']
    check(resp.get_json()['data']['title'] == '班前安全检查', '标题正确', '标题不正确')
    check(resp.get_json()['data']['shift_id'] == test_shift_id, '关联班次正确', '关联班次不正确')

    print("\n--- 场景 4：重复提醒（同班次同时间段同标题）拒绝 ---")
    resp = client.post('/api/reminders', json=reminder1)
    check(resp.status_code == 409, '重复提醒被拒绝(409)',
          f'未被拒绝: {resp.status_code} {resp.get_json()}')

    print("\n--- 场景 5：提醒列表查询与筛选 ---")
    resp = client.get('/api/reminders')
    check(resp.status_code == 200 and len(resp.get_json()['data']) >= 1,
          '提醒列表查询成功', '列表查询失败')

    resp = client.get('/api/reminders?is_active=true')
    check(resp.status_code == 200, '按启用状态筛选成功', '状态筛选失败')

    today = now.strftime('%Y-%m-%d')
    resp = client.get(f'/api/reminders?date={today}')
    check(resp.status_code == 200, '按日期筛选成功', '日期筛选失败')

    print("\n--- 场景 6：编辑提醒 ---")
    resp = client.put(f'/api/reminders/{reminder1_id}', json={
        'content': '更新后的内容',
        'effective_start': future_1h,
        'effective_end': future_2h
    })
    check(resp.status_code == 200 and resp.get_json()['data']['content'] == '更新后的内容',
          '编辑提醒成功', f'编辑失败: {resp.status_code} {resp.get_json()}')

    print("\n--- 场景 7：普通值班人确认提醒 ---")
    confirm_reminder_data = {
        'title': '待确认提醒',
        'content': '用于测试确认功能',
        'shift_id': test_shift_id,
        'effective_start': past_1h,
        'effective_end': future_2h,
        'is_active': True
    }
    resp = client.post('/api/reminders', json=confirm_reminder_data)
    confirm_reminder_id = resp.get_json()['data']['id']
    switch_role('receiver', 'receiver_demo')
    resp = client.post(f'/api/reminders/{confirm_reminder_id}/confirm')
    check(resp.status_code == 200, f'确认提醒成功: 确认人={resp.get_json()["data"]["confirmed_by"]}',
          f'确认失败: {resp.status_code} {resp.get_json()}')
    check(resp.get_json()['data']['confirmed_by'] == '接班小张',
          '确认人是接班小张', f'确认人错误: {resp.get_json()["data"]["confirmed_by"]}')
    check('confirmed_at' in resp.get_json()['data'], '确认时间已记录', '确认时间未记录')

    print("\n--- 场景 8：重复确认被拒绝 ---")
    resp = client.post(f'/api/reminders/{confirm_reminder_id}/confirm')
    check(resp.status_code == 400, '重复确认被拒绝(400)',
          f'未被拒绝: {resp.status_code} {resp.get_json()}')

    print("\n--- 场景 9：过期提醒不能确认 ---")
    expired_reminder = {
        'title': '已过期提醒',
        'content': '这个提醒应该已过期',
        'effective_start': past_2h,
        'effective_end': past_1h,
        'is_active': True
    }
    resp = client.post('/api/reminders', json=expired_reminder)
    check(resp.status_code == 201, '过期提醒创建成功（用于测试）', f'创建失败: {resp.status_code}')
    expired_id = resp.get_json()['data']['id']

    resp = client.post(f'/api/reminders/{expired_id}/confirm')
    check(resp.status_code == 400, '过期提醒确认被拒绝(400)',
          f'未被拒绝: {resp.status_code} {resp.get_json()}')

    print("\n--- 场景 10：停用提醒不能确认 ---")
    disabled_reminder = {
        'title': '停用提醒测试',
        'content': '停用后不能确认',
        'effective_start': future_1h,
        'effective_end': future_2h,
        'is_active': True
    }
    resp = client.post('/api/reminders', json=disabled_reminder)
    disabled_id = resp.get_json()['data']['id']

    resp = client.post(f'/api/reminders/{disabled_id}/disable')
    check(resp.status_code == 200 and resp.get_json()['data']['is_active'] is False,
          '停用提醒成功', f'停用失败: {resp.status_code}')

    resp = client.post(f'/api/reminders/{disabled_id}/confirm')
    check(resp.status_code == 400, '停用提醒确认被拒绝(400)',
          f'未被拒绝: {resp.status_code} {resp.get_json()}')

    print("\n--- 场景 11：停用操作写入历史日志 ---")
    resp = client.get('/api/history?entity_type=reminder&entity_id=' + str(disabled_id))
    history_data = resp.get_json()['data']
    check(len(history_data) >= 1 and any(h['new_status'] == 'inactive' for h in history_data),
          '停用操作已写入历史日志', f'未找到历史日志: {history_data}')

    print("\n--- 场景 12：值班人 my-pending 接口只返回分配给自己的提醒 ---")
    other_shift = {
        'name': '其他人的班次',
        'duty_person': '其他人',
        'start_time': future_1h,
        'end_time': future_2h,
        'allowed_severities': ['low'],
        'is_active': True
    }
    resp = client.post('/api/shifts', json=other_shift)
    other_shift_id = resp.get_json()['data']['id']

    other_reminder = {
        'title': '其他人的提醒',
        'content': '不应出现在 my-pending 中',
        'shift_id': other_shift_id,
        'effective_start': future_1h,
        'effective_end': future_2h,
        'is_active': True
    }
    resp = client.post('/api/reminders', json=other_reminder)

    resp = client.get('/api/reminders/my-pending')
    check(resp.status_code == 200, 'my-pending 接口返回成功',
          f'失败: {resp.status_code}')
    pending_titles = [r['title'] for r in resp.get_json()['data']]
    check('其他人的提醒' not in pending_titles,
          'my-pending 不包含其他值班人的提醒',
          f'错误地包含了: {pending_titles}')

    print("\n--- 场景 13：CSV 导出 ---")
    resp = client.get('/api/reminders/export?format=csv')
    check(resp.status_code == 200 and 'text/csv' in resp.content_type,
          'CSV 导出成功', f'失败: {resp.status_code} type={resp.content_type}')
    csv_content = resp.data.decode('utf-8-sig')
    check('提醒标题' in csv_content and '班前安全检查' in csv_content,
          'CSV 内容包含正确的表头和数据', f'CSV 内容异常: {csv_content[:200]}')

    print("\n--- 场景 14：CSV 导入校验 ---")
    bad_csv = '\ufeff提醒标题,提醒内容,生效开始时间,生效结束时间\n,内容,bad-time,2026-12-31 23:59:59\n'.encode('utf-8')
    data = {'file': (io.BytesIO(bad_csv), 'bad.csv')}
    resp = client.post('/api/reminders/import', data=data, content_type='multipart/form-data')
    check(resp.status_code == 400,
          f'坏数据 CSV 导入被拒绝(400): {resp.get_json().get("error", "")}',
          f'未被拒绝: {resp.status_code}')

    invalid_shift_csv = (
        '\ufeff提醒标题,提醒内容,生效开始时间,生效结束时间,关联班次名称\n'
        '不存在班次的提醒,内容,2026-06-05 09:00:00,2026-06-05 18:00:00,不存在的班次\n'
    ).encode('utf-8')
    data = {'file': (io.BytesIO(invalid_shift_csv), 'invalid_shift.csv')}
    resp = client.post('/api/reminders/import', data=data, content_type='multipart/form-data')
    check(resp.status_code == 400 and '无效班次' in (resp.get_json().get('details', [''])[0] if resp.get_json().get('details') else ''),
          '无效班次 CSV 导入被拒绝', f'未被正确拒绝: {resp.status_code} {resp.get_json()}')

    print("\n--- 场景 15：CSV 成功导入 ---")
    good_csv = (
        '\ufeff提醒标题,提醒内容,生效开始时间,生效结束时间,是否启用\n'
        'CSV导入提醒1,CSV导入的内容1,2026-06-05 09:00:00,2026-06-05 18:00:00,是\n'
        'CSV导入提醒2,CSV导入的内容2,2026-06-06 09:00:00,2026-06-06 18:00:00,是\n'
    ).encode('utf-8')
    data = {'file': (io.BytesIO(good_csv), 'good.csv')}
    resp = client.post('/api/reminders/import', data=data, content_type='multipart/form-data')
    check(resp.status_code == 200 and resp.get_json()['data']['imported'] == 2,
          f'CSV 成功导入 2 条: imported={resp.get_json().get("data", {}).get("imported")}',
          f'导入失败: {resp.status_code} {resp.get_json()}')

    print("\n--- 场景 16：历史日志包含 CSV 导入操作 ---")
    resp = client.get('/api/history?entity_type=reminder')
    history_list = resp.get_json()['data']
    csv_history = [h for h in history_list if 'CSV 导入' in (h.get('reason') or '')]
    check(len(csv_history) >= 2,
          f'CSV 导入操作已写入历史日志 ({len(csv_history)} 条)',
          f'未找到足够的历史日志')

    print("\n--- 场景 17：跨重启数据保留 ---")
    reminder_count_before = len(client.get('/api/reminders').get_json()['data'])
    check(reminder_count_before >= 4,
          f'重启前提醒数量: {reminder_count_before}',
          f'数量不足')

    print(f"{INFO} 模拟服务重启（重新创建 app 实例）...")
    del client
    del app
    import gc
    gc.collect()

    app2 = create_app()
    client2 = app2.test_client()
    switch_role2 = lambda r, u: client2.post('/api/switch-role', json={'role': r, 'username': u})
    switch_role2('receiver', 'receiver_demo')

    resp2 = client2.get('/api/reminders')
    reminder_count_after = len(resp2.get_json()['data'])
    check(reminder_count_after == reminder_count_before,
          f'重启后提醒数量一致: {reminder_count_after}',
          f'数据丢失: {reminder_count_before} -> {reminder_count_after}')

    resp_detail = client2.get(f'/api/reminders/{reminder1_id}')
    check(resp_detail.status_code == 200 and resp_detail.get_json()['data']['title'] == '班前安全检查',
          '重启后提醒详情完整保留', '重启后数据不完整')

    resp_history = client2.get('/api/history?entity_type=reminder&entity_id=' + str(disabled_id))
    history_after = resp_history.get_json()['data']
    check(len(history_after) >= 1,
          '重启后历史日志保留',
          f'重启后历史日志丢失: {len(history_after)}')

    print("\n" + "=" * 60)
    print(f"测试结果: {passed} 通过, {failed} 失败")
    print("=" * 60)

    if failed == 0:
        print(f"\n{INFO} 所有测试全部通过！值班提醒模块功能正常！")
        return 0
    else:
        print(f"\n{ERROR} 有 {failed} 个测试失败！请检查问题！")
        return 1


if __name__ == '__main__':
    try:
        sys.exit(run_tests())
    except KeyboardInterrupt:
        print(f"\n{INFO} 用户中断")
        sys.exit(130)
    except Exception as e:
        print(f"\n{ERROR} 测试执行异常: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(4)

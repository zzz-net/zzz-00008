"""
升级预案库模块回归测试
覆盖场景：
1. 权限拒绝（cs/handover 不能维护预案）
2. 关键词同级别重复拒绝
3. 编辑生成新版本，旧版本仍可查看
4. 启用/停用逻辑
5. CSV 导入导出一致性、校验失败回滚
6. 工单引用预案写入日志
7. 跨重启数据保留
8. 按客户名/严重级别/关键词筛选
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
    print("升级预案库模块回归测试")
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

    print("\n--- 场景 1：权限拒绝（cs/handover 不能管理预案）---")

    switch_role('cs', 'cs_demo')
    resp = client.post('/api/plans', json={
        'title': '越权测试预案',
        'applicable_severity': 'high',
        'keywords': ['越权', '测试'],
        'steps': '测试步骤',
    })
    check(resp.status_code == 403,
          f"普通客服创建预案返回 403 (实际: {resp.status_code})",
          f"普通客服越权创建应返回 403，实际: {resp.status_code}, {resp.get_json()}")

    resp = client.post('/api/plans/import', data={}, content_type='multipart/form-data')
    check(resp.status_code == 403,
          f"普通客服导入 CSV 返回 403 (实际: {resp.status_code})",
          f"普通客服越权导入应返回 403，实际: {resp.status_code}")

    resp = client.get('/api/plans/export')
    check(resp.status_code == 403,
          f"普通客服导出 CSV 返回 403 (实际: {resp.status_code})",
          f"普通客服越权导出应返回 403，实际: {resp.status_code}")

    switch_role('handover', 'handover_demo')
    resp = client.post('/api/plans', json={
        'title': '越权测试预案2',
        'applicable_severity': 'medium',
        'keywords': ['交班人越权'],
        'steps': '步骤',
    })
    check(resp.status_code == 403,
          f"交班人创建预案返回 403 (实际: {resp.status_code})",
          f"交班人越权创建应返回 403，实际: {resp.status_code}")

    switch_role('receiver', 'receiver_demo')
    resp = client.post('/api/plans', json={
        'title': '高危客户登录异常处理',
        'applicable_severity': 'high',
        'keywords': ['登录异常', '客户A'],
        'steps': '1. 核实账号状态\n2. 联系客户确认',
        'assignee_suggestion': '张三',
        'is_active': True,
    })
    check(resp.status_code == 201,
          f"接班人创建预案返回 201 (实际: {resp.status_code})",
          f"接班人创建预案应返回 201，实际: {resp.status_code}, {resp.get_json()}")
    plan_1_id = resp.get_json()['data']['id']
    plan_1_group = resp.get_json()['data']['plan_group_id']

    switch_role('cs', 'cs_demo')
    resp = client.get('/api/plans')
    check(resp.status_code == 200 and len(resp.get_json().get('data', [])) >= 1,
          "普通客服可查看预案列表",
          f"普通客服查看预案列表失败: {resp.status_code}, {resp.get_json()}")

    print("\n--- 场景 2：关键词同级别重复拒绝 ---")

    switch_role('receiver', 'receiver_demo')
    resp = client.post('/api/plans', json={
        'title': '高危客户登录异常处理（重复关键词）',
        'applicable_severity': 'high',
        'keywords': ['客户A', '登录异常'],
        'steps': '不同的步骤',
    })
    check(resp.status_code == 409,
          f"同级别同关键词创建返回 409 (实际: {resp.status_code})",
          f"同级别完全相同关键词应返回 409，实际: {resp.status_code}, {resp.get_json()}")

    resp = client.post('/api/plans', json={
        'title': '中危客户登录异常处理',
        'applicable_severity': 'medium',
        'keywords': ['客户A', '登录异常'],
        'steps': '不同级别允许相同关键词',
    })
    check(resp.status_code == 201,
          f"不同级别相同关键词可成功创建 (实际: {resp.status_code})",
          f"不同级别相同关键词应可创建，实际: {resp.status_code}, {resp.get_json()}")

    print("\n--- 场景 3：编辑生成新版本，旧版本保留 ---")

    resp = client.put(f'/api/plans/{plan_1_id}', json={
        'title': '高危客户登录异常处理 v2',
        'steps': '1. 核实账号状态\n2. 联系客户确认\n3. 上报主管',
    })
    check(resp.status_code == 200,
          f"编辑预案返回 200 (实际: {resp.status_code})",
          f"编辑预案应返回 200，实际: {resp.status_code}, {resp.get_json()}")

    new_plan = resp.get_json()['data']
    check(new_plan['version'] == 2,
          f"新版本号为 2 (实际: {new_plan['version']})",
          f"新版本号应为 2，实际: {new_plan['version']}")
    check(new_plan['is_latest'] is True,
          "新版本标记为最新",
          "新版本应标记为 is_latest=true")

    resp = client.get(f'/api/plans/group/{plan_1_group}/versions')
    versions = resp.get_json().get('data', [])
    check(len(versions) == 2,
          f"版本历史包含 2 个版本 (实际: {len(versions)})",
          f"版本历史应包含 2 个版本，实际: {len(versions)}")

    old_version = [v for v in versions if v['version'] == 1][0]
    check(old_version['is_latest'] is False,
          "旧版本标记为非最新",
          "旧版本应标记为 is_latest=false")
    check(old_version['title'] == '高危客户登录异常处理',
          f"旧版本标题保留 (实际: {old_version['title']})",
          f"旧版本标题应保留原内容")

    new_version = [v for v in versions if v['version'] == 2][0]
    check('上报主管' in new_version['steps'],
          "新版本包含更新后的步骤",
          "新版本步骤应包含新增内容")

    print("\n--- 场景 4：停用/启用逻辑 ---")

    resp = client.post(f'/api/plans/{plan_1_id}/disable')
    check(resp.status_code == 400,
          f"停用旧版本（非最新）返回 400 (实际: {resp.status_code})",
          f"停用非最新版本应返回 400，实际: {resp.status_code}")

    latest_plan_id = new_plan['id']
    resp = client.post(f'/api/plans/{latest_plan_id}/disable')
    check(resp.status_code == 200,
          f"停用最新版本成功 (实际: {resp.status_code})",
          f"停用最新版本应成功，实际: {resp.status_code}, {resp.get_json()}")
    check(resp.get_json()['data']['is_active'] is False,
          "停用后 is_active=false",
          "停用后 is_active 应为 false")

    resp = client.post(f'/api/plans/{latest_plan_id}/enable')
    check(resp.status_code == 200,
          f"重新启用成功 (实际: {resp.status_code})",
          f"重新启用应成功，实际: {resp.status_code}")
    check(resp.get_json()['data']['is_active'] is True,
          "启用后 is_active=true",
          "启用后 is_active 应为 true")

    print("\n--- 场景 5：CSV 导入导出 ---")

    resp = client.get('/api/plans/export')
    check(resp.status_code == 200 and 'text/csv' in resp.content_type,
          f"CSV 导出成功 (实际: {resp.status_code}, type: {resp.content_type})",
          f"CSV 导出失败: {resp.status_code}")

    csv_content = resp.data.decode('utf-8-sig')
    check('预案标题' in csv_content and '适用严重级别' in csv_content,
          "CSV 包含正确的列名",
          "CSV 列名不符合预期")

    bad_csv = (
        "预案标题,适用严重级别,关键词,处理步骤,负责人建议,是否启用\n"
        "好预案,高危,网络,延迟,步骤内容,是\n"
        "缺级别预案,,关键词2,步骤2,负责人,是\n"
        "无效级别,超级严重,关键词3,步骤3,,是\n"
    )
    data = {'file': (io.BytesIO(bad_csv.encode('utf-8')), 'bad_plans.csv')}
    before_count = len(client.get('/api/plans').get_json().get('data', []))
    resp = client.post('/api/plans/import', data=data, content_type='multipart/form-data')
    after_count = len(client.get('/api/plans').get_json().get('data', []))
    check(resp.status_code == 400 and before_count == after_count,
          f"校验失败导入回滚 (状态: {resp.status_code}, 数量不变: {before_count})",
          f"校验失败应回滚，状态: {resp.status_code}, 数量: {before_count} -> {after_count}")
    details = resp.get_json().get('details', [])
    check(len(details) >= 2,
          f"返回至少 2 条校验错误 (实际: {len(details)})",
          f"应返回详细校验错误，实际: {details}")

    good_csv = (
        "预案标题,适用严重级别,关键词,处理步骤,负责人建议,是否启用\n"
        "CSV导入预案A,高危,\"支付,超时\",\"步骤1\\n步骤2\",支付组,是\n"
        "CSV导入预案B,中危,订单,订单核对步骤,订单组,是\n"
    )
    data = {'file': (io.BytesIO(good_csv.encode('utf-8')), 'good_plans.csv')}
    resp = client.post('/api/plans/import', data=data, content_type='multipart/form-data')
    check(resp.status_code == 200,
          f"合法 CSV 导入成功 (实际: {resp.status_code})",
          f"合法 CSV 导入应成功，实际: {resp.status_code}, {resp.get_json()}")
    import_result = resp.get_json().get('data', {})
    check(import_result.get('imported', 0) == 2,
          f"成功导入 2 条 (实际: {import_result.get('imported')})",
          f"应成功导入 2 条，实际: {import_result}")

    resp = client.get('/api/plans?title=CSV导入预案A')
    check(len(resp.get_json().get('data', [])) == 1,
          "按标题筛选可找到导入的预案",
          "按标题筛选失败")

    print("\n--- 场景 6：工单引用预案写入日志 ---")

    switch_role('cs', 'cs_demo')
    resp = client.get('/api/tickets')
    tickets = resp.get_json().get('data', {}).get('items', [])
    if tickets:
        ticket_id = tickets[0]['id']
        switch_role('cs', 'cs_demo')
        resp = client.post(f'/api/plans/{latest_plan_id}/reference/{ticket_id}')
        check(resp.status_code == 200,
              f"客服引用预案成功 (实际: {resp.status_code})",
              f"客服引用预案应成功，实际: {resp.status_code}, {resp.get_json()}")

        resp = client.get(f'/api/history?entity_type=ticket&entity_id={ticket_id}')
        history = resp.get_json().get('data', [])
        ref_logs = [h for h in history if h.get('new_status') == 'plan_referenced']
        check(len(ref_logs) >= 1,
              f"工单历史包含引用预案日志 (实际: {len(ref_logs)} 条)",
              f"应写入 plan_referenced 历史记录")
        check('v' in (ref_logs[0].get('reason') or ''),
              "日志原因包含预案版本号",
              f"日志应记录版本，实际: {ref_logs[0].get('reason')}")
    else:
        print(f"  {INFO} 无可用工单，跳过引用日志测试")

    print("\n--- 场景 7：筛选和智能匹配 ---")

    switch_role('receiver', 'receiver_demo')
    resp = client.get('/api/plans?severity=high')
    high_plans = resp.get_json().get('data', [])
    check(all(p['applicable_severity'] == 'high' for p in high_plans),
          "按严重级别筛选正确",
          "按级别筛选结果不正确")

    resp = client.get('/api/plans?is_active=true')
    active_plans = resp.get_json().get('data', [])
    check(all(p['is_active'] is True for p in active_plans),
          "按启用状态筛选正确",
          "按状态筛选结果不正确")

    resp = client.get('/api/plans?keyword=登录')
    kw_plans = resp.get_json().get('data', [])
    check(len(kw_plans) >= 1,
          f"按关键词搜索返回结果 (实际: {len(kw_plans)} 条)",
          "按关键词搜索应返回结果")

    resp = client.get('/api/plans/match?customer_name=客户A&severity=high')
    matched = resp.get_json().get('data', [])
    check(len(matched) >= 1,
          f"智能匹配返回预案 (实际: {len(matched)})",
          "按客户名和级别智能匹配应返回结果")

    print("\n--- 场景 8：跨重启数据保留 ---")

    plans_before = sorted(client.get('/api/plans').get_json().get('data', []), key=lambda s: s['id'])
    versions_before = sorted(client.get(f'/api/plans/group/{plan_1_group}/versions').get_json().get('data', []), key=lambda v: v['id'])

    del client
    del app
    import gc
    gc.collect()

    app2 = create_app()
    client2 = app2.test_client()

    with app2.app_context():
        from backend.models import db as db2
        db2.create_all()

    def switch_role2(role, username):
        resp = client2.post('/api/switch-role', json={'role': role, 'username': username})
        if resp.status_code != 200:
            raise RuntimeError(f"切换角色失败: {role}/{username} -> {resp.status_code}")
        return resp.get_json()

    switch_role2('receiver', 'receiver_demo')
    plans_after = sorted(client2.get('/api/plans').get_json().get('data', []), key=lambda s: s['id'])
    versions_after = sorted(client2.get(f'/api/plans/group/{plan_1_group}/versions').get_json().get('data', []), key=lambda v: v['id'])

    check(len(plans_before) == len(plans_after),
          f"跨重启后预案数量一致 ({len(plans_before)})",
          f"跨重启后预案数量不一致: 前 {len(plans_before)}, 后 {len(plans_after)}")

    ids_before = [p['id'] for p in plans_before]
    ids_after = [p['id'] for p in plans_after]
    check(ids_before == ids_after,
          "跨重启后预案 ID 完全一致",
          f"跨重启后预案 ID 不一致: 前 {ids_before}, 后 {ids_after}")

    check(len(versions_before) == len(versions_after),
          f"跨重启后版本历史数量一致 ({len(versions_before)})",
          f"跨重启后版本数量不一致")

    print("\n" + "=" * 60)
    print(f"测试结果: {passed} 通过, {failed} 失败")
    print("=" * 60)

    if failed > 0:
        print(f"\n{ERROR} 存在失败的测试用例，请检查")
        sys.exit(1)
    else:
        print(f"\n{INFO} 所有测试全部通过！升级预案库模块功能正常！")


if __name__ == '__main__':
    run_tests()

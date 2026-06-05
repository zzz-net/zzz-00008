"""
API 集成测试
覆盖主要 API 接口的功能测试
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
    sys.path.insert(0, '.')
    from backend.app import create_app, init_sample_data
    from backend.models import db

    try:
        app = create_app()
        client = app.test_client()
    except Exception as e:
        print(f"\n{ERROR} 初始化 Flask 应用失败: {e}")
        sys.exit(3)

    print("Testing API endpoints...")
    print("=" * 50)

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
        # Test current role
        print("\n1. GET /api/current-role")
        resp = client.get('/api/current-role')
        print(f"   Status: {resp.status_code}")
        data = resp.get_json()
        print(f"   Response: {data}")
        check(resp.status_code == 200 and data.get('success'),
              "获取当前角色成功",
              f"获取当前角色失败: {resp.status_code}")

        # Test dashboard stats
        print("\n2. GET /api/dashboard/stats")
        resp = client.get('/api/dashboard/stats')
        print(f"   Status: {resp.status_code}")
        data = resp.get_json()
        if data and data.get('success'):
            print(f"   Tickets total: {data['data']['tickets']['total']}")
            print(f"   Tickets by status: {data['data']['tickets']['by_status']}")
        check(resp.status_code == 200 and data.get('success'),
              "获取看板统计成功",
              f"获取看板统计失败: {resp.status_code}")

        # Test tickets list
        print("\n3. GET /api/tickets")
        resp = client.get('/api/tickets')
        print(f"   Status: {resp.status_code}")
        data = resp.get_json()
        if data and data.get('success'):
            print(f"   Total tickets: {data['data']['total']}")
            if data['data']['items']:
                print(f"   First ticket: {data['data']['items'][0]['customer_name']}")
        check(resp.status_code == 200 and data.get('success'),
              "获取工单列表成功",
              f"获取工单列表失败: {resp.status_code}")

        # Test switch role
        print("\n4. POST /api/switch-role")
        resp = client.post('/api/switch-role', json={'role': 'handover', 'username': 'handover_demo'})
        print(f"   Status: {resp.status_code}")
        data = resp.get_json()
        print(f"   Response: {data}")
        check(resp.status_code == 200 and data.get('success'),
              "切换到交班人角色成功",
              f"切换角色失败: {resp.status_code}")

        # Test get tickets for handover
        print("\n5. GET /api/tickets/open-for-handover")
        resp = client.get('/api/tickets/open-for-handover')
        print(f"   Status: {resp.status_code}")
        data = resp.get_json()
        if data and data.get('success'):
            print(f"   Open tickets: {len(data['data'])}")
        check(resp.status_code == 200 and data.get('success'),
              "获取可交接工单成功",
              f"获取可交接工单失败: {resp.status_code}")

        # Test create ticket
        print("\n6. POST /api/tickets (create)")
        from datetime import datetime, timedelta
        try:
            deadline = (datetime.now(datetime.UTC) + timedelta(days=3)).isoformat()
        except Exception:
            deadline = (datetime.utcnow() + timedelta(days=3)).isoformat()
        resp = client.post('/api/tickets', json={
            'customer_name': '测试客户',
            'severity': 'high',
            'assignee': '测试责任人',
            'deadline': deadline,
            'progress': '测试进展'
        })
        print(f"   Status: {resp.status_code}")
        data = resp.get_json()
        print(f"   Response: {data}")
        check(resp.status_code == 201 and data.get('success'),
              "创建工单成功",
              f"创建工单失败: {resp.status_code}")

        # Test create batch
        print("\n7. POST /api/batches (create)")
        resp = client.post('/api/batches', json={
            'name': '测试批次',
            'description': '测试描述',
            'ticket_ids': [1],
            'handover_person': '交班老李'
        })
        print(f"   Status: {resp.status_code}")
        data = resp.get_json()
        print(f"   Response: {data}")
        batch_id = data['data']['id'] if data and data.get('success') else None
        check(resp.status_code == 201 and data.get('success') and batch_id is not None,
              f"创建批次成功，ID={batch_id}",
              f"创建批次失败: {resp.status_code}")

        # Test duplicate batch with same ticket
        print("\n8. POST /api/batches (duplicate ticket)")
        resp = client.post('/api/batches', json={
            'name': '测试批次2',
            'ticket_ids': [1],
            'handover_person': '交班老李'
        })
        print(f"   Status: {resp.status_code}")
        data = resp.get_json()
        print(f"   Response: {data}")
        check(resp.status_code == 400 and not data.get('success'),
              "同一工单不能重复加入批次，正确返回 400",
              f"重复批次校验失败: {resp.status_code}")

        # Test switch to receiver role
        print("\n9. POST /api/switch-role (receiver)")
        resp = client.post('/api/switch-role', json={'role': 'receiver', 'username': 'receiver_demo'})
        print(f"   Status: {resp.status_code}")
        check(resp.status_code == 200,
              "切换到接班人角色成功",
              f"切换角色失败: {resp.status_code}")

        # Test confirm batch
        if batch_id:
            print(f"\n10. POST /api/batches/{batch_id}/confirm")
            resp = client.post(f'/api/batches/{batch_id}/confirm', json={'receiver_person': '接班小张'})
            print(f"   Status: {resp.status_code}")
            data = resp.get_json()
            print(f"   Response: {data}")
            check(resp.status_code == 200 and data.get('success'),
                  "确认批次成功",
                  f"确认批次失败: {resp.status_code}")

            # Test duplicate confirm
            print(f"\n11. POST /api/batches/{batch_id}/confirm (duplicate)")
            resp = client.post(f'/api/batches/{batch_id}/confirm', json={'receiver_person': '接班小张'})
            print(f"   Status: {resp.status_code}")
            data = resp.get_json()
            print(f"   Response: {data}")
            check(resp.status_code == 400 and not data.get('success'),
                  "重复确认正确返回 400",
                  f"重复确认校验失败: {resp.status_code}")
        else:
            print(f"\n10-11. {INFO} 跳过批次确认测试（批次创建失败）")

        # Test switch to cs role and try to close critical overdue ticket
        print("\n12. POST /api/switch-role (cs)")
        resp = client.post('/api/switch-role', json={'role': 'cs', 'username': 'cs_demo'})
        print(f"   Status: {resp.status_code}")
        check(resp.status_code == 200,
              "切换到普通客服角色成功",
              f"切换角色失败: {resp.status_code}")

        print("\n13. POST /api/tickets/2/close (cs closing critical overdue)")
        resp = client.post('/api/tickets/2/close')
        print(f"   Status: {resp.status_code}")
        data = resp.get_json()
        print(f"   Response: {data}")
        check(resp.status_code == 403 and not data.get('success') and '权限不足' in data.get('error', ''),
              "普通客服关闭逾期高危单正确返回 403",
              f"高危单关闭权限校验失败: {resp.status_code}")

        # Test history
        print("\n14. GET /api/history")
        resp = client.get('/api/history?limit=5')
        print(f"   Status: {resp.status_code}")
        data = resp.get_json()
        if data and data.get('success'):
            print(f"   History entries: {len(data['data'])}")
            for h in data['data'][:3]:
                print(f"   - {h['entity_type']} #{h['entity_id']}: {h['old_status']} -> {h['new_status']} by {h['operator']}")
        check(resp.status_code == 200 and data.get('success'),
              "获取历史记录成功",
              f"获取历史记录失败: {resp.status_code}")

        # Test export
        print("\n15. GET /api/export/tickets?format=json")
        resp = client.get('/api/export/tickets?format=json')
        print(f"   Status: {resp.status_code}")
        print(f"   Content-Type: {resp.content_type}")
        check(resp.status_code == 200 and 'json' in resp.content_type,
              "JSON 导出成功",
              f"JSON 导出失败: {resp.status_code}")

    except Exception as e:
        print(f"\n{ERROR} 测试执行过程中发生异常: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(4)

    print("\n" + "=" * 50)
    print(f"测试结果: {passed} 通过, {failed} 失败")
    print("=" * 50)

    if failed == 0:
        print(f"\n{INFO} 所有测试全部通过！")
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
        sys.exit(99)

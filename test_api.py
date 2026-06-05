import sys
sys.path.insert(0, '.')

from backend.app import create_app

app = create_app()
client = app.test_client()

print("Testing API endpoints...")
print("=" * 50)

# Test current role
print("\n1. GET /api/current-role")
resp = client.get('/api/current-role')
print(f"   Status: {resp.status_code}")
print(f"   Response: {resp.get_json()}")

# Test dashboard stats
print("\n2. GET /api/dashboard/stats")
resp = client.get('/api/dashboard/stats')
print(f"   Status: {resp.status_code}")
data = resp.get_json()
if data and data.get('success'):
    print(f"   Tickets total: {data['data']['tickets']['total']}")
    print(f"   Tickets by status: {data['data']['tickets']['by_status']}")

# Test tickets list
print("\n3. GET /api/tickets")
resp = client.get('/api/tickets')
print(f"   Status: {resp.status_code}")
data = resp.get_json()
if data and data.get('success'):
    print(f"   Total tickets: {data['data']['total']}")
    if data['data']['items']:
        print(f"   First ticket: {data['data']['items'][0]['customer_name']}")

# Test switch role
print("\n4. POST /api/switch-role")
resp = client.post('/api/switch-role', json={'role': 'handover', 'username': 'handover_demo'})
print(f"   Status: {resp.status_code}")
print(f"   Response: {resp.get_json()}")

# Test get tickets for handover
print("\n5. GET /api/tickets/open-for-handover")
resp = client.get('/api/tickets/open-for-handover')
print(f"   Status: {resp.status_code}")
data = resp.get_json()
if data and data.get('success'):
    print(f"   Open tickets: {len(data['data'])}")

# Test create ticket
print("\n6. POST /api/tickets (create)")
from datetime import datetime, timedelta
deadline = (datetime.utcnow() + timedelta(days=3)).isoformat()
resp = client.post('/api/tickets', json={
    'customer_name': '测试客户',
    'severity': 'high',
    'assignee': '测试责任人',
    'deadline': deadline,
    'progress': '测试进展'
})
print(f"   Status: {resp.status_code}")
print(f"   Response: {resp.get_json()}")

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

# Test duplicate batch with same ticket
print("\n8. POST /api/batches (duplicate ticket)")
resp = client.post('/api/batches', json={
    'name': '测试批次2',
    'ticket_ids': [1],
    'handover_person': '交班老李'
})
print(f"   Status: {resp.status_code}")
print(f"   Response: {resp.get_json()}")

# Test switch to receiver role
print("\n9. POST /api/switch-role (receiver)")
resp = client.post('/api/switch-role', json={'role': 'receiver', 'username': 'receiver_demo'})
print(f"   Status: {resp.status_code}")

# Test confirm batch
if batch_id:
    print(f"\n10. POST /api/batches/{batch_id}/confirm")
    resp = client.post(f'/api/batches/{batch_id}/confirm', json={'receiver_person': '接班小张'})
    print(f"   Status: {resp.status_code}")
    print(f"   Response: {resp.get_json()}")

    # Test duplicate confirm
    print(f"\n11. POST /api/batches/{batch_id}/confirm (duplicate)")
    resp = client.post(f'/api/batches/{batch_id}/confirm', json={'receiver_person': '接班小张'})
    print(f"   Status: {resp.status_code}")
    print(f"   Response: {resp.get_json()}")

# Test switch to cs role and try to close critical overdue ticket
print("\n12. POST /api/switch-role (cs)")
resp = client.post('/api/switch-role', json={'role': 'cs', 'username': 'cs_demo'})
print(f"   Status: {resp.status_code}")

print("\n13. POST /api/tickets/2/close (cs closing critical overdue)")
resp = client.post('/api/tickets/2/close')
print(f"   Status: {resp.status_code}")
print(f"   Response: {resp.get_json()}")

# Test history
print("\n14. GET /api/history")
resp = client.get('/api/history?limit=5')
print(f"   Status: {resp.status_code}")
data = resp.get_json()
if data and data.get('success'):
    print(f"   History entries: {len(data['data'])}")
    for h in data['data'][:3]:
        print(f"   - {h['entity_type']} #{h['entity_id']}: {h['old_status']} -> {h['new_status']} by {h['operator']}")

# Test export
print("\n15. GET /api/export/tickets?format=json")
resp = client.get('/api/export/tickets?format=json')
print(f"   Status: {resp.status_code}")
print(f"   Content-Type: {resp.content_type}")

print("\n" + "=" * 50)
print("All tests completed!")

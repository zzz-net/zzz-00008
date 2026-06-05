import requests
BASE = 'http://127.0.0.1:5000'

print('=== After Restart Verification ===')

# 1. Dashboard stats
r1 = requests.get(f'{BASE}/api/dashboard/stats')
d = r1.json()['data']
print('1. Dashboard Stats:')
print(f'   Tickets total: {d["tickets"]["total"]}')
print(f'   Tickets by status: {d["tickets"]["by_status"]}')
print(f'   Tickets by severity: {d["tickets"]["by_severity"]}')
print(f'   Batches total: {d["batches"]["total"]}')
print(f'   Batches by status: {d["batches"]}')

# 2. Ticket details
r2 = requests.get(f'{BASE}/api/tickets')
print(f'2. Tickets response keys: {r2.json().keys()}')
tickets_data = r2.json()['data']
print(f'   Tickets type: {type(tickets_data)}')
if isinstance(tickets_data, dict):
    print(f'   Tickets dict keys: {tickets_data.keys()}')
    tickets_list = tickets_data.get('items', [])
    print(f'   Tickets count: {len(tickets_list)}')
    for t in tickets_list[:3]:
        print(f'   #{t["id"]}: {t["customer_name"]} - {t["status"]} - {t["severity"]}')
else:
    print(f'   Tickets count: {len(tickets_data)}')
    for t in tickets_data[:3]:
        print(f'   #{t["id"]}: {t["customer_name"]} - {t["status"]} - {t["severity"]}')

# 3. Batch details
r3 = requests.get(f'{BASE}/api/batches')
batches_data = r3.json()['data']
if isinstance(batches_data, dict):
    batches_list = batches_data.get('items', [])
else:
    batches_list = batches_data
print(f'3. Batches count: {len(batches_list)}')
for b in batches_list:
    print(f'   #{b["id"]}: {b["name"]} - {b["status"]} - {b["ticket_ids"]}')

# 4. History entries
r4 = requests.get(f'{BASE}/api/history')
history_data = r4.json()['data']
if isinstance(history_data, dict):
    history_list = history_data.get('items', [])
else:
    history_list = history_data
print(f'4. History entries: {len(history_list)}')
for h in history_list[:3]:
    print(f'   #{h["id"]}: {h["entity_type"]} #{h["entity_id"]}: {h["old_status"]} -> {h["new_status"]} by {h["operator"]}')

# 5. CSV Export
r5 = requests.get(f'{BASE}/api/export/tickets?format=csv')
print(f'5. CSV Export: {r5.status_code}, {r5.headers.get("Content-Type")}')
print(f'   CSV first 200 chars: {r5.text[:200]}')

# 6. JSON Export
r6 = requests.get(f'{BASE}/api/export/tickets?format=json')
print(f'6. JSON Export: {r6.status_code}, {r6.headers.get("Content-Type")}')

print('=== Verification Complete ===')
print()
print('Expected matches:')
print('  - Tickets total: 4 (3 sample + 1 created)')
print('  - Tickets by status: open=2, in_progress=1, overdue=1')
print('  - Tickets by severity: high=2, critical=1, medium=1')
print('  - Batches total: 1, confirmed=1')
print('  - History entries: 3')

from backend.app import create_app

app = create_app()

print("URL Rules:")
for rule in app.url_map.iter_rules():
    print(f"  {rule.rule:40s} -> {rule.endpoint:40s} [{','.join(rule.methods)}]")

print("\nRegistered Blueprints:")
for name, bp in app.blueprints.items():
    print(f"  {name}")

print("\nTesting URL matching:")
from werkzeug.routing import Map, Rule
from werkzeug.exceptions import NotFound

url_map = app.url_map
adapter = url_map.bind('localhost', '/')

test_paths = [
    '/api/current-role',
    '/api/tickets',
    '/api/batches',
    '/api/dashboard/stats',
    '/',
    '/tickets',
    '/batches',
]

for path in test_paths:
    try:
        endpoint, values = adapter.match(path)
        print(f"  {path:30s} -> {endpoint:30s} {values}")
    except NotFound:
        print(f"  {path:30s} -> 404 NOT FOUND")
    except Exception as e:
        print(f"  {path:30s} -> ERROR: {e}")

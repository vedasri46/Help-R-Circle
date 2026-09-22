import os
import sqlite3
from jinja2 import Environment, FileSystemLoader

env = Environment(loader=FileSystemLoader(os.path.join(os.path.dirname(__file__), '..', 'templates')))
env.globals['url_for'] = lambda *args, **kwargs: '#'
env.globals['request'] = type('Request', (), {'endpoint': None})()
env.globals['get_flashed_messages'] = lambda **kwargs: []
template = env.get_template('dashboard.html')

base = {
    'id': 1, 'status': 'pending', 'priority': 'normal', 'help_type': 'Other',
    'name': 'Requester', 'location': 'Area', 'phone': '9876543210',
    'description': 'Need help', 'created_at': 'now',
    'request_latitude': None, 'request_longitude': None,
}
conn = sqlite3.connect(':memory:')
conn.row_factory = sqlite3.Row
conn.execute('CREATE TABLE requests (id INTEGER, status TEXT, priority TEXT, help_type TEXT, name TEXT, location TEXT, phone TEXT, description TEXT, created_at TEXT, helper_name TEXT, request_latitude REAL, request_longitude REAL)')
for helper_name in (None, 'Helper Name'):
    conn.execute('INSERT INTO requests VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)', (1, 'pending', 'normal', 'Other', 'Requester', 'Area', '9876543210', 'Need help', 'now', helper_name, None, None))
row = conn.execute('SELECT * FROM requests LIMIT 1').fetchone()
# Render representative request-card fragments through the actual template.
html = template.render(
    session={}, stats={'pending': 0, 'accepted': 0, 'completed': 0},
    requests=[row], my_requests=[], my_request_stats={}, notifications=[],
    status_filter='all', type_filter='all', search_query='', t=lambda key, default=None: default,
    available_locales={}, current_lang='en', priority_filter='all',
)
print('rendered_sqlite_row:', 'Requester' in html)
print('helper_access_is_bracket_style:', "req['helper_name']" not in html)
conn.close()

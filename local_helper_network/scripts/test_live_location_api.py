import os
import sys
import time
from werkzeug.security import generate_password_hash

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from app import app, db

# Apply the additive helper-coordinate migration before testing.
db.init_db()
username = f'location-helper-{time.time_ns()}'
email = f'{username}@example.com'
with db.connect() as conn:
    cur = conn.execute(
        "INSERT INTO users (username, email, password_hash, role, is_verified) VALUES (?, ?, ?, 'helper', 1)",
        (username, email, generate_password_hash('Password123!')),
    )
    user_id = cur.lastrowid
helper_id = db.add_helper(username, '9876543210', email, 'Area', 'help', 'always', user_id=user_id)
request_id = db.add_help_request('Requester', '9876543210', 'Area', 'Other', 'Need help', user_id=None, request_latitude=17.385, request_longitude=78.486)
db.update_request_status(request_id, 'accepted', helper_id=helper_id, helper_name=username)

client = app.test_client()
with client.session_transaction() as session:
    session['user_id'] = user_id
    session['role'] = 'helper'
response = client.post('/api/helper/location', data={'request_id': request_id, 'latitude': '17.390', 'longitude': '78.490'}, headers={'Accept': 'application/json'})
row = db.get_request_by_id(request_id)
latest = db.get_latest_helper_location(request_id, helper_id)
print('api_status:', response.status_code)
print('api_ok:', response.get_json().get('ok'))
print('api_returns_updated_at:', bool(response.get_json().get('updated_at')))
print('request_helper_latitude_saved:', row['helper_latitude'] == 17.39)
print('request_helper_longitude_saved:', row['helper_longitude'] == 78.49)
print('latest_location_saved:', latest is not None and latest['latitude'] == 17.39)

with db.connect() as conn:
    conn.execute('DELETE FROM helper_locations WHERE request_id = ?', (request_id,))
    conn.execute('DELETE FROM help_requests WHERE id = ?', (request_id,))
    conn.execute('DELETE FROM volunteers WHERE id = ?', (helper_id,))
    conn.execute('DELETE FROM users WHERE id = ?', (user_id,))

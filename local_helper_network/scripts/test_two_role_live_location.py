import os
import sys
import time
from werkzeug.security import generate_password_hash

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from app import app, db

db.init_db()
suffix = str(time.time_ns())
with db.connect() as conn:
    requester = conn.execute(
        "INSERT INTO users (username,email,password_hash,role,is_verified) VALUES (?,?,?,?,1)",
        ('requester-' + suffix, 'requester-' + suffix + '@example.com', generate_password_hash('Password123!'), 'user'),
    ).lastrowid
    helper_user = conn.execute(
        "INSERT INTO users (username,email,password_hash,role,is_verified) VALUES (?,?,?,?,1)",
        ('helper-' + suffix, 'helper-' + suffix + '@example.com', generate_password_hash('Password123!'), 'helper'),
    ).lastrowid
helper_id = db.add_helper('Helper ' + suffix, '9876543210', 'helper-' + suffix + '@example.com', 'Area', 'help', 'always', user_id=helper_user)
request_id = db.add_help_request('Requester', '9876543210', 'Area', 'Other', 'Need help', user_id=requester, request_latitude=17.385, request_longitude=78.486)
db.update_request_status(request_id, 'accepted', helper_id=helper_id, helper_name='Helper ' + suffix)

helper_client = app.test_client()
with helper_client.session_transaction() as session:
    session['user_id'] = helper_user
    session['role'] = 'helper'
post = helper_client.post('/api/helper/location', data={'request_id': request_id, 'latitude': '17.390', 'longitude': '78.490'}, headers={'Accept': 'application/json'})

requester_client = app.test_client()
with requester_client.session_transaction() as session:
    session['user_id'] = requester
    session['role'] = 'user'
get = requester_client.get(f'/api/request/{request_id}/helper-location', headers={'Accept': 'application/json'})
page = requester_client.get(f'/track/{request_id}').get_data(as_text=True)
print('helper_post_status:', post.status_code)
print('helper_post_saved:', post.get_json().get('success'))
print('requester_get_status:', get.status_code)
print('requester_get_available:', get.get_json().get('available'))
print('requester_get_coordinates:', get.get_json().get('latitude'), get.get_json().get('longitude'))
print('helper_contact_rendered:', 'Helper ' + suffix in page)

with db.connect() as conn:
    conn.execute('DELETE FROM helper_locations WHERE request_id = ?', (request_id,))
    conn.execute('DELETE FROM help_requests WHERE id = ?', (request_id,))
    conn.execute('DELETE FROM volunteers WHERE id = ?', (helper_id,))
    conn.execute('DELETE FROM users WHERE id IN (?, ?)', (requester, helper_user))

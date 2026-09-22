import sys
import time
import re
from unittest.mock import patch

sys.path.insert(0, __import__('os').path.abspath(__import__('os').path.dirname(__file__) + '/..'))
from app import app, db, generate_verification_token

email = f"state-flow-{int(time.time())}@example.com"
username = f"state_flow_{int(time.time())}"
client = app.test_client()
initial_page = client.get('/signup').get_data(as_text=True)

def rendered_email_status(page):
    match = re.search(r'<div id="emailVerificationStatus"[^>]*>(.*?)</div>', page, re.S)
    return match.group(1).strip() if match else None

with patch('app.send_verification_email'):
    response = client.post('/create-pending', data={'email': email, 'username': username})

payload = response.get_json()
pending_id = payload['pending_id']
pending_before = db.get_pending_by_id(pending_id)
token = pending_before['email_token']
page_before = client.get('/signup').get_data(as_text=True)
page_after_refresh_before_link = client.get('/signup').get_data(as_text=True)

invalid_response = client.get('/verify-email/not-a-valid-link', follow_redirects=True)
pending_after_invalid = db.get_pending_by_id(pending_id)

link_response = client.get(f'/verify-email/{token}', follow_redirects=True)
pending_after = db.get_pending_by_id(pending_id)
page_after = link_response.get_data(as_text=True)

finalized = client.post('/finalize-pending', data={
    'pending_id': pending_id,
    'username': username,
    'email': email,
    'phone': '9876543210',
    'password': 'Password123!',
    'confirm_password': 'Password123!',
    'role': 'user',
}, headers={'Accept': 'application/json'})
finalized_payload = finalized.get_json() or {}
if finalized_payload.get('user_id'):
    with db.connect() as conn:
        conn.execute('DELETE FROM users WHERE id = ?', (finalized_payload['user_id'],))

db.delete_pending(pending_id)

print('send_status:', response.status_code)
print('initial_page_has_no_email_status:', rendered_email_status(initial_page) == '')
print('pending_email_verified_after_send:', bool(pending_before['email_verified']))
print('page_has_no_email_status_before_link:', rendered_email_status(page_before) == '')
print('refresh_before_link_has_no_email_status:', rendered_email_status(page_after_refresh_before_link) == '')
print('invalid_link_keeps_unverified:', not bool(pending_after_invalid['email_verified']))
print('link_status:', link_response.status_code)
print('pending_email_verified_after_link:', bool(pending_after['email_verified']))
print('page_after_link_shows_verified:', '✓ Email Verified' in page_after)
print('finalize_email_verified_without_phone_otp_status:', finalized.status_code)
print('finalize_email_verified_without_phone_otp_ok:', bool(finalized_payload.get('ok')))

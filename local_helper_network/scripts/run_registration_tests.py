import os
import sys
import time
from unittest.mock import patch

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from app import app, db, generate_verification_token

client = app.test_client()
created_users = []
created_pending = []
results = []


def cleanup():
    for user_id in created_users:
        with db.connect() as conn:
            conn.execute('DELETE FROM users WHERE id = ?', (user_id,))
    for pending_id in created_pending:
        db.delete_pending(pending_id)


def test_email_required_before_finalize():
    email = f'email-gate-{time.time_ns()}@example.com'
    pending_id = db.create_pending_registration('Email Gate', email, 'hash', phone='+919876543210')
    created_pending.append(pending_id)
    response = client.post('/finalize-pending', data={
        'pending_id': pending_id, 'username': 'Email Gate', 'email': email,
        'phone': '9876543210', 'password': 'Password123!',
        'confirm_password': 'Password123!', 'role': 'user',
    }, headers={'Accept': 'application/json'})
    return response.status_code == 400 and response.get_json().get('error') == 'finalization_failed'


def test_email_verified_allows_finalize_without_phone_otp():
    email = f'email-only-{time.time_ns()}@example.com'
    token = generate_verification_token(email)
    pending_id = db.create_pending_registration('Email Only', email, 'hash', phone='+919876543210', email_token=token)
    created_pending.append(pending_id)
    client.get(f'/verify-email/{token}')
    response = client.post('/finalize-pending', data={
        'pending_id': pending_id, 'username': 'Email Only', 'email': email,
        'phone': '9876543210', 'password': 'Password123!',
        'confirm_password': 'Password123!', 'role': 'user',
    }, headers={'Accept': 'application/json'})
    payload = response.get_json()
    if response.status_code == 200 and payload and payload.get('ok'):
        created_users.append(payload['user_id'])
        return True
    return False


def test_invalid_email_link_does_not_verify():
    email = f'invalid-link-{time.time_ns()}@example.com'
    pending_id = db.create_pending_registration('Invalid Link', email, 'hash', email_token=generate_verification_token(email))
    created_pending.append(pending_id)
    client.get('/verify-email/not-a-valid-link')
    return not bool(db.get_pending_by_id(pending_id)['email_verified'])


try:
    results.append(('Email required before finalization', test_email_required_before_finalize()))
    results.append(('Email verification allows email-only finalization', test_email_verified_allows_finalize_without_phone_otp()))
    results.append(('Invalid email link remains unverified', test_invalid_email_link_does_not_verify()))
finally:
    cleanup()

print('TEST RESULTS')
for name, passed in results:
    print(f'{name}: {"PASS" if passed else "FAIL"}')
print('Total passed:', sum(passed for _, passed in results))
print('Total failed:', sum(not passed for _, passed in results))
if any(not passed for _, passed in results):
    raise SystemExit(1)

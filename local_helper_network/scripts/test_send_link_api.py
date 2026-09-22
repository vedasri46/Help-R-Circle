import sys
import time
from unittest.mock import patch

sys.path.insert(0, 'local_helper_network')
from app import app, db, generate_verification_token

client = app.test_client()
email = f'already-{int(time.time())}@example.com'
pending_id = db.create_pending_registration(
    f'already-{int(time.time())}', email, 'hash', email_token=generate_verification_token(email)
)
db.mark_pending_email_verified(pending_id)
with client.session_transaction() as session:
    session['pending_id'] = pending_id
already = client.post('/create-pending', data={'email': email, 'username': 'Already'})
print('already_status:', already.status_code)
print('already_json:', already.get_json())
db.delete_pending(pending_id)

fresh_email = f'fresh-{int(time.time())}@example.com'
with patch('app.send_verification_email') as send_email:
    fresh = client.post('/create-pending', data={'email': fresh_email, 'username': 'Fresh'})
print('fresh_status:', fresh.status_code)
print('fresh_send_called:', send_email.called)
fresh_id = fresh.get_json().get('pending_id')
if fresh_id:
    db.delete_pending(fresh_id)

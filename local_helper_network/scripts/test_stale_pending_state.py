import sys
import time
import re

sys.path.insert(0, 'local_helper_network')
from app import app, db, generate_verification_token

client = app.test_client()
email = f'stale-state-{int(time.time())}@example.com'
pending_id = db.create_pending_registration(
    f'stale-state-{int(time.time())}', email, 'hash', email_token=generate_verification_token(email)
)
db.mark_pending_email_verified(pending_id)
with client.session_transaction() as session:
    session['pending_id'] = pending_id
stale_page = client.get('/signup').get_data(as_text=True)

fresh_email = f'fresh-state-{int(time.time())}@example.com'
response = client.post('/create-pending', data={'email': fresh_email, 'username': 'Fresh State'})
fresh_id = response.get_json()['pending_id']
fresh = db.get_pending_by_id(fresh_id)
fresh_token = fresh['email_token']
pre_link = client.get('/signup').get_data(as_text=True)
verified_page = client.get(f'/verify-email/{fresh_token}', follow_redirects=True).get_data(as_text=True)
with client.session_transaction() as session:
    marker = session.get('email_verification_completed_for')

def pending_script(page):
    match = re.search(r'const pendingRegistration = (.*?);', page)
    if not match:
        return 'missing'
    return 'null' if match.group(1).strip() == 'null' else 'object'

print('stale_verified_page_pending_value:', pending_script(stale_page))
print('fresh_pending_email_verified:', bool(fresh['email_verified']))
print('pre_link_pending_value:', pending_script(pre_link))
print('post_link_marker_matches:', marker == fresh_id)
print('pre_link_has_send_button:', 'id="sendEmailLink"' in pre_link)
print('post_link_shows_verified:', '✓ Email Verified' in verified_page)
print('post_link_hides_send_button:', 'id="sendEmailLink"' not in verified_page)
print('post_link_preserves_email:', f'value="{fresh_email}"' in verified_page)

db.delete_pending(pending_id)
db.delete_pending(fresh_id)

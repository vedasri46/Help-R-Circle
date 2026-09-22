import re
import sys
import time
from unittest.mock import patch

sys.path.insert(0, 'local_helper_network')
from app import app, db

client = app.test_client()

def field_value(page, field_id):
    match = re.search(rf'id="{field_id}"[^>]*value="([^"]*)"', page)
    return match.group(1) if match else None

with patch('app.send_verification_email'):
    response = client.post('/create-pending', data={
        'email': f'nameless-{int(time.time())}@example.com',
    })
nameless_id = response.get_json()['pending_id']
nameless_page = client.get('/signup').get_data(as_text=True)
nameless_pending = db.get_pending_by_id(nameless_id)

with patch('app.send_verification_email'):
    response = client.post('/create-pending', data={
        'email': f'named-{int(time.time())}@example.com',
        'username': 'Actual User',
    })
named_id = response.get_json()['pending_id']
named_page = client.get('/signup').get_data(as_text=True)
named_pending = db.get_pending_by_id(named_id)

print('nameless_stored_username_is_empty:', nameless_pending['username'] == '')
print('nameless_form_name_is_empty:', field_value(nameless_page, 'username') == '')
print('nameless_form_name_has_no_pending_prefix:', not (field_value(nameless_page, 'username') or '').startswith('pending_'))
print('named_stored_username_preserved:', named_pending['username'] == 'Actual User')
print('named_form_name_preserved:', field_value(named_page, 'username') == 'Actual User')

db.delete_pending(nameless_id)
db.delete_pending(named_id)

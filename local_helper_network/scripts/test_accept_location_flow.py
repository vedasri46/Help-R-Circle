import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from app import app, db

request_id = db.add_help_request('Accept Test', '9876543210', 'Area', 'Other', 'Test', user_id=None)
helper_id = None
with db.connect() as conn:
    row = conn.execute("SELECT id FROM volunteers LIMIT 1").fetchone()
    if row:
        helper_id = row['id']
if helper_id:
    db.update_request_status(request_id, 'accepted', helper_id=helper_id, helper_name='Helper')
    req = dict(db.get_request_by_id(request_id))
    print('accepted_status_persisted:', req['status'] == 'accepted')
    print('accepted_helper_persisted:', req['volunteer_id'] == helper_id)
else:
    print('accepted_status_persisted: skipped_no_helper_fixture')
    print('accepted_helper_persisted: skipped_no_helper_fixture')
with db.connect() as conn:
    conn.execute('DELETE FROM help_requests WHERE id = ?', (request_id,))

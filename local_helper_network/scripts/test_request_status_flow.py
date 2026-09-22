import os
import sqlite3
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from app import db

request_id = db.add_help_request('Status Test', '9876543210', 'Area', 'Other', 'Test', user_id=None)
expected = ['submitted', 'helper_assigned', 'helper_on_way', 'helper_near_location', 'helper_reached_location', 'completed']
actual = []
for status in expected:
    db.update_request_status(request_id, status)
    actual.append(db.get_request_by_id(request_id)['status'])
print('status_sequence_matches:', actual == expected)
print('initial_status:', actual[0])
print('final_status:', actual[-1])
with db.connect() as conn:
    conn.execute('DELETE FROM help_requests WHERE id = ?', (request_id,))

import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from app import db

request_id = db.add_help_request(
    'Location Test', '9876543210', 'Detected Address', 'Other', 'Test request',
    user_id=None, request_latitude=17.385, request_longitude=78.486,
)
row = db.get_request_by_id(request_id)
print('request_id:', request_id)
print('latitude_stored:', row['request_latitude'] == 17.385)
print('longitude_stored:', row['request_longitude'] == 78.486)
with db.connect() as conn:
    conn.execute('DELETE FROM help_requests WHERE id = ?', (request_id,))

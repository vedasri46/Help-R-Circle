import os
import sqlite3

db_path = os.path.join(os.path.dirname(__file__), '..', 'local_helper.db')
conn = sqlite3.connect(db_path)
checks = {
    'admin_count': conn.execute("SELECT COUNT(*) FROM users WHERE role = 'admin'").fetchone()[0],
    'non_admin_count': conn.execute("SELECT COUNT(*) FROM users WHERE role != 'admin'").fetchone()[0],
    'volunteer_count': conn.execute('SELECT COUNT(*) FROM volunteers').fetchone()[0],
    'pending_count': conn.execute('SELECT COUNT(*) FROM pending_registrations').fetchone()[0],
    'non_admin_phone_count': conn.execute("SELECT COUNT(*) FROM users WHERE role != 'admin' AND phone IS NOT NULL AND phone != ''").fetchone()[0],
    'volunteer_phone_count': conn.execute("SELECT COUNT(*) FROM volunteers WHERE phone IS NOT NULL AND phone != ''").fetchone()[0],
    'helper_location_count': conn.execute('SELECT COUNT(*) FROM helper_locations').fetchone()[0],
}
conn.close()
for key, value in checks.items():
    print(f'{key}: {value}')

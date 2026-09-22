import sqlite3, os
DB = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'local_helper.db'))
conn = sqlite3.connect(DB)
conn.row_factory = sqlite3.Row
cur = conn.cursor()
print('Users with test_/dup_/bad_ in email:')
rows = cur.execute("SELECT id, email, username, phone, is_verified, phone_verified FROM users WHERE email LIKE '%test_%' OR email LIKE '%dup_%' OR email LIKE '%bad_%'").fetchall()
for r in rows:
    print(dict(r))
print('All users count:', cur.execute('SELECT COUNT(*) FROM users').fetchone()[0])
print('Volunteer rows with email containing test/dup/bad:')
rows = cur.execute("SELECT * FROM volunteers WHERE email LIKE '%test_%' OR email LIKE '%dup_%' OR email LIKE '%bad_%'").fetchall()
for r in rows:
    print(dict(r))
conn.close()

import sqlite3
import os

DB = os.path.join(os.path.dirname(__file__), '..', 'local_helper.db')
DB = os.path.abspath(DB)

TEST_EMAILS = [
    'test_user_1@example.com',
    'test_helper_1@example.com',
    'bad_phone@example.com',
    'dup_phone@example.com'
]

print('Using DB:', DB)
conn = sqlite3.connect(DB)
conn.row_factory = sqlite3.Row
cur = conn.cursor()

# Find users matching test emails
users = cur.execute('SELECT id, email, username, role FROM users WHERE email IN ({})'.format(','.join('?'*len(TEST_EMAILS))), TEST_EMAILS).fetchall()
print('Found users to delete:', [dict(u) for u in users])

# Delete related help_requests and volunteer rows
for u in users:
    uid = u['id']
    print('Deleting help_requests for user id', uid)
    cur.execute('DELETE FROM help_requests WHERE user_id = ?', (uid,))
    print('Deleting volunteers rows linked to user id', uid)
    cur.execute('DELETE FROM volunteers WHERE user_id = ?', (uid,))

# Also delete volunteers that were created without user_id but have test emails
vols = cur.execute('SELECT id, email, name FROM volunteers WHERE email IN ({})'.format(','.join('?'*len(TEST_EMAILS))), TEST_EMAILS).fetchall()
print('Found volunteer rows to delete:', [dict(v) for v in vols])
for v in vols:
    cur.execute('DELETE FROM volunteers WHERE id = ?', (v['id'],))

# Finally delete the users (avoid deleting admin role)
for u in users:
    if u['role'] == 'admin':
        print('Skipping admin user', u['email'])
        continue
    print('Deleting user', u['email'])
    cur.execute('DELETE FROM users WHERE id = ?', (u['id'],))

conn.commit()
print('Cleanup committed.')

# Verify
remaining = cur.execute('SELECT id, email FROM users WHERE email IN ({})'.format(','.join('?'*len(TEST_EMAILS))), TEST_EMAILS).fetchall()
print('Remaining matching users:', [dict(r) for r in remaining])

remaining_vols = cur.execute('SELECT id, email FROM volunteers WHERE email IN ({})'.format(','.join('?'*len(TEST_EMAILS))), TEST_EMAILS).fetchall()
print('Remaining matching volunteers:', [dict(r) for r in remaining_vols])

conn.close()

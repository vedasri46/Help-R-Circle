import sqlite3, os, sys
DB=r'c:\Users\VEDA\Downloads\local_helper_network\local_helper_network\local_helper.db'
if not os.path.exists(DB):
    print('DB not found:', DB); sys.exit(1)
conn = sqlite3.connect(DB)
conn.row_factory = sqlite3.Row
cur = conn.cursor()
row = cur.execute('SELECT * FROM pending_registrations ORDER BY id DESC LIMIT 1').fetchone()
if not row:
    print('No pending rows found')
    sys.exit(1)
print('id', row['id'])
print('email', row['email'])
print('email_verified', row['email_verified'])
print('email_token_sent_at', row['email_token_sent_at'])
print('phone', row['phone'])
print('phone_verified', row['phone_verified'])
print('created_at', row['created_at'])
# token info (length only)
print('email_token_present', bool(row['email_token']))
if row['email_token']:
    print('email_token_len', len(row['email_token']))
conn.close()

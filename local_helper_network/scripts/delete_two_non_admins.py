import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from database import Database


def main():
    db = Database()
    with db.connect() as conn:
        cur = conn.cursor()
        users = cur.execute("SELECT id, username, email, role FROM users ORDER BY id").fetchall()
        non_admins = [u for u in users if u['role'] != 'admin']
        admins = [u for u in users if u['role'] == 'admin']

        print('Total users found:', len(users))
        print('Admin users:', len(admins))
        print('Non-admin users:', len(non_admins))
        for u in non_admins:
            print(dict(u))

        if len(non_admins) != 2:
            print('\nAborting: found != 2 non-admin users. No deletions performed.')
            return 1
        if len(admins) < 1:
            print('\nAborting: no admin account found. No deletions performed.')
            return 1

        # Proceed to delete each non-admin user and directly tied volunteer row if present
        for u in non_admins:
            uid = u['id']
            vol = cur.execute('SELECT id FROM volunteers WHERE user_id = ?', (uid,)).fetchone()
            if vol:
                vid = vol['id']
                print(f'Deleting volunteer id={vid} tied to user id={uid}')
                cur.execute('DELETE FROM helper_locations WHERE helper_id = ?', (vid,))
                cur.execute('DELETE FROM volunteers WHERE id = ?', (vid,))
            # delete help_requests tied to user (delete_user would also do this)
            print(f'Deleting help_requests tied to user id={uid}')
            cur.execute('DELETE FROM help_requests WHERE user_id = ?', (uid,))
            print(f'Deleting user id={uid}')
            cur.execute("DELETE FROM users WHERE id = ? AND role != 'admin'", (uid,))

        conn.commit()

        # Post-check
        remaining_users = cur.execute('SELECT id, username, email, role FROM users ORDER BY id').fetchall()
        remaining_non_admins = [u for u in remaining_users if u['role'] != 'admin']
        remaining_admins = [u for u in remaining_users if u['role'] == 'admin']
        print('\nAfter deletion:')
        print('Total users remaining:', len(remaining_users))
        print('Admin users remaining:', len(remaining_admins))
        print('Non-admin users remaining:', len(remaining_non_admins))
        if remaining_admins:
            print('Admin sample:', dict(remaining_admins[0]))
    return 0

if __name__ == '__main__':
    exit(main())

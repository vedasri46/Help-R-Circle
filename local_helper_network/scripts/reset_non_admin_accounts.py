import os
import sqlite3

DB_PATH = os.path.join(os.path.dirname(__file__), '..', 'local_helper.db')


def main():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        conn.execute('PRAGMA foreign_keys = ON')
        cur = conn.cursor()

        admins = cur.execute("SELECT id FROM users WHERE role = 'admin'").fetchall()
        if not admins:
            raise RuntimeError('Aborting: no admin account exists')

        non_admin_ids = [row['id'] for row in cur.execute("SELECT id FROM users WHERE role != 'admin'").fetchall()]
        volunteer_ids = [row['id'] for row in cur.execute('SELECT id FROM volunteers').fetchall()]

        user_placeholders = ','.join('?' for _ in non_admin_ids)
        volunteer_placeholders = ','.join('?' for _ in volunteer_ids)

        linked_requests = 0
        if non_admin_ids or volunteer_ids:
            clauses = []
            params = []
            if non_admin_ids:
                clauses.append(f'user_id IN ({user_placeholders})')
                params.extend(non_admin_ids)
            if volunteer_ids:
                clauses.append(f'volunteer_id IN ({volunteer_placeholders})')
                params.extend(volunteer_ids)
            linked_requests = cur.execute(
                f"SELECT COUNT(*) FROM help_requests WHERE {' OR '.join(clauses)}", params
            ).fetchone()[0]

        counts = {
            'admins_before': len(admins),
            'non_admin_users_before': len(non_admin_ids),
            'volunteers_before': len(volunteer_ids),
            'linked_help_requests_before': linked_requests,
            'pending_registrations_before': cur.execute('SELECT COUNT(*) FROM pending_registrations').fetchone()[0],
            'helper_locations_before': cur.execute('SELECT COUNT(*) FROM helper_locations').fetchone()[0],
        }

        conn.execute('BEGIN')
        # Remove location rows before volunteer rows.
        cur.execute('DELETE FROM helper_locations')

        if non_admin_ids or volunteer_ids:
            clauses = []
            params = []
            if non_admin_ids:
                clauses.append(f'user_id IN ({user_placeholders})')
                params.extend(non_admin_ids)
            if volunteer_ids:
                clauses.append(f'volunteer_id IN ({volunteer_placeholders})')
                params.extend(volunteer_ids)
            cur.execute(f"DELETE FROM help_requests WHERE {' OR '.join(clauses)}", params)

        # All volunteers are helper accounts/profile rows; none are admin accounts.
        cur.execute('DELETE FROM volunteers')
        cur.execute('DELETE FROM pending_registrations')
        cur.execute("DELETE FROM users WHERE role != 'admin'")

        remaining_admins = cur.execute("SELECT COUNT(*) FROM users WHERE role = 'admin'").fetchone()[0]
        remaining_non_admins = cur.execute("SELECT COUNT(*) FROM users WHERE role != 'admin'").fetchone()[0]
        remaining_volunteers = cur.execute('SELECT COUNT(*) FROM volunteers').fetchone()[0]
        remaining_pending = cur.execute('SELECT COUNT(*) FROM pending_registrations').fetchone()[0]
        remaining_locations = cur.execute('SELECT COUNT(*) FROM helper_locations').fetchone()[0]

        if remaining_admins != len(admins) or remaining_non_admins or remaining_volunteers or remaining_pending or remaining_locations:
            raise RuntimeError('Cleanup verification failed; rolling back')

        conn.commit()
        print('Cleanup committed')
        for key, value in counts.items():
            print(f'{key}: {value}')
        print('admins_after:', remaining_admins)
        print('non_admin_users_after:', remaining_non_admins)
        print('volunteers_after:', remaining_volunteers)
        print('pending_registrations_after:', remaining_pending)
        print('helper_locations_after:', remaining_locations)
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


if __name__ == '__main__':
    main()

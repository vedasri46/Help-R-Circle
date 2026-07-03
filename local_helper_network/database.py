"""
database.py — SQLite Database Layer
=====================================
All database logic lives here so app.py stays clean.
Tables: users, help_requests, volunteers, contact_messages
"""

import sqlite3
from datetime import datetime
import os
from werkzeug.security import generate_password_hash, check_password_hash

DB_PATH = os.path.join(os.path.dirname(__file__), "local_helper.db")


class Database:
    """Simple wrapper around SQLite for Help R Circle."""

    # ── Connection helper ─────────────────────────────────────────────────────
    def _connect(self):
        """Return a new connection with row-factory so rows act like dicts."""
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        return conn

    # ── Schema Setup ──────────────────────────────────────────────────────────
    def init_db(self):
        """Create all tables if they do not already exist."""
        conn = self._connect()
        cursor = conn.cursor()

        # ── Users table (for authentication) ──────────────────────────────────
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                username        TEXT    NOT NULL UNIQUE,
                email           TEXT    NOT NULL UNIQUE,
                password_hash   TEXT    NOT NULL,
                role            TEXT    NOT NULL DEFAULT 'user',
                created_at      TEXT    DEFAULT (datetime('now', 'localtime')),
                updated_at      TEXT    DEFAULT (datetime('now', 'localtime'))
            )
        """)

        # ── Help Requests table ───────────────────────────────────────────────
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS help_requests (
                id                  INTEGER PRIMARY KEY AUTOINCREMENT,
                name                TEXT    NOT NULL,
                phone               TEXT    NOT NULL,
                location            TEXT    NOT NULL,
                help_type           TEXT    NOT NULL,
                description         TEXT    NOT NULL,
                urgency             TEXT    DEFAULT 'normal',
                status              TEXT    DEFAULT 'pending',
                user_id             INTEGER REFERENCES users(id),
                volunteer_id        INTEGER,
                volunteer_name      TEXT    DEFAULT NULL,
                volunteer_email     TEXT,
                volunteer_phone     TEXT,
                volunteer_location  TEXT,
                accepted_at         TEXT,
                created_at          TEXT    DEFAULT (datetime('now', 'localtime')),
                updated_at          TEXT    DEFAULT (datetime('now', 'localtime'))
            )
        """)

        # ── Volunteers table ──────────────────────────────────────────────────
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS volunteers (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,                user_id      INTEGER REFERENCES users(id),                name         TEXT NOT NULL,
                phone        TEXT NOT NULL,
                email        TEXT,
                location     TEXT NOT NULL,
                skills       TEXT NOT NULL,
                availability TEXT NOT NULL,
                about        TEXT,
                is_active    INTEGER DEFAULT 1,
                created_at   TEXT DEFAULT (datetime('now', 'localtime'))
            )
        """)

        # ── Contact Messages table ────────────────────────────────────────────
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS contact_messages (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                name       TEXT NOT NULL,
                email      TEXT NOT NULL,
                subject    TEXT,
                message    TEXT NOT NULL,
                status     TEXT DEFAULT 'pending',
                created_at TEXT DEFAULT (datetime('now', 'localtime')),
                updated_at TEXT DEFAULT (datetime('now', 'localtime'))
            )
        """)

        conn.commit()

        # Ensure users table has role column for older databases.
        cols = [r[1] for r in cursor.execute("PRAGMA table_info(users)").fetchall()]
        if 'role' not in cols:
            cursor.execute("ALTER TABLE users ADD COLUMN role TEXT NOT NULL DEFAULT 'user'")
            conn.commit()
            print("🔧 Migrated: added role column to users table.")

        conn.close()
        print("✅ Database initialized.")

        # Ensure schema is up-to-date: add user_id to help_requests if missing
        conn = self._connect()
        cur = conn.cursor()
        cols = [r[1] for r in cur.execute("PRAGMA table_info(help_requests)").fetchall()]
        if 'user_id' not in cols:
            cur.execute("ALTER TABLE help_requests ADD COLUMN user_id INTEGER REFERENCES users(id)")
            conn.commit()
            print("🔧 Migrated: added user_id to help_requests table.")
        
        # Add volunteer contact info columns if missing
        if 'volunteer_id' not in cols:
            cur.execute("ALTER TABLE help_requests ADD COLUMN volunteer_id INTEGER")
            conn.commit()
            print("🔧 Migrated: added volunteer_id to help_requests table.")
        if 'volunteer_email' not in cols:
            cur.execute("ALTER TABLE help_requests ADD COLUMN volunteer_email TEXT")
            conn.commit()
            print("🔧 Migrated: added volunteer_email to help_requests table.")
        if 'volunteer_phone' not in cols:
            cur.execute("ALTER TABLE help_requests ADD COLUMN volunteer_phone TEXT")
            conn.commit()
            print("🔧 Migrated: added volunteer_phone to help_requests table.")
        if 'volunteer_location' not in cols:
            cur.execute("ALTER TABLE help_requests ADD COLUMN volunteer_location TEXT")
            conn.commit()
            print("🔧 Migrated: added volunteer_location to help_requests table.")
        if 'accepted_at' not in cols:
            cur.execute("ALTER TABLE help_requests ADD COLUMN accepted_at TEXT")
            conn.commit()
            print("🔧 Migrated: added accepted_at to help_requests table.")
        if 'request_latitude' not in cols:
            cur.execute("ALTER TABLE help_requests ADD COLUMN request_latitude REAL")
            conn.commit()
            print("🔧 Migrated: added request_latitude to help_requests table.")
        if 'request_longitude' not in cols:
            cur.execute("ALTER TABLE help_requests ADD COLUMN request_longitude REAL")
            conn.commit()
            print("🔧 Migrated: added request_longitude to help_requests table.")
        if 'volunteer_latitude' not in cols:
            cur.execute("ALTER TABLE help_requests ADD COLUMN volunteer_latitude REAL")
            conn.commit()
            print("🔧 Migrated: added volunteer_latitude to help_requests table.")
        if 'volunteer_longitude' not in cols:
            cur.execute("ALTER TABLE help_requests ADD COLUMN volunteer_longitude REAL")
            conn.commit()
            print("🔧 Migrated: added volunteer_longitude to help_requests table.")
        if 'journey_started_at' not in cols:
            cur.execute("ALTER TABLE help_requests ADD COLUMN journey_started_at TEXT")
            conn.commit()
            print("🔧 Migrated: added journey_started_at to help_requests table.")
        if 'reached_at' not in cols:
            cur.execute("ALTER TABLE help_requests ADD COLUMN reached_at TEXT")
            conn.commit()
            print("🔧 Migrated: added reached_at to help_requests table.")
        if 'completed_at' not in cols:
            cur.execute("ALTER TABLE help_requests ADD COLUMN completed_at TEXT")
            conn.commit()
            print("🔧 Migrated: added completed_at to help_requests table.")
        if 'last_location_update' not in cols:
            cur.execute("ALTER TABLE help_requests ADD COLUMN last_location_update TEXT")
            conn.commit()
            print("🔧 Migrated: added last_location_update to help_requests table.")
        conn.close()

        # Ensure contact_messages table has status and subject columns
        conn = self._connect()
        cur = conn.cursor()
        cols = [r[1] for r in cur.execute("PRAGMA table_info(contact_messages)").fetchall()]
        if 'status' not in cols:
            cur.execute("ALTER TABLE contact_messages ADD COLUMN status TEXT DEFAULT 'pending'")
            conn.commit()
            print("🔧 Migrated: added status column to contact_messages table.")
        if 'subject' not in cols:
            cur.execute("ALTER TABLE contact_messages ADD COLUMN subject TEXT")
            conn.commit()
            print("🔧 Migrated: added subject column to contact_messages table.")
        if 'updated_at' not in cols:
            cur.execute("ALTER TABLE contact_messages ADD COLUMN updated_at TEXT DEFAULT (datetime('now', 'localtime'))")
            conn.commit()
            print("🔧 Migrated: added updated_at column to contact_messages table.")
        conn.close()

        # ── Migrate: Add user_id to volunteers table if missing ──────────────
        conn = self._connect()
        cur = conn.cursor()
        cols = [r[1] for r in cur.execute("PRAGMA table_info(volunteers)").fetchall()]
        if 'user_id' not in cols:
            cur.execute("ALTER TABLE volunteers ADD COLUMN user_id INTEGER REFERENCES users(id)")
            conn.commit()
            print("🔧 Migrated: added user_id to volunteers table.")
        conn.close()

        # Ensure a default admin account exists
        if not self.get_user_by_email("admin@localhelper.com"):
            admin_user_id = self.register_user("admin", "admin@localhelper.com", "admin123", role="admin")
            if admin_user_id:
                print("🔒 Default admin account initialized: admin@localhelper.com / admin123")
            else:
                print("⚠️  Admin account creation failed")
        # Repair: ensure volunteers table has an entry for every user with role 'volunteer'
        try:
            self.repair_missing_volunteers()
        except Exception:
            # Do not raise on init; print for diagnostics
            print("⚠️  repair_missing_volunteers failed during init")

    # ── User Authentication ───────────────────────────────────────────────────
    def register_user(self, username, email, password, role="user"):
        """Register a new user. Returns user_id if successful, False if user exists."""
        try:
            conn = self._connect()
            password_hash = generate_password_hash(password)
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO users (username, email, password_hash, role)
                VALUES (?, ?, ?, ?)
            """, (username, email, password_hash, role))
            conn.commit()
            user_id = cursor.lastrowid
            conn.close()
            return user_id
        except sqlite3.IntegrityError:
            # Email or username already exists
            return False

    def register_admin(self, username, email, password):
        """Register an admin account. Returns user_id if successful."""
        return self.register_user(username, email, password, role="admin")

    def login_user(self, email, password):
        """Authenticate a user. Returns user dict if successful, None otherwise."""
        conn = self._connect()
        user = conn.execute(
            "SELECT * FROM users WHERE email = ?", (email,)
        ).fetchone()
        conn.close()

        if user and check_password_hash(user['password_hash'], password):
            return dict(user)  # Convert sqlite3.Row to dict
        return None

    def get_user_by_email(self, email):
        """Fetch a user by email."""
        conn = self._connect()
        user = conn.execute(
            "SELECT * FROM users WHERE email = ?", (email,)
        ).fetchone()
        conn.close()
        return dict(user) if user else None

    def get_user_by_id(self, user_id):
        """Fetch a user by ID."""
        conn = self._connect()
        user = conn.execute(
            "SELECT * FROM users WHERE id = ?", (user_id,)
        ).fetchone()
        conn.close()
        return dict(user) if user else None

    # ── Help Requests CRUD ────────────────────────────────────────────────────
    def add_help_request(self, name, phone, location, help_type,
                         description, urgency="normal", user_id=None,
                         request_latitude=None, request_longitude=None):
        """Insert a new help request. Returns the new row ID."""
        # Prevent obvious duplicates: same name, phone, location, help_type
        existing = self.find_duplicate_help_request(name, phone, location, help_type)
        if existing:
            # Return existing id instead of inserting duplicate
            return existing

        conn = self._connect()
        cursor = conn.cursor()
        if user_id:
            cursor.execute("""
                INSERT INTO help_requests
                    (name, phone, location, help_type, description, urgency, user_id, request_latitude, request_longitude)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (name, phone, location, help_type, description, urgency, user_id, request_latitude, request_longitude))
        else:
            cursor.execute("""
                INSERT INTO help_requests
                    (name, phone, location, help_type, description, urgency, request_latitude, request_longitude)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (name, phone, location, help_type, description, urgency, request_latitude, request_longitude))
        conn.commit()
        new_id = cursor.lastrowid
        conn.close()
        return new_id

    def get_requests_by_user(self, user_id):
        """Return all help requests created by a specific user ID."""
        conn = self._connect()
        rows = conn.execute(
            "SELECT * FROM help_requests WHERE user_id = ? ORDER BY datetime(created_at) DESC",
            (user_id,)
        ).fetchall()
        conn.close()
        return rows

    def get_completed_requests_by_volunteer(self, volunteer_id):
        """Return completed help requests assigned to the given volunteer ID."""
        conn = self._connect()
        rows = conn.execute(
            "SELECT * FROM help_requests WHERE volunteer_id = ? AND status = 'completed' "
            "ORDER BY datetime(completed_at) DESC",
            (volunteer_id,)
        ).fetchall()
        conn.close()
        return rows

    def get_requests(self, status="all", help_type="all", search=""):
        """Fetch help requests with optional filters."""
        conn  = self._connect()
        query = "SELECT * FROM help_requests WHERE 1=1"
        params = []

        if status != "all":
            query += " AND status = ?"
            params.append(status)

        if help_type != "all":
            query += " AND help_type = ?"
            params.append(help_type)

        if search:
            query += " AND (name LIKE ? OR location LIKE ? OR description LIKE ?)"
            like = f"%{search}%"
            params.extend([like, like, like])

        query += " ORDER BY CASE urgency WHEN 'urgent' THEN 1 WHEN 'normal' THEN 2 ELSE 3 END, created_at DESC"

        rows = conn.execute(query, params).fetchall()
        conn.close()
        return rows

    def get_request_by_id(self, req_id):
        """Fetch a single request by ID."""
        conn = self._connect()
        row  = conn.execute(
            "SELECT * FROM help_requests WHERE id = ?", (req_id,)
        ).fetchone()
        conn.close()
        return row

    def get_volunteer_by_name(self, name):
        """Fetch a volunteer record by exact name."""
        conn = self._connect()
        row = conn.execute(
            "SELECT * FROM volunteers WHERE name = ?", (name,)
        ).fetchone()
        conn.close()
        return row

    def get_volunteer_by_email(self, email):
        """Fetch a volunteer record by email."""
        conn = self._connect()
        row = conn.execute(
            "SELECT * FROM volunteers WHERE email = ?", (email,)
        ).fetchone()
        conn.close()
        return row

    def update_request_status(self, req_id, new_status, volunteer_name=None, 
                             volunteer_id=None, volunteer_email=None, 
                             volunteer_phone=None, volunteer_location=None,
                             accepted_at=None, journey_started_at=None,
                             reached_at=None, completed_at=None, volunteer_latitude=None,
                             volunteer_longitude=None, last_location_update=None):
        """Update request status and optionally store journey/location metadata."""
        conn = self._connect()

        if new_status == 'volunteer_assigned' and volunteer_name:
            conn.execute("""
                UPDATE help_requests
                SET status = ?, volunteer_name = ?, volunteer_id = ?,
                    volunteer_email = ?, volunteer_phone = ?, volunteer_location = ?,
                    accepted_at = COALESCE(?, datetime('now','localtime')),
                    updated_at = datetime('now','localtime')
                WHERE id = ?
            """, (new_status, volunteer_name, volunteer_id, volunteer_email,
                  volunteer_phone, volunteer_location, accepted_at, req_id))
        elif volunteer_name:
            conn.execute("""
                UPDATE help_requests
                SET status = ?, volunteer_name = ?,
                    updated_at = datetime('now','localtime')
                WHERE id = ?
            """, (new_status, volunteer_name, req_id))
        else:
            conn.execute("""
                UPDATE help_requests
                SET status = ?, updated_at = datetime('now','localtime')
                WHERE id = ?
            """, (new_status, req_id))

        if journey_started_at is not None:
            conn.execute("UPDATE help_requests SET journey_started_at = ? WHERE id = ?", (journey_started_at, req_id))
        if reached_at is not None:
            conn.execute("UPDATE help_requests SET reached_at = ? WHERE id = ?", (reached_at, req_id))
        if completed_at is not None:
            conn.execute("UPDATE help_requests SET completed_at = ? WHERE id = ?", (completed_at, req_id))
        if volunteer_latitude is not None:
            conn.execute("UPDATE help_requests SET volunteer_latitude = ? WHERE id = ?", (volunteer_latitude, req_id))
        if volunteer_longitude is not None:
            conn.execute("UPDATE help_requests SET volunteer_longitude = ? WHERE id = ?", (volunteer_longitude, req_id))
        if last_location_update is not None:
            conn.execute("UPDATE help_requests SET last_location_update = ? WHERE id = ?", (last_location_update, req_id))

        conn.commit()
        conn.close()

    # ── Volunteers CRUD ───────────────────────────────────────────────────────
    def add_volunteer(self, name, phone, email, location,
                      skills, availability, about="", user_id=None):
        """Insert a new volunteer. Returns the new row ID."""
        # Prevent obvious duplicates: same name, phone, email
        existing = self.find_duplicate_volunteer(name, phone, email)
        if existing:
            return existing

        conn = self._connect()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO volunteers
                (user_id, name, phone, email, location, skills, availability, about)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (user_id, name, phone, email, location, skills, availability, about))
        conn.commit()
        new_id = cursor.lastrowid
        conn.close()
        return new_id

    def get_volunteers(self):
        """Fetch all active volunteers."""
        conn  = self._connect()
        rows  = conn.execute(
            "SELECT * FROM volunteers WHERE is_active=1 ORDER BY created_at DESC"
        ).fetchall()
        conn.close()
        return rows

    # ── Contact Messages ──────────────────────────────────────────────────────
    def add_contact_message(self, name, email, message, subject=""):
        conn = self._connect()
        conn.execute(
            "INSERT INTO contact_messages (name, email, subject, message) VALUES (?, ?, ?, ?)",
            (name, email, subject, message)
        )
        conn.commit()
        conn.close()

    def get_all_contact_messages(self, search=""):
        """Fetch all contact messages, optionally filtered by search."""
        conn = self._connect()
        query = "SELECT * FROM contact_messages WHERE 1=1"
        params = []
        if search:
            query += " AND (name LIKE ? OR email LIKE ? OR subject LIKE ? OR message LIKE ?)"
            like = f"%{search}%"
            params.extend([like, like, like, like])
        query += " ORDER BY created_at DESC"
        rows = conn.execute(query, params).fetchall()
        conn.close()
        return rows

    def get_contact_message_by_id(self, msg_id):
        """Fetch a single contact message by ID."""
        conn = self._connect()
        row = conn.execute(
            "SELECT * FROM contact_messages WHERE id = ?", (msg_id,)
        ).fetchone()
        conn.close()
        return row

    def update_contact_message_status(self, msg_id, status):
        """Update contact message status (pending/resolved)."""
        conn = self._connect()
        conn.execute(
            "UPDATE contact_messages SET status = ?, updated_at = datetime('now', 'localtime') WHERE id = ?",
            (status, msg_id)
        )
        conn.commit()
        conn.close()

    def delete_contact_message(self, msg_id):
        """Delete a contact message."""
        conn = self._connect()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM contact_messages WHERE id = ?", (msg_id,))
        affected = cursor.rowcount
        conn.commit()
        conn.close()
        return affected > 0

    def get_contact_messages_stats(self):
        """Return contact messages statistics."""
        conn = self._connect()
        cur = conn.cursor()
        total = cur.execute("SELECT COUNT(*) FROM contact_messages").fetchone()[0]
        pending = cur.execute("SELECT COUNT(*) FROM contact_messages WHERE status = 'pending'").fetchone()[0]
        resolved = cur.execute("SELECT COUNT(*) FROM contact_messages WHERE status = 'resolved'").fetchone()[0]
        conn.close()
        return {
            "total": total,
            "pending": pending,
            "resolved": resolved,
        }

    # ── Statistics ────────────────────────────────────────────────────────────
    def get_stats(self):
        """Return a dict of counts used on the home page and dashboard."""
        conn   = self._connect()
        cur    = conn.cursor()

        total_requests   = cur.execute("SELECT COUNT(*) FROM help_requests").fetchone()[0]
        pending          = cur.execute("SELECT COUNT(*) FROM help_requests WHERE status='pending'").fetchone()[0]
        accepted         = cur.execute("SELECT COUNT(*) FROM help_requests WHERE status IN ('volunteer_assigned','volunteer_on_way','volunteer_near_location','volunteer_reached_location','accepted')").fetchone()[0]
        completed        = cur.execute("SELECT COUNT(*) FROM help_requests WHERE status='completed'").fetchone()[0]
        total_volunteers = cur.execute("SELECT COUNT(*) FROM volunteers WHERE is_active=1").fetchone()[0]

        conn.close()
        return {
            "total_requests":   total_requests,
            "pending":          pending,
            "accepted":         accepted,
            "completed":        completed,
            "total_volunteers": total_volunteers,
        }

    def get_admin_dashboard_stats(self):
        """Return admin dashboard statistics."""
        conn = self._connect()
        cur = conn.cursor()

        total_users = cur.execute("SELECT COUNT(*) FROM users WHERE role != 'admin'").fetchone()[0]
        total_admins = cur.execute("SELECT COUNT(*) FROM users WHERE role = 'admin'").fetchone()[0]
        total_requests = cur.execute("SELECT COUNT(*) FROM help_requests").fetchone()[0]
        pending_requests = cur.execute("SELECT COUNT(*) FROM help_requests WHERE status = 'pending'").fetchone()[0]
        accepted_requests = cur.execute("SELECT COUNT(*) FROM help_requests WHERE status IN ('volunteer_assigned','volunteer_on_way','volunteer_near_location','volunteer_reached_location','accepted')").fetchone()[0]
        completed_requests = cur.execute("SELECT COUNT(*) FROM help_requests WHERE status = 'completed'").fetchone()[0]
        total_volunteers = cur.execute("SELECT COUNT(*) FROM volunteers WHERE is_active=1").fetchone()[0]

        conn.close()
        return {
            "total_users": total_users,
            "total_admins": total_admins,
            "total_requests": total_requests,
            "pending_requests": pending_requests,
            "accepted_requests": accepted_requests,
            "completed_requests": completed_requests,
            "total_volunteers": total_volunteers,
        }

    def get_all_users(self, search=""):
        """Return all non-admin users, optionally filtered by search."""
        conn = self._connect()
        query = "SELECT * FROM users WHERE role != 'admin'"
        params = []
        if search:
            query += " AND (username LIKE ? OR email LIKE ?)"
            like = f"%{search}%"
            params.extend([like, like])
        query += " ORDER BY created_at DESC"
        rows = conn.execute(query, params).fetchall()
        conn.close()
        return rows

    def delete_user(self, user_id):
        """Delete a user and their help requests."""
        conn = self._connect()
        conn.execute("DELETE FROM help_requests WHERE user_id = ?", (user_id,))
        cursor = conn.cursor()
        cursor.execute("DELETE FROM users WHERE id = ? AND role != 'admin'", (user_id,))
        affected = cursor.rowcount
        conn.commit()
        conn.close()
        return affected > 0

    def get_all_volunteers(self, search=""):
        """Fetch volunteers, optionally filtered by name, email, or location."""
        conn = self._connect()
        query = "SELECT * FROM volunteers WHERE is_active=1"
        params = []
        if search:
            query += " AND (name LIKE ? OR email LIKE ? OR location LIKE ?)"
            like = f"%{search}%"
            params.extend([like, like, like])
        query += " ORDER BY created_at DESC"
        rows = conn.execute(query, params).fetchall()
        conn.close()
        return rows

    def delete_volunteer(self, volunteer_id):
        """Delete a volunteer and reset any assigned requests."""
        volunteer = self.get_volunteer_by_id(volunteer_id)
        if not volunteer:
            return False

        conn = self._connect()
        conn.execute(
            "UPDATE help_requests SET volunteer_name = NULL, status = 'pending' WHERE volunteer_name = ?",
            (volunteer['name'],)
        )
        cursor = conn.cursor()
        cursor.execute("DELETE FROM volunteers WHERE id = ?", (volunteer_id,))
        affected = cursor.rowcount
        conn.commit()
        conn.close()
        return affected > 0

    def get_volunteer_by_id(self, volunteer_id):
        """Fetch a volunteer by ID."""
        conn = self._connect()
        row = conn.execute("SELECT * FROM volunteers WHERE id = ?", (volunteer_id,)).fetchone()
        conn.close()
        return row

    def delete_request(self, request_id):
        """Delete a help request."""
        conn = self._connect()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM help_requests WHERE id = ?", (request_id,))
        affected = cursor.rowcount
        conn.commit()
        conn.close()
        return affected > 0

    # ── Duplicate helpers and cleanup ─────────────────────────────────────────
    def find_duplicate_help_request(self, name, phone, location, help_type):
        """Return an existing help_request id matching the key or None.

        Matching is case-insensitive for text fields and compares phone exactly.
        """
        conn = self._connect()
        row = conn.execute(
            """
            SELECT id FROM help_requests
            WHERE LOWER(TRIM(name)) = LOWER(TRIM(?))
              AND phone = ?
              AND LOWER(TRIM(location)) = LOWER(TRIM(?))
              AND LOWER(TRIM(help_type)) = LOWER(TRIM(?))
            ORDER BY datetime(created_at) DESC
            LIMIT 1
            """, (name, phone, location, help_type)
        ).fetchone()
        conn.close()
        return int(row['id']) if row else None

    def find_duplicate_volunteer(self, name, phone, email):
        """Return an existing volunteer id matching the key or None.

        Matching is case-insensitive for text fields and compares phone exactly.
        """
        conn = self._connect()
        row = conn.execute(
            """
            SELECT id FROM volunteers
            WHERE LOWER(TRIM(name)) = LOWER(TRIM(?))
              AND phone = ?
              AND LOWER(TRIM(email)) = LOWER(TRIM(?))
            ORDER BY datetime(created_at) DESC
            LIMIT 1
            """, (name, phone, email)
        ).fetchone()
        conn.close()
        return int(row['id']) if row else None

    def repair_missing_volunteers(self):
        """Create volunteer rows for users with role 'volunteer' that lack a volunteers record.

        Returns a list of created volunteer ids for reporting.
        """
        conn = self._connect()
        cur = conn.cursor()
        created = []

        # Find all users with role volunteer
        users = cur.execute("SELECT id, username, email FROM users WHERE role = 'volunteer'").fetchall()
        for u in users:
            uid = u['id']
            # Check if there's already a volunteers row linked
            exists = cur.execute("SELECT id FROM volunteers WHERE user_id = ?", (uid,)).fetchone()
            if exists:
                continue

            # Also avoid creating if a volunteer exists with same email
            if u.get('email'):
                by_email = cur.execute("SELECT id FROM volunteers WHERE LOWER(TRIM(email)) = LOWER(TRIM(?))", (u['email'],)).fetchone()
                if by_email:
                    # Link existing volunteer to user_id
                    cur.execute("UPDATE volunteers SET user_id = ? WHERE id = ?", (uid, by_email['id']))
                    created.append(by_email['id'])
                    continue

            # Create a minimal volunteer record
            cur.execute(
                """INSERT INTO volunteers (user_id, name, phone, email, location, skills, availability, about)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (uid, u['username'] or '', '', u['email'] or '', '', '', '', '')
            )
            created.append(cur.lastrowid)

        conn.commit()
        conn.close()
        return created

    # ── User Profile Methods ──────────────────────────────────────────────────
    def update_user_profile(self, user_id, username, email, phone=None, location=None):
        """Update user profile information."""
        conn = self._connect()
        conn.execute("""
            UPDATE users
            SET username = ?, email = ?, updated_at = datetime('now','localtime')
            WHERE id = ?
        """, (username, email, user_id))
        conn.commit()
        conn.close()

    def get_user_activity_stats(self, user_id):
        """Get activity statistics for a user."""
        conn = self._connect()
        cur = conn.cursor()
        
        total_requests = cur.execute(
            "SELECT COUNT(*) FROM help_requests WHERE user_id = ?", (user_id,)
        ).fetchone()[0]
        
        pending_requests = cur.execute(
            "SELECT COUNT(*) FROM help_requests WHERE user_id = ? AND status = 'pending'", (user_id,)
        ).fetchone()[0]
        
        accepted_requests = cur.execute(
            "SELECT COUNT(*) FROM help_requests WHERE user_id = ? AND status = 'accepted'", (user_id,)
        ).fetchone()[0]
        
        completed_requests = cur.execute(
            "SELECT COUNT(*) FROM help_requests WHERE user_id = ? AND status = 'completed'", (user_id,)
        ).fetchone()[0]
        
        conn.close()
        return {
            'total_requests': total_requests,
            'pending_requests': pending_requests,
            'accepted_requests': accepted_requests,
            'completed_requests': completed_requests,
        }

    # ── Volunteer Profile Methods ─────────────────────────────────────────────
    def get_volunteer_by_user_id(self, user_id):
        """Get volunteer record linked to a user's account."""
        conn = self._connect()
        volunteer = conn.execute(
            "SELECT * FROM volunteers WHERE user_id = ?", (user_id,)
        ).fetchone()
        conn.close()
        return dict(volunteer) if volunteer else None

    def update_volunteer_profile(self, volunteer_id, name, phone, email, location, 
                                  skills, availability, about=""):
        """Update volunteer profile information."""
        conn = self._connect()
        conn.execute("""
            UPDATE volunteers
            SET name = ?, phone = ?, email = ?, location = ?, 
                skills = ?, availability = ?, about = ?
            WHERE id = ?
        """, (name, phone, email, location, skills, availability, about, volunteer_id))
        conn.commit()
        conn.close()

    def get_volunteer_activity_stats(self, volunteer_name):
        """Get activity statistics for a volunteer."""
        conn = self._connect()
        cur = conn.cursor()
        
        accepted_requests = cur.execute(
            "SELECT COUNT(*) FROM help_requests WHERE volunteer_name = ? AND status IN ('volunteer_assigned','volunteer_on_way','volunteer_near_location','volunteer_reached_location','accepted')",
            (volunteer_name,)
        ).fetchone()[0]
        
        completed_requests = cur.execute(
            "SELECT COUNT(*) FROM help_requests WHERE volunteer_name = ? AND status = 'completed'", 
            (volunteer_name,)
        ).fetchone()[0]
        
        active_requests = cur.execute(
            "SELECT COUNT(*) FROM help_requests WHERE volunteer_name = ? AND status IN ('volunteer_assigned','volunteer_on_way','volunteer_near_location','volunteer_reached_location','accepted')",
            (volunteer_name,)
        ).fetchone()[0]
        
        conn.close()
        return {
            'accepted_requests': accepted_requests,
            'completed_requests': completed_requests,
            'active_requests': active_requests,
        }

    def backup_db(self, backup_path=None):
        """Create a filesystem copy of the SQLite DB for safe backup.

        If `backup_path` is None the function will create a timestamped file
        next to the original DB, e.g. local_helper.db.bak-20260529-150405.
        Returns the path to the backup file.
        """
        import shutil, datetime
        src = DB_PATH
        if not backup_path:
            ts = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
            backup_path = src + f".bak-{ts}"
        shutil.copy(src, backup_path)
        return backup_path

    def cleanup_duplicate_help_requests(self, keep="latest"):
        """Remove duplicate help_requests.

        Duplicates are rows with same (name, phone, location, help_type).
        `keep` may be 'latest' or 'first'. Returns dict with deleted ids.
        """
        conn = self._connect()
        cur = conn.cursor()

        order = "DESC" if keep == "latest" else "ASC"
        rows = cur.execute(f"""
            SELECT id, name, phone, location, help_type, created_at
            FROM help_requests
            ORDER BY LOWER(TRIM(name)), phone, LOWER(TRIM(location)), LOWER(TRIM(help_type)), datetime(created_at) {order}
        """
        ).fetchall()

        seen = set()
        to_delete = []
        for r in rows:
            key = (r['name'].strip().lower(), r['phone'].strip(), r['location'].strip().lower(), r['help_type'].strip().lower())
            if key in seen:
                to_delete.append(r['id'])
            else:
                seen.add(key)

        if to_delete:
            cur.executemany("DELETE FROM help_requests WHERE id = ?", [(i,) for i in to_delete])
            conn.commit()

        conn.close()
        return {"deleted_count": len(to_delete), "deleted_ids": to_delete}

    def cleanup_duplicate_volunteers(self, keep="latest"):
        """Remove duplicate volunteers.

        Duplicates are rows with same (name, phone, email).
        `keep` may be 'latest' or 'first'. Returns dict with deleted ids.
        """
        conn = self._connect()
        cur = conn.cursor()

        order = "DESC" if keep == "latest" else "ASC"
        rows = cur.execute(f"""
            SELECT id, name, phone, email, created_at
            FROM volunteers
            ORDER BY LOWER(TRIM(name)), phone, LOWER(TRIM(email)), datetime(created_at) {order}
        """
        ).fetchall()

        seen = set()
        to_delete = []
        for r in rows:
            key = (r['name'].strip().lower(), r['phone'].strip(), (r['email'] or '').strip().lower())
            if key in seen:
                to_delete.append(r['id'])
            else:
                seen.add(key)

        if to_delete:
            cur.executemany("DELETE FROM volunteers WHERE id = ?", [(i,) for i in to_delete])
            conn.commit()

        conn.close()
        return {"deleted_count": len(to_delete), "deleted_ids": to_delete}

    # ── Sample Data ───────────────────────────────────────────────────────────
    def seed_sample_data(self):
        """Insert demo data only if the tables are empty (safe to call repeatedly)."""
        conn  = self._connect()
        count = conn.execute("SELECT COUNT(*) FROM help_requests").fetchone()[0]
        if count > 0:
            conn.close()
            return   # Already seeded

        sample_requests = [
            ("Meena Sharma",   "9876543210", "Banjara Hills",  "Grocery Shopping",
             "Need someone to buy milk, bread, vegetables from the nearby market. I am 72 years old and cannot walk long distances.", "urgent"),
            ("Ravi Kumar",     "9988776655", "Jubilee Hills",  "Medicine Collection",
             "Prescribed medicines need to be collected from Apollo Pharmacy on Road No. 36.", "normal"),
            ("Lakshmi Devi",   "9123456780", "Secunderabad",   "Bill Payment",
             "Electricity bill payment at TSSPDCL office. Senior citizen, need assistance.", "normal"),
            ("Arjun Reddy",    "9000112233", "Madhapur",       "Travel Assistance",
             "Need someone to accompany me to a hospital appointment at KIMS on Monday morning.", "urgent"),
            ("Priya Nair",     "9445566778", "Gachibowli",     "Other",
             "Recently delivered, need help with some household errands for a few days.", "normal"),
        ]

        for r in sample_requests:
            conn.execute("""
                INSERT INTO help_requests
                    (name, phone, location, help_type, description, urgency)
                VALUES (?,?,?,?,?,?)
            """, r)

        sample_volunteers = [
            ("Aditya Singh",  "9111222333", "aditya@email.com", "Banjara Hills",
             "Grocery Shopping, Medicine Collection", "Weekends + weekday evenings",
             "College student, happy to help seniors in my neighbourhood."),
            ("Sneha Verma",   "9222333444", "sneha@email.com",  "Jubilee Hills",
             "Bill Payment, Travel Assistance", "Saturday & Sunday all day",
             "Working professional, free on weekends."),
        ]

        for v in sample_volunteers:
            conn.execute("""
                INSERT INTO volunteers
                    (name, phone, email, location, skills, availability, about)
                VALUES (?,?,?,?,?,?,?)
            """, v)

        conn.commit()
        conn.close()
        print("✅ Sample data seeded.")

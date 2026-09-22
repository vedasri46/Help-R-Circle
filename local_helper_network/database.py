"""
database.py — SQLite Database Layer
=====================================
All database logic lives here so app.py stays clean.
Tables: users, help_requests, volunteers, contact_messages, helper_locations
"""

import sqlite3
import os
from contextlib import contextmanager
from datetime import datetime, timedelta
from werkzeug.security import generate_password_hash, check_password_hash

DB_PATH = os.path.join(os.path.dirname(__file__), "local_helper.db")


class Database:
    """Simple wrapper around SQLite for Help R Circle.

    This class centralizes connection handling with the `connect` context
    manager which ensures PRAGMAs are applied, commits on success,
    rolls back on exception, and always closes the connection to avoid
    sqlite3.OperationalError: database is locked.
    """

    def _connect(self):
        """Backwards-compatible helper that returns a raw connection.

        Prefer using the `connect` context manager instead of calling
        this directly.
        """
        return sqlite3.connect(DB_PATH, timeout=30, check_same_thread=False)

    @contextmanager
    def connect(self):
        """Yield a configured sqlite3.Connection and ensure safe commit/rollback.

        Usage:
            with db.connect() as conn:
                conn.execute(...)

        On normal exit the transaction is committed. If an exception is
        raised the transaction is rolled back and the exception re-raised.
        The connection is always closed.
        """
        conn = sqlite3.connect(DB_PATH, timeout=30, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        try:
            # Apply recommended pragmas for WAL + foreign keys
            try:
                conn.execute("PRAGMA foreign_keys = ON")
                conn.execute("PRAGMA journal_mode = WAL")
                conn.execute("PRAGMA synchronous = NORMAL")
            except Exception:
                # Don't fail if a PRAGMA isn't supported on a given build
                pass

            yield conn

            # Commit on success
            try:
                conn.commit()
            except Exception:
                try:
                    conn.rollback()
                except Exception:
                    pass
                raise

        except sqlite3.OperationalError:
            # Ensure rollback on operational errors
            try:
                conn.rollback()
            except Exception:
                pass
            raise
        except Exception:
            try:
                conn.rollback()
            except Exception:
                pass
            raise
        finally:
            try:
                conn.close()
            except Exception:
                pass

    # ---------------- Schema / Migrations ----------------
    def init_db(self):
        """Create required tables and run lightweight migrations.

        Uses a single connection for the entire initialization process
        to avoid nested opens/closes which can cause locking.
        """
        with self.connect() as conn:
            cur = conn.cursor()

            cur.execute("""
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

            cur.execute("""
                CREATE TABLE IF NOT EXISTS help_requests (
                    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
                    name                TEXT    NOT NULL,
                    phone               TEXT    NOT NULL,
                    location            TEXT    NOT NULL,
                    help_type           TEXT    NOT NULL,
                    description         TEXT    NOT NULL,
                    urgency             TEXT    DEFAULT 'normal',
                    priority            TEXT    NOT NULL DEFAULT 'normal',
                    status              TEXT    DEFAULT 'submitted',
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

            cur.execute("""
                CREATE TABLE IF NOT EXISTS volunteers (
                    id           INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id      INTEGER REFERENCES users(id),
                    name         TEXT NOT NULL,
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

            cur.execute("""
                CREATE TABLE IF NOT EXISTS contact_messages (
                    id         INTEGER PRIMARY KEY AUTOINCREMENT,
                    name       TEXT NOT NULL,
                    email      TEXT NOT NULL,
                    subject    TEXT,
                    message    TEXT NOT NULL,
                    status     TEXT DEFAULT 'pending',
                    user_id    INTEGER REFERENCES users(id),
                    created_at TEXT DEFAULT (datetime('now', 'localtime')),
                    updated_at TEXT DEFAULT (datetime('now', 'localtime'))
                )
            """)

            cur.execute("""
                CREATE TABLE IF NOT EXISTS notifications (
                    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id             INTEGER NOT NULL REFERENCES users(id),
                    message             TEXT NOT NULL,
                    notification_type   TEXT,
                    related_request_id  INTEGER,
                    is_read             INTEGER DEFAULT 0,
                    created_at          TEXT DEFAULT (datetime('now', 'localtime'))
                )
            """)

            cur.execute("""
                CREATE TABLE IF NOT EXISTS helper_locations (
                    id            INTEGER PRIMARY KEY AUTOINCREMENT,
                    helper_id     INTEGER NOT NULL,
                    request_id    INTEGER NOT NULL,
                    latitude      REAL NOT NULL,
                    longitude     REAL NOT NULL,
                    updated_at    TEXT DEFAULT (datetime('now', 'localtime')),
                    FOREIGN KEY(helper_id) REFERENCES volunteers(id),
                    FOREIGN KEY(request_id) REFERENCES help_requests(id)
                )
            """)

            # Lightweight migrations: check PRAGMA table_info once per table
            users_cols = [r[1] for r in cur.execute("PRAGMA table_info(users)").fetchall()]
            if 'role' not in users_cols:
                cur.execute("ALTER TABLE users ADD COLUMN role TEXT NOT NULL DEFAULT 'user'")
                print("🔧 Migrated: added role column to users table.")
            if 'is_verified' not in users_cols:
                cur.execute("ALTER TABLE users ADD COLUMN is_verified BOOLEAN DEFAULT 0")
                print("🔧 Migrated: added is_verified column to users table.")
            if 'verification_token' not in users_cols:
                cur.execute("ALTER TABLE users ADD COLUMN verification_token TEXT")
                print("🔧 Migrated: added verification_token column to users table.")
            if 'otp_code' not in users_cols:
                cur.execute("ALTER TABLE users ADD COLUMN otp_code TEXT")
                print("🔧 Migrated: added otp_code column to users table.")
            if 'otp_expiry' not in users_cols:
                cur.execute("ALTER TABLE users ADD COLUMN otp_expiry TEXT")
                print("🔧 Migrated: added otp_expiry column to users table.")
            if 'phone' not in users_cols:
                cur.execute("ALTER TABLE users ADD COLUMN phone TEXT")
                print("🔧 Migrated: added phone column to users table.")
            if 'location' not in users_cols:
                cur.execute("ALTER TABLE users ADD COLUMN location TEXT")
                print("🔧 Migrated: added location column to users table.")
            if 'phone_verified' not in users_cols:
                cur.execute("ALTER TABLE users ADD COLUMN phone_verified BOOLEAN DEFAULT 0")
                print("🔧 Migrated: added phone_verified column to users table.")
            if 'phone_otp_sent_at' not in users_cols:
                cur.execute("ALTER TABLE users ADD COLUMN phone_otp_sent_at TEXT")
                print("🔧 Migrated: added phone_otp_sent_at column to users table.")
            if 'phone_otp_attempts' not in users_cols:
                cur.execute("ALTER TABLE users ADD COLUMN phone_otp_attempts INTEGER DEFAULT 0")
                print("🔧 Migrated: added phone_otp_attempts column to users table.")
            if 'location_latitude' not in users_cols:
                cur.execute("ALTER TABLE users ADD COLUMN location_latitude REAL")
                print("🔧 Migrated: added location_latitude column to users table.")
            if 'location_longitude' not in users_cols:
                cur.execute("ALTER TABLE users ADD COLUMN location_longitude REAL")
                print("🔧 Migrated: added location_longitude column to users table.")

            # Pending registrations table for verification-before-create flow
            pending_cols = [r[1] for r in cur.execute("PRAGMA table_info(pending_registrations)").fetchall()]
            if not pending_cols:
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS pending_registrations (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        username TEXT NOT NULL,
                        email TEXT NOT NULL,
                        password_hash TEXT NOT NULL,
                        role TEXT NOT NULL DEFAULT 'user',
                        phone TEXT,
                        email_verified INTEGER DEFAULT 0,
                        phone_verified INTEGER DEFAULT 0,
                        email_token TEXT,
                        email_token_sent_at TEXT,
                        phone_otp_sent_at TEXT,
                        phone_otp_attempts INTEGER DEFAULT 0,
                        helper_location TEXT,
                        helper_skills TEXT,
                        helper_availability TEXT,
                        helper_about TEXT,
                        created_at TEXT DEFAULT (datetime('now', 'localtime'))
                    )
                """)
                print("🔧 Migrated: created pending_registrations table for verification flow.")

            help_cols = [r[1] for r in cur.execute("PRAGMA table_info(help_requests)").fetchall()]
            migrations = [
                ("user_id", "ALTER TABLE help_requests ADD COLUMN user_id INTEGER REFERENCES users(id)"),
                ("volunteer_id", "ALTER TABLE help_requests ADD COLUMN volunteer_id INTEGER"),
                ("volunteer_email", "ALTER TABLE help_requests ADD COLUMN volunteer_email TEXT"),
                ("volunteer_phone", "ALTER TABLE help_requests ADD COLUMN volunteer_phone TEXT"),
                ("volunteer_location", "ALTER TABLE help_requests ADD COLUMN volunteer_location TEXT"),
                ("accepted_at", "ALTER TABLE help_requests ADD COLUMN accepted_at TEXT"),
                ("priority", "ALTER TABLE help_requests ADD COLUMN priority TEXT NOT NULL DEFAULT 'normal'"),
                ("request_latitude", "ALTER TABLE help_requests ADD COLUMN request_latitude REAL"),
                ("request_longitude", "ALTER TABLE help_requests ADD COLUMN request_longitude REAL"),
                ("volunteer_latitude", "ALTER TABLE help_requests ADD COLUMN volunteer_latitude REAL"),
                ("volunteer_longitude", "ALTER TABLE help_requests ADD COLUMN volunteer_longitude REAL"),
                ("helper_latitude", "ALTER TABLE help_requests ADD COLUMN helper_latitude REAL"),
                ("helper_longitude", "ALTER TABLE help_requests ADD COLUMN helper_longitude REAL"),
                ("journey_started_at", "ALTER TABLE help_requests ADD COLUMN journey_started_at TEXT"),
                ("reached_at", "ALTER TABLE help_requests ADD COLUMN reached_at TEXT"),
                ("completed_at", "ALTER TABLE help_requests ADD COLUMN completed_at TEXT"),
                ("last_location_update", "ALTER TABLE help_requests ADD COLUMN last_location_update TEXT"),
                ("completion_code_hash", "ALTER TABLE help_requests ADD COLUMN completion_code_hash TEXT"),
                ("completion_code_expires_at", "ALTER TABLE help_requests ADD COLUMN completion_code_expires_at TEXT"),
                ("completion_code_attempts", "ALTER TABLE help_requests ADD COLUMN completion_code_attempts INTEGER DEFAULT 0"),
                ("completion_code_used_at", "ALTER TABLE help_requests ADD COLUMN completion_code_used_at TEXT"),
                ("completion_code_sent_at", "ALTER TABLE help_requests ADD COLUMN completion_code_sent_at TEXT"),
            ]
            for col, sql in migrations:
                if col not in help_cols:
                    cur.execute(sql)
                    print(f"🔧 Migrated: added {col} to help_requests table.")
            cur.execute("UPDATE help_requests SET priority = 'normal' WHERE priority IS NULL OR priority NOT IN ('emergency', 'urgent', 'normal')")

            contact_cols = [r[1] for r in cur.execute("PRAGMA table_info(contact_messages)").fetchall()]
            if 'status' not in contact_cols:
                cur.execute("ALTER TABLE contact_messages ADD COLUMN status TEXT DEFAULT 'pending'")
                print("🔧 Migrated: added status column to contact_messages table.")
            if 'subject' not in contact_cols:
                cur.execute("ALTER TABLE contact_messages ADD COLUMN subject TEXT")
                print("🔧 Migrated: added subject column to contact_messages table.")
            if 'user_id' not in contact_cols:
                cur.execute("ALTER TABLE contact_messages ADD COLUMN user_id INTEGER REFERENCES users(id)")
                print("🔧 Migrated: added user_id column to contact_messages table.")
            if 'updated_at' not in contact_cols:
                cur.execute("ALTER TABLE contact_messages ADD COLUMN updated_at TEXT DEFAULT (datetime('now', 'localtime'))")
                print("🔧 Migrated: added updated_at column to contact_messages table.")

            notification_cols = [r[1] for r in cur.execute("PRAGMA table_info(notifications)").fetchall()]
            if not notification_cols:
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS notifications (
                        id                  INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id             INTEGER NOT NULL REFERENCES users(id),
                        message             TEXT NOT NULL,
                        notification_type   TEXT,
                        related_request_id  INTEGER,
                        is_read             INTEGER DEFAULT 0,
                        created_at          TEXT DEFAULT (datetime('now', 'localtime'))
                    )
                """)
                print("🔧 Migrated: created notifications table.")

            vol_cols = [r[1] for r in cur.execute("PRAGMA table_info(volunteers)").fetchall()]
            if 'user_id' not in vol_cols:
                cur.execute("ALTER TABLE volunteers ADD COLUMN user_id INTEGER REFERENCES users(id)")
                print("🔧 Migrated: added user_id to volunteers table.")
            if 'phone_verified' not in vol_cols:
                cur.execute("ALTER TABLE volunteers ADD COLUMN phone_verified BOOLEAN DEFAULT 0")
                print("🔧 Migrated: added phone_verified column to volunteers table.")
            if 'location_latitude' not in vol_cols:
                cur.execute("ALTER TABLE volunteers ADD COLUMN location_latitude REAL")
                print("🔧 Migrated: added location_latitude column to volunteers table.")
            if 'location_longitude' not in vol_cols:
                cur.execute("ALTER TABLE volunteers ADD COLUMN location_longitude REAL")
                print("🔧 Migrated: added location_longitude column to volunteers table.")

            # Repair missing volunteers in a single transaction
            
            import traceback

            try:
                created = self.repair_missing_volunteers(conn=conn)
                if created:
                    print(f"Created {len(created)} volunteers")
            except Exception as e:
                print("repair_missing_volunteers failed")
                traceback.print_exc()

            self.ensure_default_admin(conn=conn)
            print("✅ Database initialized.")

    # ---------------- User / Auth ----------------
    def register_user(self, username, email, password, role="user"):
        """Register a new user. Returns user_id if successful, False if user exists."""
        try:
            with self.connect() as conn:
                password_hash = generate_password_hash(password)
                cursor = conn.cursor()
                cursor.execute(
                    "INSERT INTO users (username, email, password_hash, role) VALUES (?, ?, ?, ?)",
                    (username, email, password_hash, role),
                )
                return cursor.lastrowid
        except sqlite3.IntegrityError:
            return False

    # ---------------- Pending registrations ----------------
    def create_pending_registration(self, username, email, password_hash, role='user', phone=None, helper_location=None, helper_skills=None, helper_availability=None, helper_about=None, email_token=None):
        with self.connect() as conn:
            cur = conn.cursor()
            cur.execute(
                "INSERT INTO pending_registrations (username, email, password_hash, role, phone, helper_location, helper_skills, helper_availability, helper_about, email_token, email_token_sent_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now','localtime'))",
                (username, email, password_hash, role, phone, helper_location or '', helper_skills or '', helper_availability or '', helper_about or '', email_token)
            )
            return cur.lastrowid

    def update_pending_registration(self, pending_id, username, password_hash, role='user', phone=None, helper_location=None, helper_skills=None, helper_availability=None, helper_about=None):
        with self.connect() as conn:
            conn.execute(
                """UPDATE pending_registrations
                   SET username = ?, password_hash = ?, role = ?, phone = ?,
                       helper_location = ?, helper_skills = ?, helper_availability = ?, helper_about = ?
                   WHERE id = ?""",
                (username, password_hash, role, phone, helper_location or '', helper_skills or '', helper_availability or '', helper_about or '', pending_id),
            )

    def get_pending_by_id(self, pending_id):
        with self.connect() as conn:
            row = conn.execute("SELECT * FROM pending_registrations WHERE id = ?", (pending_id,)).fetchone()
        return dict(row) if row else None

    def get_pending_by_email(self, email):
        with self.connect() as conn:
            row = conn.execute("SELECT * FROM pending_registrations WHERE LOWER(TRIM(email)) = LOWER(TRIM(?)) ORDER BY id DESC LIMIT 1", (email,)).fetchone()
        return dict(row) if row else None

    def mark_pending_email_verified(self, pending_id):
        with self.connect() as conn:
            conn.execute("UPDATE pending_registrations SET email_verified = 1 WHERE id = ?", (pending_id,))

    def consume_pending_email_token(self, pending_id, token):
        with self.connect() as conn:
            pending = conn.execute(
                "SELECT email_verified, email_token FROM pending_registrations WHERE id = ?",
                (pending_id,),
            ).fetchone()
            if not pending:
                return 'not_found'
            if pending['email_verified']:
                return 'already_verified'
            if not pending['email_token'] or pending['email_token'] != token:
                return 'invalid'
            conn.execute(
                "UPDATE pending_registrations SET email_verified = 1, email_token = NULL WHERE id = ?",
                (pending_id,),
            )
            return 'verified'

    def set_pending_phone(self, pending_id, phone, sent_at=None):
        with self.connect() as conn:
            conn.execute("UPDATE pending_registrations SET phone = ?, phone_verified = 0, phone_otp_sent_at = COALESCE(?, datetime('now','localtime')) WHERE id = ?", (phone, sent_at, pending_id))

    def mark_pending_phone_verified(self, pending_id):
        with self.connect() as conn:
            conn.execute("UPDATE pending_registrations SET phone_verified = 1, phone_otp_sent_at = NULL, phone_otp_attempts = 0 WHERE id = ?", (pending_id,))

    def increment_pending_phone_otp_attempts(self, pending_id):
        with self.connect() as conn:
            conn.execute("UPDATE pending_registrations SET phone_otp_attempts = COALESCE(phone_otp_attempts,0) + 1 WHERE id = ?", (pending_id,))

    def delete_pending(self, pending_id):
        with self.connect() as conn:
            conn.execute("DELETE FROM pending_registrations WHERE id = ?", (pending_id,))

    def finalize_pending_registration(self, pending_id):
        """Create final user (and volunteer if helper) from pending registration. Returns new user_id or raises Exception."""
        with self.connect() as conn:
            cur = conn.cursor()
            pending = cur.execute("SELECT * FROM pending_registrations WHERE id = ?", (pending_id,)).fetchone()
            if not pending:
                raise ValueError('pending not found')
            # check expiry: 48 hours
            created_at = pending['created_at']
            try:
                from datetime import datetime as _dt
                if _dt.fromisoformat(created_at) < _dt.now() - timedelta(days=2):
                    raise ValueError('pending expired')
            except Exception:
                pass

            email = pending['email']
            phone = pending['phone']
            # Email verification is required; phone verification is optional.
            if not pending['email_verified']:
                raise ValueError('email not verified')

            # Prevent duplicates
            exists = cur.execute("SELECT id FROM users WHERE LOWER(TRIM(email)) = LOWER(TRIM(?))", (email,)).fetchone()
            if exists:
                raise ValueError('email already exists')
            if phone:
                exists2 = cur.execute("SELECT id FROM users WHERE phone = ?", (phone,)).fetchone()
                if exists2:
                    raise ValueError('phone already exists')

            # Insert user
            cur.execute("INSERT INTO users (username, email, password_hash, role, created_at, updated_at) VALUES (?, ?, ?, ?, datetime('now','localtime'), datetime('now','localtime'))",
                        (pending['username'], pending['email'], pending['password_hash'], pending['role']))
            user_id = cur.lastrowid

            # If helper, create volunteer row using stored helper_* fields
            if pending['role'] == 'helper':
                cur.execute("INSERT INTO volunteers (user_id, name, phone, email, location, skills, availability, about, is_active, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 1, datetime('now','localtime'))",
                            (user_id, pending['username'], pending['phone'] or '', pending['email'], pending['helper_location'] or '', pending['helper_skills'] or '', pending['helper_availability'] or '', pending['helper_about'] or ''))

            # Cleanup pending row
            cur.execute("DELETE FROM pending_registrations WHERE id = ?", (pending_id,))
            return user_id

    def ensure_default_admin(self, conn=None):
        """Ensure the Help R Circle default admin account exists and is correctly configured."""
        target_email = "helprcircle.support@gmail.com"
        target_password = "admin@123"
        target_username = "Help R Circle Admin"
        desired_password_hash = generate_password_hash(target_password)

        def _ensure(cur):
            admin_user = cur.execute(
                "SELECT id, username, email, role, password_hash FROM users WHERE role = 'admin' LIMIT 1"
            ).fetchone()

            if admin_user:
                is_already_configured = (
                    admin_user["username"] == target_username
                    and admin_user["email"] == target_email
                    and admin_user["role"] == "admin"
                )
                if is_already_configured:
                    print("ℹ️ Default admin already configured.")
                    return

                email_in_use = cur.execute(
                    "SELECT id FROM users WHERE email = ? AND id != ?",
                    (target_email, admin_user["id"]),
                ).fetchone()
                if email_in_use:
                    cur.execute(
                        "UPDATE users SET role = 'admin', password_hash = ?, username = ?, email = ? WHERE id = ?",
                        (desired_password_hash, target_username, target_email, email_in_use["id"]),
                    )
                    print("✅ Existing admin updated.")
                    return

                cur.execute(
                    "UPDATE users SET username = ?, email = ?, password_hash = ?, role = 'admin' WHERE id = ?",
                    (target_username, target_email, desired_password_hash, admin_user["id"]),
                )
                print("✅ Existing admin updated.")
                return

            same_email_user = cur.execute(
                "SELECT id, username, role FROM users WHERE email = ? LIMIT 1",
                (target_email,),
            ).fetchone()
            if same_email_user:
                cur.execute(
                    "UPDATE users SET username = ?, password_hash = ?, role = 'admin' WHERE id = ?",
                    (target_username, desired_password_hash, same_email_user["id"]),
                )
                print("✅ Existing admin updated.")
                return

            cur.execute(
                "INSERT INTO users (username, email, password_hash, role) VALUES (?, ?, ?, ?)",
                (target_username, target_email, desired_password_hash, "admin"),
            )
            print("✅ Default admin created.")

        if conn is None:
            with self.connect() as conn:
                cur = conn.cursor()
                _ensure(cur)
        else:
            cur = conn.cursor()
            _ensure(cur)

    def register_admin(self, username, email, password):
        return self.register_user(username, email, password, role="admin")

    def login_user(self, email, password):
        with self.connect() as conn:
            user = conn.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
        if user and check_password_hash(user['password_hash'], password):
            return dict(user)
        return None

    def get_user_by_email(self, email):
        with self.connect() as conn:
            user = conn.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
        return dict(user) if user else None

    def get_user_by_id(self, user_id):
        with self.connect() as conn:
            user = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
        return dict(user) if user else None

    def update_user_password(self, user_id, password):
        """Replace one user's password hash and return whether it was updated."""
        password_hash = generate_password_hash(password)
        with self.connect() as conn:
            cursor = conn.execute(
                "UPDATE users SET password_hash = ?, updated_at = datetime('now', 'localtime') WHERE id = ?",
                (password_hash, user_id),
            )
            return cursor.rowcount > 0

    def store_verification_token(self, user_id, token):
        with self.connect() as conn:
            conn.execute("UPDATE users SET verification_token = ? WHERE id = ?", (token, user_id))

    def mark_email_as_verified(self, user_id):
        with self.connect() as conn:
            conn.execute("UPDATE users SET is_verified = 1, verification_token = NULL WHERE id = ?", (user_id,))

    def store_otp(self, user_id, otp_code, otp_expiry):
        with self.connect() as conn:
            conn.execute("UPDATE users SET otp_code = ?, otp_expiry = ? WHERE id = ?", (otp_code, otp_expiry, user_id))

    def verify_otp(self, user_id, otp_code):
        from datetime import datetime as _dt
        with self.connect() as conn:
            user = conn.execute("SELECT otp_code, otp_expiry FROM users WHERE id = ?", (user_id,)).fetchone()
        if not user:
            return False
        if user['otp_code'] != otp_code:
            return False
        if not user['otp_expiry']:
            return False
        expiry_time = _dt.fromisoformat(user['otp_expiry'])
        if datetime.now() > expiry_time:
            return False
        return True

    def clear_otp(self, user_id):
        with self.connect() as conn:
            conn.execute("UPDATE users SET otp_code = NULL, otp_expiry = NULL WHERE id = ?", (user_id,))

    # ---------------- Phone helpers ----------------
    def get_user_by_phone(self, phone):
        with self.connect() as conn:
            row = conn.execute("SELECT * FROM users WHERE phone = ?", (phone,)).fetchone()
        return dict(row) if row else None

    def get_user_by_otp(self, otp_code):
        with self.connect() as conn:
            user = conn.execute("SELECT * FROM users WHERE otp_code = ?", (otp_code,)).fetchone()
        return dict(user) if user else None

    # ---------------- Help requests ----------------
    def add_help_request(self, name, phone, location, help_type, description, user_id=None, request_latitude=None, request_longitude=None, priority="normal"):
        existing = self.find_duplicate_help_request(name, phone, location, help_type)
        if existing:
            return existing
        with self.connect() as conn:
            cur = conn.cursor()
            if user_id:
                cur.execute(
                    """
                    INSERT INTO help_requests (name, phone, location, help_type, description, priority, status, user_id, request_latitude, request_longitude)
                    VALUES (?, ?, ?, ?, ?, ?, 'submitted', ?, ?, ?)
                    """,
                    (name, phone, location, help_type, description, priority, user_id, request_latitude, request_longitude),
                )
            else:
                cur.execute(
                    """
                    INSERT INTO help_requests (name, phone, location, help_type, description, priority, status, request_latitude, request_longitude)
                    VALUES (?, ?, ?, ?, ?, ?, 'submitted', ?, ?)
                    """,
                    (name, phone, location, help_type, description, priority, request_latitude, request_longitude),
                )
            return cur.lastrowid

    def get_requests_by_user(self, user_id):
        with self.connect() as conn:
            rows = conn.execute("SELECT * FROM help_requests WHERE user_id = ? ORDER BY datetime(created_at) DESC", (user_id,)).fetchall()
        return rows

    def get_completed_requests_by_volunteer(self, volunteer_id):
        with self.connect() as conn:
            rows = conn.execute("SELECT * FROM help_requests WHERE volunteer_id = ? AND status = 'completed' ORDER BY datetime(completed_at) DESC", (volunteer_id,)).fetchall()
        return rows

    def get_requests(self, status="all", help_type="all", search="", priority="all"):
        query = "SELECT * FROM help_requests WHERE 1=1"
        params = []
        if status != "all":
            if status == 'pending':
                query += " AND status IN ('pending', 'submitted')"
            else:
                query += " AND status = ?"
                params.append(status)
        if help_type != "all":
            query += " AND help_type = ?"
            params.append(help_type)
        if search:
            query += " AND (name LIKE ? OR location LIKE ? OR description LIKE ?)"
            like = f"%{search}%"
            params.extend([like, like, like])
        if priority in ('emergency', 'urgent', 'normal'):
            query += " AND COALESCE(priority, 'normal') = ?"
            params.append(priority)
        query += " ORDER BY CASE COALESCE(priority, 'normal') WHEN 'emergency' THEN 1 WHEN 'urgent' THEN 2 ELSE 3 END, created_at DESC"
        with self.connect() as conn:
            rows = conn.execute(query, params).fetchall()
        return rows

    def get_request_by_id(self, req_id):
        with self.connect() as conn:
            row = conn.execute("SELECT * FROM help_requests WHERE id = ?", (req_id,)).fetchone()
        return row

    def save_helper_location(self, helper_id, request_id, latitude, longitude):
        with self.connect() as conn:
            conn.execute("INSERT INTO helper_locations (helper_id, request_id, latitude, longitude, updated_at) VALUES (?, ?, ?, ?, datetime('now','localtime'))", (helper_id, request_id, latitude, longitude))

    def update_helper_coordinates(self, request_id, latitude, longitude, updated_at):
        """Store live helper coordinates without changing the request status."""
        with self.connect() as conn:
            conn.execute(
                """
                UPDATE help_requests
                SET helper_latitude = ?, helper_longitude = ?,
                    volunteer_latitude = ?, volunteer_longitude = ?,
                    last_location_update = ?, updated_at = datetime('now','localtime')
                WHERE id = ?
                """,
                (latitude, longitude, latitude, longitude, updated_at, request_id),
            )

    def get_latest_helper_location(self, request_id, helper_id):
        with self.connect() as conn:
            row = conn.execute("SELECT * FROM helper_locations WHERE request_id = ? AND helper_id = ? ORDER BY updated_at DESC, id DESC LIMIT 1", (request_id, helper_id)).fetchone()
        return dict(row) if row else None

    def start_journey_if_accepted(self, req_id, helper_id, latitude, longitude, started_at):
        with self.connect() as conn:
            cursor = conn.execute(
                """
                UPDATE help_requests
                SET status = 'helper_on_way', journey_started_at = ?,
                    helper_latitude = ?, helper_longitude = ?,
                    volunteer_latitude = ?, volunteer_longitude = ?,
                    last_location_update = ?, updated_at = datetime('now','localtime')
                WHERE id = ? AND volunteer_id = ?
                  AND status IN ('accepted', 'helper_assigned')
                """,
                (started_at, latitude, longitude, latitude, longitude, started_at, req_id, helper_id),
            )
            return cursor.rowcount == 1

    def complete_request_if_arrived(self, req_id, helper_id, completed_at):
        with self.connect() as conn:
            cursor = conn.execute(
                """
                UPDATE help_requests
                SET status = 'completed', completed_at = ?, updated_at = datetime('now','localtime')
                WHERE id = ? AND volunteer_id = ?
                  AND status IN ('helper_reached_location', 'arrived')
                """,
                (completed_at, req_id, helper_id),
            )
            return cursor.rowcount == 1

    def save_completion_code(self, req_id, helper_id, code_hash, expires_at, sent_at):
        with self.connect() as conn:
            cursor = conn.execute(
                """
                UPDATE help_requests
                SET completion_code_hash = ?, completion_code_expires_at = ?,
                    completion_code_attempts = 0, completion_code_used_at = NULL,
                    completion_code_sent_at = ?, updated_at = datetime('now','localtime')
                WHERE id = ? AND volunteer_id = ?
                  AND status IN ('helper_reached_location', 'arrived')
                """,
                (code_hash, expires_at, sent_at, req_id, helper_id),
            )
            return cursor.rowcount == 1

    def increment_completion_code_attempts(self, req_id, max_attempts):
        with self.connect() as conn:
            cursor = conn.execute(
                """
                UPDATE help_requests
                SET completion_code_attempts = completion_code_attempts + 1
                WHERE id = ? AND completion_code_used_at IS NULL
                  AND completion_code_attempts < ?
                """,
                (req_id, max_attempts),
            )
            return cursor.rowcount == 1

    def complete_request_with_code(self, req_id, helper_id, code_hash, completed_at, used_at):
        with self.connect() as conn:
            cursor = conn.execute(
                """
                UPDATE help_requests
                SET status = 'completed', completed_at = ?, completion_code_used_at = ?,
                    updated_at = datetime('now','localtime')
                WHERE id = ? AND volunteer_id = ?
                  AND status IN ('helper_reached_location', 'arrived')
                  AND completion_code_hash = ? AND completion_code_used_at IS NULL
                """,
                (completed_at, used_at, req_id, helper_id, code_hash),
            )
            return cursor.rowcount == 1

    # ---------------- Volunteers ----------------
    def get_volunteer_by_name(self, name):
        with self.connect() as conn:
            row = conn.execute("SELECT * FROM volunteers WHERE name = ?", (name,)).fetchone()
        return row

    def get_volunteer_by_email(self, email):
        with self.connect() as conn:
            row = conn.execute("SELECT * FROM volunteers WHERE email = ?", (email,)).fetchone()
        return row

    def update_request_status(self, req_id, new_status, volunteer_name=None, volunteer_id=None, volunteer_email=None, volunteer_phone=None, volunteer_location=None, accepted_at=None, journey_started_at=None, reached_at=None, completed_at=None, volunteer_latitude=None, volunteer_longitude=None, helper_latitude=None, helper_longitude=None, last_location_update=None, helper_name=None, helper_id=None, helper_email=None, helper_phone=None, helper_location=None):
        effective_name = volunteer_name or helper_name
        effective_id = volunteer_id if volunteer_id is not None else helper_id
        effective_email = volunteer_email or helper_email
        effective_phone = volunteer_phone or helper_phone
        effective_location = volunteer_location or helper_location

        with self.connect() as conn:
            if new_status in ('volunteer_assigned', 'helper_assigned', 'accepted') and effective_name:
                conn.execute(
                    """
                    UPDATE help_requests
                    SET status = ?, volunteer_name = ?, volunteer_id = ?, volunteer_email = ?, volunteer_phone = ?, volunteer_location = ?, accepted_at = COALESCE(?, datetime('now','localtime')), updated_at = datetime('now','localtime')
                    WHERE id = ?
                    """,
                    (new_status, effective_name, effective_id, effective_email, effective_phone, effective_location, accepted_at, req_id),
                )
            elif effective_name:
                conn.execute("UPDATE help_requests SET status = ?, volunteer_name = ?, updated_at = datetime('now','localtime') WHERE id = ?", (new_status, effective_name, req_id))
            else:
                conn.execute("UPDATE help_requests SET status = ?, updated_at = datetime('now','localtime') WHERE id = ?", (new_status, req_id))

            if journey_started_at is not None:
                conn.execute("UPDATE help_requests SET journey_started_at = ? WHERE id = ?", (journey_started_at, req_id))
            if reached_at is not None:
                conn.execute("UPDATE help_requests SET reached_at = ? WHERE id = ?", (reached_at, req_id))
            if completed_at is not None:
                conn.execute("UPDATE help_requests SET completed_at = ? WHERE id = ?", (completed_at, req_id))
            if volunteer_latitude is not None:
                conn.execute("UPDATE help_requests SET volunteer_latitude = ? WHERE id = ?", (volunteer_latitude, req_id))
                conn.execute("UPDATE help_requests SET helper_latitude = ? WHERE id = ?", (volunteer_latitude, req_id))
            if volunteer_longitude is not None:
                conn.execute("UPDATE help_requests SET volunteer_longitude = ? WHERE id = ?", (volunteer_longitude, req_id))
                conn.execute("UPDATE help_requests SET helper_longitude = ? WHERE id = ?", (volunteer_longitude, req_id))
            if helper_latitude is not None:
                conn.execute("UPDATE help_requests SET volunteer_latitude = ?, helper_latitude = ? WHERE id = ?", (helper_latitude, helper_latitude, req_id))
            if helper_longitude is not None:
                conn.execute("UPDATE help_requests SET volunteer_longitude = ?, helper_longitude = ? WHERE id = ?", (helper_longitude, helper_longitude, req_id))
            if last_location_update is not None:
                conn.execute("UPDATE help_requests SET last_location_update = ? WHERE id = ?", (last_location_update, req_id))

    def add_volunteer(self, name, phone, email, location, skills, availability, about="", user_id=None):
        existing = self.find_duplicate_volunteer(name, phone, email)
        if existing:
            return existing
        with self.connect() as conn:
            cur = conn.cursor()
            cur.execute("INSERT INTO volunteers (user_id, name, phone, email, location, skills, availability, about) VALUES (?, ?, ?, ?, ?, ?, ?, ?)", (user_id, name, phone, email, location, skills, availability, about))
            return cur.lastrowid

    def get_volunteers(self):
        with self.connect() as conn:
            rows = conn.execute("SELECT * FROM volunteers WHERE is_active=1 ORDER BY created_at DESC").fetchall()
        return rows

    # ---------------- Contacts ----------------
    def add_contact_message(self, name, email, message, subject="", user_id=None):
        with self.connect() as conn:
            conn.execute(
                "INSERT INTO contact_messages (name, email, subject, message, user_id) VALUES (?, ?, ?, ?, ?)",
                (name, email, subject, message, user_id),
            )

    def get_all_contact_messages(self, search=""):
        with self.connect() as conn:
            query = "SELECT * FROM contact_messages WHERE 1=1"
            params = []
            if search:
                query += " AND (name LIKE ? OR email LIKE ? OR subject LIKE ? OR message LIKE ?)"
                like = f"%{search}%"
                params.extend([like, like, like, like])
            query += " ORDER BY created_at DESC"
            rows = conn.execute(query, params).fetchall()
        return rows

    def get_contact_message_by_id(self, msg_id):
        with self.connect() as conn:
            row = conn.execute("SELECT * FROM contact_messages WHERE id = ?", (msg_id,)).fetchone()
        return row

    def update_contact_message_status(self, msg_id, status):
        with self.connect() as conn:
            conn.execute("UPDATE contact_messages SET status = ?, updated_at = datetime('now', 'localtime') WHERE id = ?", (status, msg_id))

    def add_notification(self, user_id, message, notification_type=None, related_request_id=None):
        with self.connect() as conn:
            cur = conn.cursor()
            cur.execute(
                "INSERT INTO notifications (user_id, message, notification_type, related_request_id, is_read) VALUES (?, ?, ?, ?, 0)",
                (user_id, message, notification_type, related_request_id),
            )
            return cur.lastrowid

    def get_notifications_for_user(self, user_id, unread_only=False, limit=20):
        with self.connect() as conn:
            query = "SELECT * FROM notifications WHERE user_id = ?"
            params = [user_id]
            if unread_only:
                query += " AND is_read = 0"
            query += " ORDER BY created_at DESC, id DESC LIMIT ?"
            params.append(int(limit))
            rows = conn.execute(query, params).fetchall()
        return rows

    def get_unread_notification_count(self, user_id):
        with self.connect() as conn:
            row = conn.execute("SELECT COUNT(*) AS count FROM notifications WHERE user_id = ? AND is_read = 0", (user_id,)).fetchone()
        return int(row['count']) if row else 0

    def mark_notification_read(self, notification_id, user_id):
        with self.connect() as conn:
            cur = conn.cursor()
            cur.execute("UPDATE notifications SET is_read = 1 WHERE id = ? AND user_id = ?", (notification_id, user_id))
            return cur.rowcount > 0

    def mark_all_notifications_read(self, user_id):
        with self.connect() as conn:
            cur = conn.cursor()
            cur.execute("UPDATE notifications SET is_read = 1 WHERE user_id = ?", (user_id,))
            return cur.rowcount > 0

    def has_recent_notification(self, user_id, message, related_request_id=None, window_seconds=86400):
        with self.connect() as conn:
            if related_request_id is not None:
                row = conn.execute(
                    "SELECT id FROM notifications WHERE user_id = ? AND related_request_id = ? AND message = ? AND datetime(created_at) >= datetime('now', 'localtime', '-' || ? || ' seconds') ORDER BY created_at DESC LIMIT 1",
                    (user_id, related_request_id, message, str(window_seconds)),
                ).fetchone()
            else:
                row = conn.execute(
                    "SELECT id FROM notifications WHERE user_id = ? AND message = ? AND datetime(created_at) >= datetime('now', 'localtime', '-' || ? || ' seconds') ORDER BY created_at DESC LIMIT 1",
                    (user_id, message, str(window_seconds)),
                ).fetchone()
        return bool(row)

    def delete_contact_message(self, msg_id):
        with self.connect() as conn:
            cur = conn.cursor()
            cur.execute("DELETE FROM contact_messages WHERE id = ?", (msg_id,))
            return cur.rowcount > 0

    def get_contact_messages_stats(self):
        with self.connect() as conn:
            cur = conn.cursor()
            total = cur.execute("SELECT COUNT(*) FROM contact_messages").fetchone()[0]
            pending = cur.execute("SELECT COUNT(*) FROM contact_messages WHERE status = 'pending'").fetchone()[0]
            resolved = cur.execute("SELECT COUNT(*) FROM contact_messages WHERE status = 'resolved'").fetchone()[0]
        return {"total": total, "pending": pending, "resolved": resolved}

    # ---------------- Stats / Admin ----------------
    def get_stats(self):
        with self.connect() as conn:
            cur = conn.cursor()
            total_requests = cur.execute("SELECT COUNT(*) FROM help_requests").fetchone()[0]
            pending = cur.execute("SELECT COUNT(*) FROM help_requests WHERE status IN ('pending', 'submitted')").fetchone()[0]
            accepted = cur.execute("SELECT COUNT(*) FROM help_requests WHERE status IN ('volunteer_assigned','volunteer_on_way','volunteer_near_location','volunteer_reached_location','accepted')").fetchone()[0]
            completed = cur.execute("SELECT COUNT(*) FROM help_requests WHERE status='completed'").fetchone()[0]
            total_volunteers = cur.execute("SELECT COUNT(*) FROM volunteers WHERE is_active=1").fetchone()[0]
        return {"total_requests": total_requests, "pending": pending, "accepted": accepted, "completed": completed, "total_volunteers": total_volunteers}

    def get_admin_dashboard_stats(self):
        with self.connect() as conn:
            cur = conn.cursor()
            total_users = cur.execute("SELECT COUNT(*) FROM users WHERE role = 'user'").fetchone()[0]
            total_admins = cur.execute("SELECT COUNT(*) FROM users WHERE role = 'admin'").fetchone()[0]
            total_helpers = cur.execute("SELECT COUNT(*) FROM users WHERE role IN ('helper', 'volunteer')").fetchone()[0]
            total_requests = cur.execute("SELECT COUNT(*) FROM help_requests").fetchone()[0]
            pending_requests = cur.execute("SELECT COUNT(*) FROM help_requests WHERE status IN ('pending', 'submitted')").fetchone()[0]
            accepted_requests = cur.execute("SELECT COUNT(*) FROM help_requests WHERE status IN ('volunteer_assigned','volunteer_on_way','volunteer_near_location','volunteer_reached_location','accepted')").fetchone()[0]
            completed_requests = cur.execute("SELECT COUNT(*) FROM help_requests WHERE status = 'completed'").fetchone()[0]
            total_volunteers = cur.execute("SELECT COUNT(*) FROM volunteers WHERE is_active=1").fetchone()[0]
        return {"total_users": total_users, "total_admins": total_admins, "total_helpers": total_helpers, "total_requests": total_requests, "pending_requests": pending_requests, "accepted_requests": accepted_requests, "completed_requests": completed_requests, "total_volunteers": total_volunteers}

    def get_admin_location_map_data(self):
        """Return privacy-safe user, helper, and active-request map data."""
        active_statuses = ('submitted', 'pending', 'accepted', 'helper_assigned', 'helper_on_way', 'helper_near_location', 'helper_reached_location', 'arrived')
        placeholders = ','.join('?' for _ in active_statuses)
        with self.connect() as conn:
            user_rows = conn.execute(
                """
                SELECT id, username, phone, location, location_latitude, location_longitude
                FROM users
                WHERE role = 'user'
                  AND location_latitude IS NOT NULL AND location_longitude IS NOT NULL
                  AND location_latitude BETWEEN -90 AND 90
                  AND location_longitude BETWEEN -180 AND 180
                ORDER BY id
                """
            ).fetchall()
            request_user_rows = conn.execute(
                """
                SELECT id, name, phone, location, help_type, status,
                       request_latitude, request_longitude, volunteer_name
                FROM help_requests
                WHERE request_latitude IS NOT NULL AND request_longitude IS NOT NULL
                ORDER BY datetime(created_at) DESC
                """
            ).fetchall()
            helper_rows = conn.execute(
                """
                SELECT v.id, v.name, v.phone, v.location, v.availability,
                       v.location_latitude, v.location_longitude,
                       hl.latitude AS current_latitude, hl.longitude AS current_longitude,
                       hl.updated_at AS current_updated_at
                FROM volunteers v
                LEFT JOIN users u ON u.id = v.user_id
                LEFT JOIN helper_locations hl ON hl.id = (
                    SELECT latest.id FROM helper_locations latest
                    WHERE latest.helper_id = v.id
                    ORDER BY latest.updated_at DESC, latest.id DESC LIMIT 1
                )
                WHERE v.is_active = 1
                ORDER BY v.id
                """
            ).fetchall()
            request_rows = conn.execute(
                f"""
                SELECT hr.id, hr.name, hr.phone, hr.location, hr.help_type, hr.status,
                       hr.request_latitude, hr.request_longitude, hr.volunteer_id,
                       hr.volunteer_name, hr.helper_latitude, hr.helper_longitude,
                       hr.last_location_update,
                       hl.latitude AS latest_helper_latitude,
                       hl.longitude AS latest_helper_longitude,
                       hl.updated_at AS latest_helper_updated_at
                FROM help_requests hr
                LEFT JOIN helper_locations hl ON hl.id = (
                    SELECT latest.id FROM helper_locations latest
                    WHERE latest.request_id = hr.id
                    ORDER BY latest.updated_at DESC, latest.id DESC LIMIT 1
                )
                WHERE hr.status IN ({placeholders})
                ORDER BY datetime(hr.updated_at) DESC
                """,
                active_statuses,
            ).fetchall()

        def point(latitude, longitude):
            if latitude is None or longitude is None:
                return None
            try:
                latitude = float(latitude)
                longitude = float(longitude)
            except (TypeError, ValueError):
                return None
            if not (-90 <= latitude <= 90 and -180 <= longitude <= 180):
                return None
            return [latitude, longitude]

        users = []
        for row in user_rows:
            users.append({
                "id": row["id"], "name": row["username"], "phone": row["phone"],
                "address": row["location"], "point": point(row["location_latitude"], row["location_longitude"]),
                "source": "registered profile",
            })
        for row in request_user_rows:
            request_point = point(row["request_latitude"], row["request_longitude"])
            if request_point:
                users.append({
                    "id": row["id"], "name": row["name"], "phone": row["phone"],
                    "address": row["location"], "point": request_point,
                    "source": "request location", "request_id": row["id"],
                    "help_type": row["help_type"], "status": row["status"],
                    "assigned_helper": row["volunteer_name"],
                })

        helpers = []
        for row in helper_rows:
            current_point = point(row["current_latitude"], row["current_longitude"])
            profile_point = point(row["location_latitude"], row["location_longitude"])
            helpers.append({
                "id": row["id"], "name": row["name"], "phone": row["phone"],
                "address": row["location"], "availability": row["availability"],
                "point": current_point or profile_point,
                "location_source": "shared GPS" if current_point else "registered profile",
                "updated_at": row["current_updated_at"],
            })

        requests = []
        for row in request_rows:
            request_point = point(row["request_latitude"], row["request_longitude"])
            helper_point = point(row["latest_helper_latitude"], row["latest_helper_longitude"])
            if helper_point is None:
                helper_point = point(row["helper_latitude"], row["helper_longitude"])
            requests.append({
                "id": row["id"], "user_name": row["name"], "user_phone": row["phone"],
                "address": row["location"], "help_type": row["help_type"], "status": row["status"],
                "request_point": request_point, "helper_id": row["volunteer_id"],
                "helper_name": row["volunteer_name"], "helper_point": helper_point,
                "helper_updated_at": row["latest_helper_updated_at"] or row["last_location_update"],
            })
        return {"users": users, "helpers": helpers, "requests": requests}

    def get_admin_request_details(self, request_id):
        with self.connect() as conn:
            row = conn.execute(
                """
                SELECT hr.*, u.email AS requester_email,
                       v.id AS assigned_helper_id, v.name AS assigned_helper_name,
                       v.email AS assigned_helper_email, v.phone AS assigned_helper_phone,
                       v.location AS assigned_helper_location, v.availability AS assigned_helper_availability,
                       v.skills AS assigned_helper_skills,
                       hl.latitude AS latest_helper_latitude,
                       hl.longitude AS latest_helper_longitude,
                       hl.updated_at AS latest_helper_updated_at
                FROM help_requests hr
                LEFT JOIN users u ON u.id = hr.user_id
                LEFT JOIN volunteers v ON v.id = hr.volunteer_id
                LEFT JOIN helper_locations hl ON hl.id = (
                    SELECT latest.id FROM helper_locations latest
                    WHERE latest.request_id = hr.id AND latest.helper_id = hr.volunteer_id
                    ORDER BY latest.updated_at DESC, latest.id DESC LIMIT 1
                )
                WHERE hr.id = ?
                """,
                (request_id,),
            ).fetchone()
        return row

    def get_all_users(self, search=""):
        with self.connect() as conn:
            query = """
                SELECT u.*,
                       COUNT(hr.id) AS request_count
                FROM users u
                LEFT JOIN help_requests hr ON hr.user_id = u.id
                WHERE u.role = 'user'
            """
            params = []
            if search:
                query += " AND (u.username LIKE ? OR u.email LIKE ? OR u.phone LIKE ? OR u.location LIKE ?)"
                like = f"%{search}%"
                params.extend([like, like, like, like])
            query += " GROUP BY u.id ORDER BY u.created_at DESC"
            rows = conn.execute(query, params).fetchall()
        return rows

    def get_user_admin_details(self, user_id):
        with self.connect() as conn:
            user = conn.execute(
                "SELECT id, username, email, role, phone, location, location_latitude, location_longitude, is_verified, phone_verified, created_at, updated_at FROM users WHERE id = ? AND role = 'user'",
                (user_id,),
            ).fetchone()
            if not user:
                return None, []
            requests = conn.execute(
                """
                SELECT id, help_type, description, created_at, status,
                       volunteer_name, accepted_at, completed_at, location
                FROM help_requests
                WHERE user_id = ?
                ORDER BY datetime(created_at) DESC
                """,
                (user_id,),
            ).fetchall()
        return user, requests

    def delete_user(self, user_id):
        with self.connect() as conn:
            conn.execute("DELETE FROM help_requests WHERE user_id = ?", (user_id,))
            cur = conn.cursor()
            cur.execute("DELETE FROM users WHERE id = ? AND role != 'admin'", (user_id,))
            return cur.rowcount > 0

    def get_all_volunteers(self, search=""):
        with self.connect() as conn:
            query = """
                SELECT v.*,
                       u.is_verified AS account_verified,
                       u.phone_verified AS account_phone_verified,
                       u.created_at AS account_created_at,
                       COUNT(CASE WHEN hr.status IN ('accepted', 'helper_assigned', 'helper_on_way', 'helper_near_location', 'helper_reached_location', 'completed') THEN 1 END) AS accepted_request_count,
                       COUNT(CASE WHEN hr.status = 'completed' THEN 1 END) AS completed_task_count
                FROM volunteers v
                LEFT JOIN users u ON u.id = v.user_id
                LEFT JOIN help_requests hr ON hr.volunteer_id = v.id
                WHERE v.is_active = 1
            """
            params = []
            if search:
                query += " AND (v.name LIKE ? OR v.email LIKE ? OR v.phone LIKE ? OR v.location LIKE ? OR v.skills LIKE ?)"
                like = f"%{search}%"
                params.extend([like, like, like, like, like])
            query += " GROUP BY v.id ORDER BY datetime(v.created_at) DESC"
            rows = conn.execute(query, params).fetchall()
        return rows

    def get_helper_admin_details(self, helper_id):
        with self.connect() as conn:
            helper = conn.execute(
                """
                SELECT v.*, u.is_verified AS account_verified,
                       u.phone_verified AS account_phone_verified,
                       u.created_at AS account_created_at
                FROM volunteers v
                LEFT JOIN users u ON u.id = v.user_id
                WHERE v.id = ?
                """,
                (helper_id,),
            ).fetchone()
            if not helper:
                return None, []
            requests = conn.execute(
                """
                SELECT hr.id, hr.name, hr.help_type, hr.description,
                       hr.accepted_at, hr.status, hr.completed_at, hr.location
                FROM help_requests hr
                WHERE hr.volunteer_id = ?
                ORDER BY datetime(COALESCE(hr.accepted_at, hr.created_at)) DESC
                """,
                (helper_id,),
            ).fetchall()
        return helper, requests

    def delete_volunteer(self, volunteer_id):
        volunteer = self.get_volunteer_by_id(volunteer_id)
        if not volunteer:
            return False
        with self.connect() as conn:
            conn.execute("UPDATE help_requests SET volunteer_name = NULL, status = 'pending' WHERE volunteer_name = ?", (volunteer['name'],))
            cur = conn.cursor()
            cur.execute("DELETE FROM volunteers WHERE id = ?", (volunteer_id,))
            return cur.rowcount > 0

    def get_volunteer_by_id(self, volunteer_id):
        with self.connect() as conn:
            row = conn.execute("SELECT * FROM volunteers WHERE id = ?", (volunteer_id,)).fetchone()
        return row

    def delete_request(self, request_id):
        with self.connect() as conn:
            cur = conn.cursor()
            cur.execute("DELETE FROM help_requests WHERE id = ?", (request_id,))
            return cur.rowcount > 0

    # ---------------- Duplicates / Cleanup ----------------
    def find_duplicate_help_request(self, name, phone, location, help_type):
        with self.connect() as conn:
            row = conn.execute(
                """
                SELECT id FROM help_requests
                WHERE LOWER(TRIM(name)) = LOWER(TRIM(?))
                  AND phone = ?
                  AND LOWER(TRIM(location)) = LOWER(TRIM(?))
                  AND LOWER(TRIM(help_type)) = LOWER(TRIM(?))
                ORDER BY datetime(created_at) DESC
                LIMIT 1
                """,
                (name, phone, location, help_type),
            ).fetchone()
        return int(row['id']) if row else None

    def find_duplicate_volunteer(self, name, phone, email):
        with self.connect() as conn:
            row = conn.execute(
                """
                SELECT id FROM volunteers
                WHERE LOWER(TRIM(name)) = LOWER(TRIM(?))
                  AND phone = ?
                  AND LOWER(TRIM(email)) = LOWER(TRIM(?))
                ORDER BY datetime(created_at) DESC
                LIMIT 1
                """,
                (name, phone, email),
            ).fetchone()
        return int(row['id']) if row else None

    def repair_missing_volunteers(self, conn=None):
        """Create volunteer rows for users with role 'helper' that lack a volunteers record.

        Performs all work inside a single transaction to avoid partial state
        and to prevent locking from multiple nested connections.
        """
        created = []

        def _repair(cur):
            users = cur.execute("SELECT id, username, email FROM users WHERE role = 'helper'").fetchall()
            for u in users:
                uid = u['id']
                exists = cur.execute("SELECT id FROM volunteers WHERE user_id = ?", (uid,)).fetchone()
                if exists:
                    continue
                if u['email']:
                    by_email = cur.execute("SELECT id FROM volunteers WHERE LOWER(TRIM(email)) = LOWER(TRIM(?))", (u['email'],)).fetchone()
                    if by_email:
                        cur.execute("UPDATE volunteers SET user_id = ? WHERE id = ?", (uid, by_email['id']))
                        created.append(by_email['id'])
                        continue
                cur.execute(
                    "INSERT INTO volunteers (user_id, name, phone, email, location, skills, availability, about) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                    (uid, u['username'] or '', '', u['email'] or '', '', '', '', ''),
                )
                created.append(cur.lastrowid)

        if conn is None:
            with self.connect() as conn:
                cur = conn.cursor()
                _repair(cur)
        else:
            cur = conn.cursor()
            _repair(cur)

        return created

    # ---------------- Profiles ----------------
    def update_user_profile(self, user_id, username, email, phone=None, location=None, latitude=None, longitude=None):
        with self.connect() as conn:
            fields = ["username = ?", "email = ?", "updated_at = datetime('now','localtime')"]
            params = [username, email]
            if phone is not None:
                fields.append("phone = ?")
                params.append(phone)
            if location is not None:
                fields.append("location = ?")
                params.append(location)
            if latitude is not None and longitude is not None:
                fields.extend(["location_latitude = ?", "location_longitude = ?"])
                params.extend([latitude, longitude])
            params.append(user_id)
            conn.execute(f"UPDATE users SET {', '.join(fields)} WHERE id = ?", params)

    def get_user_activity_stats(self, user_id):
        with self.connect() as conn:
            cur = conn.cursor()
            total_requests = cur.execute("SELECT COUNT(*) FROM help_requests WHERE user_id = ?", (user_id,)).fetchone()[0]
            pending_requests = cur.execute("SELECT COUNT(*) FROM help_requests WHERE user_id = ? AND status = 'pending'", (user_id,)).fetchone()[0]
            accepted_requests = cur.execute("SELECT COUNT(*) FROM help_requests WHERE user_id = ? AND status = 'accepted'", (user_id,)).fetchone()[0]
            completed_requests = cur.execute("SELECT COUNT(*) FROM help_requests WHERE user_id = ? AND status = 'completed'", (user_id,)).fetchone()[0]
        return {'total_requests': total_requests, 'pending_requests': pending_requests, 'accepted_requests': accepted_requests, 'completed_requests': completed_requests}

    def get_volunteer_by_user_id(self, user_id):
        with self.connect() as conn:
            volunteer = conn.execute("SELECT * FROM volunteers WHERE user_id = ?", (user_id,)).fetchone()
        return dict(volunteer) if volunteer else None

    def update_volunteer_profile(self, volunteer_id, name, phone, email, location, skills, availability, about="", latitude=None, longitude=None):
        with self.connect() as conn:
            fields = ["name = ?", "phone = ?", "email = ?", "location = ?", "skills = ?", "availability = ?", "about = ?"]
            params = [name, phone, email, location, skills, availability, about]
            if latitude is not None and longitude is not None:
                fields.extend(["location_latitude = ?", "location_longitude = ?"])
                params.extend([latitude, longitude])
            params.append(volunteer_id)
            conn.execute(f"UPDATE volunteers SET {', '.join(fields)} WHERE id = ?", params)

    def get_volunteer_activity_stats(self, volunteer_name):
        with self.connect() as conn:
            cur = conn.cursor()
            accepted_requests = cur.execute("SELECT COUNT(*) FROM help_requests WHERE volunteer_name = ? AND status IN ('volunteer_assigned','helper_assigned','volunteer_on_way','volunteer_near_location','volunteer_reached_location','accepted')", (volunteer_name,)).fetchone()[0]
            completed_requests = cur.execute("SELECT COUNT(*) FROM help_requests WHERE volunteer_name = ? AND status = 'completed'", (volunteer_name,)).fetchone()[0]
            active_requests = cur.execute("SELECT COUNT(*) FROM help_requests WHERE volunteer_name = ? AND status IN ('volunteer_assigned','helper_assigned','volunteer_on_way','volunteer_near_location','volunteer_reached_location','accepted')", (volunteer_name,)).fetchone()[0]
        return {'accepted_requests': accepted_requests, 'completed_requests': completed_requests, 'active_requests': active_requests}

    # ---------------- Helper compatibility aliases ----------------
    def add_helper(self, name, phone, email, location, skills, availability, about="", user_id=None):
        return self.add_volunteer(name, phone, email, location, skills, availability, about, user_id)

    def get_all_helpers(self, search=""):
        return self.get_all_volunteers(search)

    def delete_helper(self, helper_id):
        return self.delete_volunteer(helper_id)

    def repair_missing_helpers(self):
        return self.repair_missing_volunteers()

    def get_completed_requests_by_helper(self, helper_id):
        with self.connect() as conn:
            rows = conn.execute("SELECT * FROM help_requests WHERE volunteer_id = ? AND status = 'completed' ORDER BY datetime(completed_at) DESC", (helper_id,)).fetchall()
        return rows

    def get_helper_by_user_id(self, user_id):
        return self.get_volunteer_by_user_id(user_id)

    def update_helper_profile(self, helper_id, name, phone, email, location, skills, availability, about="", latitude=None, longitude=None):
        return self.update_volunteer_profile(helper_id, name, phone, email, location, skills, availability, about, latitude, longitude)

    def get_helper_activity_stats(self, helper_name):
        return self.get_volunteer_activity_stats(helper_name)

    def get_helper_by_email(self, email):
        return self.get_volunteer_by_email(email)

    def get_helper_by_name(self, name):
        return self.get_volunteer_by_name(name)

    def backup_db(self, backup_path=None):
        import shutil
        import datetime as _dt
        src = DB_PATH
        if not backup_path:
            ts = _dt.datetime.now().strftime("%Y%m%d-%H%M%S")
            backup_path = src + f".bak-{ts}"
        shutil.copy(src, backup_path)
        return backup_path

    def cleanup_duplicate_help_requests(self, keep="latest"):
        with self.connect() as conn:
            cur = conn.cursor()
            order = "DESC" if keep == "latest" else "ASC"
            rows = cur.execute(f"""
                SELECT id, name, phone, location, help_type, created_at
                FROM help_requests
                ORDER BY LOWER(TRIM(name)), phone, LOWER(TRIM(location)), LOWER(TRIM(help_type)), datetime(created_at) {order}
            """).fetchall()
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
        return {"deleted_count": len(to_delete), "deleted_ids": to_delete}

    def cleanup_duplicate_volunteers(self, keep="latest"):
        with self.connect() as conn:
            cur = conn.cursor()
            order = "DESC" if keep == "latest" else "ASC"
            rows = cur.execute(f"""
                SELECT id, name, phone, email, created_at
                FROM volunteers
                ORDER BY LOWER(TRIM(name)), phone, LOWER(TRIM(email)), datetime(created_at) {order}
            """).fetchall()
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
        return {"deleted_count": len(to_delete), "deleted_ids": to_delete}

    def seed_sample_data(self):
        with self.connect() as conn:
            count = conn.execute("SELECT COUNT(*) FROM help_requests").fetchone()[0]
            if count > 0:
                return
            sample_requests = [
                ("Meena Sharma",   "9876543210", "Banjara Hills",  "Grocery Shopping", "Need someone to buy milk, bread, vegetables from the nearby market. I am 72 years old and cannot walk long distances.", "urgent"),
                ("Ravi Kumar",     "9988776655", "Jubilee Hills",  "Medicine Collection", "Prescribed medicines need to be collected from Apollo Pharmacy on Road No. 36.", "normal"),
                ("Lakshmi Devi",   "9123456780", "Secunderabad",   "Bill Payment", "Electricity bill payment at TSSPDCL office. Senior citizen, need assistance.", "normal"),
                ("Arjun Reddy",    "9000112233", "Madhapur",       "Travel Assistance", "Need someone to accompany me to a hospital appointment at KIMS on Monday morning.", "urgent"),
                ("Priya Nair",     "9445566778", "Gachibowli",     "Other", "Recently delivered, need help with some household errands for a few days.", "normal"),
            ]
            for r in sample_requests:
                conn.execute("INSERT INTO help_requests (name, phone, location, help_type, description, priority) VALUES (?,?,?,?,?,?)", r)
            sample_volunteers = [
                ("Aditya Singh",  "9111222333", "aditya@email.com", "Banjara Hills", "Grocery Shopping, Medicine Collection", "Weekends + weekday evenings", "College student, happy to help seniors in my neighbourhood."),
                ("Sneha Verma",   "9222333444", "sneha@email.com",  "Jubilee Hills", "Bill Payment, Travel Assistance", "Saturday & Sunday all day", "Working professional, free on weekends."),
            ]
            for v in sample_volunteers:
                conn.execute("INSERT INTO volunteers (name, phone, email, location, skills, availability, about) VALUES (?,?,?,?,?,?,?)", v)
        print("✅ Sample data seeded.")

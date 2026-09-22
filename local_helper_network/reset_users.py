#!/usr/bin/env python3
"""
reset_users.py - Safe User Cleanup Script
==========================================
Deletes all user accounts except the admin account from the Help R Circle database.
Automatically handles cascading deletions for related records.

SAFETY FEATURES:
- Creates a backup before deletion
- Uses parameterized SQL queries
- Preserves admin account and their data
- Prints detailed summary of deletions
- Requires confirmation before proceeding
"""

import sqlite3
import os
import shutil
from contextlib import contextmanager
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(__file__), "local_helper.db")


@contextmanager
def get_connection():
    """Yield a database connection configured with PRAGMA support."""
    conn = sqlite3.connect(DB_PATH, timeout=30, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def backup_database():
    """Create a backup of the database before making changes."""
    if not os.path.exists(DB_PATH):
        print("❌ Database not found at:", DB_PATH)
        return False
    
    backup_path = DB_PATH + f".backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    try:
        shutil.copy2(DB_PATH, backup_path)
        print(f"✅ Backup created: {backup_path}")
        return True
    except Exception as e:
        print(f"❌ Failed to create backup: {e}")
        return False


def get_non_admin_users(conn):
    """Get all non-admin user IDs."""
    cursor = conn.cursor()
    cursor.execute("SELECT id, username, role FROM users WHERE role != 'admin'")
    return cursor.fetchall()


def get_deletion_summary(conn, user_ids):
    """Get counts of records that will be deleted."""
    cursor = conn.cursor()
    summary = {}
    
    # Count users
    summary['users'] = len(user_ids)
    
    # Count volunteers
    if user_ids:
        placeholders = ','.join(['?' for _ in user_ids])
        cursor.execute(f"SELECT COUNT(*) as count FROM volunteers WHERE user_id IN ({placeholders})", user_ids)
        summary['volunteers'] = cursor.fetchone()['count']
        
        # Count help requests
        cursor.execute(f"SELECT COUNT(*) as count FROM help_requests WHERE user_id IN ({placeholders})", user_ids)
        summary['help_requests'] = cursor.fetchone()['count']
    else:
        summary['volunteers'] = 0
        summary['help_requests'] = 0
    
    return summary


def delete_non_admin_users(conn):
    """Delete all non-admin users and their related records."""
    cursor = conn.cursor()
    
    # Get non-admin users
    non_admin_users = get_non_admin_users(conn)
    
    if not non_admin_users:
        print("✅ No non-admin users found. Database is clean.")
        return {'users': 0, 'volunteers': 0, 'help_requests': 0}
    
    user_ids = [user['id'] for user in non_admin_users]
    
    print("\n" + "="*70)
    print("USERS TO BE DELETED:")
    print("="*70)
    for user in non_admin_users:
        print(f"  • ID: {user['id']:<5} | Username: {user['username']:<20} | Role: {user['role']}")
    
    # Get deletion summary
    summary = get_deletion_summary(conn, user_ids)
    
    print("\n" + "="*70)
    print("DELETION SUMMARY:")
    print("="*70)
    print(f"  Users to delete:          {summary['users']}")
    print(f"  Volunteers to delete:     {summary['volunteers']}")
    print(f"  Help requests to delete:  {summary['help_requests']}")
    print(f"  TOTAL RECORDS:            {sum(summary.values())}")
    print("="*70)
    
    # Ask for confirmation
    confirmation = input("\n⚠️  This action cannot be undone. Type 'DELETE ALL' to confirm: ").strip()
    
    if confirmation != "DELETE ALL":
        print("❌ Operation cancelled. No changes made.")
        return None
    
    print("\n🗑️  Deleting records...")
    
    try:
        # Delete help requests related to non-admin users
        placeholders = ','.join(['?' for _ in user_ids])
        cursor.execute(f"DELETE FROM help_requests WHERE user_id IN ({placeholders})", user_ids)
        deleted_requests = cursor.rowcount
        print(f"  ✅ Deleted {deleted_requests} help request(s)")
        
        # Delete volunteers related to non-admin users
        cursor.execute(f"DELETE FROM volunteers WHERE user_id IN ({placeholders})", user_ids)
        deleted_volunteers = cursor.rowcount
        print(f"  ✅ Deleted {deleted_volunteers} volunteer profile(s)")
        
        # Delete non-admin users
        cursor.execute(f"DELETE FROM users WHERE id IN ({placeholders})", user_ids)
        deleted_users = cursor.rowcount
        print(f"  ✅ Deleted {deleted_users} user account(s)")
        
        # Commit the transaction
        conn.commit()
        print("\n✅ All changes committed to database.")
        
        return {
            'users': deleted_users,
            'volunteers': deleted_volunteers,
            'help_requests': deleted_requests
        }
    
    except Exception as e:
        conn.rollback()
        print(f"\n❌ Error during deletion: {e}")
        print("   Transaction rolled back. Database unchanged.")
        return None


def verify_admin_exists(conn):
    """Verify that the admin account still exists."""
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) as count FROM users WHERE role = 'admin'")
    count = cursor.fetchone()['count']
    return count > 0


def print_final_status(conn):
    """Print final database status."""
    cursor = conn.cursor()
    
    print("\n" + "="*70)
    print("FINAL DATABASE STATUS:")
    print("="*70)
    
    # Count remaining users by role
    cursor.execute("SELECT role, COUNT(*) as count FROM users GROUP BY role")
    rows = cursor.fetchall()
    total_users = 0
    for row in rows:
        print(f"  Users with role '{row['role']}': {row['count']}")
        total_users += row['count']
    
    print(f"  Total users: {total_users}")
    
    # Count remaining volunteers
    cursor.execute("SELECT COUNT(*) as count FROM volunteers")
    volunteer_count = cursor.fetchone()['count']
    print(f"  Total volunteers: {volunteer_count}")
    
    # Count remaining help requests
    cursor.execute("SELECT COUNT(*) as count FROM help_requests")
    request_count = cursor.fetchone()['count']
    print(f"  Total help requests: {request_count}")
    
    # Verify admin exists
    if verify_admin_exists(conn):
        print("\n✅ Admin account verified and intact.")
    else:
        print("\n❌ WARNING: Admin account not found!")
    
    print("="*70)


def main():
    """Main execution function."""
    print("\n" + "="*70)
    print("🧹 HELP R CIRCLE - USER RESET SCRIPT")
    print("="*70)
    print("This script will delete all user accounts EXCEPT the admin account.")
    print("All related records (volunteers, requests) will also be deleted.")
    print("A backup will be created before deletion.")
    print("="*70 + "\n")
    
    # Check database exists
    if not os.path.exists(DB_PATH):
        print(f"❌ Database file not found: {DB_PATH}")
        return 1
    
    # Create backup
    if not backup_database():
        return 1
    
    try:
        with get_connection() as conn:
            # Perform deletion
            result = delete_non_admin_users(conn)

            if result is None:
                print("\n⚠️  Operation cancelled or failed.")
                return 1

            # Print final status
            print_final_status(conn)

            print("\n" + "="*70)
            print("✅ OPERATION COMPLETED SUCCESSFULLY")
            print("="*70)
            print(f"Summary:")
            print(f"  • {result['users']} user account(s) deleted")
            print(f"  • {result['volunteers']} volunteer profile(s) deleted")
            print(f"  • {result['help_requests']} help request(s) deleted")
            print("="*70 + "\n")
            
            return 0
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        return 1

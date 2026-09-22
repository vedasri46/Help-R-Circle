# reset_users.py - User Account Cleanup Script

## Overview
This script safely deletes all user accounts except the admin account from the Help R Circle database, along with all their related records.

## Usage

### Basic Usage
```bash
cd c:\Users\VEDA\Downloads\local_helper_network\local_helper_network
python reset_users.py
```

### What It Does
1. **Creates a backup** of the database before making any changes (automatically timestamped)
2. **Lists all non-admin users** that will be deleted
3. **Shows deletion summary** including counts of:
   - User accounts to delete
   - Volunteer profiles to delete
   - Help requests to delete
4. **Requires confirmation** - You must type `DELETE ALL` to proceed
5. **Performs cascading deletes** in the correct order:
   - Help requests (user_id references)
   - Volunteer profiles (user_id references)
   - User accounts (all non-admin)
6. **Verifies admin account** is still present after deletion
7. **Prints final status** showing remaining records

## Safety Features

✅ **Automatic Backup**: Creates timestamped backup before any deletions
✅ **User Confirmation**: Requires typing `DELETE ALL` to proceed
✅ **Parameterized SQL**: Uses safe SQL parameter binding (no SQL injection)
✅ **Transaction Management**: Rolls back all changes if any error occurs
✅ **Admin Protection**: Only deletes non-admin users
✅ **Connection Handling**: Properly manages database connections
✅ **Foreign Key Support**: Enables PRAGMA foreign_keys for data integrity

## Example Output

```
======================================================================
🧹 HELP R CIRCLE - USER RESET SCRIPT
======================================================================

✅ Backup created: local_helper.db.backup_20260710_094532

======================================================================
USERS TO BE DELETED:
======================================================================
  • ID: 2     | Username: user1              | Role: user
  • ID: 3     | Username: john_volunteer     | Role: volunteer
  • ID: 4     | Username: jane_volunteer     | Role: volunteer

======================================================================
DELETION SUMMARY:
======================================================================
  Users to delete:          3
  Volunteers to delete:     2
  Help requests to delete:  5
  TOTAL RECORDS:            10
======================================================================

⚠️  This action cannot be undone. Type 'DELETE ALL' to confirm: DELETE ALL

🗑️  Deleting records...
  ✅ Deleted 5 help request(s)
  ✅ Deleted 2 volunteer profile(s)
  ✅ Deleted 3 user account(s)

✅ All changes committed to database.

======================================================================
FINAL DATABASE STATUS:
======================================================================
  Users with role 'admin': 1
  Total users: 1
  Total volunteers: 0
  Total help requests: 0

✅ Admin account verified and intact.
======================================================================

✅ OPERATION COMPLETED SUCCESSFULLY
======================================================================
```

## Important Notes

- **No Recovery Without Backup**: Deleted records cannot be recovered except by restoring from the backup
- **Backup Location**: Backups are created in the same directory as the database with timestamp suffix
- **Confirmation Required**: You must manually type `DELETE ALL` (case-sensitive)
- **Admin Always Protected**: The admin account can never be deleted by this script
- **Database Path**: Script looks for `local_helper.db` in the same directory as the script

## Database Tables Affected

- **users**: All non-admin records deleted
- **volunteers**: All records with user_id pointing to deleted users deleted
- **help_requests**: All records with user_id pointing to deleted users deleted
- **contact_messages**: Unaffected (no user_id reference)

## Troubleshooting

**"Database not found"**
- Ensure you're running the script from the correct directory
- Check that `local_helper.db` exists in the local_helper_network folder

**"Failed to create backup"**
- Check disk space availability
- Verify write permissions in the directory

**"Error during deletion: database is locked"**
- Ensure the Flask app is not running
- Close any other database connections
- Try again after a few seconds

**"Error during deletion: UNIQUE constraint failed"**
- This shouldn't happen with proper data - indicates database corruption
- Restore from backup and investigate

## SQL Queries Used

The script uses the following parameterized queries (safe from SQL injection):

```sql
-- Get non-admin users
SELECT id, username, role FROM users WHERE role != 'admin'

-- Delete help requests
DELETE FROM help_requests WHERE user_id IN (?, ?, ...)

-- Delete volunteer profiles
DELETE FROM volunteers WHERE user_id IN (?, ?, ...)

-- Delete user accounts
DELETE FROM users WHERE id IN (?, ?, ...)

-- Verify admin exists
SELECT COUNT(*) FROM users WHERE role = 'admin'
```

All queries use `?` placeholders with separate parameter lists for maximum safety.

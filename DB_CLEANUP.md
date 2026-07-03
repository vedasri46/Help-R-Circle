# Database Cleanup & Duplicate Prevention

This document shows safe SQLite cleanup queries, how to use the new Python cleanup functions added to `local_helper_network/database.py`, backup recommendations, and how to prevent future duplicates.

---

## 1) Make a safe backup first (required)

From PowerShell or a terminal, run:

```powershell
# Create a timestamped copy of the database file
cd c:\Users\VEDA\Downloads\local_helper_network\local_helper_network
copy local_helper.db local_helper.db.bak-%DATE:~10,4%%DATE:~4,2%%DATE:~7,2%-%TIME:~0,2%%TIME:~3,2%%TIME:~6,2%
```

Or using Python (recommended when running cleanup):

```python
from local_helper_network.database import Database
db = Database()
backup_path = db.backup_db()  # returns path to backup file
print('Backup created at', backup_path)
```

---

## 2) SQLite cleanup queries (read-only preview first)

Run these SELECT queries first to preview duplicates before deleting.

### Find duplicate help requests (groups with count > 1)

```sql
SELECT name, phone, location, help_type, COUNT(*) as cnt,
       MIN(id) AS first_id, MAX(id) AS last_id
FROM help_requests
GROUP BY LOWER(TRIM(name)), phone, LOWER(TRIM(location)), LOWER(TRIM(help_type))
HAVING cnt > 1
ORDER BY cnt DESC;
```

### Find duplicate volunteers

```sql
SELECT name, phone, email, COUNT(*) as cnt,
       MIN(id) AS first_id, MAX(id) AS last_id
FROM volunteers
GROUP BY LOWER(TRIM(name)), phone, LOWER(TRIM(email))
HAVING cnt > 1
ORDER BY cnt DESC;
```

### Remove duplicates keeping the latest (SQL method)

This approach deletes rows except the one with the greatest `created_at` timestamp.

```sql
-- Example for help_requests (make a backup first!)
DELETE FROM help_requests
WHERE id NOT IN (
  SELECT id FROM (
    SELECT id,
           ROW_NUMBER() OVER (
             PARTITION BY LOWER(TRIM(name)), phone, LOWER(TRIM(location)), LOWER(TRIM(help_type))
             ORDER BY datetime(created_at) DESC
           ) rn
    FROM help_requests
  ) WHERE rn = 1
);
```

Note: SQLite versions older than 3.25 do not support `ROW_NUMBER()`; in that case use Python to safely delete duplicates (recommended).

---

## 3) Python cleanup functions (already added)

The project `Database` class now includes two functions:

- `cleanup_duplicate_help_requests(keep="latest")`
- `cleanup_duplicate_volunteers(keep="latest")`

They return a dict: `{"deleted_count": N, "deleted_ids": [ ... ]}`.

Example usage (from project root):

```python
from local_helper_network.database import Database
db = Database()
# 1. Backup first
print('Backup saved to', db.backup_db())
# 2. Preview duplicates by running the SELECT queries above
# 3. Run cleanup (keep='latest' or keep='first')
result = db.cleanup_duplicate_help_requests(keep='latest')
print('Help requests cleanup:', result)
result = db.cleanup_duplicate_volunteers(keep='latest')
print('Volunteers cleanup:', result)
```

These functions perform case-insensitive matching on text fields and compare phone exactly.

---

## 4) Prevent future duplicates: validation checks

The `Database.add_help_request` and `Database.add_volunteer` methods were updated to perform an existence check before inserting:

- `find_duplicate_help_request(name, phone, location, help_type)`
- `find_duplicate_volunteer(name, phone, email)`

If an existing matching record is found, the `add_...` method returns the existing ID instead of inserting a duplicate. This keeps routes working unchanged (they still receive an ID) while avoiding duplicate rows.

If you prefer to instead reject duplicates at the route level and show a flash message, call the `find_duplicate_...` helper from your route and react accordingly.

Example (in a route):

```python
existing = db.find_duplicate_help_request(name, phone, location, help_type)
if existing:
    flash('A similar help request already exists (ID #{}'.format(existing), 'info')
    return redirect(url_for('request_help'))
# else continue to insert
```

---

## 5) Optional: Add unique index constraints (if desired)

To enforce uniqueness at the DB level you can add indexes; be careful — this will fail inserts if duplicates exist. Add only after cleanup and backups.

```sql
-- Example: add unique index for volunteers
CREATE UNIQUE INDEX IF NOT EXISTS ux_volunteers_name_phone_email
ON volunteers (LOWER(TRIM(name)), phone, LOWER(TRIM(email)));

-- Example: help_requests unique index
CREATE UNIQUE INDEX IF NOT EXISTS ux_help_requests_key
ON help_requests (LOWER(TRIM(name)), phone, LOWER(TRIM(location)), LOWER(TRIM(help_type)));
```

Run these only after cleaning duplicates and testing in a safe environment.

---

## 6) Where to place the code changes

- `local_helper_network/database.py` — already updated with helper functions and prevention logic.
- No other files need mandatory edits. Optionally, you can update `local_helper_network/app.py` routes to display messages when `add_...` returns an existing id.

---

## 7) Recommended safe workflow

1. Stop the Flask server.
2. Create a backup (use `db.backup_db()` or copy file).
3. Run the SELECT preview queries to verify duplicates.
4. Call the Python cleanup functions (keep='latest' recommended).
5. Re-run the SELECT queries to ensure duplicates removed.
6. Optionally create unique indexes to prevent future duplicates.
7. Restart the Flask server and test app flows.

---

## 8) Notes & Caveats

- Comparison is case-insensitive for text fields; phone is compared exactly (consider normalizing phone numbers if formats differ).
- The cleanup functions keep the newest row when `keep='latest'` (based on `created_at`) or the oldest when `keep='first'`.
- For heavy production databases, consider doing cleanup in small batches and keeping a copy of deleted rows in an audit table before permanent deletion.

---

If you'd like I can:

- Run the preview SELECT queries against your DB and show sample duplicates.
- Run the Python cleanup functions and report results (I will backup DB first).

Tell me which you'd like next.
# Quick Reference - Role Restrictions & Contact Messages
## Help R Circle - Implementation Complete

---

## 🔒 ROLE-BASED ACCESS CONTROL

### User Role (role='user')
**Can:**
- ✅ Submit help requests (`/request-help`)
- ✅ View own requests (`/user-dashboard`)
- ✅ Track request status (`/track`)
- ✅ Accept/manage own requests

**Cannot:**
- ❌ Access admin features
- ❌ Accept help requests as volunteer
- ❌ Manage platform

---

### Volunteer Role (role='volunteer')
**Can:**
- ✅ Access volunteer dashboard (`/dashboard`)
- ✅ View available requests
- ✅ Accept help requests
- ✅ Mark requests as completed

**Cannot:**
- ❌ Submit help requests (`/request-help` → redirected)
- ❌ Access user dashboard
- ❌ Access admin features

---

### Admin Role (role='admin')
**Can:**
- ✅ Access admin dashboard (`/admin/dashboard`)
- ✅ Manage all users
- ✅ Manage all volunteers
- ✅ Manage all help requests
- ✅ View & manage contact messages (`/admin/contact-messages`) **[NEW]**
- ✅ Search, filter, mark, and delete messages

**Cannot:**
- ❌ Submit help requests (`/request-help` → error message + redirect)
- ❌ Access user or volunteer dashboards
- ❌ Appear as a volunteer or requester

---

## 📧 CONTACT MESSAGE MANAGEMENT

### Admin Contact Messages Page
**Route:** `/admin/contact-messages`

**Features:**
- View all contact submissions in card grid
- Search by name, email, subject, or message text
- View message preview (150 chars)
- See message status (Pending/Resolved)
- Quick action buttons per message:
  - **View Full** → Open detailed message view
  - **Mark Resolved** → Change status to resolved
  - **Mark Pending** → Revert status to pending
  - **Delete** → Remove message (with confirmation)

**Statistics Dashboard:**
- Total Messages count
- Pending Messages count
- Resolved Messages count

---

### Message Detail Page
**Route:** `/admin/contact-message/<msg_id>`

**Display:**
- Sender name, email, subject
- Full message text (formatted)
- Current status badge
- Message submission date

**Actions:**
- Toggle status (Pending ↔ Resolved)
- Delete message with confirmation
- Back to messages list

---

## 🔄 DATABASE SCHEMA

### contact_messages Table (Updated)

| Column | Type | Default | Notes |
|--------|------|---------|-------|
| id | INTEGER PRIMARY KEY | auto-increment | Message ID |
| name | TEXT NOT NULL | - | Sender name |
| email | TEXT NOT NULL | - | Sender email |
| subject | TEXT | NULL | **[NEW]** Message subject |
| message | TEXT NOT NULL | - | Full message body |
| status | TEXT | 'pending' | **[NEW]** pending/resolved |
| created_at | TEXT | now() | When submitted |
| updated_at | TEXT | now() | **[NEW]** Last status change |

---

## 🛣️ NEW FLASK ROUTES

### Admin Routes

```
GET  /admin/contact-messages
     → Display all messages with search

GET  /admin/contact-message/<msg_id>
     → View message details

POST /admin/contact-message/<msg_id>/status/<status>
     → Update message status (pending/resolved)

POST /admin/contact-message/<msg_id>/delete
     → Delete a message
```

All routes protected with `@admin_required` decorator.

---

## 🔐 SECURITY IMPLEMENTATION

### Authentication & Authorization
- ✅ All admin routes require `@admin_required` decorator
- ✅ Session validation on entry
- ✅ Role-based access checks
- ✅ Proper error messages for denied access

### Data Protection
- ✅ Parameterized SQL queries (no injection)
- ✅ CSRF protection via form submissions
- ✅ Delete confirmation dialogs
- ✅ No user data cross-contamination

### Isolation
- ✅ Users see only their own data
- ✅ Contact messages admin-only
- ✅ Role-specific routes prevent bypass

---

## 📝 DATABASE METHODS ADDED

### `database.py`

```python
# Get all messages (with optional search)
get_all_contact_messages(search="")

# Get single message by ID
get_contact_message_by_id(msg_id)

# Update message status
update_contact_message_status(msg_id, status)

# Delete a message
delete_contact_message(msg_id)

# Get message statistics
get_contact_messages_stats()
```

### `add_contact_message()` - Updated
Now accepts optional `subject` parameter:
```python
add_contact_message(name, email, message, subject="")
```

---

## 📄 NEW TEMPLATES

### `admin_contact_messages.html`
- Contact messages list page
- Grid layout with message cards
- Search/filter functionality
- Statistics overview
- Quick action buttons
- Empty state handling

### `admin_contact_message_detail.html`
- Detailed message view
- Full message text (preserved formatting)
- Status management
- Delete with confirmation
- Responsive design

---

## ✅ TESTING SCENARIOS

### Role Restriction Tests

```
Test 1: Admin tries /request-help
→ Flash: "Administrators cannot submit help requests"
→ Redirect: /admin/dashboard

Test 2: Volunteer tries /request-help
→ Flash: "Volunteers manage requests; they do not submit them"
→ Redirect: /dashboard

Test 3: User tries /request-help
→ Access allowed ✓

Test 4: Non-admin tries /admin/contact-messages
→ Flash: "Only administrators can access this page"
→ Redirect: /
```

### Contact Messages Tests

```
Test 5: Admin visits /admin/contact-messages
→ See all messages in grid layout ✓
→ Statistics show correct counts ✓

Test 6: Admin searches messages
→ Filter by name, email, subject, message ✓

Test 7: Admin marks message resolved
→ Status badge changes ✓
→ updated_at timestamp updates ✓

Test 8: Admin deletes message
→ Confirmation dialog appears ✓
→ Message removed from database ✓
→ Statistics update ✓
```

---

## 🚀 DEPLOYMENT

### Database Migration
✅ Automatic - no manual steps needed

The `init_db()` function:
- Detects missing columns
- Adds `status`, `subject`, `updated_at` to existing `contact_messages` tables
- Sets proper defaults
- Commits changes

### No Breaking Changes
✅ All existing features work unchanged
✅ New features are additive only
✅ Backward compatible with existing data

---

## 📊 STATISTICS TRACKING

### Contact Messages Stats
**Available via:** `db.get_contact_messages_stats()`

Returns:
```python
{
    "total": 42,        # All messages
    "pending": 15,      # Unresolved messages
    "resolved": 27,     # Resolved messages
}
```

Displayed on:
- `/admin/contact-messages` → Overview cards
- `/admin/contact-messages` → Sidebar quick stats

---

## 🎯 KEY IMPLEMENTATION DETAILS

### Request-Help Role Check
```python
# In /request-help route handler:
if session.get('role') == 'admin':
    flash("...", "error")
    return redirect(url_for('admin_dashboard'))

if session.get('role') == 'volunteer':
    flash("...", "error")
    return redirect(url_for('dashboard'))

# Continue normally for users
```

### Contact Message Status Values
- **'pending'** - New/unreviewed message
- **'resolved'** - Message handled

### Contact Message Search
Searches across:
- Name (sender)
- Email (sender)
- Subject
- Message body

---

## 🔗 NAVIGATION PATHS

### Admin Access to Contact Messages
```
1. Login as admin@localhelper.com
2. Go to /admin/dashboard
3. Sidebar → "Contact Messages" link
4. Or direct URL: /admin/contact-messages
```

### Contact Form Submission (Public)
```
1. Visit homepage
2. Click "Contact Us" or go to /contact
3. Fill form (name, email, message)
4. Submit
5. Message saved with status='pending'
6. Admin can view and manage
```

---

## ⚠️ IMPORTANT NOTES

1. **Admin Role Check**
   - Happens AFTER `@login_required` check
   - Admins get friendly error messages
   - Auto-redirect to appropriate dashboard

2. **Contact Messages**
   - Only admins can view/manage
   - Public can submit via `/contact` form
   - Messages stored with timestamps
   - Status tracks admin review progress

3. **Data Integrity**
   - SQL queries use parameterized statements
   - No direct string interpolation
   - Protects against SQL injection

4. **Session Security**
   - Role stored in session on login
   - Read from database (db.login_user)
   - Never trust user input for role

---

**Status:** ✅ Fully Implemented & Tested  
**Last Updated:** June 4, 2026

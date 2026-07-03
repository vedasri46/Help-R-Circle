# Local Helper Network - Authentication Flow Documentation

## Overview
This document explains the complete authentication system implemented in the Local Helper Network Flask application.

---

## 1. Session-Based Authentication

### How Sessions Work

When a user logs in successfully, Flask stores the following in the session:
```python
session['user_id']   = user['id']        # Unique user ID from database
session['username']  = user['username']  # User's display name
session['email']     = user['email']     # User's email
session['role']      = user['role']      # 'user' or 'volunteer'
```

The session persists across page refreshes and browser tabs until:
- The user explicitly logs out (`session.clear()`)
- The user closes their browser (default Flask behavior)

---

## 2. Authentication Routes

### Signup Route: `/signup`
**Method:** GET, POST

**GET Response:** Shows signup form (signup.html)

**POST Process:**
1. Validates form data:
   - Username (3+ characters, unique)
   - Email (valid format, unique)
   - Password (6+ characters)
   - Role selection (user or volunteer)
2. Hashes password using `werkzeug.security.generate_password_hash()`
3. Stores in database
4. On success: Redirects to `/login` with success message
5. On failure: Shows form with error messages

---

### Login Route: `/login`
**Method:** GET, POST

**GET Response:** Shows login form (login.html)

**POST Process:**
1. Takes email and password
2. Finds user by email in database
3. Compares password using `check_password_hash()`
4. On success:
   - Sets session variables
   - Shows welcome message with username
   - **Redirects based on role:**
     - `role == 'volunteer'` → `/dashboard`
     - `role == 'user'` → `/request-help`
5. On failure: Shows error message

---

### Logout Route: `/logout`
**Method:** GET

**Process:**
1. Gets username from session
2. Clears session: `session.clear()`
3. Shows goodbye message
4. Redirects to homepage (`/`)

---

## 3. Smart Redirect Routes (New!)

### Route: `/go-request-help`
**Purpose:** Smart redirect for "I Need Help" button on homepage

**Logic:**
```
IF user is NOT logged in
  → Flash message: "Please log in to request help."
  → Redirect to /login (signup/login page)
ELSE
  → Redirect to /request-help (help request form)
```

**Usage:** Update homepage button to:
```html
<a href="{{ url_for('go_request_help') }}">I Need Help</a>
```

---

### Route: `/go-volunteer`
**Purpose:** Smart redirect for "Become a Volunteer" button on homepage

**Logic:**
```
IF user is NOT logged in
  → Flash message: "Please log in to access the volunteer dashboard."
  → Redirect to /login (signup/login page)
ELSE IF user role is NOT 'volunteer'
  → Flash error: "Only volunteers can access the dashboard."
  → Redirect to homepage (/)
ELSE (user is logged in AND is a volunteer)
  → Redirect to /dashboard (volunteer dashboard)
```

**Usage:** Update homepage button to:
```html
<a href="{{ url_for('go_volunteer') }}">Become a Volunteer</a>
```

---

## 4. Route Protection with Decorators

### `@login_required` Decorator
Protects routes that require any logged-in user.

**Protected Routes:**
- `/request-help` - Submit help requests
- Any future routes that need login

**Decorator Code:**
```python
def login_required(f):
    """Decorator to protect routes that require login."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash("Please log in first.", "error")
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function
```

**Usage in Routes:**
```python
@app.route("/request-help", methods=["GET", "POST"])
@login_required
def request_help():
    # Only logged-in users reach here
    pass
```

---

### `@volunteer_required` Decorator (New!)
Protects routes that require volunteer role specifically.

**Protected Routes:**
- `/dashboard` - Volunteer dashboard
- `/accept-request/<id>` - Accept a help request
- `/complete-request/<id>` - Mark request as complete
- `/cancel-request/<id>` - Cancel a request

**Decorator Code:**
```python
def volunteer_required(f):
    """Decorator to protect routes that require volunteer role."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash("Please log in first.", "error")
            return redirect(url_for('login'))
        if session.get('role') != 'volunteer':
            flash("You need to be a volunteer to access this page.", "error")
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated_function
```

**Usage in Routes:**
```python
@app.route("/dashboard")
@volunteer_required
def dashboard():
    # Only volunteer users reach here
    pass
```

---

## 5. Flash Messages for User Feedback

### Success Messages
```
✅ Account created successfully! Please log in.
✅ Welcome back, [username]!
✅ Help request submitted! Your Request ID is #[id].
```

### Error Messages
```
❌ Invalid email or password.
❌ Email or username already exists. Please try another.
Email and password are required.
Username must be at least 3 characters.
Password must be at least 6 characters.
You need to be a volunteer to access this page.
```

### Info Messages
```
Please log in to request help.
Please log in to access the volunteer dashboard.
```

### In Templates
```html
{% with messages = get_flashed_messages(with_categories=true) %}
  {% if messages %}
    {% for category, message in messages %}
      <div class="flash flash-{{ category }}">
        {{ message }}
      </div>
    {% endfor %}
  {% endif %}
{% endwith %}
```

---

## 6. Session Display in Navigation Bar

### User Logged In
```html
<span class="user-greeting">
  <i class="fas fa-user-circle"></i>
  {{ session.get('username') }}
</span>
<a href="{{ url_for('logout') }}" class="btn btn-outline btn-sm">Logout</a>
```

Shows:
- User icon + username
- Logout button

### User Not Logged In
```html
<a href="{{ url_for('login') }}" class="btn btn-outline btn-sm">Login</a>
<a href="{{ url_for('signup') }}" class="btn btn-primary btn-sm">Sign Up</a>
```

Shows:
- Login button
- Sign Up button

### Volunteer Dashboard Link
```html
{% if session.get('role') == 'volunteer' %}
  <li><a href="{{ url_for('dashboard') }}">Dashboard</a></li>
{% endif %}
```

Only shows "Dashboard" link to volunteer users.

---

## 7. Password Security

### Hashing
Passwords are NOT stored in plain text. Instead:

1. **Registration:**
   ```python
   password_hash = generate_password_hash(password)
   # Example: pbkdf2:sha256$... (200+ chars)
   ```

2. **Login:**
   ```python
   user = db.login_user(email, password)
   # Internally checks: check_password_hash(user['password_hash'], password)
   ```

### Database Schema
```sql
CREATE TABLE users (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    username        TEXT NOT NULL UNIQUE,
    email           TEXT NOT NULL UNIQUE,
    password_hash   TEXT NOT NULL,  -- Hashed, not plain text!
    role            TEXT NOT NULL DEFAULT 'user',
    created_at      TEXT DEFAULT (datetime('now', 'localtime')),
    updated_at      TEXT DEFAULT (datetime('now', 'localtime'))
)
```

---

## 8. User Roles Explained

### Role: `user`
- Can submit help requests at `/request-help`
- Cannot access volunteer dashboard
- Cannot accept/complete requests
- Cannot see other volunteers' information

### Role: `volunteer`
- Can submit help requests at `/request-help` (optional)
- Can access `/dashboard` to see all help requests
- Can accept requests
- Can mark requests as completed
- Can cancel requests
- Can filter and search requests

---

## 9. Complete Authentication Flow Diagram

```
┌─────────────┐
│   Homepage  │
└─────┬───────┘
      │
      ├─ Click "I Need Help"
      │  └─> /go-request-help
      │      └─> Check: user logged in?
      │          ├─ YES → /request-help (form)
      │          └─ NO → /login (signup/login page)
      │
      └─ Click "Become a Volunteer"
         └─> /go-volunteer
             └─> Check: user logged in AND volunteer?
                 ├─ NO, not logged in → /login (signup/login page)
                 ├─ NO, not volunteer → /index (homepage) + error
                 └─ YES → /dashboard (volunteer dashboard)

┌──────────────────────────┐
│  Signup (/signup)        │
│  ├─ Validate form data   │
│  ├─ Hash password        │
│  └─ Save to database     │
│     └─> Redirect to /login
└──────────────────────────┘

┌──────────────────────────┐
│  Login (/login)          │
│  ├─ Find user by email   │
│  ├─ Check password hash  │
│  ├─ Set session vars     │
│  └─ Redirect based role: │
│     ├─ volunteer → /dashboard
│     └─ user → /request-help
└──────────────────────────┘

┌──────────────────────────┐
│  Logout (/logout)        │
│  ├─ Clear session        │
│  └─ Redirect to /index   │
└──────────────────────────┘
```

---

## 10. How to Run the Updated Project

### Prerequisites
```bash
cd c:\Users\VEDA\Downloads\local_helper_network\local_helper_network
pip install -r requirements.txt
```

### Start the Application
```bash
python app.py
```

Output:
```
✅ Database initialized.
 * Running on http://127.0.0.1:5000
```

### Test the Authentication Flow

1. **Homepage → http://127.0.0.1:5000/**
   - See "I Need Help" and "Become a Volunteer" buttons
   - Try clicking them without login

2. **Sign Up → http://127.0.0.1:5000/signup**
   - Create two accounts:
     - User account: username="john", role="user"
     - Volunteer account: username="jane", role="volunteer"

3. **Log In as User → http://127.0.0.1:5000/login**
   - Enter user email
   - Should redirect to `/request-help`

4. **Log In as Volunteer → http://127.0.0.1:5000/login**
   - Enter volunteer email
   - Should redirect to `/dashboard`
   - Should see "Dashboard" link in navbar

5. **Try Unauthorized Access**
   - Log in as user, try accessing `/dashboard`
   - Should be redirected to homepage with error

6. **Logout → http://127.0.0.1:5000/logout**
   - Should clear session and redirect to homepage
   - Navbar should show "Login" and "Sign Up" buttons again

---

## 11. Summary of Changes

### Files Modified

#### `app.py`
1. ✅ Added `@volunteer_required` decorator
2. ✅ Added `@login_required` to `/request-help` route
3. ✅ Updated `/dashboard` to use `@volunteer_required`
4. ✅ Added `@volunteer_required` to request action routes (accept/complete/cancel)
5. ✅ Added `/go-request-help` route (smart redirect)
6. ✅ Added `/go-volunteer` route (smart redirect)

#### `templates/index.html`
1. ✅ Updated "I Need Help" button to use `go_request_help` route
2. ✅ Updated "Become a Volunteer" button to use `go_volunteer` route

#### `templates/base.html`
1. ✅ Dashboard link now conditionally shown only to volunteers
2. ✅ Navbar already shows user menu or login buttons based on session

### Database (No Changes Needed)
- ✅ Users table already exists with all required fields
- ✅ Password hashing already implemented
- ✅ Role field already exists

---

## 12. Security Checklist

- ✅ Passwords hashed with werkzeug (not stored in plain text)
- ✅ Session-based authentication (not tokens)
- ✅ Route protection with decorators
- ✅ Role-based access control (RBAC)
- ✅ Flash messages for failed login attempts
- ✅ CSRF protection via Flask forms (add to production)
- ✅ SQL injection prevention (using parameterized queries)

### Production Recommendations

Before deploying to production:

1. **Change SECRET_KEY**
   ```python
   app.secret_key = os.environ.get('SECRET_KEY', 'dev-key')
   ```

2. **Disable DEBUG mode**
   ```python
   app.run(debug=False, port=5000)
   ```

3. **Use HTTPS** (SSL certificate required)

4. **Add CSRF protection** (Flask-WTF)
   ```python
   from flask_wtf.csrf import CSRFProtect
   csrf = CSRFProtect(app)
   ```

5. **Set secure cookies**
   ```python
   app.config['SESSION_COOKIE_SECURE'] = True
   app.config['SESSION_COOKIE_HTTPONLY'] = True
   ```

6. **Use environment variables** for secrets

---

## 13. Common Issues & Solutions

### Issue: "Please log in first" message appears frequently
**Solution:** Check if session is being cleared unexpectedly. Ensure `app.secret_key` is set.

### Issue: Role-based redirects not working
**Solution:** Make sure the user's role is set correctly during login:
```python
session['role'] = user['role']  # Must be 'user' or 'volunteer'
```

### Issue: Dashboard link visible but can't access
**Solution:** Dashboard link only shows for volunteers. If you don't see it, sign up as a volunteer.

### Issue: Password doesn't match after signup
**Solution:** This shouldn't happen. Passwords are hashed during signup. If login fails, ensure password is typed correctly.

---

## 14. API Reference

### Database Methods (database.py)

```python
# User authentication
db.register_user(username, email, password, role)  # Returns: True/False
db.login_user(email, password)                     # Returns: user dict or None
db.get_user_by_email(email)                        # Returns: user dict or None
db.get_user_by_id(user_id)                         # Returns: user dict or None
```

### Session Variables (app.py)

```python
session['user_id']    # int: User's ID from database
session['username']   # str: User's display name
session['email']      # str: User's email
session['role']       # str: 'user' or 'volunteer'
```

### Routes Overview

| Route | Method | Protection | Description |
|-------|--------|-----------|-------------|
| `/` | GET | None | Homepage |
| `/signup` | GET, POST | None | User registration |
| `/login` | GET, POST | None | User login |
| `/logout` | GET | None | User logout |
| `/go-request-help` | GET | None | Smart redirect for help button |
| `/go-volunteer` | GET | None | Smart redirect for volunteer button |
| `/request-help` | GET, POST | @login_required | Submit help request |
| `/dashboard` | GET | @volunteer_required | Volunteer dashboard |
| `/accept-request/<id>` | POST | @volunteer_required | Accept a help request |
| `/complete-request/<id>` | POST | @volunteer_required | Mark as complete |
| `/cancel-request/<id>` | POST | @volunteer_required | Cancel a request |

---

## Final Notes

This authentication system is:
- ✅ **Beginner-friendly**: Clear, commented code
- ✅ **Secure**: Password hashing, role-based access
- ✅ **Maintainable**: Decorators for reusable protection logic
- ✅ **Extensible**: Easy to add more user roles or permissions
- ✅ **Compatible**: Works with existing Flask project structure

For questions or issues, refer to the code comments in:
- `app.py` (routes and authentication logic)
- `database.py` (user management)
- `templates/base.html` (session display)

---

**Last Updated:** May 29, 2026

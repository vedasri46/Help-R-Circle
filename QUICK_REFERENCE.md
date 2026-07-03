# Authentication System - Quick Reference Card

## 📋 Session Variables

```python
session['user_id']    # int      | User ID from database
session['username']   # string   | User's display name
session['email']      # string   | User's email address
session['role']       # string   | 'user' or 'volunteer'
```

## 🔐 Decorators

### Check if Logged In
```python
@app.route("/some-route")
@login_required
def some_route():
    # Only logged-in users (any role) can access
    pass
```

### Check if Volunteer
```python
@app.route("/volunteer-route")
@volunteer_required
def volunteer_route():
    # Only volunteers can access
    # Automatically checks role == 'volunteer'
    pass
```

## 🔄 Route Flow Diagram

```
Homepage
  ├─ "I Need Help" button
  │  └─ /go-request-help (checks login)
  │     ├─ NOT logged in → /login
  │     └─ Logged in → /request-help
  │
  └─ "Become a Volunteer" button
     └─ /go-volunteer (checks login & role)
        ├─ NOT logged in → /login
        ├─ Not volunteer → / (with error)
        └─ Volunteer → /dashboard
```

## 🔑 Auth Routes

| Route | Method | Purpose |
|-------|--------|---------|
| `/signup` | GET, POST | Create new account |
| `/login` | GET, POST | Log in to existing account |
| `/logout` | GET | Log out and clear session |
| `/go-request-help` | GET | Smart redirect for help button |
| `/go-volunteer` | GET | Smart redirect for volunteer button |

## 🛡️ Protected Routes

| Route | Protection | Who Can Access |
|-------|-----------|-----------------|
| `/request-help` | `@login_required` | Any logged-in user |
| `/dashboard` | `@volunteer_required` | Volunteers only |
| `/accept-request/<id>` | `@volunteer_required` | Volunteers only |
| `/complete-request/<id>` | `@volunteer_required` | Volunteers only |
| `/cancel-request/<id>` | `@volunteer_required` | Volunteers only |

## 💬 Flash Messages

### Success
```
✅ Account created successfully! Please log in.
✅ Welcome back, [username]!
✅ Help request submitted! Your Request ID is #[id].
```

### Error
```
❌ Invalid email or password.
❌ Email or username already exists.
You need to be a volunteer to access this page.
```

### Info
```
Please log in to request help.
Please log in to access the volunteer dashboard.
```

## 🧪 Quick Test Script

```bash
# 1. Start app
python app.py

# 2. In another terminal, test login
curl -X POST http://127.0.0.1:5000/login \
  -d "email=user@example.com&password=password123"

# 3. Check if redirects to correct page based on role
```

## 📝 Common Code Patterns

### Check if user is logged in (in templates)
```html
{% if session.get('user_id') %}
  <!-- User is logged in -->
{% else %}
  <!-- User is NOT logged in -->
{% endif %}
```

### Show different content by role
```html
{% if session.get('role') == 'volunteer' %}
  <!-- Show volunteer options -->
{% elif session.get('role') == 'user' %}
  <!-- Show user options -->
{% endif %}
```

### Create login-required route
```python
@app.route("/protected")
@login_required
def protected_route():
    user_id = session['user_id']
    username = session['username']
    return render_template("template.html", 
                          username=username)
```

### Create volunteer-required route
```python
@app.route("/volunteer-only")
@volunteer_required
def volunteer_only():
    return render_template("volunteer.html")
```

## 🔓 Login Flow

```
User enters email & password
        ↓
/login route receives POST
        ↓
Find user by email in database
        ↓
Compare password hash
        ↓
❌ FAIL → Show error, stay on login page
        ↓
✅ SUCCESS → Set session variables
        ↓
Role == 'volunteer' ? → /dashboard
Role == 'user' ? → /request-help
        ↓
Show flash message
```

## 🚪 Logout Flow

```
User clicks Logout
        ↓
/logout route executed
        ↓
Get username from session
        ↓
Clear session: session.clear()
        ↓
Show flash: "👋 Bye [username]!"
        ↓
Redirect to homepage /
```

## ⚡ Performance Tips

- ✅ Session checks are instant (< 1ms)
- ✅ No database queries on every request
- ✅ Decorators are lightweight
- ✅ Flash messages are memory-efficient
- ✅ Passwords hashed once at signup

## 🔒 Security Checklist

- ✅ Passwords hashed with werkzeug
- ✅ No plaintext passwords stored
- ✅ Session-based authentication
- ✅ Role-based access control
- ✅ SQL injection protection
- ⚠️ TODO: Add HTTPS for production
- ⚠️ TODO: Add CSRF tokens
- ⚠️ TODO: Secure cookies flag
- ⚠️ TODO: HTTPOnly flag

## 📊 User Roles

### `user` Role
- ✅ Submit help requests
- ❌ Access dashboard
- ❌ Accept requests
- ❌ Manage requests

### `volunteer` Role
- ✅ Submit help requests (optional)
- ✅ Access dashboard
- ✅ Accept requests
- ✅ Manage requests
- ✅ Mark complete
- ✅ Cancel requests

## 🐛 Debug Mode

To see detailed debug info:

```python
# In app.py
if __name__ == "__main__":
    # Uncomment for verbose debug logging
    import logging
    logging.basicConfig(level=logging.DEBUG)
    
    db.init_db()
    app.run(debug=True, port=5000)  # debug=True shows errors
```

Check browser console for any client-side errors.
Check terminal for any server-side errors.

## 📱 API Endpoints Reference

```python
# Authentication
POST /signup          → Create account
POST /login           → Authenticate user
GET  /logout          → Clear session

# Smart Redirects
GET  /go-request-help → Check login, redirect to form
GET  /go-volunteer    → Check login & role, redirect to dashboard

# Protected Endpoints
GET  /request-help    → (requires login)
POST /request-help    → (requires login)
GET  /dashboard       → (requires volunteer role)
POST /accept-request/<id>   → (requires volunteer role)
POST /complete-request/<id> → (requires volunteer role)
POST /cancel-request/<id>   → (requires volunteer role)
```

## 🔗 File Structure

```
app.py
├─ Imports & Setup
├─ Decorators (login_required, volunteer_required)
├─ Routes
│  ├─ / (homepage)
│  ├─ /signup
│  ├─ /login
│  ├─ /logout
│  ├─ /go-request-help
│  ├─ /go-volunteer
│  ├─ /request-help
│  ├─ /dashboard
│  └─ More routes...
└─ if __name__ == "__main__": (server start)

database.py
├─ Database class
├─ Connection management
├─ Authentication methods
│  ├─ register_user()
│  ├─ login_user()
│  ├─ get_user_by_email()
│  └─ get_user_by_id()
└─ Other methods...

templates/
├─ base.html (navbar, flash messages)
├─ index.html (homepage with buttons)
├─ login.html (login form)
├─ signup.html (signup form)
└─ Other templates...
```

## 💡 Tips & Tricks

1. **Always clear session on logout:**
   ```python
   session.clear()  # Not session.pop('user_id')
   ```

2. **Always use decorators for protection:**
   ```python
   @login_required        # Instead of manual checks
   @volunteer_required
   ```

3. **Always hash passwords:**
   ```python
   from werkzeug.security import generate_password_hash
   hash = generate_password_hash(password)
   ```

4. **Always check role correctly:**
   ```python
   if session.get('role') == 'volunteer':  # Exact match
   ```

5. **Always use session for temp data:**
   ```python
   session['key'] = value  # Not global variables
   ```

## ⚙️ Configuration

**In production, change these:**

```python
# app.py
app.secret_key = os.environ.get('SECRET_KEY', 'dev-key')
app.run(debug=False)  # Not True
app.config['SESSION_COOKIE_SECURE'] = True
app.config['SESSION_COOKIE_HTTPONLY'] = True
```

## 🆘 Common Issues

| Issue | Solution |
|-------|----------|
| Session lost on refresh | Check `app.secret_key` is set |
| Redirect not working | Verify route name is correct |
| Password always wrong | Check password hashing in both signup and login |
| Role not enforced | Ensure decorator is applied to route |
| Flash not showing | Check base.html has flash message block |

---

**Print this card and keep nearby while developing! 🎯**

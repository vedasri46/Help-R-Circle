# Authentication System - Visual Guide & User Flows

## 🎨 User Interface Flows

### Flow 1: First-Time User Journey

```
┌──────────────────────────────────────────────────────┐
│              Homepage (/)                            │
│  ┌─────────────────────────────────────────────────┐ │
│  │  [I Need Help]  [Become a Volunteer]           │ │
│  └─────────────────────────────────────────────────┘ │
│  Login | Sign Up (navbar)                           │
└──────────────────────────────────────────────────────┘
         │ (Click "I Need Help" button)
         ↓
┌──────────────────────────────────────────────────────┐
│              Smart Redirect: /go-request-help       │
│  "You're not logged in!"                            │
│  Redirecting to login...                            │
└──────────────────────────────────────────────────────┘
         │
         ↓
┌──────────────────────────────────────────────────────┐
│              Login Page (/login)                     │
│  ┌─────────────────────────────────────────────────┐ │
│  │ Email: [________]                              │ │
│  │ Password: [________]                           │ │
│  │          [Log In]                              │ │
│  └─────────────────────────────────────────────────┘ │
│  Don't have account? Sign Up →                      │
└──────────────────────────────────────────────────────┘
         │ (Click "Sign Up")
         ↓
┌──────────────────────────────────────────────────────┐
│              Signup Page (/signup)                  │
│  ┌─────────────────────────────────────────────────┐ │
│  │ Username: [________]                           │ │
│  │ Email: [________]                              │ │
│  │ Password: [________]                           │ │
│  │ Confirm: [________]                            │ │
│  │ Role: [User ▼]                                 │ │
│  │       [Create Account]                         │ │
│  └─────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────┘
         │ (Click "Create Account")
         ↓
┌──────────────────────────────────────────────────────┐
│              Success Message                         │
│  ✅ Account created successfully!                    │
│  Redirecting to login...                            │
└──────────────────────────────────────────────────────┘
         │
         ↓
┌──────────────────────────────────────────────────────┐
│              Login Page (/login)                     │
│  (User fills in their new credentials)              │
└──────────────────────────────────────────────────────┘
         │
         ↓
┌──────────────────────────────────────────────────────┐
│              Success Message                         │
│  ✅ Welcome back, [username]!                        │
│  Redirecting...                                     │
└──────────────────────────────────────────────────────┘
         │
         ↓
┌──────────────────────────────────────────────────────┐
│              Help Request Form (/request-help)      │
│  ┌─────────────────────────────────────────────────┐ │
│  │ Name: [________]                               │ │
│  │ Phone: [________]                              │ │
│  │ Location: [________]                           │ │
│  │ Help Type: [Select ▼]                          │ │
│  │ Description: [________]                        │ │
│  │              [Submit Request]                  │ │
│  └─────────────────────────────────────────────────┘ │
│  👤 john_user | Logout (navbar)                    │
└──────────────────────────────────────────────────────┘
```

---

### Flow 2: Volunteer Journey

```
┌──────────────────────────────────────────────────────┐
│              Homepage (/)                            │
│  [I Need Help]  [Become a Volunteer]                │
└──────────────────────────────────────────────────────┘
         │ (Click "Become a Volunteer")
         ↓
┌──────────────────────────────────────────────────────┐
│              Smart Redirect: /go-volunteer          │
│  "You're not logged in!"                            │
│  Redirecting to login...                            │
└──────────────────────────────────────────────────────┘
         │
         ↓
┌──────────────────────────────────────────────────────┐
│              Signup Page (/signup)                  │
│  Username: jane_volunteer                           │
│  Email: jane@example.com                            │
│  Password: [hidden]                                 │
│  Role: [Volunteer ▼]    ← Important!               │
└──────────────────────────────────────────────────────┘
         │
         ↓
┌──────────────────────────────────────────────────────┐
│              Login Page (/login)                     │
│  (User logs in with volunteer credentials)          │
└──────────────────────────────────────────────────────┘
         │
         ↓
┌──────────────────────────────────────────────────────┐
│              Success Message                         │
│  ✅ Welcome back, jane_volunteer!                    │
│  Redirecting to dashboard...                        │
└──────────────────────────────────────────────────────┘
         │
         ↓
┌──────────────────────────────────────────────────────┐
│              Dashboard (/dashboard)                 │
│  ┌─────────────────────────────────────────────────┐ │
│  │  Filter: [Status ▼]  [Type ▼]  [Search ___]   │ │
│  ├─────────────────────────────────────────────────┤ │
│  │ PENDING REQUESTS:                              │ │
│  │ ┌─────────────────────────────────────────────┐ │
│  │ │ #1: Grocery Shopping (Urgent)               │ │
│  │ │ [Accept] [View Details]                     │ │
│  │ ├─────────────────────────────────────────────┤ │
│  │ │ #2: Medicine Pickup (Normal)                │ │
│  │ │ [Accept] [View Details]                     │ │
│  │ └─────────────────────────────────────────────┘ │
│  │                                                 │ │
│  │ ACCEPTED BY ME:                                 │ │
│  │ ┌─────────────────────────────────────────────┐ │
│  │ │ #3: Doctor's Appointment                    │ │
│  │ │ [Complete] [Cancel]                         │ │
│  │ └─────────────────────────────────────────────┘ │
│  └─────────────────────────────────────────────────┘ │
│  Home | Get Help | Volunteer | Dashboard ← NEW!    │
│  👤 jane_volunteer | Logout (navbar)               │
└──────────────────────────────────────────────────────┘
```

---

### Flow 3: Regular User Tries to Access Dashboard

```
┌──────────────────────────────────────────────────────┐
│              Homepage (/)                            │
│  [I Need Help]  [Become a Volunteer]                │
│  👤 john_user | Logout (navbar)                    │
└──────────────────────────────────────────────────────┘
         │ (Click "Become a Volunteer")
         ↓
┌──────────────────────────────────────────────────────┐
│              Smart Redirect: /go-volunteer          │
│  Checking:                                          │
│  ✓ Is user logged in? YES                           │
│  ✗ Is user a volunteer? NO                          │
│  "Only volunteers can access the dashboard."        │
└──────────────────────────────────────────────────────┘
         │
         ↓
┌──────────────────────────────────────────────────────┐
│              Back to Homepage (/)                    │
│  ❌ ERROR: "Only volunteers can access..."           │
│  [I Need Help]  [Become a Volunteer]                │
│  👤 john_user | Logout (navbar)                    │
└──────────────────────────────────────────────────────┘
```

---

## 📊 State Diagram

```
                    ┌─────────────────────┐
                    │   NOT LOGGED IN     │
                    │  No session vars    │
                    └──────────┬──────────┘
                               │
                ┌──────────────┼──────────────┐
                │                             │
         (Sign Up)                    (Log In)
                │                             │
                ↓                             ↓
         ┌────────────────┐           ┌──────────────┐
         │ SIGNUP PAGE    │           │ LOGIN PAGE   │
         │ (user submits) │           │ (user logs)  │
         │ ROLE = USER    │           │              │
         └────────┬───────┘           └──────┬───────┘
                  │                           │
                  └───────────┬───────────────┘
                              │
                              ↓
                      ┌───────────────┐
                      │ LOGGED IN     │
                      │ session set   │
                      └───────┬───────┘
                              │
                ┌─────────────┴─────────────┐
                │                           │
          ROLE = 'user'            ROLE = 'volunteer'
                │                           │
                ↓                           ↓
          ┌──────────────┐         ┌──────────────┐
          │ CAN ACCESS:  │         │ CAN ACCESS:  │
          │ /request-help│         │ /request-help│
          │ /about       │         │ /dashboard   │
          │ /contact     │         │ /about       │
          │ /track       │         │ /contact     │
          └──────────────┘         └──────────────┘
                │                           │
                └──────────────┬────────────┘
                               │
                          (Logout)
                               │
                               ↓
                    ┌─────────────────────┐
                    │   NOT LOGGED IN     │
                    │  Session cleared    │
                    └─────────────────────┘
```

---

## 🔐 Decorator Protection Levels

```
┌────────────────────────────────────────────────┐
│                 Request comes in               │
└──────────────────────┬─────────────────────────┘
                       │
                       ↓
        ┌──────────────────────────┐
        │  No Decorator (@app.route)
        │  ✓ Anyone can access     │
        │  Examples: /, /about,    │
        │  /contact, /track, /login│
        └──────────────────────────┘
        
        ┌──────────────────────────┐
        │  @login_required         │
        │  ✓ Any logged-in user    │
        │  ✗ Not logged in? → /login
        │  Examples:               │
        │  /request-help, /api/*   │
        └──────────────────────────┘
        
        ┌──────────────────────────┐
        │  @volunteer_required     │
        │  ✓ Logged-in volunteers  │
        │  ✗ Not logged in? → /login
        │  ✗ Not volunteer? → /    │
        │  Examples:               │
        │  /dashboard,             │
        │  /accept-request/*,      │
        │  /complete-request/*,    │
        │  /cancel-request/*       │
        └──────────────────────────┘
```

---

## 📱 Navbar States

### State 1: Not Logged In

```
┌─────────────────────────────────────────────────────────┐
│  🤝 LocalHelper  Home | Get Help | Volunteer | ... │
│                                                   Login │
│                                                Sign Up →│
└─────────────────────────────────────────────────────────┘
```

### State 2: Logged In as User (role='user')

```
┌─────────────────────────────────────────────────────────┐
│  🤝 LocalHelper  Home | Get Help | Volunteer | ... │
│                                          👤 john_user  │
│                                              Logout  ← │
└─────────────────────────────────────────────────────────┘
Note: NO Dashboard link visible
```

### State 3: Logged In as Volunteer (role='volunteer')

```
┌─────────────────────────────────────────────────────────┐
│  🤝 LocalHelper  Home | Get Help | Volunteer │ ↓
│                         Dashboard | Track | ... │
│                                   👤 jane_volunteer  │
│                                       Logout      ← │
└─────────────────────────────────────────────────────────┘
Note: Dashboard link IS visible
```

---

## 🔄 Button Behavior Matrix

| Scenario | "I Need Help" Button | "Become Volunteer" Button |
|----------|----------------------|--------------------------|
| Not logged in | → `/go-request-help` → Shows "login" message → `/login` | → `/go-volunteer` → Shows "login" message → `/login` |
| Logged in as User | → `/go-request-help` → `/request-help` form | → `/go-volunteer` → Shows "volunteers only" error → `/` |
| Logged in as Volunteer | → `/go-request-help` → `/request-help` form | → `/go-volunteer` → `/dashboard` |

---

## 🎯 Route Access Control Matrix

| Route | No Auth | User Role | Volunteer Role |
|-------|---------|-----------|-----------------|
| `/` (home) | ✅ Access | ✅ Access | ✅ Access |
| `/signup` | ✅ Access | ✅ Access | ✅ Access |
| `/login` | ✅ Access | ✅ Access | ✅ Access |
| `/logout` | ✅ Access | ✅ Access | ✅ Access |
| `/go-request-help` | → `/login` | ✅ Access | ✅ Access |
| `/go-volunteer` | → `/login` | → `/` + error | ✅ Access |
| `/request-help` | ❌ Forbidden | ✅ Access | ✅ Access |
| `/dashboard` | ❌ Forbidden | ❌ Forbidden | ✅ Access |
| `/accept-request/*` | ❌ Forbidden | ❌ Forbidden | ✅ Access |
| `/complete-request/*` | ❌ Forbidden | ❌ Forbidden | ✅ Access |
| `/cancel-request/*` | ❌ Forbidden | ❌ Forbidden | ✅ Access |
| `/about` | ✅ Access | ✅ Access | ✅ Access |
| `/contact` | ✅ Access | ✅ Access | ✅ Access |
| `/track` | ✅ Access | ✅ Access | ✅ Access |

✅ = Full Access
❌ = Blocked / Error Message
→ = Redirected To

---

## 💾 Session Data Over Time

### At Signup
```python
session = {}
# User creates account, data stored in database
```

### After Login
```python
session = {
    'user_id': 1,
    'username': 'john_user',
    'email': 'john@example.com',
    'role': 'user',
    # Plus any Flask internal session data
}
```

### After Logout
```python
session = {}
# All data cleared
```

---

## 🌐 Route Organization

```
Authentication Routes:
├── GET  /signup       → Show signup form
├── POST /signup       → Process signup, save to DB
├── GET  /login        → Show login form
├── POST /login        → Process login, set session
└── GET  /logout       → Clear session, redirect

Smart Redirect Routes:
├── GET  /go-request-help  → Check session, redirect appropriately
└── GET  /go-volunteer     → Check session + role, redirect appropriately

Protected Routes (User):
├── GET  /request-help     → Show help request form (@login_required)
└── POST /request-help     → Save help request (@login_required)

Protected Routes (Volunteer):
├── GET  /dashboard              → Show volunteer dashboard (@volunteer_required)
├── POST /accept-request/<id>    → Accept request (@volunteer_required)
├── POST /complete-request/<id>  → Mark complete (@volunteer_required)
└── POST /cancel-request/<id>    → Cancel request (@volunteer_required)

Public Routes (No Auth Needed):
├── GET  /          → Homepage
├── GET  /about     → About page
├── GET  /contact   → Contact page
├── POST /contact   → Submit contact form
├── GET  /track     → Track request page
└── POST /track     → Search request
```

---

## 📊 Database Tables

```
┌─────────────────────────────────────────────┐
│             USERS TABLE                     │
├──────────┬────────────┬────────────────────┤
│ id       │ INT        │ PRIMARY KEY        │
│ username │ TEXT       │ UNIQUE, NOT NULL   │
│ email    │ TEXT       │ UNIQUE, NOT NULL   │
│ password_hash │ TEXT  │ NOT NULL (hashed)  │
│ role     │ TEXT       │ 'user' or 'vol'    │
│ created_at    │ TEXT  │ Timestamp          │
│ updated_at    │ TEXT  │ Timestamp          │
└──────────┴────────────┴────────────────────┘

┌─────────────────────────────────────────────┐
│          HELP_REQUESTS TABLE                │
├──────────┬────────────┬────────────────────┤
│ id       │ INT        │ PRIMARY KEY        │
│ name     │ TEXT       │ NOT NULL           │
│ phone    │ TEXT       │ NOT NULL           │
│ location │ TEXT       │ NOT NULL           │
│ help_type│ TEXT       │ NOT NULL           │
│ urgency  │ TEXT       │ pending/urgent     │
│ status   │ TEXT       │ pending/accepted/  │
│          │            │ completed          │
│ volunteer_name│ TEXT  │ Who accepted it    │
└──────────┴────────────┴────────────────────┘
```

---

## 🔐 Password Hashing Flow

```
User enters password at signup: "password123"
         ↓
Flask routes to /signup POST
         ↓
app.py calls: db.register_user(username, email, "password123", role)
         ↓
database.py calls: password_hash = generate_password_hash("password123")
         ↓
Result: "pbkdf2:sha256$260000$..."  (200+ character hash)
         ↓
Stored in database: users.password_hash
         ↓
[User returns next day]
         ↓
User enters: "password123"
         ↓
app.py calls: db.login_user(email, "password123")
         ↓
database.py calls: check_password_hash(stored_hash, "password123")
         ↓
Result: True (password matches!)
         ↓
Set session variables and redirect
```

---

## 🎓 Summary

This visual guide shows:

1. **Complete user flows** - How users navigate through the system
2. **State diagrams** - How the system changes based on login status
3. **Decorator protection levels** - How routes are secured
4. **Navbar variations** - What users see based on their role
5. **Button behavior matrix** - What happens when buttons are clicked
6. **Route access control** - Who can access which routes
7. **Database schema** - How data is organized
8. **Password hashing flow** - How passwords are secured

---

**For detailed implementation details, see AUTHENTICATION_FLOW.md**
**For testing procedures, see TESTING_GUIDE.md**
**For quick lookup, see QUICK_REFERENCE.md**

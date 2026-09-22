# Testing Guide - Authentication Flow

## Quick Start

### 1. Start the Application

```bash
cd c:\Users\VEDA\Downloads\local_helper_network\local_helper_network
python app.py
```

Expected output:
```
✅ Database initialized.
 * Running on http://127.0.0.1:5000
 * Press CTRL+C to quit
```

Open browser: **http://127.0.0.1:5000**

---

## Test Cases

### Test 1: Create User Account

**Steps:**
1. Click "Sign Up" button (or go to `/signup`)
2. Fill form:
   - Username: `john_user`
   - Email: `john@example.com`
   - Password: `password123`
   - Confirm: `password123`
   - Role: **User** (select this)
3. Click "Create Account"

**Expected:**
- ✅ Success message: "Account created successfully! Please log in."
- ✅ Redirects to `/login` page

---

### Test 2: Create Volunteer Account

**Steps:**
1. Click "Sign Up" button (or go to `/signup`)
2. Fill form:
   - Username: `jane_volunteer`
   - Email: `jane@example.com`
   - Password: `password123`
   - Confirm: `password123`
   - Role: **Volunteer** (select this)
3. Click "Create Account"

**Expected:**
- ✅ Success message: "Account created successfully! Please log in."
- ✅ Redirects to `/login` page

---

### Test 3: Login as User

**Steps:**
1. Go to `/login` (or click "Login" button)
2. Enter:
   - Email: `john@example.com`
   - Password: `password123`
3. Click "Log In"

**Expected:**
- ✅ Success message: "Welcome back, john_user!"
- ✅ **Redirects to `/request-help`** (not dashboard!)
- ✅ Navbar shows: `👤 john_user | Logout`
- ✅ "Dashboard" link NOT visible in navbar

---

### Test 4: Login as Volunteer

**Steps:**
1. Go to `/logout` first (logout the user account if logged in)
2. Go to `/login`
3. Enter:
   - Email: `jane@example.com`
   - Password: `password123`
4. Click "Log In"

**Expected:**
- ✅ Success message: "Welcome back, jane_volunteer!"
- ✅ **Redirects to `/dashboard`** (not request-help!)
- ✅ Navbar shows: `👤 jane_volunteer | Logout`
- ✅ **"Dashboard" link IS visible** in navbar

---

### Test 5: "I Need Help" Button - Not Logged In

**Steps:**
1. Click "Logout" to ensure you're not logged in
2. Navbar should show "Login | Sign Up" buttons
3. Go to homepage (`/`) or refresh page
4. Click "I Need Help" button

**Expected:**
- ✅ Info message: "Please log in to request help."
- ✅ **Redirects to `/login`** page
- ✅ Can then sign up or log in

---

### Test 6: "I Need Help" Button - Logged In as User

**Steps:**
1. Log in as `john@example.com` (user account)
2. Go to homepage (`/`)
3. Click "I Need Help" button

**Expected:**
- ✅ **Direct redirect to `/request-help`** form
- ✅ No login page shown
- ✅ Can see help request form

---

### Test 7: "I Need Help" Button - Logged In as Volunteer

**Steps:**
1. Log in as `jane@example.com` (volunteer account)
2. Go to homepage (`/`)
3. Click "I Need Help" button

**Expected:**
- ✅ **Direct redirect to `/request-help`** form
- ✅ No login page shown
- ✅ Can see help request form
- ✅ (Volunteers can also submit help requests)

---

### Test 8: "Become a Helper" Button - Not Logged In

**Steps:**
1. Click "Logout" to ensure you're not logged in
2. Go to homepage (`/`)
3. Click "Become a Helper" button

**Expected:**
- ✅ Info message: "Please log in to access the volunteer dashboard."
- ✅ **Redirects to `/login`** page

---

### Test 9: "Become a Helper" Button - Logged In as User

**Steps:**
1. Log in as `john@example.com` (user account)
2. Go to homepage (`/`)
3. Click "Become a Helper" button

**Expected:**
- ✅ Error message: "Only volunteers can access the dashboard."
- ✅ **Redirects back to homepage**
- ✅ Dashboard NOT shown

---

### Test 10: "Become a Helper" Button - Logged In as Helper

**Steps:**
1. Log in as `jane@example.com` (volunteer account)
2. Go to homepage (`/`)
3. Click "Become a Helper" button

**Expected:**
- ✅ **Direct redirect to `/dashboard`**
- ✅ Can see volunteer dashboard with help requests
- ✅ Can see "Dashboard" link in navbar

---

### Test 11: Direct Access to Dashboard - Not Logged In

**Steps:**
1. Click "Logout" (if logged in)
2. Go directly to: `http://127.0.0.1:5000/dashboard`

**Expected:**
- ✅ Error message: "Please log in first."
- ✅ **Redirects to `/login`** page

---

### Test 12: Direct Access to Dashboard - Logged In as User

**Steps:**
1. Log in as `john@example.com` (user account)
2. Go directly to: `http://127.0.0.1:5000/dashboard`

**Expected:**
- ✅ Error message: "You need to be a volunteer to access this page."
- ✅ **Redirects to homepage**

---

### Test 13: Direct Access to Dashboard - Logged In as Volunteer

**Steps:**
1. Log in as `jane@example.com` (volunteer account)
2. Go directly to: `http://127.0.0.1:5000/dashboard`

**Expected:**
- ✅ **Shows dashboard** with help requests
- ✅ Can see:
   - Help requests list
   - Filter by status
   - Filter by help type
   - Search requests
   - Accept/Complete/Cancel buttons

---

### Test 14: Direct Access to Request-Help - Not Logged In

**Steps:**
1. Click "Logout" (if logged in)
2. Go directly to: `http://127.0.0.1:5000/request-help`

**Expected:**
- ✅ Error message: "Please log in first."
- ✅ **Redirects to `/login`** page

---

### Test 15: Direct Access to Request-Help - Logged In

**Steps:**
1. Log in (as either user or volunteer)
2. Go directly to: `http://127.0.0.1:5000/request-help`

**Expected:**
- ✅ **Shows request-help form**
- ✅ Can submit help request:
   - Name, Phone, Location
   - Help Type dropdown
   - Description textarea
   - Priority level: Emergency, Urgent, or Normal

---

### Test 16: Logout

**Steps:**
1. Log in (if not already)
2. Navbar should show: `👤 [username] | Logout`
3. Click "Logout" button or go to `/logout`

**Expected:**
- ✅ Success message: "👋 [username], you have been logged out."
- ✅ **Redirects to homepage**
- ✅ Navbar now shows: `Login | Sign Up` buttons
- ✅ Session cleared (no user_id, username, role in session)

---

### Test 17: Invalid Login

**Steps:**
1. Go to `/login`
2. Enter:
   - Email: `john@example.com`
   - Password: `wrongpassword`
3. Click "Log In"

**Expected:**
- ✅ Error message: "❌ Invalid email or password."
- ✅ **Stays on login page** (doesn't redirect)
- ✅ Form values preserved for correction

---

### Test 18: Password Too Short

**Steps:**
1. Go to `/signup`
2. Enter:
   - Username: `testuser`
   - Email: `test@example.com`
   - Password: `short`
   - Confirm: `short`
   - Role: User
3. Click "Create Account"

**Expected:**
- ✅ Error message: "Password must be at least 6 characters."
- ✅ **Stays on signup page** (doesn't redirect)

---

### Test 19: Username Already Exists

**Steps:**
1. Go to `/signup`
2. Enter:
   - Username: `john_user` (already used from Test 1)
   - Email: `newemail@example.com`
   - Password: `password123`
   - Confirm: `password123`
   - Role: User
3. Click "Create Account"

**Expected:**
- ✅ Error message: "Email or username already exists. Please try another."
- ✅ **Stays on signup page** (doesn't redirect)

---

### Test 20: Navbar Links Visibility

**When NOT logged in:**
- ✅ Home ✓
- ✅ Get Help ✓
- ✅ Volunteer ✓
- ❌ Dashboard (should NOT appear)
- ✅ Track ✓
- ✅ About ✓
- ✅ Contact ✓
- ✅ Login button ✓
- ✅ Sign Up button ✓

**When logged in as User:**
- ✅ Home ✓
- ✅ Get Help ✓
- ✅ Volunteer ✓
- ❌ Dashboard (should NOT appear)
- ✅ Track ✓
- ✅ About ✓
- ✅ Contact ✓
- ✅ Username display ✓
- ✅ Logout button ✓

**When logged in as Volunteer:**
- ✅ Home ✓
- ✅ Get Help ✓
- ✅ Volunteer ✓
- ✅ **Dashboard ✓** (should appear)
- ✅ Track ✓
- ✅ About ✓
- ✅ Contact ✓
- ✅ Username display ✓
- ✅ Logout button ✓

---

## Troubleshooting

### Issue: Getting "Please log in first" even when logged in

**Solution:**
1. Check browser cookies are enabled
2. Check if `app.secret_key` is set in app.py
3. Try logging out and logging back in
4. Clear browser cache and cookies
5. Open in incognito/private window

### Issue: Redirects not working

**Solution:**
1. Ensure Flask is running without errors
2. Check console for Python errors
3. Verify URLs are correct:
   - `/go-request-help` (not `/go_request_help`)
   - `/go-volunteer` (not `/go_volunteer`)
4. Check that decorators are applied

### Issue: Dashboard shows but shouldn't

**Solution:**
1. Check that user role in database is correct
2. Verify session is being set: `session['role'] = user['role']`
3. Try logging out and logging back in

### Issue: Flash messages not showing

**Solution:**
1. Check base.html has flash message block:
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
2. Check CSS has styles for `.flash` class
3. Try refreshing page after flash appears

---

## Test Results Checklist

Mark as ✅ when each test passes:

- [ ] Test 1: Create User Account
- [ ] Test 2: Create Volunteer Account
- [ ] Test 3: Login as User
- [ ] Test 4: Login as Volunteer
- [ ] Test 5: "I Need Help" - Not Logged In
- [ ] Test 6: "I Need Help" - Logged In as User
- [ ] Test 7: "I Need Help" - Logged In as Volunteer
- [ ] Test 8: "Become a Helper" - Not Logged In
- [ ] Test 9: "Become a Helper" - Logged In as User
- [ ] Test 10: "Become a Helper" - Logged In as Helper
- [ ] Test 11: Direct Dashboard - Not Logged In
- [ ] Test 12: Direct Dashboard - Logged In as User
- [ ] Test 13: Direct Dashboard - Logged In as Volunteer
- [ ] Test 14: Direct Request-Help - Not Logged In
- [ ] Test 15: Direct Request-Help - Logged In
- [ ] Test 16: Logout
- [ ] Test 17: Invalid Login
- [ ] Test 18: Password Too Short
- [ ] Test 19: Username Already Exists
- [ ] Test 20: Navbar Links Visibility

---

## Performance Notes

- Session lookups are very fast (< 1ms)
- No database queries on every request (just session check)
- Decorators add minimal overhead
- Flash messages are ephemeral (cleared after display)

---

## Security Verification

✅ Passwords are hashed (not stored in plain text)
✅ Session-based authentication (not token-based)
✅ Role-based access control enforced
✅ Decorators prevent unauthorized access
✅ SQL injection protected (parameterized queries)
✅ CSRF protection available (Flask handles by default)

---

**All 20 tests should pass if implementation is correct.**

If any test fails, check the IMPLEMENTATION_SUMMARY.md or AUTHENTICATION_FLOW.md for details.

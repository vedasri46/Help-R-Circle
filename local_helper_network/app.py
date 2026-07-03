"""
Help R Circle - Main Flask Application
============================================
This is the core server file. It handles all routes, form submissions,
and connects the frontend to the database.
"""

from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
from database import Database
from datetime import datetime
import os
from functools import wraps
print("APP FILE LOADED")
# ── App Setup ────────────────────────────────────────────────────────────────
app = Flask(__name__)
app.secret_key = "lhn_secret_key_2024"   # Change this in production!
db = Database()


def get_status_label(status):
    labels = {
        'pending': 'Request Submitted',
        'awaiting_volunteer': 'Request Submitted',
        'volunteer_assigned': 'Accepted',
        'volunteer_on_way': 'Volunteer On The Way',
        'volunteer_near_location': 'Volunteer Near Location',
        'volunteer_reached_location': 'Volunteer Reached Location',
        'completed': 'Completed',
        'cancelled': 'Request Cancelled',
        'volunteer_unavailable': 'Volunteer Unavailable',
        'reassigned_volunteer': 'Reassigned Volunteer',
        'expired_request': 'Expired Request',
    }
    return labels.get(status, (status or 'pending').replace('_', ' ').title())


def get_status_class(status):
    classes = {
        'pending': 'secondary',
        'awaiting_volunteer': 'secondary',
        'volunteer_assigned': 'primary',
        'volunteer_on_way': 'warning',
        'volunteer_near_location': 'info',
        'volunteer_reached_location': 'info',
        'completed': 'success',
        'cancelled': 'danger',
        'volunteer_unavailable': 'danger',
        'reassigned_volunteer': 'warning',
        'expired_request': 'secondary',
    }
    return classes.get(status, 'secondary')


# ── Login Required Decorator ──────────────────────────────────────────────────
def login_required(f):
    """Decorator to protect routes that require login."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash("Please log in first.", "error")
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function
# ── Volunteer Required Decorator ──────────────────────────────────────────
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


# ── User Required Decorator ─────────────────────────────────────────────────
def user_required(f):
    """Decorator to protect routes that require user role."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash("Please log in first.", "error")
            return redirect(url_for('login'))
        if session.get('role') != 'user':
            flash("Only requesters can access this page.", "error")
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated_function

# ── Admin Required Decorator ──────────────────────────────────────────────────
def admin_required(f):
    """Decorator to protect routes that require admin role."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash("Please log in first.", "error")
            return redirect(url_for('login'))
        if session.get('role') != 'admin':
            flash("Only administrators can access this page.", "error")
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated_function
# ── Home Page ─────────────────────────────────────────────────────────────────
@app.route("/")
def index():
    """Render the landing page with stats."""
    stats = db.get_stats()
    return render_template("index.html", stats=stats)

# ── Signup ────────────────────────────────────────────────────────────────────
@app.route("/signup", methods=["GET", "POST"])
def signup():
    """Show signup form (GET) or register a new user (POST)."""
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        email    = request.form.get("email", "").strip()
        password = request.form.get("password", "").strip()
        confirm  = request.form.get("confirm_password", "").strip()
        role     = request.form.get("role", "user").strip()

        # ── Validation ────────────────────────────────────────────────────────
        errors = []
        if not username:
            errors.append("Username is required.")
        elif len(username) < 3:
            errors.append("Username must be at least 3 characters.")
        
        if not email:
            errors.append("Email is required.")
        elif "@" not in email:
            errors.append("Please enter a valid email address.")
        
        if not password:
            errors.append("Password is required.")
        elif len(password) < 6:
            errors.append("Password must be at least 6 characters.")
        
        if password != confirm:
            errors.append("Passwords do not match.")
        
        if role not in ["user", "volunteer"]:
            errors.append("Invalid role selected.")

        if errors:
            for err in errors:
                flash(err, "error")
            return render_template("signup.html", form_data=request.form)

        # ── Register user ─────────────────────────────────────────────────────
        user_id = db.register_user(username, email, password, role)
        if user_id:
            # If registering as volunteer, auto-create basic volunteer profile
            if role == "volunteer":
                db.add_volunteer(
                    name=username,
                    phone="",
                    email=email,
                    location="",
                    skills="",
                    availability="",
                    about="",
                    user_id=user_id
                )
            flash(f"✅ Account created successfully! Please log in.", "success")
            return redirect(url_for("login"))
        else:
            flash("Email or username already exists. Please try another.", "error")
            return render_template("signup.html", form_data=request.form)

    return render_template("signup.html", form_data={})

# ── Login ─────────────────────────────────────────────────────────────────────
@app.route("/login", methods=["GET", "POST"])
def login():
    """Show login form (GET) or authenticate user (POST)."""
    if request.method == "POST":
        email    = request.form.get("email", "").strip()
        password = request.form.get("password", "").strip()

        # ── Validation ────────────────────────────────────────────────────────
        if not email or not password:
            flash("Email and password are required.", "error")
            return render_template("login.html", form_data=request.form)

        # ── Authenticate ──────────────────────────────────────────────────────
        user = db.login_user(email, password)
        if user:
            session['user_id'] = user['id']
            session['username'] = user['username']
            session['email'] = user['email']
            session['role'] = user['role']
            
            flash(f"✅ Welcome back, {user['username']}!", "success")
            
            # Redirect based on role
            if user['role'] == 'admin':
                return redirect(url_for("admin_dashboard"))
            elif user['role'] == 'volunteer':
                # Run repair to ensure volunteer profiles exist (helps older accounts)
                app.logger.info("Login (volunteer): user_id=%s username=%s", user['id'], user['username'])
                try:
                    created = db.repair_missing_volunteers()
                    app.logger.info("repair_missing_volunteers result: %s", str(created))
                except Exception as e:
                    app.logger.exception("repair_missing_volunteers failed: %s", e)

                # Ensure current user's volunteer row exists; create if still missing
                try:
                    vol = db.get_volunteer_by_user_id(user['id'])
                    app.logger.info("Volunteer lookup post-repair: %s", str(vol))
                    if not vol:
                        vid = db.add_volunteer(
                            name=user['username'], phone="", email=user.get('email',''),
                            location="", skills="", availability="", about="", user_id=user['id']
                        )
                        app.logger.info("Created volunteer record id %s for user_id %s", str(vid), user['id'])
                except Exception:
                    app.logger.exception("Failed ensuring volunteer profile for user_id=%s", user['id'])

                return redirect(url_for("dashboard"))
            else:
                return redirect(url_for("user_dashboard"))
        else:
            flash("❌ Invalid email or password.", "error")
            return render_template("login.html", form_data=request.form)

    return render_template("login.html", form_data={})

# ── Admin Login ───────────────────────────────────────────────────────────────
@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    """Show admin login form or authenticate an administrator."""
    if request.method == "POST":
        email    = request.form.get("email", "").strip()
        password = request.form.get("password", "").strip()

        if not email or not password:
            flash("Email and password are required.", "error")
            return render_template("admin_login.html", form_data=request.form)

        user = db.login_user(email, password)
        if user and user.get('role') == 'admin':
            session['user_id'] = user['id']
            session['username'] = user['username']
            session['email'] = user['email']
            session['role'] = user['role']
            flash(f"✅ Welcome back, {user['username']}!", "success")
            return redirect(url_for("admin_dashboard"))

        if user:
            flash("Use the regular login page for requester or volunteer accounts.", "error")
        else:
            flash("❌ Invalid email or password.", "error")
        return render_template("admin_login.html", form_data=request.form)

    return render_template("admin_login.html", form_data={})

# ── Logout ────────────────────────────────────────────────────────────────────
@app.route("/logout")
def logout():
    """Clear user session and logout."""
    username = session.get('username', 'User')
    session.clear()
    flash(f"👋 {username}, you have been logged out.", "success")
    return redirect(url_for("index"))
# ── Session-Aware Redirect Routes ─────────────────────────────────────────────
@app.route("/go-request-help")
def go_request_help():
    """Redirect to login if not logged in, else go to request-help form."""
    if 'user_id' not in session:
        flash("Please log in to request help.", "info")
        return redirect(url_for('login'))
    return redirect(url_for('request_help'))

@app.route("/go-volunteer")
def go_volunteer():
    """Redirect to login if not logged in, else go to volunteer dashboard."""
    if 'user_id' not in session:
        flash("Please log in to access the volunteer dashboard.", "info")
        return redirect(url_for('login'))
    
    # Check if user is a volunteer
    if session.get('role') != 'volunteer':
        flash("Only volunteers can access the dashboard.", "error")
        return redirect(url_for('index'))
    
    return redirect(url_for('dashboard'))
# ── Request Help ──────────────────────────────────────────────────────────────
@app.route("/request-help", methods=["GET", "POST"])
@login_required
def request_help():
    """Show the help-request form (GET) or save a new request (POST)."""
    # Admins cannot submit help requests
    if session.get('role') == 'admin':
        flash("Administrators cannot submit help requests. Access denied.", "error")
        return redirect(url_for('admin_dashboard'))
    
    # Users and Volunteers can submit help requests
    if request.method == "POST":
        name        = request.form.get("name", "").strip()
        phone       = request.form.get("phone", "").strip()
        location    = request.form.get("location", "").strip()
        help_type   = request.form.get("help_type", "").strip()
        description = request.form.get("description", "").strip()
        urgency     = request.form.get("urgency", "normal").strip()
        request_latitude = request.form.get("request_latitude", "").strip()
        request_longitude = request.form.get("request_longitude", "").strip()
        try:
            request_latitude = float(request_latitude) if request_latitude else None
            request_longitude = float(request_longitude) if request_longitude else None
        except (TypeError, ValueError):
            request_latitude = None
            request_longitude = None

        # ── Validation ───────────────────────────────────────────────────────
        errors = []
        if not name:            errors.append("Name is required.")
        if not phone:           errors.append("Phone number is required.")
        if len(phone) < 10:     errors.append("Enter a valid phone number.")
        if not location:        errors.append("Location is required.")
        if not help_type:       errors.append("Please select a help type.")
        if not description:     errors.append("Please describe what you need.")

        if errors:
            for err in errors:
                flash(err, "error")
            return render_template("request_help.html",
                                   form_data=request.form)

        # ── Save to DB ───────────────────────────────────────────────────────
        request_id = db.add_help_request(
            name=name, phone=phone, location=location,
            help_type=help_type, description=description, urgency=urgency,
            user_id=session.get('user_id'),
            request_latitude=request_latitude,
            request_longitude=request_longitude,
        )
        flash(f"✅ Help request submitted! Your Request ID is #{request_id}. "
              "A volunteer will contact you soon.", "success")
        return redirect(url_for("request_help"))

    return render_template("request_help.html", form_data={})

# ── Volunteer Registration ─────────────────────────────────────────────────────
@app.route("/volunteer", methods=["GET", "POST"])
def volunteer():
    """Show volunteer sign-up form (GET) or save a new volunteer (POST)."""
    if request.method == "POST":
        name         = request.form.get("name", "").strip()
        phone        = request.form.get("phone", "").strip()
        email        = request.form.get("email", "").strip()
        location     = request.form.get("location", "").strip()
        skills       = request.form.getlist("skills")          # multi-select checkboxes
        availability = request.form.get("availability", "").strip()
        about        = request.form.get("about", "").strip()

        # ── Validation ───────────────────────────────────────────────────────
        errors = []
        if not name:         errors.append("Name is required.")
        if not phone:        errors.append("Phone number is required.")
        if len(phone) < 10:  errors.append("Enter a valid phone number.")
        if not location:     errors.append("Location / area is required.")
        if not skills:       errors.append("Please select at least one skill.")
        if not availability: errors.append("Please enter your availability.")

        if errors:
            for err in errors:
                flash(err, "error")
            return render_template("volunteer.html", form_data=request.form,
                                   selected_skills=skills)

        # ── Save to DB ───────────────────────────────────────────────────────
        vol_id = db.add_volunteer(
            name=name, phone=phone, email=email, location=location,
            skills=", ".join(skills), availability=availability, about=about
        )
        flash(f"🎉 Thank you, {name}! You are now registered as a volunteer "
              f"(ID #{vol_id}). We will reach out soon.", "success")
        return redirect(url_for("volunteer"))

    return render_template("volunteer.html", form_data={}, selected_skills=[])

# ── Volunteer Dashboard ────────────────────────────────────────────────────────
@app.route("/dashboard")
@volunteer_required
def dashboard():
    """Show all pending/accepted help requests for volunteers to act on, plus their own requests."""
    status_filter   = request.args.get("status", "all")
    type_filter     = request.args.get("help_type", "all")
    search_query    = request.args.get("q", "").strip()

    # Get requests available for volunteers to help with
    requests = db.get_requests(
        status=status_filter,
        help_type=type_filter,
        search=search_query
    )
    
    # Get this volunteer's own submitted requests
    volunteer_user_id = session.get('user_id')
    my_requests = db.get_requests_by_user(volunteer_user_id)
    
    # Calculate volunteer's request stats
    my_request_stats = {
        'total_requests': len(my_requests),
        'pending': sum(1 for r in my_requests if r['status'] == 'pending'),
        'accepted': sum(1 for r in my_requests if r['status'] == 'accepted'),
        'completed': sum(1 for r in my_requests if r['status'] == 'completed'),
    }

    volunteer = db.get_volunteer_by_user_id(volunteer_user_id)
    volunteer_name = volunteer.get('name') if volunteer else session.get('username')
    volunteer_activity = db.get_volunteer_activity_stats(volunteer_name)
    overview_stats = {
        'pending': db.get_stats().get('pending', 0),
        'accepted': volunteer_activity.get('accepted_requests', 0),
        'active': volunteer_activity.get('active_requests', 0),
        'completed': volunteer_activity.get('completed_requests', 0),
    }
    notifications = []

    return render_template("dashboard.html",
                           requests=requests,
                           my_requests=my_requests,
                           my_request_stats=my_request_stats,
                           stats=overview_stats,
                           notifications=notifications,
                           status_filter=status_filter,
                           type_filter=type_filter,
                           search_query=search_query)


@app.route("/dashboard/completed-requests")
@volunteer_required
def completed_requests():
    """Show completed help requests assigned to the logged-in volunteer."""
    volunteer_user_id = session.get('user_id')
    volunteer = db.get_volunteer_by_user_id(volunteer_user_id)
    if not volunteer:
        flash("Unable to locate your volunteer profile. Please contact support.", "error")
        return redirect(url_for('dashboard'))

    completed_requests = db.get_completed_requests_by_volunteer(volunteer['id'])
    return render_template("completed_requests.html",
                           requests=completed_requests,
                           volunteer_name=volunteer.get('name'))


# ── User Dashboard ──────────────────────────────────────────────────────────
@app.route("/user-dashboard")
@login_required
def user_dashboard():
    """Show the logged-in user's help requests and actions."""
    if session.get('role') not in ['user', 'volunteer']:
        flash("Only requesters and volunteers can access My Requests.", "error")
        return redirect(url_for('index'))

    user_id = session.get('user_id')
    username = session.get('username')
    requests = db.get_requests_by_user(user_id)
    user_stats = {
        'total_requests': len(requests),
        'pending': sum(1 for r in requests if r['status'] == 'pending'),
        'accepted': sum(1 for r in requests if r['status'] == 'accepted'),
        'completed': sum(1 for r in requests if r['status'] == 'completed'),
    }
    return render_template("user_dashboard.html", requests=requests,
                           username=username, user_stats=user_stats)


# ── Admin Dashboard ──────────────────────────────────────────────────────────
@app.route("/admin/dashboard")
@admin_required
def admin_dashboard():
    """Show the admin dashboard overview and management panels."""
    status_filter = request.args.get("status", "all")
    user_search = request.args.get("user_search", "").strip()
    volunteer_search = request.args.get("volunteer_search", "").strip()
    request_search = request.args.get("request_search", "").strip()

    users = db.get_all_users(search=user_search)
    volunteers = db.get_all_volunteers(search=volunteer_search)
    requests = db.get_requests(status=status_filter, help_type="all", search=request_search)
    stats = db.get_admin_dashboard_stats()

    return render_template(
        "admin_dashboard.html",
        users=users,
        volunteers=volunteers,
        requests=requests,
        stats=stats,
        status_filter=status_filter,
        user_search=user_search,
        volunteer_search=volunteer_search,
        request_search=request_search
    )


@app.route("/admin/users")
@admin_required
def admin_users():
    return redirect(url_for('admin_dashboard', _anchor='users'))


@app.route("/admin/volunteers")
@admin_required
def admin_volunteers():
    return redirect(url_for('admin_dashboard', _anchor='volunteers'))


@app.route("/admin/requests")
@admin_required
def admin_requests():
    return redirect(url_for('admin_dashboard', _anchor='requests'))


@app.route("/admin/delete-user/<int:user_id>", methods=["POST"])
@admin_required
def admin_delete_user(user_id):
    if db.delete_user(user_id):
        flash("✅ User account deleted successfully.", "success")
    else:
        flash("Unable to delete user account.", "error")
    return redirect(url_for('admin_dashboard'))


@app.route("/admin/delete-volunteer/<int:volunteer_id>", methods=["POST"])
@admin_required
def admin_delete_volunteer(volunteer_id):
    if db.delete_volunteer(volunteer_id):
        flash("✅ Volunteer removed and assignments reset.", "success")
    else:
        flash("Unable to delete volunteer.", "error")
    return redirect(url_for('admin_dashboard'))


@app.route("/admin/delete-request/<int:req_id>", methods=["POST"])
@admin_required
def admin_delete_request(req_id):
    if db.delete_request(req_id):
        flash("✅ Help request deleted successfully.", "success")
    else:
        flash("Unable to delete help request.", "error")
    return redirect(url_for('admin_dashboard'))


# ── Admin Contact Messages Management ─────────────────────────────────────────
@app.route("/admin/contact-messages")
@admin_required
def admin_contact_messages():
    """Show all contact messages with management options."""
    search_query = request.args.get("search", "").strip()
    messages = db.get_all_contact_messages(search=search_query)
    stats = db.get_contact_messages_stats()
    return render_template("admin_contact_messages.html", 
                           messages=messages, 
                           stats=stats,
                           search_query=search_query)


@app.route("/admin/contact-message/<int:msg_id>")
@admin_required
def admin_contact_message_detail(msg_id):
    """Show a single contact message detail."""
    message = db.get_contact_message_by_id(msg_id)
    if not message:
        flash("Message not found.", "error")
        return redirect(url_for('admin_contact_messages'))
    return render_template("admin_contact_message_detail.html", message=message)


@app.route("/admin/contact-message/<int:msg_id>/status/<status>", methods=["POST"])
@admin_required
def admin_update_contact_status(msg_id, status):
    """Update a contact message status (pending/resolved)."""
    if status not in ['pending', 'resolved']:
        flash("Invalid status.", "error")
        return redirect(url_for('admin_contact_messages'))
    
    db.update_contact_message_status(msg_id, status)
    flash(f"✅ Message status updated to {status}.", "success")
    return redirect(url_for('admin_contact_messages'))


@app.route("/admin/contact-message/<int:msg_id>/delete", methods=["POST"])
@admin_required
def admin_delete_contact_message(msg_id):
    """Delete a contact message."""
    if db.delete_contact_message(msg_id):
        flash("✅ Message deleted successfully.", "success")
    else:
        flash("Unable to delete message.", "error")
    return redirect(url_for('admin_contact_messages'))


@app.route("/request/<int:req_id>")
@login_required
def request_details(req_id):
    """Show the request detail page for a logged-in user or volunteer."""
    
    # Role-based access check
    if session.get('role') not in ['user', 'volunteer', 'admin']:
        flash("Only requesters, volunteers, and admins can view request details.", "error")
        return redirect(url_for('index'))

    # Fetch the request
    req = db.get_request_by_id(req_id)
    if req:
        req = dict(req)
    if not req:
        flash("Request not found.", "error")
        return redirect(url_for('user_dashboard'))

    # Access control: users can only view their own requests
    if session.get('role') == 'user':
        # Check ownership if user_id exists; if NULL, deny for safety
        if not req['user_id'] or req['user_id'] != session.get('user_id'):
            flash("You can only view your own requests.", "error")
            return redirect(url_for('user_dashboard'))
    
    # Volunteers can view all requests (no additional access check)

    # Show volunteer contact once a volunteer is assigned or later
    volunteer_contact = None
    if req['status'] in ('volunteer_assigned', 'volunteer_on_way', 'volunteer_near_location', 'volunteer_reached_location', 'completed') and req['volunteer_name']:
        volunteer_contact = {
            'name': req['volunteer_name'],
            'phone': req['volunteer_phone'] if 'volunteer_phone' in req.keys() else '',
            'email': req['volunteer_email'] if 'volunteer_email' in req.keys() else '',
            'availability': ''
        }

    can_update_progress = False
    if session.get('role') == 'volunteer':
        volunteer = db.get_volunteer_by_user_id(session.get('user_id'))
        if volunteer and req.get('volunteer_id') == volunteer.get('id'):
            can_update_progress = True

    return render_template(
        "request_details.html",
        req=req,
        volunteer_contact=volunteer_contact,
        can_update_progress=can_update_progress,
        status_label=get_status_label(req['status']),
        status_class=get_status_class(req['status']),
    )


# ── User Cancel a Request ───────────────────────────────────────────────────
@app.route("/user/cancel-request/<int:req_id>", methods=["POST"])
@login_required
def user_cancel_request(req_id):
    """Allow a requester to cancel their own request."""
    # Ensure the request belongs to the current user
    req = db.get_request_by_id(req_id)
    if not req:
        flash("Request not found.", "error")
        return redirect(url_for('user_dashboard'))

    # Some rows may not have user_id if created before migration
    if not req['user_id'] or req['user_id'] != session.get('user_id'):
        flash("You are not authorized to cancel this request.", "error")
        return redirect(url_for('user_dashboard'))

    # Only allow cancelling if not already completed
    if req['status'] == 'completed':
        flash("Completed requests cannot be cancelled.", "error")
        return redirect(url_for('user_dashboard'))

    db.update_request_status(req_id, 'cancelled')
    flash(f"Request #{req_id} cancelled.", "info")
    return redirect(url_for('user_dashboard'))

# ── Accept a Request (AJAX or redirect) ───────────────────────────────────────
@app.route("/accept-request/<int:req_id>", methods=["POST"])
@volunteer_required
def accept_request(req_id):
    """Assign a request to the logged-in volunteer."""
    user_id = session.get('user_id')
    volunteer = db.get_volunteer_by_user_id(user_id)

    if not volunteer:
        user = db.get_user_by_id(user_id)
        if user:
            try:
                db.add_volunteer(
                    name=user.get('username', 'Volunteer'),
                    phone="",
                    email=user.get('email', ''),
                    location="",
                    skills="",
                    availability="",
                    about="",
                    user_id=user_id,
                )
                volunteer = db.get_volunteer_by_user_id(user_id)
            except Exception as exc:
                app.logger.exception("Failed to create volunteer record: %s", exc)

    if not volunteer:
        flash("Unable to create volunteer profile.", "error")
        return redirect(url_for("dashboard"))

    volunteer = dict(volunteer)
    volunteer_name = volunteer.get('name', 'A volunteer')
    volunteer_email = volunteer.get('email', '')
    volunteer_phone = volunteer.get('phone', '')
    volunteer_location = volunteer.get('location', '')
    volunteer_id = volunteer.get('id', None)

    db.update_request_status(
        req_id,
        "volunteer_assigned",
        volunteer_name=volunteer_name,
        volunteer_id=volunteer_id,
        volunteer_email=volunteer_email,
        volunteer_phone=volunteer_phone,
        volunteer_location=volunteer_location,
        accepted_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    )

    flash(f"✅ Request #{req_id} accepted by {volunteer_name}. The requester will receive your contact information.", "success")
    return redirect(url_for("dashboard"))

# ── Complete a Request ─────────────────────────────────────────────────────────
@app.route("/complete-request/<int:req_id>", methods=["POST"])
@volunteer_required
def complete_request(req_id):
    """Mark a request as completed."""
    req = db.get_request_by_id(req_id)
    volunteer = db.get_volunteer_by_user_id(session.get('user_id'))
    if req:
        req = dict(req)

    if volunteer:
        volunteer = dict(volunteer)

    db.update_request_status(req_id, "completed", completed_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    flash(f"🎉 Request #{req_id} has been marked as completed!", "success")
    return redirect(url_for("dashboard"))

@app.route("/request/<int:req_id>/start-journey", methods=["POST"])
@volunteer_required
def start_journey(req_id):
    req = db.get_request_by_id(req_id)
    if req:
        req = dict(req)

    volunteer = db.get_volunteer_by_user_id(session.get('user_id'))
    if volunteer:
        volunteer = dict(volunteer)

    if not req or not volunteer or req['volunteer_id'] != volunteer['id']:
        flash("You are not authorized to update this request.", "error")
        return redirect(url_for('dashboard'))

    lat = request.form.get('volunteer_latitude')
    lng = request.form.get('volunteer_longitude')
    try:
        lat = float(lat) if lat not in (None, '') else None
        lng = float(lng) if lng not in (None, '') else None
    except (TypeError, ValueError):
        lat = None
        lng = None

    if lat is not None and lng is not None:
        db.update_request_status(
            req_id,
            'volunteer_on_way',
            journey_started_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            volunteer_latitude=lat,
            volunteer_longitude=lng,
            last_location_update=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        )
        flash(f"🚗 Journey started for request #{req_id}.", "success")
    else:
        flash("Unable to start journey without location data.", "info")

    return redirect(url_for('request_details', req_id=req_id))

@app.route("/request/<int:req_id>/refresh-location", methods=["POST"])
@volunteer_required
def refresh_location(req_id):
    req = db.get_request_by_id(req_id)
    if req:
        req = dict(req)

    volunteer = db.get_volunteer_by_user_id(session.get('user_id'))
    if volunteer:
        volunteer = dict(volunteer)

    # Authorization check
    if not req or not volunteer or req['volunteer_id'] != volunteer['id']:
        flash("You are not authorized to update this request.", "error")
        return redirect(url_for('dashboard'))

    lat = request.form.get('volunteer_latitude')
    lng = request.form.get('volunteer_longitude')

    try:
        lat = float(lat) if lat not in (None, '') else None
        lng = float(lng) if lng not in (None, '') else None
    except (TypeError, ValueError):
        lat = None
        lng = None

    status = req['status'] or 'volunteer_assigned'

    if (
        lat is not None
        and lng is not None
        and req['request_latitude'] is not None
        and req['request_longitude'] is not None
    ):
        distance_km = abs(lat - req['request_latitude']) * 111.0

        if distance_km <= 0.1:
            status = 'volunteer_reached_location'
        elif distance_km <= 0.5:
            status = 'volunteer_near_location'
        else:
            status = 'volunteer_on_way'

    db.update_request_status(
        req_id,
        status,
        volunteer_latitude=lat,
        volunteer_longitude=lng,
        last_location_update=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    )

    flash(f"📍 Location refreshed for request #{req_id}.", "success")
    return redirect(url_for('request_details', req_id=req_id))
@app.route("/request/<int:req_id>/mark-reached", methods=["POST"])
@volunteer_required
def mark_reached(req_id):
    req = db.get_request_by_id(req_id)
    if req:
        req = dict(req)

    volunteer = db.get_volunteer_by_user_id(session.get('user_id'))
    if volunteer:
        volunteer = dict(volunteer)

    if not req or not volunteer or req['volunteer_id'] != volunteer['id']:
        flash("You are not authorized to update this request.", "error")
        return redirect(url_for('dashboard'))

    db.update_request_status(
        req_id,
        "volunteer_reached_location",
        reached_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    )

    flash(f"📍 Request #{req_id} marked as reached.", "success")
    return redirect(url_for("request_details", req_id=req_id))


@app.route("/cancel-request/<int:req_id>", methods=["POST"])
@volunteer_required
def cancel_request(req_id):
    db.update_request_status(req_id, "cancelled")
    flash(f"Request #{req_id} has been cancelled.", "info")
    return redirect(url_for("dashboard"))
# ── API: Get single request details (JSON) ────────────────────────────────────
@app.route("/api/request/<int:req_id>")
@login_required
def api_request(req_id):
    """Return a single request as JSON for authorized users."""
    req = db.get_request_by_id(req_id)
    if not req:
        return jsonify({"error": "Not found"}), 404

    if session.get('role') != 'user' or req['user_id'] != session.get('user_id'):
        return jsonify({"error": "Unauthorized"}), 403

    return jsonify(dict(req))

# ── About Page ────────────────────────────────────────────────────────────────
@app.route("/about")
def about():
    return render_template("about.html")

# ── Contact Page ──────────────────────────────────────────────────────────────
@app.route("/contact", methods=["GET", "POST"])
def contact():
    if session.get('role') == 'admin':
        flash("Administrators manage inquiries through the Contact Messages panel.", "info")
        return redirect(url_for('admin_contact_messages'))

    if request.method == "POST":
        name    = request.form.get("name", "").strip()
        email   = request.form.get("email", "").strip()
        message = request.form.get("message", "").strip()

        if not name or not email or not message:
            flash("All fields are required.", "error")
            return render_template("contact.html", form_data=request.form)

        db.add_contact_message(name=name, email=email, message=message)
        flash("✅ Message sent! We will get back to you within 24 hours.", "success")
        return redirect(url_for("contact"))

    return render_template("contact.html", form_data={})

# ── Track Request Status ───────────────────────────────────────────────────────
@app.route("/track", methods=["GET", "POST"])
@login_required
def track():
    """Allow requesters or volunteers to check their request status by ID."""
    if session.get('role') not in ['user', 'volunteer']:
        flash("Only requesters and volunteers can track requests.", "error")
        return redirect(url_for('index'))

    if request.method == "POST":
        req_id = request.form.get("request_id", "").strip()
        if req_id.isdigit():
            return redirect(url_for('track_request', request_id=int(req_id)))
        flash("Please enter a valid numeric Request ID.", "error")

    return render_template("track.html", result=None)


@app.route("/track/<int:request_id>")
@login_required
def track_request(request_id):
    """Show the request tracking page for a specific request."""
    if session.get('role') not in ['user', 'volunteer']:
        flash("Only requesters and volunteers can track requests.", "error")
        return redirect(url_for('index'))

    result = db.get_request_by_id(request_id)
    if result:
        result = dict(result)
    if not result:
        flash(f"No request found with ID #{request_id}.", "error")
        return redirect(url_for('track'))

    if result['user_id'] != session.get('user_id'):
        flash("You can only track your own requests.", "error")
        return redirect(url_for('track'))

    # Show volunteer contact if request is accepted or completed
    volunteer_contact = None
    if result['status'] in ('accepted', 'completed') and result['volunteer_name']:
        # Use volunteer info stored at time of acceptance
        volunteer_contact = {
            'name': result['volunteer_name'],
            'phone': result['volunteer_phone'] if result['volunteer_phone'] else '',
            'email': result['volunteer_email'] if result['volunteer_email'] else '',
            'availability': ''
        }

    return render_template("track.html", result=result,
                           volunteer_contact=volunteer_contact)

# ── Profile Routes ──────────────────────────────────────────────────────────
@app.route("/profile")
@login_required
def profile():
    """Show user profile page."""
    user_id = session.get('user_id')
    user = db.get_user_by_id(user_id)
    
    if not user:
        flash("User not found.", "error")
        return redirect(url_for('index'))
    
    if user['role'] == 'user':
        # User profile
        activity_stats = db.get_user_activity_stats(user_id)
        return render_template("profile.html", user=user, stats=activity_stats)
    
    elif user['role'] == 'volunteer':
        # Volunteer profile: ensure volunteer row exists; auto-create if missing
        app.logger.info("Profile access: session user_id=%s role=%s", session.get('user_id'), session.get('role'))
        volunteer = db.get_volunteer_by_user_id(user_id)
        app.logger.info("Volunteer lookup result: %s", str(volunteer))
        if not volunteer:
            app.logger.info("No volunteer record found for user_id=%s — attempting to create one.", user_id)
            try:
                created = db.add_volunteer(
                    name=user['username'], phone="", email=user.get('email',''),
                    location="", skills="", availability="", about="", user_id=user_id
                )
                app.logger.info("add_volunteer returned: %s", str(created))
            except Exception as e:
                app.logger.exception("Failed to create volunteer record: %s", e)

            # Re-fetch after attempted creation
            volunteer = db.get_volunteer_by_user_id(user_id)

        if not volunteer:
            flash("Your volunteer profile could not be found. Please contact support.", "error")
            return redirect(url_for('index'))

        activity_stats = db.get_volunteer_activity_stats(volunteer['name'])
        return render_template("profile_volunteer.html", user=user, 
                             volunteer=volunteer, stats=activity_stats)
    
    elif user['role'] == 'admin':
        return render_template("profile_admin.html", user=user)

    flash("Invalid user role.", "error")
    return redirect(url_for('index'))


@app.route("/profile/edit", methods=["GET", "POST"])
@login_required
def edit_profile():
    """Allow users to edit their profile."""
    user_id = session.get('user_id')
    user = db.get_user_by_id(user_id)
    
    if not user:
        flash("User not found.", "error")
        return redirect(url_for('index'))
    
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        email = request.form.get("email", "").strip()
        phone = request.form.get("phone", "").strip()
        location = request.form.get("location", "").strip()
        
        # Validation
        errors = []
        if not username or len(username) < 3:
            errors.append("Username must be at least 3 characters.")
        if not email or "@" not in email:
            errors.append("Please enter a valid email.")
        
        if errors:
            for err in errors:
                flash(err, "error")
        else:
            try:
                # Check if email is already taken by another user
                existing = db.get_user_by_email(email)
                if existing and existing['id'] != user_id:
                    flash("Email already in use.", "error")
                else:
                    db.update_user_profile(user_id, username, email, phone, location)
                    session['username'] = username
                    flash("✅ Profile updated successfully!", "success")
                    return redirect(url_for('profile'))
            except Exception as e:
                flash(f"Error updating profile: {str(e)}", "error")
    
    return render_template("edit_profile.html", user=user)


@app.route("/profile/edit-volunteer", methods=["GET", "POST"])
@login_required
def edit_profile_volunteer():
    """Allow volunteers to edit their profile."""
    user_id = session.get('user_id')
    user = db.get_user_by_id(user_id)
    if user:
        user = dict(user)
    
    if not user or user['role'] != 'volunteer':
        flash("You must be a volunteer to access this page.", "error")
        return redirect(url_for('index'))
    
    volunteer = db.get_volunteer_by_user_id(user_id)
    if not volunteer:
        flash("Volunteer profile not found.", "error")
        return redirect(url_for('profile'))
    
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip()
        phone = request.form.get("phone", "").strip()
        location = request.form.get("location", "").strip()
        skills = request.form.get("skills", "").strip()
        availability = request.form.get("availability", "").strip()
        about = request.form.get("about", "").strip()
        
        # Validation
        errors = []
        if not name or len(name) < 3:
            errors.append("Name must be at least 3 characters.")
        if not email or "@" not in email:
            errors.append("Please enter a valid email.")
        if not phone:
            errors.append("Phone number is required.")
        if not location:
            errors.append("Location is required.")
        if not skills:
            errors.append("Skills are required.")
        if not availability:
            errors.append("Availability is required.")
        
        if errors:
            for err in errors:
                flash(err, "error")
        else:
            try:
                existing_user = db.get_user_by_email(email)
                if existing_user and existing_user['id'] != user_id:
                    flash("Email already in use.", "error")
                else:
                    db.update_user_profile(user_id, name, email)
                    db.update_volunteer_profile(volunteer['id'], name, phone, email, 
                                               location, skills, availability, about)
                    session['username'] = name
                    flash("✅ Volunteer profile updated successfully!", "success")
                    return redirect(url_for('profile'))
            except Exception as e:
                flash(f"Error updating profile: {str(e)}", "error")
    
    return render_template("edit_profile_volunteer.html", user=user, volunteer=volunteer)

# ── Run ───────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    db.init_db()          # Create tables if they don't exist
    db.seed_sample_data() # Add sample data for demonstration
    app.run(debug=True, port=5000)


@app.route("/debug/volunteers")
def debug_volunteers():
    import sqlite3

    conn = sqlite3.connect("local_helper.db")  # use your actual DB file name
    conn.row_factory = sqlite3.Row

    users = conn.execute(
        "SELECT id, username, email, role FROM users WHERE role='volunteer'"
    ).fetchall()

    volunteers = conn.execute(
        "SELECT * FROM volunteers"
    ).fetchall()

    conn.close()

    return {
        "users": [dict(u) for u in users],
        "volunteers": [dict(v) for v in volunteers]
    }
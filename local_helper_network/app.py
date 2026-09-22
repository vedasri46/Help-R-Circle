"""
Help R Circle - Main Flask Application
============================================
This is the core server file. It handles all routes, form submissions,
and connects the frontend to the database.
"""

from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify, g
from flask_mail import Mail, Message
from flask_socketio import SocketIO, emit
from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired
from dotenv import load_dotenv
from database import Database
from werkzeug.security import check_password_hash, generate_password_hash
from datetime import datetime, timedelta
import os
import json
import math
import secrets
import uuid
import urllib.error
import urllib.parse
import urllib.request
from functools import wraps


print("APP FILE LOADED")
# ── App Setup ────────────────────────────────────────────────────────────────
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
load_dotenv(os.path.join(PROJECT_ROOT, '.env'))
app = Flask(__name__)
app.config.update(
    SECRET_KEY=os.environ.get("SECRET_KEY", "lhn_secret_key_2024"),
    MAIL_SERVER=os.environ.get("MAIL_SERVER", "smtp.gmail.com"),
    MAIL_PORT=int(os.environ.get("MAIL_PORT", 587)),
    MAIL_USE_TLS=os.environ.get("MAIL_USE_TLS", "True").lower() in ("true", "1", "yes"),
    MAIL_USE_SSL=os.environ.get("MAIL_USE_SSL", "False").lower() in ("true", "1", "yes"),
    MAIL_USERNAME=os.environ.get("MAIL_USERNAME"),
    MAIL_PASSWORD=os.environ.get("MAIL_PASSWORD"),
    MAIL_DEFAULT_SENDER=os.environ.get("MAIL_DEFAULT_SENDER", "Help R Circle <no-reply@helprcircle.com>"),
)
app.secret_key = app.config["SECRET_KEY"]
mail = Mail(app)
socketio = SocketIO(app, cors_allowed_origins="*")
db = Database()

COMPLETION_CODE_TTL_MINUTES = 10
COMPLETION_CODE_COOLDOWN_SECONDS = 60
COMPLETION_CODE_MAX_ATTEMPTS = 5

def normalize_indian_phone(phone_raw):
    if not phone_raw:
        return None
    digits = ''.join(c for c in phone_raw if c.isdigit())
    # strip leading country code if present
    if digits.startswith('91') and len(digits) > 10:
        digits = digits[-10:]
    if len(digits) == 10 and digits[0] in '6789':
        return f"+91{digits}"
    return None


def parse_profile_coordinates(latitude_raw, longitude_raw):
    try:
        latitude = float(latitude_raw)
        longitude = float(longitude_raw)
    except (TypeError, ValueError):
        return None, None
    if not valid_coordinate_pair(latitude, longitude):
        return None, None
    return latitude, longitude


def valid_coordinate_pair(latitude, longitude):
    return (
        latitude is not None and longitude is not None
        and
        math.isfinite(latitude) and math.isfinite(longitude)
        and -90 <= latitude <= 90
        and -180 <= longitude <= 180
    )


def geocode_location(query):
    """Resolve a user-entered place name through OpenStreetMap Nominatim."""
    geocode_url = "https://nominatim.openstreetmap.org/search?format=jsonv2&limit=1&q=" + urllib.parse.quote(query)
    geocode_request = urllib.request.Request(
        geocode_url,
        headers={
            "Accept": "application/json",
            "User-Agent": "HelpRCircle/1.0 (help request location lookup)",
        },
    )
    with urllib.request.urlopen(geocode_request, timeout=8) as response:
        results = json.loads(response.read().decode("utf-8"))
    if not results:
        return None
    result = results[0]
    latitude, longitude = parse_profile_coordinates(result.get("lat"), result.get("lon"))
    if latitude is None or longitude is None:
        return None
    return {
        "latitude": latitude,
        "longitude": longitude,
        "display_name": result.get("display_name") or query,
    }


def get_route_eta(helper_latitude, helper_longitude, request_latitude, request_longitude):
    coordinates = (helper_longitude, helper_latitude, request_longitude, request_latitude)
    if any(value is None for value in coordinates):
        return None
    if not valid_coordinate_pair(helper_latitude, helper_longitude):
        return None
    if not valid_coordinate_pair(request_latitude, request_longitude):
        return None

    route_url = (
        "https://router.project-osrm.org/route/v1/driving/"
        f"{helper_longitude},{helper_latitude};{request_longitude},{request_latitude}"
        "?overview=full&geometries=geojson"
    )
    try:
        route_request = urllib.request.Request(route_url, headers={"User-Agent": "HelpRCircle/1.0"})
        with urllib.request.urlopen(route_request, timeout=4) as response:
            payload = json.loads(response.read().decode("utf-8"))
        route = payload.get("routes", [])[0]
        distance_m = float(route["distance"])
        duration_seconds = float(route["duration"])
        geometry = route.get("geometry", {}).get("coordinates", [])
        if distance_m < 0 or duration_seconds < 0 or not geometry:
            return None
        return {
            "distance_km": distance_m / 1000,
            "duration_seconds": duration_seconds,
            "eta_minutes": 0 if distance_m <= 25 else max(1, int((duration_seconds + 59) // 60)),
            "route_coordinates": [[point[1], point[0]] for point in geometry],
        }
    except (IndexError, KeyError, TypeError, ValueError, json.JSONDecodeError,
            urllib.error.URLError, TimeoutError):
        app.logger.warning("Unable to calculate route ETA", exc_info=True)
        return None

SUPPORTED_LOCALES = {
    "en": "English",
    "te": "తెలుగు",
    "hi": "हिन्दी",
}
DEFAULT_LOCALE = "en"
TRANSLATIONS_DIR = os.path.join(os.path.dirname(__file__), "translations")
TRANSLATIONS_CACHE = {}


def load_translations():
    translations = {}
    for locale in SUPPORTED_LOCALES:
        path = os.path.join(TRANSLATIONS_DIR, f"{locale}.json")
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as handle:
                translations[locale] = json.load(handle)
        else:
            translations[locale] = {}
    return translations


TRANSLATIONS_CACHE = load_translations()


def get_locale():
    if "lang" in session and session["lang"] in SUPPORTED_LOCALES:
        return session["lang"]

    requested = request.args.get("lang", "").strip().lower()
    if requested in SUPPORTED_LOCALES:
        session["lang"] = requested
        return requested

    browser_locale = request.accept_languages.best_match(list(SUPPORTED_LOCALES.keys()), default=DEFAULT_LOCALE)
    if browser_locale in SUPPORTED_LOCALES:
        return browser_locale
    return DEFAULT_LOCALE


def translate(key, default=None):
    locale = getattr(g, "locale", None) or get_locale()
    locale_translations = TRANSLATIONS_CACHE.get(locale, {})
    if key in locale_translations:
        return locale_translations[key]
    fallback_translations = TRANSLATIONS_CACHE.get(DEFAULT_LOCALE, {})
    if key in fallback_translations:
        return fallback_translations[key]
    return default if default is not None else key


def flash_t(key, default, category='info', **kwargs):
    message = translate(key, default)
    if kwargs:
        try:
            message = message.format(**kwargs)
        except (AttributeError, KeyError, IndexError):
            pass
    flash(message, category)


@app.before_request
def attach_locale():
    g.locale = get_locale()
    g.translations = TRANSLATIONS_CACHE.get(g.locale, {})


@app.context_processor
def inject_locale_context():
    return {
        "current_lang": g.get("locale", DEFAULT_LOCALE),
        "available_locales": SUPPORTED_LOCALES,
        "t": translate,
    }


@app.route("/set_language/<lang>")
def set_language(lang):
    if lang in SUPPORTED_LOCALES:
        session["lang"] = lang
        response = redirect(request.referrer or url_for("index"))
        response.set_cookie("lang", lang, max_age=60 * 60 * 24 * 365, samesite="Lax")
        return response
    return redirect(request.referrer or url_for("index"))


# ── Email Verification Helpers ───────────────────────────────────────────────
VERIFICATION_TOKEN_EXPIRATION = 60 * 60 * 24  # 24 hours

def _get_email_serializer():
    return URLSafeTimedSerializer(app.config["SECRET_KEY"])


def generate_verification_token(email):
    serializer = _get_email_serializer()
    return serializer.dumps({"email": email, "nonce": secrets.token_urlsafe(16)}, salt="email-confirmation")


def confirm_verification_token(token, expiration=VERIFICATION_TOKEN_EXPIRATION):
    serializer = _get_email_serializer()
    payload = serializer.loads(token, salt="email-confirmation", max_age=expiration)
    if isinstance(payload, dict):
        return payload.get("email")
    return payload


def send_verification_email(email, username, token):
    verification_url = url_for('verify_email', token=token, _external=True)
    subject = "Verify your Help R Circle email"
    body = (
        f"Hello {username},\n\n"
        "Thank you for registering with Help R Circle. Please verify your email by clicking the link below:\n\n"
        f"{verification_url}\n\n"
        "If you did not register for this account, please ignore this message.\n\n"
        "Thanks,\nHelp R Circle Team"
    )
    msg = Message(subject=subject, recipients=[email], body=body)
    # Log intent to send (without revealing secrets)
    app.logger.info('Preparing verification email to %s from %s', email, app.config.get('MAIL_DEFAULT_SENDER'))
    try:
        mail.send(msg)
        app.logger.info('Verification email sent to %s', email)
    except Exception as e:
        app.logger.exception('Failed to send verification email to %s: %s', email, e)
        raise


def send_notification_email(recipient_email, subject, message):
    if not recipient_email:
        return False
    msg = Message(subject=subject, recipients=[recipient_email], body=message)
    try:
        mail.send(msg)
        app.logger.info('Notification email sent to %s', recipient_email)
        return True
    except Exception as exc:
        app.logger.exception('Failed to send notification email to %s: %s', recipient_email, exc)
        return False


def create_notification(user_id, message, notification_type=None, related_request_id=None):
    if not user_id:
        return None
    existing = db.has_recent_notification(user_id, message, related_request_id=related_request_id, window_seconds=60 * 60 * 24)
    if existing:
        return None
    nid = db.add_notification(user_id, message, notification_type=notification_type, related_request_id=related_request_id)
    if not nid:
        return None
    notification = {
        'id': nid,
        'user_id': user_id,
        'message': message,
        'notification_type': notification_type,
        'related_request_id': related_request_id,
        'is_read': 0,
        'created_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
    }
    socketio.emit(
    'notification',
    notification,
    room=f'user_{user_id}',
    namespace='/'
)
    return nid


def notify_user(user_id, message, email_subject=None, email_message=None, notification_type=None, related_request_id=None):
    if not user_id:
        return None
    notification = create_notification(user_id, message, notification_type=notification_type, related_request_id=related_request_id)
    if email_subject and email_message:
        user = db.get_user_by_id(user_id)
        recipient = user.get('email') if user else None
        if recipient:
            send_notification_email(recipient, email_subject, email_message)
    return notification


def notify_request_status_change(req_id, previous_status, new_status):
    if not req_id or previous_status == new_status:
        return
    req = db.get_request_by_id(req_id)
    if not req:
        return
    req_user = db.get_user_by_id(req['user_id']) if req['user_id'] else None
    helper = db.get_helper_by_user_id(req['volunteer_id']) if req['volunteer_id'] else None
    if req_user:
        socketio.emit(
            'request_status',
            {
                'request_id': req_id,
                'previous_status': previous_status,
                'status': new_status,
            },
            room=f"user_{req_user['id']}",
            namespace='/'
        )
    message_map = {
        'accepted': ('Your help request has been accepted by a volunteer.', 'Help R Circle - Your Help Request Has Been Accepted'),
        'helper_on_way': ('The volunteer has started the journey to assist you.', 'Help R Circle - Volunteer Has Started the Journey'),
        'helper_near_location': ('The volunteer is near your location.', 'Help R Circle - Volunteer Is Near Your Location'),
        'helper_reached_location': ('The volunteer has arrived.', 'Help R Circle - Volunteer Has Arrived'),
        'completed': ('Your help request has been completed.', 'Help R Circle - Help Request Completed'),
        'cancelled': ('Your help request has been cancelled.', 'Help R Circle - Help Request Cancelled'),
    }
    if new_status in message_map and req_user:
        body = (
            f"Hello {req_user.get('username', 'there')},\n\n"
            f"{message_map[new_status][0]}\n\n"
            "Please log in to Help R Circle to view the latest request details.\n\n"
            "Regards,\nHelp R Circle Team\n"
        )
        notify_user(
            req_user['id'],
            message_map[new_status][0],
            email_subject=message_map[new_status][1],
            email_message=body,
            notification_type='request_status',
            related_request_id=req_id,
        )
    if helper and helper['user_id'] and new_status in ('accepted', 'helper_on_way', 'helper_near_location', 'helper_reached_location', 'completed', 'cancelled'):
        volunteer_message = 'A help request you are involved with has been updated.'
        volunteer_email = helper['email'] or (db.get_user_by_id(helper['user_id']) or {}).get('email')
        if volunteer_email:
            send_notification_email(volunteer_email, 'Help R Circle - Help Request Updated', 'A help request you are involved with has been updated. Please log in to Help R Circle to view the latest status.')
        notify_user(helper['user_id'], volunteer_message, notification_type='request_update', related_request_id=req_id)
    if req_user and req_user.get('role') == 'user' and new_status == 'completed' and helper and helper['user_id']:
        notify_user(helper['user_id'], 'A help request you are involved with has been updated.', notification_type='request_update', related_request_id=req_id)


def notify_new_help_request_for_helpers(req_id):
    req = db.get_request_by_id(req_id)
    req = dict(req) if req else None
    priority = (req.get('priority') if req else 'normal') or 'normal'
    priority_label = {'emergency': '🔴 Emergency', 'urgent': '🟡 Urgent', 'normal': '🟢 Normal'}.get(priority, '🟢 Normal')
    helpers = db.get_all_volunteers()
    for helper in helpers:
        helper_user = db.get_user_by_id(helper['user_id']) if helper['user_id'] else None
        if helper_user:
            notify_user(
                helper_user['id'],
                f'{priority_label} help request received. A new help request is available.',
                email_subject=f'Help R Circle - {priority_label} Request Available',
                email_message=f'Hello,\n\n{priority_label} help request received. A new help request is available. Please log in to Help R Circle to review it.\n\nRegards,\nHelp R Circle Team',
                notification_type='new_request',
                related_request_id=req_id,
            )


def notify_admin_for_new_request(req_id):
    req = db.get_request_by_id(req_id)
    req = dict(req) if req else None
    priority = (req.get('priority') if req else 'normal') or 'normal'
    priority_label = {'emergency': '🔴 Emergency', 'urgent': '🟡 Urgent', 'normal': '🟢 Normal'}.get(priority, '🟢 Normal')
    admin_user = db.get_user_by_email('support.helprcircle@gmail.com')
    if admin_user:
        notify_user(
            admin_user['id'],
            f'{priority_label} help request received.',
            notification_type='admin_new_request',
            related_request_id=req_id,
        )


def send_contact_admin_notification(contact_message):
    admin_user = db.get_user_by_email('support.helprcircle@gmail.com')
    if admin_user:
        notify_user(
            admin_user['id'],
            'A new complaint/contact message has been received.',
            notification_type='admin_contact_message',
            related_request_id=None,
        )


# ── Login Required Decorator ──────────────────────────────────────────────────
def login_required(f):
    """Decorator to protect routes that require login."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash_t("flash_login_required", "Please log in first.", "error")
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function


# ── Helper Required Decorator ──────────────────────────────────────────
def helper_required(f):
    """Decorator to protect routes that require helper role."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash_t("flash_login_required", "Please log in first.", "error")
            return redirect(url_for('login'))
        if session.get('role') not in ('helper', 'helper'):
            flash_t("flash_helper_required", "You must be a helper to view this page.", "error")
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated_function


# ── User Required Decorator ─────────────────────────────────────────────────
def user_required(f):
    """Decorator to protect routes that require user role."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash_t("flash_login_required", "Please log in first.", "error")
            return redirect(url_for('login'))
        if session.get('role') != 'user':
            flash_t("flash_requester_only", "Only requesters can access this page.", "error")
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated_function


# ── Admin Required Decorator ──────────────────────────────────────────────────
def admin_required(f):
    """Decorator to protect routes that require admin role."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash_t("flash_login_required", "Please log in first.", "error")
            return redirect(url_for('login'))
        if session.get('role') != 'admin':
            flash_t("flash_admin_only", "Only admins can access this page.", "error")
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated_function


@app.route('/api/notifications')
@login_required
def api_notifications():
    notifications = db.get_notifications_for_user(session['user_id'], limit=20)
    payload = []
    for item in notifications:
        payload.append({
            'id': item['id'],
            'message': item['message'],
            'notification_type': item['notification_type'],
            'related_request_id': item['related_request_id'],
            'is_read': bool(item['is_read']),
            'created_at': item['created_at'],
        })
    return jsonify({'notifications': payload, 'unread_count': db.get_unread_notification_count(session['user_id'])})


@app.route('/api/notifications/<int:notification_id>/read', methods=['POST'])
@login_required
def api_mark_notification_read(notification_id):
    ok = db.mark_notification_read(notification_id, session['user_id'])
    return jsonify({'ok': ok})


@app.route('/api/notifications/read-all', methods=['POST'])
@login_required
def api_mark_all_notifications_read():
    ok = db.mark_all_notifications_read(session['user_id'])
    return jsonify({'ok': ok})


@socketio.on('join')
def handle_join(data=None):
    user_id = None
    if isinstance(data, dict):
        user_id = data.get('userId')
    if not user_id and session.get('user_id'):
        user_id = session.get('user_id')
    if user_id:
        emit('joined', {'userId': user_id}, room=f'user_{user_id}')


@app.before_request
def attach_locale():
    g.locale = get_locale()
    g.translations = TRANSLATIONS_CACHE.get(g.locale, {})


@app.context_processor
def inject_locale_context():
    return {
        "current_lang": g.get("locale", DEFAULT_LOCALE),
        "available_locales": SUPPORTED_LOCALES,
        "t": translate,
    }


def get_status_label(status):
    labels = {
        'submitted': 'Request Submitted',
        'pending': 'Request Submitted',
        'awaiting_helper': 'Request Submitted',
        'helper_assigned': 'Accepted',
        'helper_on_way': 'Helper On The Way',
        'helper_near_location': 'Helper Near Location',
        'helper_reached_location': 'Helper Reached Location',
        'completed': 'Completed',
        'cancelled': 'Request Cancelled',
        'helper_unavailable': 'Helper Unavailable',
        'reassigned_helper': 'Reassigned Helper',
        'expired_request': 'Expired Request',
    }
    return labels.get(status, (status or 'pending').replace('_', ' ').title())


def get_status_class(status):
    classes = {
        'submitted': 'secondary',
        'pending': 'secondary',
        'awaiting_helper': 'secondary',
        'helper_assigned': 'primary',
        'helper_on_way': 'warning',
        'helper_near_location': 'info',
        'helper_reached_location': 'info',
        'completed': 'success',
        'cancelled': 'danger',
        'helper_unavailable': 'danger',
        'reassigned_helper': 'warning',
        'expired_request': 'secondary',
    }
    return classes.get(status, 'secondary')
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
        phone_raw = request.form.get("phone", "").strip()
        phone = normalize_indian_phone(phone_raw)
        password = request.form.get("password", "").strip()
        confirm  = request.form.get("confirm_password", "").strip()
        role     = request.form.get("role", "user").strip()
        pending_id = request.form.get('pending_id') or session.get('pending_id')

        # ── Validation ────────────────────────────────────────────────────────
        errors = []
        if not username:
            errors.append(("flash_username_required", "Username is required."))
        elif len(username) < 3:
            errors.append(("flash_username_min_length", "Username must be at least 3 characters."))
        
        if not email:
            errors.append(("flash_email_required", "Email is required."))
        elif "@" not in email:
            errors.append(("flash_valid_email_required", "Please enter a valid email address."))
        if not phone:
            errors.append(("flash_phone_required", "Phone number is required."))
        elif phone is None:
            errors.append(("flash_phone_invalid", "Please enter a valid 10-digit Indian mobile number."))
        
        if not password:
            errors.append(("flash_password_required", "Password is required."))
        elif len(password) < 6:
            errors.append(("flash_password_min_length", "Password must be at least 6 characters."))
        
        if password != confirm:
            errors.append(("flash_passwords_do_not_match", "Passwords do not match."))
        
        if role not in ["user", "helper", "helper"]:
            errors.append(("flash_invalid_role", "Invalid role selected."))

        if errors:
            for key, default in errors:
                flash_t(key, default, "error")
            pending_registration = db.get_pending_by_id(int(pending_id)) if pending_id else None
            return render_template("signup.html", form_data=request.form, pending_registration=pending_registration)
        if not pending_id:
            flash_t("flash_verification_required", "Please send and verify your email before creating an account.", "error")
            return render_template("signup.html", form_data=request.form)

        try:
            pending = db.get_pending_by_id(int(pending_id))
            if not pending or pending.get('email') != email:
                raise ValueError('pending registration not found')
            db.update_pending_registration(
                int(pending_id), username, generate_password_hash(password), role, phone,
                request.form.get('location', ''), request.form.get('skills', ''),
                request.form.get('availability', ''), request.form.get('about', ''),
            )
            db.finalize_pending_registration(int(pending_id))
            session.pop('pending_id', None)
            session.pop('email_verification_completed_for', None)
            flash_t("flash_account_created", "✅ Registration complete. You can now log in.", "success")
            return redirect(url_for("login"))
        except Exception as e:
            app.logger.exception("Failed to finalize pending registration: %s", e)
            flash_t("flash_signup_exception", "Please complete both email and phone verification before creating an account.", "error")
            pending_registration = db.get_pending_by_id(int(pending_id)) if pending_id else None
            return render_template("signup.html", form_data=request.form, pending_registration=pending_registration)

    pending_registration = None
    if session.get('pending_id'):
        try:
            session_pending_id = int(session['pending_id'])
            pending_registration = db.get_pending_by_id(session_pending_id)
            if (
                pending_registration and pending_registration.get('email_verified')
                and session.get('email_verification_completed_for') != session_pending_id
            ):
                session.pop('pending_id', None)
                pending_registration = None
        except (TypeError, ValueError):
            session.pop('pending_id', None)
    form_data = {}
    if pending_registration:
        pending_username = pending_registration.get('username', '') or ''
        if pending_username.startswith('pending_'):
            pending_username = ''
        form_data = {
            'username': pending_username,
            'email': pending_registration.get('email', ''),
            'phone': pending_registration.get('phone', ''),
        }
    return render_template("signup.html", form_data=form_data, pending_registration=pending_registration)


# API: create a pending registration without finalizing (AJAX)
@app.route('/create-pending', methods=['POST'])
def create_pending():
    data = request.form or request.get_json() or {}
    email = (data.get('email') or '').strip()
    if not email or '@' not in email:
        return jsonify({'error': 'Invalid email'}), 400

    existing = db.get_user_by_email(email)
    if existing:
        return jsonify({'error': 'Email address already registered'}), 409

    pending_id = data.get('pending_id') or session.get('pending_id')
    try:
        pending = db.get_pending_by_id(int(pending_id)) if pending_id else None
        if pending and pending.get('email') == email:
            if pending.get('email_verified'):
                return jsonify({
                    'ok': False,
                    'error': 'email_already_verified',
                    'message': 'This email is already verified. Continue with phone verification.',
                    'pending_id': pending['id'],
                }), 409
            token = pending.get('email_token') or generate_verification_token(email)
            if not pending.get('email_token'):
                with db.connect() as conn:
                    conn.execute("UPDATE pending_registrations SET email_token = ?, email_token_sent_at = datetime('now','localtime') WHERE id = ?", (token, pending['id']))
        else:
            token = generate_verification_token(email)
            pending_id = db.create_pending_registration(
                username=(data.get('username') or '').strip(),
                email=email,
                password_hash=generate_password_hash(uuid.uuid4().hex),
                role='user',
                email_token=token,
            )
    except Exception as e:
        app.logger.exception('create_pending failed: %s', e)
        return jsonify({'error': 'Unable to create pending registration'}), 500

    try:
        send_verification_email(email, (data.get('username') or '').strip() or 'there', token)
    except Exception as e:
        app.logger.exception('send verification failed (create_pending): %s', e)
        # still return pending id so user can retry email
        return jsonify({'ok': False, 'pending_id': pending_id, 'message': 'Failed to send verification email'}), 502

    session['pending_id'] = pending_id
    session.pop('email_verification_completed_for', None)
    return jsonify({'ok': True, 'pending_id': pending_id}), 200


@app.route('/finalize-pending', methods=['POST'])
def finalize_pending():
    data = request.form or request.get_json() or {}
    pending_id = data.get('pending_id')
    is_ajax = (
        request.is_json
        or request.headers.get('X-Requested-With') == 'XMLHttpRequest'
        or 'application/json' in request.headers.get('Accept', '')
    )
    if not pending_id:
        if is_ajax:
            return jsonify({'error': 'missing'}), 400
        flash_t('flash_invalid_user', 'Invalid pending identifier.', 'error')
        return redirect(url_for('signup'))
    try:
        pending_id = int(pending_id)
    except Exception:
        if is_ajax:
            return jsonify({'error': 'invalid'}), 400
        flash_t('flash_invalid_user', 'Invalid pending identifier.', 'error')
        return redirect(url_for('signup'))
    try:
        pending = db.get_pending_by_id(pending_id)
        if not pending:
            raise ValueError('pending registration not found')
        username = (data.get('username') or '').strip()
        email = (data.get('email') or '').strip()
        phone = normalize_indian_phone((data.get('phone') or '').strip())
        password = (data.get('password') or '').strip()
        confirm = (data.get('confirm_password') or '').strip()
        role = (data.get('role') or 'user').strip()
        if not username or len(username) < 3 or email != pending.get('email'):
            raise ValueError('invalid account details')
        if not phone or len(password) < 6 or password != confirm or role not in ('user', 'helper'):
            raise ValueError('invalid account details')
        db.update_pending_registration(
            pending_id, username, generate_password_hash(password), role, phone,
            data.get('location', ''), data.get('skills', ''), data.get('availability', ''), data.get('about', ''),
        )
        if not pending.get('email_verified'):
            raise ValueError('email not verified')
        new_user_id = db.finalize_pending_registration(pending_id)
        if is_ajax:
            return jsonify({'ok': True, 'user_id': new_user_id}), 200
        flash_t('flash_account_created', '✅ Registration complete. You can now log in.', 'success')
        return redirect(url_for('login'))
    except Exception as e:
        app.logger.exception('finalize_pending failed: %s', e)
        if is_ajax:
            message = str(e) if isinstance(e, ValueError) else 'Unable to complete registration. Please try again.'
            return jsonify({'error': 'finalization_failed', 'message': message}), 400 if isinstance(e, ValueError) else 500
        flash_t('flash_signup_exception', 'Unable to complete registration: ' + str(e), 'error')
        return redirect(url_for('signup'))


# ── Email Verification ───────────────────────────────────────────────────────
@app.route("/verify-email/<token>")
def verify_email(token):
    """Verify user email using the token from signup email."""
    try:
        email = confirm_verification_token(token)
        user = db.get_user_by_email(email)
        if user:
            if user.get('is_verified'):
                flash_t("flash_email_already_verified", "Your email is already verified.", "info")
                return redirect(url_for("login"))
            db.mark_email_as_verified(user['id'])
            flash_t("flash_email_verified", "✅ Email verified successfully! If you have verified your phone as well you can log in.", "success")
            return redirect(url_for("login"))

        # Not a final user: check pending registrations
        pending = db.get_pending_by_email(email)
        if not pending:
            flash_t("flash_verification_invalid", "Invalid verification link or user not found.", "error")
            return redirect(url_for("login"))

        result = db.consume_pending_email_token(pending['id'], token)
        if result == 'already_verified':
            flash_t("flash_email_already_verified", "Your email is already verified.", "info")
            return redirect(url_for('signup'))
        if result != 'verified':
            flash_t("flash_verification_invalid", "Invalid or already-used verification link.", "error")
            return redirect(url_for('signup'))
        session['pending_id'] = pending['id']
        session['email_verification_completed_for'] = pending['id']
        # Return to signup so the verified state enables phone verification.
        return redirect(url_for('signup'))
    
    except SignatureExpired:
        flash_t("flash_verification_expired", "This verification link has expired. Please request a new one.", "error")
        return redirect(url_for("signup"))
    except BadSignature:
        flash_t("flash_verification_invalid", "❌ Invalid verification link.", "error")
        return redirect(url_for("signup"))


@app.route("/resend-verification", methods=["GET", "POST"])
def resend_verification():
    """Resend verification email to user."""
    if request.method == "POST":
        email = request.form.get("email", "").strip()
        
        if not email or "@" not in email:
            flash_t("flash_valid_email_required", "Please enter a valid email address.", "error")
            return render_template("resend_verification.html", form_data=request.form)
        
        user = db.get_user_by_email(email)
        if user:
            if user.get('is_verified'):
                flash_t("flash_email_already_verified", "✅ This email is already verified. Please log in.", "info")
                return redirect(url_for("login"))
            token = generate_verification_token(email)
            db.store_verification_token(user['id'], token)
            try:
                send_verification_email(email, user['username'], token)
                flash_t("flash_verification_sent", "✅ Verification email sent. Please check your inbox.", "success")
                return redirect(url_for("login"))
            except Exception as e:
                app.logger.error(f"Failed to send verification email: {e}")
                flash_t("flash_verification_failed", "❌ Verification email could not be sent. Please try again later.", "error")
                return render_template("resend_verification.html", form_data=request.form)

        # Not a final user; check pending registrations
        pending = db.get_pending_by_email(email)
        if pending:
            if pending.get('email_verified'):
                flash_t("flash_email_already_verified", "✅ This email is already verified for a pending registration. Please verify phone to complete.", "info")
                return redirect(url_for('login'))
            token = generate_verification_token(email)
            # update pending token
            with db.connect() as conn:
                conn.execute("UPDATE pending_registrations SET email_token = ?, email_token_sent_at = datetime('now','localtime') WHERE id = ?", (token, pending['id']))
            try:
                send_verification_email(email, pending.get('username') or '', token)
                flash_t("flash_verification_sent", "✅ Verification email sent. Please check your inbox.", "success")
                return redirect(url_for("login"))
            except Exception as e:
                app.logger.error(f"Failed to send verification email (pending): {e}")
                flash_t("flash_verification_failed", "❌ Verification email could not be sent. Please try again later.", "error")
                return render_template("resend_verification.html", form_data=request.form)

        flash_t("flash_verification_invalid", "Invalid verification link or user not found.", "error")
        return render_template("resend_verification.html", form_data=request.form)
    
    return render_template("resend_verification.html", form_data={})


# ── Login ─────────────────────────────────────────────────────────────────────
@app.route("/login", methods=["GET", "POST"])
def login():
    """Show login form (GET) or authenticate user (POST)."""
    if request.method == "POST":
        email    = request.form.get("email", "").strip()
        password = request.form.get("password", "").strip()

        # ── Validation ────────────────────────────────────────────────────────
        if not email or not password:
            flash_t("flash_email_password_required", "Email and password are required.", "error")
            return render_template("login.html", form_data=request.form)

        # ── Authenticate ──────────────────────────────────────────────────────
        user = db.login_user(email, password)
        if user:
    # Email verification is required for users and helpers,
    # but not for the trusted admin account.
            if user.get('role') != 'admin' and not user.get('is_verified'):
                flash_t(
                    "flash_unverified_email",
                    "📧 Your email is not verified yet. Please check your inbox for the verification link or <a href='/resend-verification'>request a new one here</a>.",
                    "warning"
                )
                return render_template("login.html", form_data=request.form)
            session['user_id'] = user['id']
            session['username'] = user['username']
            session['email'] = user['email']
            session['role'] = user['role']
            
            flash_t("flash_login_welcome", "✅ Welcome back, {username}!", "success", username=user['username'])
            
            # Redirect based on role
            if user['role'] == 'admin':
                return redirect(url_for("admin_dashboard"))
            elif user['role'] in ('helper', 'helper'):
                # Run repair to ensure helper profiles exist (helps older accounts)
                app.logger.info("Login (helper): user_id=%s username=%s", user['id'], user['username'])
                try:
                    created = db.repair_missing_helpers()
                    app.logger.info("repair_missing_helpers result: %s", str(created))
                except Exception as e:
                    app.logger.exception("repair_missing_helpers failed: %s", e)

                # Ensure current user's helper row exists; create if still missing
                try:
                    vol = db.get_helper_by_user_id(user['id'])
                    app.logger.info("Helper lookup post-repair: %s", str(vol))
                    if not vol:
                        vid = db.add_helper(
                            name=user['username'], phone="", email=user.get('email',''),
                            location="", skills="", availability="", about="", user_id=user['id']
                        )
                        app.logger.info("Created helper record id %s for user_id %s", str(vid), user['id'])
                except Exception:
                    app.logger.exception("Failed ensuring helper profile for user_id=%s", user['id'])

                return redirect(url_for("dashboard"))
            else:
                return redirect(url_for("user_dashboard"))
        else:
            flash_t("flash_login_invalid", "❌ Invalid email or password.", "error")
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
            flash_t("flash_email_password_required", "Email and password are required.", "error")
            return render_template("admin_login.html", form_data=request.form)

        user = db.login_user(email, password)
        if user and user.get('role') == 'admin':
            session['user_id'] = user['id']
            session['username'] = user['username']
            session['email'] = user['email']
            session['role'] = user['role']
            flash_t("flash_login_welcome", "✅ Welcome back, {username}!", "success", username=user['username'])
            return redirect(url_for("admin_dashboard"))

        if user:
            flash_t("flash_admin_login_hint", "Please use the regular login page for requester or helper accounts.", "error")
        else:
            flash_t("flash_login_invalid", "❌ Invalid email or password.", "error")
        return render_template("admin_login.html", form_data=request.form)

    return render_template("admin_login.html", form_data={})

# ── Logout ────────────────────────────────────────────────────────────────────
@app.route("/logout")
def logout():
    """Clear user session and logout."""
    username = session.get('username', 'User')
    session.clear()
    flash_t("flash_logged_out", "👋 {username}, you have been logged out successfully.", "success", username=username)
    return redirect(url_for("index"))
# ── Session-Aware Redirect Routes ─────────────────────────────────────────────
@app.route("/go-request-help")
def go_request_help():
    """Redirect to login if not logged in, else go to request-help form."""
    if 'user_id' not in session:
        flash_t("flash_login_to_request", "Please log in before requesting help.", "info")
        return redirect(url_for('login'))
    return redirect(url_for('request_help'))

@app.route("/go-helper")
@app.route("/go-helper")
def go_helper():
    """Redirect to login if not logged in, else go to helper dashboard."""
    if 'user_id' not in session:
        flash_t("flash_login_to_dashboard", "Please log in before viewing the helper dashboard.", "info")
        return redirect(url_for('login'))

    if session.get('role') not in ('helper', 'helper'):
        flash_t("flash_only_helpers_dashboard", "Only helpers can access this dashboard.", "error")
        return redirect(url_for('index'))

    return redirect(url_for('dashboard'))
# ── Request Help ──────────────────────────────────────────────────────────────
@app.route("/request-help", methods=["GET", "POST"])
@login_required
def request_help():
    """Show the help-request form (GET) or save a new request (POST)."""
    # Admins cannot submit help requests
    if session.get('role') == 'admin':
        flash_t("flash_admin_cannot_submit_request", "Administrators cannot submit help requests. Access denied.", "error")
        return redirect(url_for('admin_dashboard'))
    
    # Users and Helpers can submit help requests
    if request.method == "POST":
        name        = request.form.get("name", "").strip()
        phone       = request.form.get("phone", "").strip()
        location    = request.form.get("location", "").strip()
        help_type   = request.form.get("help_type", "").strip()
        description = request.form.get("description", "").strip()
        priority    = request.form.get("priority", "normal").strip().lower()
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
        if not name:            errors.append(("flash_name_required", "Name is required."))
        if not phone:           errors.append(("flash_phone_required", "Phone number is required."))
        if len(phone) < 10:     errors.append(("flash_phone_invalid", "Enter a valid phone number."))
        if not location:        errors.append(("flash_location_required", "Location is required."))
        if not help_type:       errors.append(("flash_help_type_required", "Please select a help type."))
        if not description:     errors.append(("flash_description_required", "Please describe what you need."))
        if priority not in {'emergency', 'urgent', 'normal'}:
            errors.append(("flash_priority_invalid", "Please select a valid priority level."))
        if not valid_coordinate_pair(request_latitude, request_longitude):
            errors.append(("flash_location_coordinates_required", "Please select a valid location using GPS or Find Location."))

        if errors:
            for key, default in errors:
                flash_t(key, default, "error")
            return render_template("request_help.html",
                                   form_data=request.form)

        # ── Save to DB ───────────────────────────────────────────────────────
        request_id = db.add_help_request(
            name=name, phone=phone, location=location,
            help_type=help_type, description=description, priority=priority,
            user_id=session.get('user_id'),
            request_latitude=request_latitude,
            request_longitude=request_longitude,
        )
        notify_admin_for_new_request(request_id)
        notify_new_help_request_for_helpers(request_id)
        flash_t(
            "flash_request_submitted",
            f"✅ Your help request was submitted successfully. Your request ID is #{request_id}. A helper will contact you soon.",
            "success"
        )
        return redirect(url_for("request_help"))

    return render_template("request_help.html", form_data={})


@app.route("/api/geocode-location")
@login_required
def api_geocode_location():
    query = request.args.get("q", "").strip()
    if not query:
        return jsonify({"ok": False, "error": "Location is required."}), 400
    try:
        result = geocode_location(query)
    except (json.JSONDecodeError, urllib.error.URLError, TimeoutError, ValueError):
        app.logger.warning("Location geocoding service unavailable")
        return jsonify({"ok": False, "error": "Location lookup is temporarily unavailable."}), 502
    if not result:
        return jsonify({"ok": False, "error": "Location not found."}), 404
    return jsonify({"ok": True, **result})

# ── Helper Registration ─────────────────────────────────────────────────────
@app.route("/helper", methods=["GET", "POST"])
@app.route("/helper", methods=["GET", "POST"])
def helper_registration():
    """Show helper sign-up form (GET) or save a new helper (POST)."""
    if request.method == "POST":
        name         = request.form.get("name", "").strip()
        phone_raw    = request.form.get("phone", "").strip()
        phone        = normalize_indian_phone(phone_raw)
        email        = request.form.get("email", "").strip()
        location     = request.form.get("location", "").strip()
        skills       = request.form.getlist("skills")          # multi-select checkboxes
        availability = request.form.get("availability", "").strip()
        about        = request.form.get("about", "").strip()

        # ── Validation ───────────────────────────────────────────────────────
        errors = []
        if not name:         errors.append(("flash_name_required", "Name is required."))
        if not phone_raw:    errors.append(("flash_phone_required", "Phone number is required."))
        if not phone:
            errors.append(("flash_phone_invalid", "Enter a valid 10-digit Indian mobile number."))
        if not email:        errors.append(("flash_email_required", "Email is required."))
        if not location:     errors.append(("flash_location_required", "Location / area is required."))
        if not skills:       errors.append(("flash_skills_required", "Please select at least one skill."))
        if not availability: errors.append(("flash_availability_required", "Please enter your availability."))

        if errors:
            for key, default in errors:
                flash_t(key, default, "error")
            return render_template("volunteer.html", form_data=request.form,
                                   selected_skills=skills)

        # ── Save pending helper registration (do not create final helper yet) ──
        try:
            password = request.form.get('password', '').strip()
            confirm = request.form.get('confirm_password', '').strip()
            if not password or password != confirm:
                flash_t('flash_password_required', 'Password is required and must match confirmation.', 'error')
                return render_template('volunteer.html', form_data=request.form, selected_skills=skills)
            password_hash = generate_password_hash(password)
            token = generate_verification_token(email)
            pending_id = db.create_pending_registration(username=name, email=email, password_hash=password_hash, role='helper', phone=phone, helper_location=location, helper_skills=", ".join(skills), helper_availability=availability, helper_about=about, email_token=token)
            # attempt to send verification email
            try:
                send_verification_email(email, name, token)
            except Exception:
                app.logger.exception('Failed to send verification email for pending helper %s', pending_id)

            flash_t("flash_helper_registered", "🎉 Thank you, {name}! Please verify your email and phone to complete helper registration.", "success", name=name)
            # keep pending_id in session for convenience
            session['pending_id'] = pending_id
            return redirect(url_for('helper_registration'))
        except Exception:
            app.logger.exception('Failed to create pending helper')
            flash_t('flash_signup_exception', 'Unable to process registration. Try again later.', 'error')
            return render_template('volunteer.html', form_data=request.form, selected_skills=skills)

    return render_template("volunteer.html", form_data={}, selected_skills=[])

# ── Helper Dashboard ────────────────────────────────────────────────────────
@app.route("/dashboard")
@helper_required
def dashboard():
    """Show all pending/accepted help requests for helpers to act on, plus their own requests."""
    status_filter   = request.args.get("status", "all")
    type_filter     = request.args.get("help_type", "all")
    search_query    = request.args.get("q", "").strip()
    priority_filter = request.args.get("priority", "all")

    # Get requests available for helpers to help with
    requests = db.get_requests(
        status=status_filter,
        help_type=type_filter,
        search=search_query,
        priority=priority_filter
    )
    
    # Get this helper's own submitted requests
    helper_user_id = session.get('user_id')
    my_requests = db.get_requests_by_user(helper_user_id)
    
    # Calculate helper's request stats
    my_request_stats = {
        'total_requests': len(my_requests),
        'pending': sum(1 for r in my_requests if r['status'] == 'pending'),
        'accepted': sum(1 for r in my_requests if r['status'] == 'accepted'),
        'completed': sum(1 for r in my_requests if r['status'] == 'completed'),
    }

    helper = db.get_helper_by_user_id(helper_user_id)
    if helper:
        helper = dict(helper)
    helper_name = helper.get('name') if helper else session.get('username')
    helper_activity = db.get_helper_activity_stats(helper_name)
    overview_stats = {
        'pending': db.get_stats().get('pending', 0),
        'accepted': helper_activity.get('accepted_requests', 0),
        'active': helper_activity.get('active_requests', 0),
        'completed': helper_activity.get('completed_requests', 0),
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
                           search_query=search_query,
                           priority_filter=priority_filter)


@app.route("/dashboard/completed-requests")
@helper_required
def completed_requests():
    """Show completed help requests assigned to the logged-in helper."""
    helper_user_id = session.get('user_id')
    helper = db.get_helper_by_user_id(helper_user_id)
    if not helper:
        flash_t("flash_helper_profile_missing", "Unable to locate your helper profile. Please contact support.", "error")
        return redirect(url_for('dashboard'))
    helper = dict(helper)

    completed_requests = db.get_completed_requests_by_helper(helper['id'])
    return render_template("completed_requests.html",
                           requests=completed_requests,
                           helper_name=helper.get('name'))


# ── User Dashboard ──────────────────────────────────────────────────────────
@app.route("/user-dashboard")
@login_required
def user_dashboard():
    """Show the logged-in user's help requests and actions."""
    if session.get('role') not in ['user', 'helper', 'helper']:
        flash_t("flash_requesters_helpers_only", "Only requesters and helpers can access My Requests.", "error")
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
    helper_search = request.args.get("helper_search", "").strip()
    request_search = request.args.get("request_search", "").strip()
    priority_filter = request.args.get("priority", "all")

    users = db.get_all_users(search=user_search)
    helpers = db.get_all_helpers(search=helper_search)
    requests = db.get_requests(status=status_filter, help_type="all", search=request_search, priority=priority_filter)
    stats = db.get_admin_dashboard_stats()

    return render_template(
        "admin_dashboard.html",
        users=users,
        helpers=helpers,
        requests=requests,
        stats=stats,
        status_filter=status_filter,
        user_search=user_search,
        helper_search=helper_search,
        request_search=request_search,
        priority_filter=priority_filter
    )


@app.route("/admin/map")
@admin_required
def admin_map():
    return render_template("admin_map.html", map_data=db.get_admin_location_map_data())


@app.route("/admin/users")
@admin_required
def admin_users():
    search_query = request.args.get("search", "").strip()
    return render_template("admin_users.html", users=db.get_all_users(search=search_query), search_query=search_query)


@app.route("/admin/users/<int:user_id>")
@admin_required
def admin_user_details(user_id):
    user, requests = db.get_user_admin_details(user_id)
    if not user:
        flash_t("flash_user_not_found", "User not found.", "error")
        return redirect(url_for("admin_users"))
    return render_template("admin_user_details.html", user=user, requests=requests)


@app.route("/admin/helpers")
@admin_required
def admin_helpers():
    search_query = request.args.get("search", "").strip()
    return render_template("admin_helpers.html", helpers=db.get_all_helpers(search=search_query), search_query=search_query)


@app.route("/admin/helpers/<int:helper_id>")
@admin_required
def admin_helper_details(helper_id):
    helper, requests = db.get_helper_admin_details(helper_id)
    if not helper:
        flash_t("flash_helper_not_found", "Helper not found.", "error")
        return redirect(url_for("admin_helpers"))
    return render_template("admin_helper_details.html", helper=helper, requests=requests)


@app.route("/admin/requests")
@admin_required
def admin_requests():
    status_filter = request.args.get("status", "all")
    request_search = request.args.get("search", "").strip()
    requests = db.get_requests(status=status_filter, help_type="all", search=request_search, priority="all")
    return render_template("admin_requests.html", requests=requests, status_filter=status_filter, search_query=request_search)


@app.route("/admin/requests/<int:req_id>")
@admin_required
def admin_request_details(req_id):
    req = db.get_admin_request_details(req_id)
    if not req:
        flash_t("flash_request_not_found", "Request not found.", "error")
        return redirect(url_for("admin_requests"))
    return render_template("admin_request_details.html", req=req)


@app.route("/admin/requests/<int:req_id>/tracking")
@admin_required
def admin_request_tracking(req_id):
    req = db.get_admin_request_details(req_id)
    if not req:
        flash_t("flash_request_not_found", "Request not found.", "error")
        return redirect(url_for("admin_requests"))
    return render_template("admin_request_tracking.html", req=req)


@app.route("/admin/delete-user/<int:user_id>", methods=["POST"])
@admin_required
def admin_delete_user(user_id):
    if db.delete_user(user_id):
        flash_t("flash_user_deleted", "✅ User account deleted successfully.", "success")
    else:
        flash_t("flash_user_delete_failed", "Unable to delete user account.", "error")
    return redirect(url_for('admin_dashboard'))


@app.route("/admin/delete-helper/<int:helper_id>", methods=["POST"])
@admin_required
def admin_delete_helper(helper_id):
    if db.delete_helper(helper_id):
        flash_t("flash_helper_deleted", "✅ Helper removed and assignments reset.", "success")
    else:
        flash_t("flash_helper_delete_failed", "Unable to delete helper.", "error")
    return redirect(url_for('admin_dashboard'))


@app.route("/admin/delete-request/<int:req_id>", methods=["POST"])
@admin_required
def admin_delete_request(req_id):
    if db.delete_request(req_id):
        flash_t("flash_request_deleted", "✅ Help request deleted successfully.", "success")
    else:
        flash_t("flash_request_delete_failed", "Unable to delete help request.", "error")
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
        flash_t("flash_message_not_found", "Message not found.", "error")
        return redirect(url_for('admin_contact_messages'))
    return render_template("admin_contact_message_detail.html", message=message)


@app.route("/admin/contact-message/<int:msg_id>/status/<status>", methods=["POST"])
@admin_required
def admin_update_contact_status(msg_id, status):
    """Update a contact message status (pending/resolved)."""
    if status not in ['pending', 'resolved']:
        flash_t("flash_invalid_status", "Invalid status.", "error")
        return redirect(url_for('admin_contact_messages'))

    db.update_contact_message_status(msg_id, status)
    if status == 'resolved':
        message = db.get_contact_message_by_id(msg_id)
        if message and message['user_id']:
            notify_user(
                message['user_id'],
                'The administrator has responded to your message.',
                email_subject='Help R Circle - Response From Administrator',
                email_message='Hello,\n\nThe administrator has responded to your message. Please log in to Help R Circle to view the latest response.\n\nRegards,\nHelp R Circle Team',
                notification_type='admin_response',
                related_request_id=None,
            )
    flash_t("flash_status_updated", "✅ Message status updated to {status}.", "success", status=status)
    return redirect(url_for('admin_contact_messages'))


@app.route("/admin/contact-message/<int:msg_id>/respond", methods=["POST"])
@admin_required
def admin_respond_to_contact_message(msg_id):
    response = (request.form.get('response') or '').strip()
    if not response:
        flash_t('flash_contact_response_required', 'Please enter a response before sending.', 'error')
        return redirect(url_for('admin_contact_message_detail', msg_id=msg_id))

    message = db.get_contact_message_by_id(msg_id)
    if not message:
        flash_t('flash_message_not_found', 'Message not found.', 'error')
        return redirect(url_for('admin_contact_messages'))

    if message['user_id']:
        notify_user(
            message['user_id'],
            'The administrator has responded to your message.',
            email_subject='Help R Circle - Response From Administrator',
            email_message=(
                f"Hello,\n\n"
                "The administrator has responded to your message.\n\n"
                f"{response}\n\n"
                "Please log in to Help R Circle to view the latest response.\n\n"
                "Regards,\nHelp R Circle Team"
            ),
            notification_type='admin_response',
            related_request_id=None,
        )
    send_notification_email(message['email'], 'Help R Circle - Response From Administrator', (
        f"Hello,\n\n"
        "The administrator has responded to your message.\n\n"
        f"{response}\n\n"
        "Please log in to Help R Circle to view the latest response.\n\n"
        "Regards,\nHelp R Circle Team"
    ))
    db.update_contact_message_status(msg_id, 'resolved')
    flash_t('flash_response_sent', '✅ Response sent to the sender.', 'success')
    return redirect(url_for('admin_contact_message_detail', msg_id=msg_id))


@app.route("/admin/contact-message/<int:msg_id>/delete", methods=["POST"])
@admin_required
def admin_delete_contact_message(msg_id):
    """Delete a contact message."""
    if db.delete_contact_message(msg_id):
        flash_t("flash_message_deleted", "✅ Message deleted successfully.", "success")
    else:
        flash_t("flash_message_delete_failed", "Unable to delete message.", "error")
    return redirect(url_for('admin_contact_messages'))


@app.route("/request/<int:req_id>")
@login_required
def request_details(req_id):
    """Show the request detail page for a logged-in user or helper."""

    # Role-based access check
    if session.get('role') not in ['user', 'helper', 'admin']:
        flash_t(
            "flash_request_details_access",
            "Only requesters, helpers, and admins can view request details.",
            "error"
        )
        return redirect(url_for('index'))

    # Fetch the request
    req = db.get_request_by_id(req_id)

    if req:
        req = dict(req)

    if not req:
        flash_t(
            "flash_request_not_found",
            "Request not found.",
            "error"
        )
        return redirect(url_for('user_dashboard'))

    # Users can only view their own requests
    if session.get('role') == 'user':
        if not req.get('user_id') or req.get('user_id') != session.get('user_id'):
            flash_t(
                "flash_view_own_requests_only",
                "You can only view your own requests.",
                "error"
            )
            return redirect(url_for('user_dashboard'))

    req = dict(req)

    # Show helper contact once a helper is assigned
    helper_contact = None
    assigned_name = req.get('helper_name') or req.get('volunteer_name')
    assigned_phone = req.get('helper_phone') or req.get('volunteer_phone')
    assigned_email = req.get('helper_email') or req.get('volunteer_email')

    if (
        req.get('status') in (
            'helper_assigned',
            'helper_on_way',
            'helper_near_location',
            'helper_reached_location',
            'completed'
        )
        and req.get('volunteer_id')
        and assigned_name
    ):
        helper_contact = {
            'name': assigned_name,
            'phone': assigned_phone or '',
            'email': assigned_email or '',
            'availability': ''
        }

    # Check whether logged-in helper can update progress
    can_update_progress = False
    helper_can_view_requester_location = False

    if session.get('role') == 'helper':
        helper = db.get_helper_by_user_id(session.get('user_id'))

        if helper:
            helper = dict(helper)

        if helper and req.get('volunteer_id') == helper.get('id'):
            can_update_progress = True
        helper_can_view_requester_location = True

    return render_template(
        "request_details.html",
        req=req,
        helper_contact=helper_contact,
        can_update_progress=can_update_progress,
        helper_can_view_requester_location=helper_can_view_requester_location,
        status_label=get_status_label(req.get('status')),
        status_class=get_status_class(req.get('status')),
    )


# ── User Cancel a Request ───────────────────────────────────────────────────
@app.route("/user/cancel-request/<int:req_id>", methods=["POST"])
@login_required
def user_cancel_request(req_id):
    """Allow a requester to cancel their own request."""
    req = db.get_request_by_id(req_id)
    if not req:
        flash_t("flash_request_not_found", "Request not found.", "error")
        return redirect(url_for('user_dashboard'))

    if not req['user_id'] or req['user_id'] != session.get('user_id'):
        flash_t("flash_cancel_request_not_authorized", "You are not authorized to cancel this request.", "error")
        return redirect(url_for('user_dashboard'))

    if req['status'] == 'completed':
        flash_t("flash_completed_cancel_denied", "Completed requests cannot be cancelled.", "error")
        return redirect(url_for('user_dashboard'))

    previous_status = req['status']
    db.update_request_status(req_id, 'cancelled')
    notify_request_status_change(req_id, previous_status, 'cancelled')
    flash_t("flash_request_cancelled", "Request #{req_id} cancelled.", "info", req_id=req_id)
    return redirect(url_for('user_dashboard'))

# ── Accept a Request (AJAX or redirect) ───────────────────────────────────────
@app.route("/accept-request/<int:req_id>", methods=["POST"])
@helper_required
def accept_request(req_id):
    """Assign a request to the logged-in helper."""
    user_id = session.get('user_id')
    helper = db.get_helper_by_user_id(user_id)

    if not helper:
        user = db.get_user_by_id(user_id)
        if user:
            try:
                db.add_helper(
                    name=user.get('username', 'Helper'),
                    phone="",
                    email=user.get('email', ''),
                    location="",
                    skills="",
                    availability="",
                    about="",
                    user_id=user_id,
                )
                helper = db.get_helper_by_user_id(user_id)
            except Exception as exc:
                app.logger.exception("Failed to create helper record: %s", exc)

    if not helper:
        flash_t("flash_helper_profile_create_failed", "Unable to create helper profile.", "error")
        return redirect(url_for("dashboard"))

    helper = dict(helper)
    helper_name = helper.get('name', 'A helper')
    helper_email = helper.get('email', '')
    helper_phone = helper.get('phone', '')
    helper_location = helper.get('location', '')
    helper_id = helper.get('id', None)

    req = db.get_request_by_id(req_id)
    previous_status = req['status'] if req else None
    db.update_request_status(
        req_id,
        "accepted",
        helper_name=helper_name,
        helper_id=helper_id,
        helper_email=helper_email,
        helper_phone=helper_phone,
        helper_location=helper_location,
        accepted_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    )
    notify_request_status_change(req_id, previous_status, 'accepted')

    flash_t("flash_request_accepted", "✅ Request #{req_id} accepted by {helper_name}. The requester will receive your contact information.", "success", req_id=req_id, helper_name=helper_name)
    return redirect(url_for("dashboard"))

# ── Complete a Request ─────────────────────────────────────────────────────────
@app.route("/complete-request/<int:req_id>", methods=["POST"])
@helper_required
def complete_request(req_id):
    """Reject legacy direct completion; verification must happen through the code API."""
    flash_t("flash_completion_code_required", "Enter the verification code sent to the requester.", "error")
    return redirect(url_for('dashboard'))


def get_assigned_helper_request(req_id):
    req = db.get_request_by_id(req_id)
    helper = db.get_helper_by_user_id(session.get('user_id'))
    if req:
        req = dict(req)
    if helper:
        helper = dict(helper)
    if not req or not helper or req['volunteer_id'] != helper['id']:
        return None, None
    return req, helper


@app.route("/api/request/<int:req_id>/completion-code", methods=["POST"])
@helper_required
def request_completion_code(req_id):
    req, helper = get_assigned_helper_request(req_id)
    if not req:
        return jsonify({"ok": False, "error": "Not authorized for this request."}), 403
    if req['status'] == 'completed':
        return jsonify({"ok": False, "error": "This task has already been completed."}), 409
    if req['status'] not in ('helper_reached_location', 'arrived'):
        return jsonify({"ok": False, "error": "The task can only be completed after the helper has arrived."}), 409

    sent_at = datetime.now()
    if req.get('completion_code_sent_at'):
        try:
            previous_sent_at = datetime.strptime(req['completion_code_sent_at'], "%Y-%m-%d %H:%M:%S")
            if (sent_at - previous_sent_at).total_seconds() < COMPLETION_CODE_COOLDOWN_SECONDS:
                return jsonify({"ok": False, "error": "Please wait before requesting another code."}), 429
        except ValueError:
            pass

    requester = db.get_user_by_id(req.get('user_id')) if req.get('user_id') else None
    requester_email = requester['email'] if requester and requester['email'] else None
    if not requester_email:
        return jsonify({"ok": False, "error": "The requester does not have a registered email address."}), 422

    code = f"{secrets.randbelow(900000) + 100000:06d}"
    expires_at = sent_at + timedelta(minutes=COMPLETION_CODE_TTL_MINUTES)
    sent_at_text = sent_at.strftime("%Y-%m-%d %H:%M:%S")
    expires_at_text = expires_at.strftime("%Y-%m-%d %H:%M:%S")
    message = Message(
        subject=f"Help R Circle completion code for request #{req_id}",
        recipients=[requester_email],
        body=(
            f"Hello {requester['username']},\n\n"
            f"A helper has reported that Help R Circle request #{req_id} has arrived.\n"
            "Please provide this verification code to the helper only if the requested task was completed:\n\n"
            f"{code}\n\n"
            f"This code expires in {COMPLETION_CODE_TTL_MINUTES} minutes.\n\n"
            "If the task was not completed, do not share the code.\n\n"
            "Help R Circle Team"
        ),
    )
    try:
        mail.send(message)
    except Exception:
        app.logger.exception("Failed to send completion code for request %s", req_id)
        return jsonify({"ok": False, "error": "Unable to send the verification code. Please try again."}), 503

    saved = db.save_completion_code(
        req_id, helper['id'], generate_password_hash(code), expires_at_text, sent_at_text
    )
    if not saved:
        return jsonify({"ok": False, "error": "The task is no longer available for completion."}), 409
    return jsonify({"ok": True, "message": "A verification code has been sent to the user."})


@app.route("/api/request/<int:req_id>/verify-completion", methods=["POST"])
@helper_required
def verify_completion(req_id):
    req, helper = get_assigned_helper_request(req_id)
    if not req:
        return jsonify({"ok": False, "error": "Not authorized for this request."}), 403
    if req['status'] == 'completed':
        return jsonify({"ok": False, "error": "This task has already been completed."}), 409
    if req['status'] not in ('helper_reached_location', 'arrived'):
        return jsonify({"ok": False, "error": "The task can only be completed after the helper has arrived."}), 409

    code = (request.form.get('code') or '').strip()
    if not code.isdigit() or len(code) != 6:
        return jsonify({"ok": False, "error": "Invalid verification code. Please try again."}), 400
    if (req.get('completion_code_attempts') or 0) >= COMPLETION_CODE_MAX_ATTEMPTS:
        return jsonify({"ok": False, "error": "Too many invalid attempts. Please request a new code."}), 429
    if not req.get('completion_code_hash') or not req.get('completion_code_expires_at'):
        return jsonify({"ok": False, "error": "Verification code expired. Please request a new code."}), 400

    try:
        expires_at = datetime.strptime(req['completion_code_expires_at'], "%Y-%m-%d %H:%M:%S")
    except ValueError:
        expires_at = datetime.min
    if datetime.now() >= expires_at:
        return jsonify({"ok": False, "error": "Verification code expired. Please request a new code."}), 400

    if not check_password_hash(req['completion_code_hash'], code):
        db.increment_completion_code_attempts(req_id, COMPLETION_CODE_MAX_ATTEMPTS)
        return jsonify({"ok": False, "error": "Invalid verification code. Please try again."}), 400

    previous_status = req['status']
    completed_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    completed = db.complete_request_with_code(
        req_id, helper['id'], req['completion_code_hash'], completed_at, completed_at
    )
    if not completed:
        return jsonify({"ok": False, "error": "This task has already been completed."}), 409
    notify_request_status_change(req_id, previous_status, 'completed')
    return jsonify({"ok": True, "message": "Task completed."})

@app.route("/request/<int:req_id>/start-journey", methods=["POST"])
@helper_required
def start_journey(req_id):
    req = db.get_request_by_id(req_id)
    if req:
        req = dict(req)

    helper = db.get_helper_by_user_id(session.get('user_id'))
    if helper:
        helper = dict(helper)

    if not req or not helper or req['volunteer_id'] != helper['id']:
        flash("You are not authorized to update this request.", "error")
        return redirect(url_for('dashboard'))

    if req['status'] in (
        'helper_on_way', 'helper_near_location', 'helper_reached_location',
        'journey_started', 'near_location', 'arrived', 'completed'
    ):
        flash_t("flash_journey_already_started", "Journey has already been started.", "info")
        return redirect(url_for('request_details', req_id=req_id))

    lat = request.form.get('helper_latitude')
    lng = request.form.get('helper_longitude')
    try:
        lat = float(lat) if lat not in (None, '') else None
        lng = float(lng) if lng not in (None, '') else None
    except (TypeError, ValueError):
        lat = None
        lng = None
    if lat is not None and lng is not None and not valid_coordinate_pair(lat, lng):
        lat = None
        lng = None

    previous_status = req['status']
    started_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    started = db.start_journey_if_accepted(req_id, helper['id'], lat, lng, started_at)
    if started:
        notify_request_status_change(req_id, previous_status, 'helper_on_way')
        if lat is None or lng is None:
            flash_t("flash_journey_started_no_location", "🚗 Journey started. Location sharing is unavailable until GPS is enabled.", "info")
        else:
            flash_t("flash_journey_started", "🚗 Journey started for request #{req_id}.", "success", req_id=req_id)
    else:
        flash_t("flash_journey_already_started", "Journey has already been started.", "info")

    return redirect(url_for('request_details', req_id=req_id))

@app.route("/request/<int:req_id>/refresh-location", methods=["POST"])
@helper_required
def refresh_location(req_id):
    req = db.get_request_by_id(req_id)
    if req:
        req = dict(req)

    helper = db.get_helper_by_user_id(session.get('user_id'))
    if helper:
        helper = dict(helper)

    # Authorization check
    if not req or not helper or req['volunteer_id'] != helper['id']:
        flash("You are not authorized to update this request.", "error")
        return redirect(url_for('dashboard'))

    lat = request.form.get('helper_latitude')
    lng = request.form.get('helper_longitude')

    try:
        lat = float(lat) if lat not in (None, '') else None
        lng = float(lng) if lng not in (None, '') else None
    except (TypeError, ValueError):
        lat = None
        lng = None
    if lat is not None and lng is not None and not valid_coordinate_pair(lat, lng):
        lat = None
        lng = None

    previous_status = req['status'] or 'helper_assigned'
    status = req['status'] or 'helper_assigned'

    if (
        lat is not None
        and lng is not None
        and req['request_latitude'] is not None
        and req['request_longitude'] is not None
    ):
        distance_km = abs(lat - req['request_latitude']) * 111.0

        if distance_km <= 0.1:
            status = 'helper_reached_location'
        elif distance_km <= 0.5:
            status = 'helper_near_location'
        else:
            status = 'helper_on_way'

    db.update_request_status(
        req_id,
        status,
        helper_latitude=lat,
        helper_longitude=lng,
        last_location_update=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    )
    if status != previous_status:
        notify_request_status_change(req_id, previous_status, status)

    flash_t("flash_location_refreshed", "📍 Location refreshed for request #{req_id}.", "success", req_id=req_id)
    return redirect(url_for('request_details', req_id=req_id))
@app.route("/request/<int:req_id>/mark-reached", methods=["POST"])
@helper_required
def mark_reached(req_id):
    req = db.get_request_by_id(req_id)
    if req:
        req = dict(req)

    helper = db.get_helper_by_user_id(session.get('user_id'))
    if helper:
        helper = dict(helper)

    if not req or not helper or req['volunteer_id'] != helper['id']:
        flash_t("flash_request_update_not_authorized", "You are not authorized to update this request.", "error")
        return redirect(url_for('dashboard'))

    previous_status = req['status']
    db.update_request_status(
        req_id,
        "helper_reached_location",
        reached_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    )
    notify_request_status_change(req_id, previous_status, 'helper_reached_location')

    flash_t("flash_request_reached", "📍 Request #{req_id} marked as reached.", "success", req_id=req_id)
    return redirect(url_for("request_details", req_id=req_id))


@app.route("/cancel-request/<int:req_id>", methods=["POST"])
@helper_required
def cancel_request(req_id):
    req = db.get_request_by_id(req_id)
    previous_status = req['status'] if req else None
    db.update_request_status(req_id, "cancelled")
    notify_request_status_change(req_id, previous_status, 'cancelled')
    flash_t("flash_request_cancelled", "Request #{req_id} has been cancelled.", "info", req_id=req_id)
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


@app.route("/helper/update-location", methods=["POST"])
def helper_update_location():
    """Receive helper GPS points from the browser for a live-tracking request."""
    if not session.get('user_id'):
        return jsonify({"error": "Unauthorized"}), 401

    request_id = request.form.get("request_id", "").strip()
    latitude = request.form.get("latitude", "").strip()
    longitude = request.form.get("longitude", "").strip()

    if not request_id.isdigit():
        return jsonify({"error": "Invalid request id"}), 400

    try:
        latitude = float(latitude)
        longitude = float(longitude)
    except (TypeError, ValueError):
        return jsonify({"error": "Invalid coordinates"}), 400
    if not valid_coordinate_pair(latitude, longitude):
        return jsonify({"error": "Coordinates out of range"}), 400

    helper = db.get_helper_by_user_id(session.get('user_id'))
    if not helper:
        return jsonify({"error": "Helper profile not found"}), 404

    req = db.get_request_by_id(int(request_id))
    if not req or req['volunteer_id'] != helper['id']:
        return jsonify({"error": "Unauthorized for this request"}), 403

    db.save_helper_location(helper['id'], int(request_id), latitude, longitude)
    db.update_helper_coordinates(
        int(request_id), latitude, longitude,
        datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    )
    return jsonify({"ok": True})


@app.route('/api/helper/location', methods=['POST'])
def api_helper_location():
    """Store a live GPS point for the assigned helper without changing status."""
    if not session.get('user_id'):
        return jsonify({'ok': False, 'error': 'Unauthorized'}), 401
    if session.get('role') not in ('helper', 'helper'):
        return jsonify({'ok': False, 'error': 'Helper access required'}), 403
    data = request.form or request.get_json() or {}
    try:
        request_id = int(data.get('request_id'))
        latitude = float(data.get('latitude'))
        longitude = float(data.get('longitude'))
    except (TypeError, ValueError):
        return jsonify({'ok': False, 'error': 'Invalid request or coordinates'}), 400

    if not valid_coordinate_pair(latitude, longitude):
        return jsonify({'ok': False, 'error': 'Coordinates out of range'}), 400

    helper = db.get_helper_by_user_id(session.get('user_id'))
    req = db.get_request_by_id(request_id)
    if not helper or not req or req['volunteer_id'] != helper['id']:
        return jsonify({'ok': False, 'error': 'Not authorized for this request'}), 403
    if req['status'] in ('helper_reached_location', 'completed', 'cancelled'):
        return jsonify({'ok': False, 'error': 'Location tracking is no longer active'}), 409

    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    db.save_helper_location(helper['id'], request_id, latitude, longitude)
    db.update_helper_coordinates(request_id, latitude, longitude, now)
    return jsonify({
        'ok': True,
        'success': True,
        'request_id': request_id,
        'status': db.get_request_by_id(request_id)['status'],
        'latitude': latitude,
        'longitude': longitude,
        'updated_at': now,
    })


@app.route("/helper/location/<int:request_id>")
@app.route('/api/request/<int:request_id>/helper-location')
def helper_location(request_id):
    """Return the latest tracked helper location for a request."""
    req = db.get_request_by_id(request_id)
    if not req:
        return jsonify({"error": "Not found"}), 404

    helper = db.get_helper_by_user_id(session.get('user_id')) if session.get('role') == 'helper' else None
    requester_can_view = (
        session.get('role') in ('user', 'helper')
        and req['user_id'] == session.get('user_id')
    )
    authorized = (
        session.get('role') == 'admin'
        or requester_can_view
        or (helper and req['volunteer_id'] == helper['id'])
    )
    if not authorized:
        return jsonify({"error": "Unauthorized"}), 403

    if req['volunteer_id'] is None:
        return jsonify({
            "ok": True,
            "success": True,
            "available": False,
            "assigned_helper_id": None,
            "status": req['status'],
            "message": "Waiting for a helper to accept this request...",
        })

    location = db.get_latest_helper_location(request_id, req['volunteer_id'])
    if not location:
        return jsonify({"ok": True, "success": True, "available": False, "assigned_helper_id": req['volunteer_id'], "status": req['status'], "message": "Waiting for helper location..."})

    if not valid_coordinate_pair(location['latitude'], location['longitude']):
        return jsonify({
            "ok": True,
            "success": True,
            "available": False,
            "assigned_helper_id": req['volunteer_id'],
            "status": req['status'],
            "message": "Helper location is unavailable because the stored coordinates are invalid.",
        })
    if req['volunteer_id'] is None or location['helper_id'] != req['volunteer_id']:
        return jsonify({
            "ok": True,
            "success": True,
            "available": False,
            "status": req['status'],
            "message": "Waiting for helper location...",
        })

    route = get_route_eta(
        location['latitude'], location['longitude'],
        req['request_latitude'], req['request_longitude'],
    )
    route_data = route or {
        "distance_km": None,
        "duration_seconds": None,
        "eta_minutes": None,
        "route_coordinates": [],
    }

    return jsonify({
        "ok": True,
        "success": True,
        "available": True,
        "assigned_helper_id": req['volunteer_id'],
        "helper_id": location['helper_id'],
        "request_id": location['request_id'],
        "status": req['status'],
        "latitude": location['latitude'],
        "longitude": location['longitude'],
        "updated_at": location['updated_at'],
        "route_available": route is not None,
        **route_data,
    })

# ── About Page ────────────────────────────────────────────────────────────────
@app.route("/about")
def about():
    return render_template("about.html")

# ── Animated Logo Page ───────────────────────────────────────────────────────
@app.route("/logo")
def logo_view():
    return render_template("logo_view.html")

# ── Contact Page ──────────────────────────────────────────────────────────────
@app.route("/contact", methods=["GET", "POST"])
def contact():
    if session.get('role') == 'admin':
        flash_t("flash_admin_contact_management", "Administrators manage inquiries through the Contact Messages panel.", "info")
        return redirect(url_for('admin_contact_messages'))

    if request.method == "POST":
        name    = request.form.get("name", "").strip()
        email   = request.form.get("email", "").strip()
        message = request.form.get("message", "").strip()

        if not name or not email or not message:
            flash_t("flash_contact_fields_required", "Please fill in all required fields.", "error")
            return render_template("contact.html", form_data=request.form)

        user_id = session.get('user_id') if session.get('user_id') else None
        db.add_contact_message(name=name, email=email, message=message, user_id=user_id)
        send_contact_admin_notification({'email': email, 'name': name, 'message': message})
        flash_t("flash_contact_sent", "✅ Your message has been sent. We will reply within 24 hours.", "success")
        return redirect(url_for("contact"))

    return render_template("contact.html", form_data={})

# ── Track Request Status ───────────────────────────────────────────────────────
@app.route("/track", methods=["GET", "POST"])
@login_required
def track():
    """Allow requesters or helpers to check their request status by ID."""
    if session.get('role') not in ['user', 'helper', 'helper']:
        flash_t("flash_tracker_access", "Only requesters and helpers can track requests.", "error")
        return redirect(url_for('index'))

    if request.method == "POST":
        req_id = request.form.get("request_id", "").strip()
        if req_id.isdigit():
            return redirect(url_for('track_request', request_id=int(req_id)))
        flash_t("flash_invalid_request_id", "Please enter a valid numeric Request ID.", "error")

    return render_template("track.html", result=None)


@app.route("/track/<int:request_id>")
@login_required
def track_request(request_id):
    """Show the request tracking page for a specific request."""

    if session.get('role') not in ['user', 'helper', 'admin']:
        flash_t(
            "flash_tracker_access",
            "Only requesters and helpers can track requests.",
            "error"
        )
        return redirect(url_for('index'))

    result = db.get_request_by_id(request_id)

    if result:
        result = dict(result)

    if not result:
        flash_t(
            "flash_request_id_not_found",
            "No request found with ID #{request_id}.",
            "error",
            request_id=request_id
        )
        return redirect(url_for('track'))

    has_assigned_helper = bool(result.get('volunteer_id'))

    viewer_role = session.get('role')
    is_requester = result.get('user_id') == session.get('user_id')
    assigned_helper = db.get_helper_by_user_id(session.get('user_id')) if viewer_role == 'helper' else None
    is_assigned_helper = bool(assigned_helper and result.get('volunteer_id') == assigned_helper['id'])
    if not is_requester and not is_assigned_helper and viewer_role != 'admin':
        flash_t(
            "flash_track_own_requests_only",
            "You can only track requests you own or are assigned to.",
            "error"
        )
        return redirect(url_for('track'))

    # Show helper contact if request is accepted or completed
    helper_contact = None

    assigned_name = result.get('helper_name') or result.get('volunteer_name')
    assigned_phone = result.get('helper_phone') or result.get('volunteer_phone')
    assigned_email = result.get('helper_email') or result.get('volunteer_email')
    if (
        result.get('status') in (
            'accepted',
            'helper_assigned',
            'helper_on_way',
            'helper_near_location',
            'helper_reached_location',
            'completed'
        )
        and result.get('volunteer_id')
        and assigned_name
    ):
        helper_contact = {
            'name': assigned_name,
            'phone': assigned_phone or '',
            'email': assigned_email or '',
            'availability': ''
        }

    return render_template(
        "track.html",
        result=result,
        has_assigned_helper=has_assigned_helper,
        helper_contact=helper_contact,
        viewer_role='requester' if is_requester else ('assigned_helper' if is_assigned_helper else 'admin'),
    )
# ── Profile Routes ──────────────────────────────────────────────────────────
@app.route("/profile", methods=["GET", "POST"])
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
    
    elif user['role'] == 'helper':
        # Helper profile: ensure helper row exists; auto-create if missing
        app.logger.info("Profile access: session user_id=%s role=%s", session.get('user_id'), session.get('role'))
        helper = db.get_helper_by_user_id(user_id)
        app.logger.info("Helper lookup result: %s", str(helper))
        if not helper:
            app.logger.info("No helper record found for user_id=%s — attempting to create one.", user_id)
            try:
                created = db.add_helper(
                    name=user['username'], phone="", email=user.get('email',''),
                    location="", skills="", availability="", about="", user_id=user_id
                )
                app.logger.info("add_helper returned: %s", str(created))
            except Exception as e:
                app.logger.exception("Failed to create helper record: %s", e)

            # Re-fetch after attempted creation
            helper = db.get_helper_by_user_id(user_id)

        if not helper:
            flash_t("flash_helper_profile_not_found", "Your helper profile could not be found. Please contact support.", "error")
            return redirect(url_for('index'))

        activity_stats = db.get_helper_activity_stats(helper['name'])
        return render_template("profile_helper.html", user=user, 
                             helper=helper, stats=activity_stats)
    
    elif user['role'] == 'admin':
        if request.method == "POST":
            current_password = request.form.get("current_password", "")
            new_password = request.form.get("new_password", "")
            confirm_password = request.form.get("confirm_password", "")

            if not current_password or not new_password or not confirm_password:
                flash_t("flash_password_fields_required", "Current password, new password, and confirmation are required.", "error")
            elif not check_password_hash(user['password_hash'], current_password):
                flash_t("flash_current_password_incorrect", "Current password is incorrect.", "error")
            elif new_password != confirm_password:
                flash_t("flash_passwords_do_not_match", "New passwords do not match.", "error")
            elif new_password == current_password:
                flash_t("flash_password_must_change", "New password must be different from the current password.", "error")
            elif db.update_user_password(user_id, new_password):
                flash_t("flash_password_updated", "Password changed successfully.", "success")
                user = db.get_user_by_id(user_id)
            else:
                flash_t("flash_password_update_failed", "Unable to change password. Please try again.", "error")
        return render_template("profile_admin.html", user=user)

    flash_t("flash_invalid_user_role", "Invalid user role.", "error")
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
        latitude, longitude = parse_profile_coordinates(
            request.form.get("location_latitude"), request.form.get("location_longitude")
        )
        
        # Validation
        errors = []
        if not username or len(username) < 3:
            errors.append(("flash_username_min_length", "Username must be at least 3 characters."))
        if not email or "@" not in email:
            errors.append(("flash_valid_email_required", "Please enter a valid email."))
        if not normalize_indian_phone(phone):
            errors.append(("flash_phone_invalid", "Enter a valid 10-digit Indian mobile number."))
        if not location:
            errors.append(("flash_location_required", "Location / Address is required."))
        
        if errors:
            for key, default in errors:
                flash_t(key, default, "error")
        else:
            try:
                # Check if email is already taken by another user
                existing = db.get_user_by_email(email)
                if existing and existing['id'] != user_id:
                    flash_t("flash_email_in_use", "Email already in use.", "error")
                else:
                    db.update_user_profile(
                        user_id, username, email, normalize_indian_phone(phone),
                        location or user.get('location') or None, latitude, longitude
                    )
                    session['username'] = username
                    flash_t("flash_profile_updated", "✅ Profile updated successfully!", "success")
                    return redirect(url_for('profile'))
            except Exception as e:
                flash(f"Error updating profile: {str(e)}", "error")
    
    return render_template("edit_profile.html", user=user)


@app.route("/profile/edit-helper", methods=["GET", "POST"])
@login_required
def edit_profile_helper():
    """Allow helpers to edit their profile."""
    user_id = session.get('user_id')
    user = db.get_user_by_id(user_id)
    if user:
        user = dict(user)
    
    if not user or user['role'] not in ('helper', 'helper'):
        flash_t("flash_helper_access_required", "You must be a helper to access this page.", "error")
        return redirect(url_for('index'))
    
    helper = db.get_helper_by_user_id(user_id)
    if not helper:
        flash_t("flash_helper_profile_missing", "Helper profile not found.", "error")
        return redirect(url_for('profile'))
    
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip()
        phone = request.form.get("phone", "").strip()
        location = request.form.get("location", "").strip()
        skills = request.form.get("skills", "").strip()
        availability = request.form.get("availability", "").strip()
        about = request.form.get("about", "").strip()
        latitude, longitude = parse_profile_coordinates(
            request.form.get("location_latitude"), request.form.get("location_longitude")
        )
        
        # Validation
        errors = []
        if not name or len(name) < 3:
            errors.append(("flash_name_required", "Name must be at least 3 characters."))
        if not email or "@" not in email:
            errors.append(("flash_valid_email_required", "Please enter a valid email."))
        if not normalize_indian_phone(phone):
            errors.append(("flash_phone_invalid", "Enter a valid 10-digit Indian mobile number."))
        if not location:
            errors.append(("flash_location_required", "Location is required."))
        if not skills:
            errors.append(("flash_skills_required", "Skills are required."))
        if not availability:
            errors.append(("flash_availability_required", "Availability is required."))
        
        if errors:
            for key, default in errors:
                flash_t(key, default, "error")
        else:
            try:
                existing_user = db.get_user_by_email(email)
                if existing_user and existing_user['id'] != user_id:
                    flash_t("flash_email_in_use", "Email already in use.", "error")
                else:
                    normalized_phone = normalize_indian_phone(phone)
                    db.update_user_profile(
                        user_id, name, email, normalized_phone,
                        location or user.get('location') or None, latitude, longitude
                    )
                    db.update_helper_profile(
                        helper['id'], name, normalized_phone, email,
                        location or helper.get('location') or '', skills, availability, about,
                        latitude, longitude
                    )
                    session['username'] = name
                    flash_t("flash_helper_profile_updated", "✅ Helper profile updated successfully!", "success")
                    return redirect(url_for('profile'))
            except Exception as e:
                flash(f"Error updating profile: {str(e)}", "error")
    
    return render_template("edit_profile_helper.html", user=user, helper=helper)

# ── Run ───────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    db.init_db()          # Create tables if they don't exist
    db.seed_sample_data() # Add sample data for demonstration
    app.run(debug=True, port=5000)


@app.route("/debug/helpers")
def debug_helpers():
    # Use the application's Database context manager to avoid direct sqlite connects
    with db.connect() as conn:
        users = conn.execute("SELECT id, username, email, role FROM users WHERE role='helper'").fetchall()
        # Use the helper records table for helper profiles
        helpers = conn.execute("SELECT * FROM helper_profiles").fetchall()
    return {"users": [dict(u) for u in users], "helpers": [dict(v) for v in helpers]}
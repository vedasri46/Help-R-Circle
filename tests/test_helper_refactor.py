import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "local_helper_network"))

import app as app_module
from database import Database
TARGET_FILES = [
    ROOT / "local_helper_network" / "app.py",
    ROOT / "local_helper_network" / "templates" / "base.html",
    ROOT / "local_helper_network" / "templates" / "index.html",
    ROOT / "local_helper_network" / "templates" / "signup.html",
    ROOT / "local_helper_network" / "templates" / "dashboard.html",
    ROOT / "local_helper_network" / "templates" / "request_details.html",
    ROOT / "local_helper_network" / "templates" / "request_help.html",
    ROOT / "local_helper_network" / "templates" / "profile_volunteer.html",
    ROOT / "local_helper_network" / "templates" / "edit_profile_volunteer.html",
    ROOT / "local_helper_network" / "templates" / "volunteer.html",
    ROOT / "local_helper_network" / "templates" / "admin_dashboard.html",
    ROOT / "local_helper_network" / "templates" / "admin_contact_messages.html",
    ROOT / "local_helper_network" / "templates" / "admin_contact_message_detail.html",
    ROOT / "local_helper_network" / "static" / "js" / "main.js",
    ROOT / "local_helper_network" / "static" / "css" / "style.css",
]


def test_no_visible_volunteer_terms_remain_in_primary_app_files():
    for path in TARGET_FILES:
        assert path.exists(), f"Missing expected file: {path}"
        text = path.read_text(encoding="utf-8")
        assert "Volunteer" not in text, f"Volunteer term remains in {path}"
        assert "Volunteers" not in text, f"Volunteers term remains in {path}"
        assert "volunteer" not in text, f"volunteer term remains in {path}"
        assert "volunteers" not in text, f"volunteers term remains in {path}"


def test_translation_files_exist_for_all_supported_locales():
    translations_dir = ROOT / "local_helper_network" / "translations"
    for locale in ["en", "te", "hi"]:
        path = translations_dir / f"{locale}.json"
        assert path.exists(), f"Missing translation file for {locale}"
        data = path.read_text(encoding="utf-8")
        assert data.strip(), f"Translation file for {locale} is empty"


def test_core_dashboard_request_and_tracking_keys_exist_in_all_locales():
    translations_dir = ROOT / "local_helper_network" / "translations"
    required_keys = [
        "dashboard_welcome_title",
        "dashboard_available_requests",
        "request_help_title",
        "request_help_form_title",
        "track_page_title",
        "track_request_id_heading",
    ]
    for locale in ["en", "te", "hi"]:
        path = translations_dir / f"{locale}.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        for key in required_keys:
            assert key in data, f"Missing translation key {key} in {locale}"


def test_contact_page_no_longer_renders_email_us_button_or_mailto_link():
    template_path = ROOT / "local_helper_network" / "templates" / "contact.html"
    html = template_path.read_text(encoding="utf-8")

    assert 'Email Us' not in html
    assert 'mailto:helprcircle.support@gmail.com' not in html
    assert 'helprcircle.support@gmail.com' in html


def test_popup_and_flash_message_keys_exist_in_all_locales():
    translations_dir = ROOT / "local_helper_network" / "translations"
    required_keys = [
        "flash_helper_required",
        "flash_requester_only",
        "flash_admin_only",
        "flash_account_created",
        "flash_email_taken",
        "flash_valid_email_required",
        "flash_verification_sent",
        "flash_verification_failed",
        "flash_unverified_email",
        "flash_admin_login_hint",
        "flash_logged_out",
        "flash_login_to_request",
        "flash_login_to_dashboard",
        "flash_only_helpers_dashboard",
        "flash_contact_fields_required",
        "flash_contact_sent",
        "flash_request_submitted",
        "confirm_delete_message",
        "confirm_delete_user",
        "confirm_delete_helper",
        "confirm_delete_request",
        "confirm_cancel_request",
        "otp_validation_error",
    ]
    for locale in ["en", "te", "hi"]:
        path = translations_dir / f"{locale}.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        for key in required_keys:
            assert key in data, f"Missing popup translation key {key} in {locale}"


def test_helper_tracking_routes_and_storage_helpers_exist():
    db = Database()
    assert hasattr(db, "save_helper_location")
    assert hasattr(db, "get_latest_helper_location")

    rules = {rule.rule for rule in app_module.app.url_map.iter_rules()}
    assert "/helper/update-location" in rules
    assert "/helper/location/<int:request_id>" in rules

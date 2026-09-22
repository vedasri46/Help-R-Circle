import sys
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "local_helper_network"))

import database as db_module
from database import Database


def test_default_admin_is_created_during_init_db(tmp_path, monkeypatch):
    db_path = tmp_path / "test-admin.db"
    monkeypatch.setattr(db_module, "DB_PATH", str(db_path))

    db = Database()
    db.init_db()

    user = db.get_user_by_email("support.helprcircle@gmail.com")
    assert user is not None
    assert user["role"] == "admin"
    assert user["username"] == "Help R Circle Admin"
    assert db.login_user("support.helprcircle@gmail.com", "admin@123") is not None

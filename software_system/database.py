from __future__ import annotations

import sqlite3
from pathlib import Path

from flask import current_app, g
from werkzeug.security import generate_password_hash


def get_db() -> sqlite3.Connection:
    if "db" not in g:
        db_path = Path(current_app.config["DATABASE"])
        db_path.parent.mkdir(parents=True, exist_ok=True)

        connection = sqlite3.connect(db_path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        g.db = connection

    return g.db


def close_db(_error: Exception | None = None) -> None:
    connection = g.pop("db", None)
    if connection is not None:
        connection.close()


def init_db() -> None:
    schema_path = Path(__file__).with_name("schema.sql")
    schema = schema_path.read_text(encoding="utf-8")
    db = get_db()
    db.executescript(schema)
    db.commit()


def ensure_default_admin() -> None:
    db = get_db()
    existing_admin = db.execute("SELECT id FROM admins LIMIT 1").fetchone()
    if existing_admin is not None:
        return

    username = current_app.config["DEFAULT_ADMIN_USERNAME"]
    password = current_app.config["DEFAULT_ADMIN_PASSWORD"]

    db.execute(
        "INSERT INTO admins (username, password_hash) VALUES (?, ?)",
        (username, generate_password_hash(password)),
    )
    db.commit()


def init_app(app) -> None:
    app.teardown_appcontext(close_db)

    with app.app_context():
        init_db()
        ensure_default_admin()

from __future__ import annotations

import sqlite3
from datetime import date, datetime, timedelta
from typing import Any

from flask import current_app
from werkzeug.security import check_password_hash

from .database import get_db


TIMESTAMP_FORMAT = "%Y-%m-%d %H:%M:%S"


def now_string() -> str:
    return datetime.now().replace(microsecond=0).strftime(TIMESTAMP_FORMAT)


def normalize_uid(raw_uid: Any) -> str:
    uid = str(raw_uid or "").strip().upper()
    if not uid:
        raise ValueError("RFID UID is required.")
    return uid


def serialize_row(row) -> dict[str, Any]:
    return dict(row) if row is not None else {}


def serialize_rows(rows) -> list[dict[str, Any]]:
    return [dict(row) for row in rows]


def authenticate_admin(username: str, password: str):
    db = get_db()
    admin = db.execute(
        "SELECT * FROM admins WHERE username = ?",
        (username.strip(),),
    ).fetchone()

    if admin is None:
        return None

    if not check_password_hash(admin["password_hash"], password):
        return None

    return serialize_row(admin)


def create_user(name: str, rfid_uid: str, role: str = "student", is_active: bool = True) -> dict[str, Any]:
    clean_name = (name or "").strip()
    clean_role = (role or "student").strip().lower()
    clean_uid = normalize_uid(rfid_uid)

    if not clean_name:
        raise ValueError("Name is required.")

    db = get_db()

    try:
        cursor = db.execute(
            """
            INSERT INTO users (name, rfid_uid, role, is_active, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (clean_name, clean_uid, clean_role, int(bool(is_active)), now_string()),
        )
        db.commit()
    except sqlite3.IntegrityError as exc:
        raise ValueError("That RFID UID is already registered.") from exc

    return get_user_by_id(cursor.lastrowid)


def get_user_by_id(user_id: int):
    db = get_db()
    user = db.execute(
        "SELECT * FROM users WHERE id = ?",
        (user_id,),
    ).fetchone()
    return serialize_row(user) if user else None


def list_users() -> list[dict[str, Any]]:
    db = get_db()
    users = db.execute(
        """
        SELECT id, name, rfid_uid, role, is_active, created_at
        FROM users
        ORDER BY is_active DESC, name COLLATE NOCASE ASC
        """
    ).fetchall()
    return serialize_rows(users)


def update_user(user_id: int, payload: dict[str, Any]):
    existing = get_user_by_id(user_id)
    if existing is None:
        raise LookupError("User not found.")

    name = (payload.get("name", existing["name"]) or "").strip()
    role = (payload.get("role", existing["role"]) or "student").strip().lower()
    uid = normalize_uid(payload.get("rfid_uid", existing["rfid_uid"]))
    is_active = payload.get("is_active", existing["is_active"])

    if not name:
        raise ValueError("Name is required.")

    db = get_db()

    try:
        db.execute(
            """
            UPDATE users
            SET name = ?, rfid_uid = ?, role = ?, is_active = ?
            WHERE id = ?
            """,
            (name, uid, role, int(bool(is_active)), user_id),
        )
        db.commit()
    except sqlite3.IntegrityError as exc:
        raise ValueError("That RFID UID is already registered.") from exc

    return get_user_by_id(user_id)


def delete_user(user_id: int) -> None:
    db = get_db()
    cursor = db.execute("DELETE FROM users WHERE id = ?", (user_id,))
    db.commit()

    if cursor.rowcount == 0:
        raise LookupError("User not found.")


def should_skip_duplicate(uid: str, status: str) -> bool:
    db = get_db()
    latest_scan = db.execute(
        """
        SELECT status, created_at
        FROM attendance_records
        WHERE rfid_uid = ?
        ORDER BY created_at DESC, id DESC
        LIMIT 1
        """,
        (uid,),
    ).fetchone()

    if latest_scan is None or latest_scan["status"] != status:
        return False

    last_seen = datetime.strptime(latest_scan["created_at"], TIMESTAMP_FORMAT)
    duplicate_window = timedelta(
        seconds=int(current_app.config["DUPLICATE_SCAN_WINDOW_SECONDS"])
    )
    return datetime.now() - last_seen <= duplicate_window


def process_scan(rfid_uid: str, source: str = "raspberry_pi") -> dict[str, Any]:
    uid = normalize_uid(rfid_uid)
    clean_source = (source or "raspberry_pi").strip()[:50] or "raspberry_pi"

    db = get_db()
    user = db.execute(
        "SELECT * FROM users WHERE rfid_uid = ?",
        (uid,),
    ).fetchone()

    status = "denied"
    note = "Unknown RFID card."
    user_id = None
    person_name = None
    role = None

    if user is not None and int(user["is_active"]) == 1:
        status = "granted"
        note = f"Access granted for {user['name']}."
        user_id = user["id"]
        person_name = user["name"]
        role = user["role"]
    elif user is not None:
        status = "denied"
        note = f"{user['name']}'s card is registered but inactive."
        user_id = user["id"]
        person_name = user["name"]
        role = user["role"]

    if should_skip_duplicate(uid, status):
        return {
            "access_granted": status == "granted",
            "status": status,
            "message": "Duplicate scan ignored to avoid repeated attendance logs.",
            "logged": False,
            "duplicate_scan": True,
            "user": {
                "id": user_id,
                "name": person_name,
                "role": role,
            }
            if user_id is not None
            else None,
        }

    db.execute(
        """
        INSERT INTO attendance_records
        (user_id, rfid_uid, person_name, role, status, source, note, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (user_id, uid, person_name, role, status, clean_source, note, now_string()),
    )
    db.commit()

    return {
        "access_granted": status == "granted",
        "status": status,
        "message": note,
        "logged": True,
        "duplicate_scan": False,
        "user": {
            "id": user_id,
            "name": person_name,
            "role": role,
        }
        if user_id is not None
        else None,
    }


def get_recent_attendance(limit: int = 25) -> list[dict[str, Any]]:
    safe_limit = max(1, min(int(limit), 200))
    db = get_db()
    rows = db.execute(
        """
        SELECT
            id,
            user_id,
            COALESCE(person_name, 'Unknown Card') AS person_name,
            COALESCE(role, 'unknown') AS role,
            rfid_uid,
            status,
            source,
            note,
            created_at
        FROM attendance_records
        ORDER BY created_at DESC, id DESC
        LIMIT ?
        """,
        (safe_limit,),
    ).fetchall()
    return serialize_rows(rows)


def get_summary() -> dict[str, Any]:
    db = get_db()
    summary = db.execute(
        """
        SELECT
            (SELECT COUNT(*) FROM users) AS total_users,
            (SELECT COUNT(*) FROM users WHERE is_active = 1) AS active_users,
            (
                SELECT COUNT(*)
                FROM attendance_records
                WHERE DATE(created_at) = DATE('now', 'localtime')
            ) AS scans_today,
            (
                SELECT COUNT(*)
                FROM attendance_records
                WHERE DATE(created_at) = DATE('now', 'localtime') AND status = 'granted'
            ) AS granted_today,
            (
                SELECT COUNT(*)
                FROM attendance_records
                WHERE DATE(created_at) = DATE('now', 'localtime') AND status = 'denied'
            ) AS denied_today,
            (
                SELECT created_at
                FROM attendance_records
                ORDER BY created_at DESC, id DESC
                LIMIT 1
            ) AS latest_scan_at
        """
    ).fetchone()

    data = serialize_row(summary)
    return {
        "total_users": data.get("total_users", 0),
        "active_users": data.get("active_users", 0),
        "scans_today": data.get("scans_today", 0),
        "granted_today": data.get("granted_today", 0),
        "denied_today": data.get("denied_today", 0),
        "latest_scan_at": data.get("latest_scan_at"),
    }


def get_chart_data(days: int = 7) -> dict[str, Any]:
    safe_days = max(1, min(int(days), 30))
    start_day = date.today() - timedelta(days=safe_days - 1)

    db = get_db()
    rows = db.execute(
        """
        SELECT DATE(created_at) AS day, status, COUNT(*) AS total
        FROM attendance_records
        WHERE DATE(created_at) >= ?
        GROUP BY DATE(created_at), status
        ORDER BY DATE(created_at) ASC
        """,
        (start_day.isoformat(),),
    ).fetchall()

    granted_by_day: dict[str, int] = {}
    denied_by_day: dict[str, int] = {}
    for row in rows:
        if row["status"] == "granted":
            granted_by_day[row["day"]] = row["total"]
        else:
            denied_by_day[row["day"]] = row["total"]

    labels = []
    granted = []
    denied = []

    for offset in range(safe_days):
        current_day = start_day + timedelta(days=offset)
        iso_day = current_day.isoformat()
        labels.append(current_day.strftime("%b %d"))
        granted.append(granted_by_day.get(iso_day, 0))
        denied.append(denied_by_day.get(iso_day, 0))

    return {"labels": labels, "granted": granted, "denied": denied}


def get_attendance_export_rows() -> list[dict[str, Any]]:
    db = get_db()
    rows = db.execute(
        """
        SELECT
            id,
            created_at,
            COALESCE(person_name, 'Unknown Card') AS person_name,
            COALESCE(role, 'unknown') AS role,
            rfid_uid,
            status,
            source,
            note
        FROM attendance_records
        ORDER BY created_at DESC, id DESC
        """
    ).fetchall()
    return serialize_rows(rows)

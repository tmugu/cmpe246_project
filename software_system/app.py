from __future__ import annotations

import csv
import io
import os
from functools import wraps
from pathlib import Path

from flask import (
    Flask,
    Response,
    current_app,
    flash,
    jsonify,
    redirect,
    render_template,
    request,
    session,
    url_for,
)

from .database import init_app as init_database
from .services import (
    authenticate_admin,
    create_user,
    delete_user,
    get_attendance_export_rows,
    get_chart_data,
    get_recent_attendance,
    get_summary,
    list_users,
    process_scan,
    update_user,
)


BASE_DIR = Path(__file__).resolve().parent


def admin_required(view):
    @wraps(view)
    def wrapped_view(*args, **kwargs):
        if "admin_id" not in session:
            return redirect(url_for("login"))
        return view(*args, **kwargs)

    return wrapped_view


def device_required(view):
    @wraps(view)
    def wrapped_view(*args, **kwargs):
        provided_key = request.headers.get("X-API-Key", "")
        expected_key = current_app.config["DEVICE_API_KEY"]
        if provided_key != expected_key:
            return jsonify({"error": "Unauthorized device request."}), 401
        return view(*args, **kwargs)

    return wrapped_view


def create_app(test_config: dict | None = None) -> Flask:
    app = Flask(
        __name__,
        template_folder=str(BASE_DIR / "templates"),
        static_folder=str(BASE_DIR / "static"),
    )

    app.config.from_mapping(
        SECRET_KEY=os.environ.get("SECRET_KEY", "cmpe246-dev-secret"),
        DATABASE=str(BASE_DIR / "data" / "access_control.db"),
        DEVICE_API_KEY=os.environ.get("DEVICE_API_KEY", "cmpe246-device-key"),
        DUPLICATE_SCAN_WINDOW_SECONDS=int(
            os.environ.get("DUPLICATE_SCAN_WINDOW_SECONDS", "10")
        ),
        DEFAULT_ADMIN_USERNAME=os.environ.get("ADMIN_USERNAME", "admin"),
        DEFAULT_ADMIN_PASSWORD=os.environ.get("ADMIN_PASSWORD", "123"),
    )

    if test_config:
        app.config.update(test_config)

    init_database(app)

    @app.route("/health")
    def health():
        return jsonify({"status": "ok"})

    @app.route("/")
    def index():
        if "admin_id" in session:
            return redirect(url_for("dashboard"))
        return redirect(url_for("login"))

    @app.route("/login", methods=["GET", "POST"])
    def login():
        if "admin_id" in session:
            return redirect(url_for("dashboard"))

        if request.method == "POST":
            username = request.form.get("username", "")
            password = request.form.get("password", "")
            admin = authenticate_admin(username, password)

            if admin is None:
                flash("Invalid username or password.", "error")
            else:
                session.clear()
                session["admin_id"] = admin["id"]
                session["admin_username"] = admin["username"]
                flash("Signed in successfully.", "success")
                return redirect(url_for("dashboard"))

        return render_template("login.html", body_class="login-body")

    @app.route("/logout", methods=["POST"])
    @admin_required
    def logout():
        session.clear()
        flash("You have been signed out.", "success")
        return redirect(url_for("login"))

    @app.route("/dashboard")
    @admin_required
    def dashboard():
        return render_template(
            "dashboard.html",
            body_class="dashboard-body",
            admin_username=session.get("admin_username", "admin"),
            summary=get_summary(),
            users=list_users(),
            recent_attendance=get_recent_attendance(limit=20),
            chart_data=get_chart_data(days=7),
        )

    @app.route("/api/scan", methods=["POST"])
    @device_required
    def api_scan():
        payload = request.get_json(silent=True) or {}
        rfid_uid = payload.get("rfid_uid")
        source = payload.get("source", "raspberry_pi")

        try:
            result = process_scan(rfid_uid=rfid_uid, source=source)
        except ValueError as exc:
            return jsonify({"error": str(exc)}), 400

        return jsonify(result)

    @app.route("/api/users", methods=["GET", "POST"])
    @admin_required
    def api_users():
        if request.method == "GET":
            return jsonify(list_users())

        payload = request.get_json(silent=True) or {}
        try:
            user = create_user(
                name=payload.get("name", ""),
                rfid_uid=payload.get("rfid_uid", ""),
                role=payload.get("role", "student"),
                is_active=payload.get("is_active", True),
            )
        except ValueError as exc:
            return jsonify({"error": str(exc)}), 400

        return jsonify(user), 201

    @app.route("/api/users/<int:user_id>", methods=["PATCH", "DELETE"])
    @admin_required
    def api_user_detail(user_id: int):
        if request.method == "DELETE":
            try:
                delete_user(user_id)
            except LookupError as exc:
                return jsonify({"error": str(exc)}), 404

            return jsonify({"deleted": True})

        payload = request.get_json(silent=True) or {}
        try:
            user = update_user(user_id, payload)
        except LookupError as exc:
            return jsonify({"error": str(exc)}), 404
        except ValueError as exc:
            return jsonify({"error": str(exc)}), 400

        return jsonify(user)

    @app.route("/api/attendance")
    @admin_required
    def api_attendance():
        limit = request.args.get("limit", 25)
        return jsonify(get_recent_attendance(limit=limit))

    @app.route("/api/summary")
    @admin_required
    def api_summary():
        return jsonify(get_summary())

    @app.route("/api/charts/attendance")
    @admin_required
    def api_chart_attendance():
        days = request.args.get("days", 7)
        return jsonify(get_chart_data(days=days))

    @app.route("/export/attendance.csv")
    @admin_required
    def export_attendance():
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(
            [
                "Record ID",
                "Timestamp",
                "Name",
                "Role",
                "RFID UID",
                "Status",
                "Source",
                "Note",
            ]
        )

        for row in get_attendance_export_rows():
            writer.writerow(
                [
                    row["id"],
                    row["created_at"],
                    row["person_name"],
                    row["role"],
                    row["rfid_uid"],
                    row["status"],
                    row["source"],
                    row["note"],
                ]
            )

        csv_data = output.getvalue()
        output.close()

        return Response(
            csv_data,
            mimetype="text/csv",
            headers={
                "Content-Disposition": "attachment; filename=attendance_export.csv"
            },
        )

    return app

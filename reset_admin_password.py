import os
import sys

from werkzeug.security import generate_password_hash

from software_system import create_app
from software_system.database import get_db


def main():
    username = os.environ.get("ADMIN_USERNAME", "admin")
    password = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("NEW_ADMIN_PASSWORD", "123")

    app = create_app()
    with app.app_context():
        db = get_db()
        existing = db.execute(
            "SELECT id FROM admins WHERE username = ?",
            (username,),
        ).fetchone()

        if existing is None:
            db.execute(
                "INSERT INTO admins (username, password_hash) VALUES (?, ?)",
                (username, generate_password_hash(password)),
            )
        else:
            db.execute(
                "UPDATE admins SET password_hash = ? WHERE username = ?",
                (generate_password_hash(password), username),
            )
        db.commit()

    print(f"Admin password updated for '{username}'.")


if __name__ == "__main__":
    main()

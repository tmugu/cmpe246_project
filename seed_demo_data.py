from datetime import datetime, timedelta
import random

from software_system import create_app
from software_system.database import get_db


DEMO_USERS = [
    ("Murat Guvenc", "72-134-55-21", "admin"),
    ("Alex Johnson", "88-201-14-92", "student"),
    ("Priya Patel", "45-167-203-11", "student"),
    ("Daniel Kim", "19-88-144-66", "student"),
    ("Sara Lopez", "210-5-77-132", "faculty"),
]


def seed():
    app = create_app()
    with app.app_context():
        db = get_db()

        existing = db.execute("SELECT COUNT(*) AS c FROM users").fetchone()["c"]
        if existing > 0:
            print(f"Seed skipped: {existing} users already exist.")
            return

        now = datetime.now()

        for name, uid, role in DEMO_USERS:
            db.execute(
                "INSERT INTO users (name, rfid_uid, role, is_active, created_at) VALUES (?, ?, ?, 1, ?)",
                (name, uid, role, now.strftime("%Y-%m-%d %H:%M:%S")),
            )

        users = db.execute("SELECT id, name, rfid_uid, role FROM users").fetchall()

        for day_offset in range(6, -1, -1):
            day = now - timedelta(days=day_offset)
            for _ in range(random.randint(4, 9)):
                user = random.choice(users)
                status = "granted" if random.random() > 0.2 else "denied"
                ts = day.replace(
                    hour=random.randint(8, 18),
                    minute=random.randint(0, 59),
                    second=random.randint(0, 59),
                )
                note = (
                    f"Access granted for {user['name']}."
                    if status == "granted"
                    else f"{user['name']}'s card was denied."
                )
                db.execute(
                    """
                    INSERT INTO attendance_records
                    (user_id, rfid_uid, person_name, role, status, source, note, created_at)
                    VALUES (?, ?, ?, ?, ?, 'raspberry_pi', ?, ?)
                    """,
                    (
                        user["id"],
                        user["rfid_uid"],
                        user["name"],
                        user["role"],
                        status,
                        note,
                        ts.strftime("%Y-%m-%d %H:%M:%S"),
                    ),
                )

        for _ in range(3):
            fake_uid = f"99-{random.randint(10,99)}-{random.randint(10,99)}-{random.randint(10,99)}"
            ts = now - timedelta(hours=random.randint(1, 48))
            db.execute(
                """
                INSERT INTO attendance_records
                (user_id, rfid_uid, person_name, role, status, source, note, created_at)
                VALUES (NULL, ?, NULL, NULL, 'denied', 'raspberry_pi', 'Unknown RFID card.', ?)
                """,
                (fake_uid, ts.strftime("%Y-%m-%d %H:%M:%S")),
            )

        db.commit()
        print("Seed completed: demo users and attendance records created.")


if __name__ == "__main__":
    seed()

CREATE TABLE IF NOT EXISTS admins (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    rfid_uid TEXT NOT NULL UNIQUE,
    role TEXT NOT NULL DEFAULT 'student',
    is_active INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS attendance_records (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    rfid_uid TEXT NOT NULL,
    person_name TEXT,
    role TEXT,
    status TEXT NOT NULL CHECK (status IN ('granted', 'denied')),
    source TEXT NOT NULL DEFAULT 'rfid_reader',
    note TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS idx_users_rfid_uid ON users(rfid_uid);
CREATE INDEX IF NOT EXISTS idx_attendance_created_at ON attendance_records(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_attendance_rfid_uid ON attendance_records(rfid_uid);

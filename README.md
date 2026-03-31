# CMPE 246 — Smart IoT Access Control & Attendance System

An RFID-based access control system built with a Raspberry Pi and a Flask web dashboard. When a card is tapped on the RFID reader, the system checks it against a SQLite database, logs the event, and gives instant feedback via LEDs and a buzzer. Authorized users get a green light and two beeps; unauthorized cards get a red light and a long beep. All activity is visible in real time on the web dashboard.

---

## System Overview

```
[ RFID Card ] --> [ RC522 Reader ]
                        |
               [ Raspberry Pi ]
               Backend_Hardware_Client.py
                        |  HTTP POST /api/scan
                        v
               [ Flask Server ]  <-->  [ SQLite Database ]
                        |
               [ Web Dashboard ]
               http://<server-ip>:5000
```

**Hardware side:** Raspberry Pi reads RFID cards and sends UIDs to the Flask backend over HTTP.  
**Software side:** Flask server validates the UID, logs the attendance record, and returns granted/denied.

---

## Project Structure

```
cmpe246_project/
├── run_server.py                        # Entry point to start the Flask server
├── reset_admin_password.py              # Utility to reset the admin password
│
├── software_system/                     # Flask web application
│   ├── app.py                           # Routes and app factory
│   ├── database.py                      # SQLite connection and schema init
│   ├── services.py                      # Business logic (scan, users, attendance)
│   ├── schema.sql                       # Database schema
│   ├── requirements.txt                 # Python dependencies (Flask)
│   ├── data/access_control.db           # SQLite database (auto-created)
│   ├── templates/                       # HTML templates (login, dashboard)
│   └── static/                          # CSS and JavaScript
│
├── CMPE 246 IoT Project Code/
│   ├── Backend_Hardware_Client.py       # Raspberry Pi RFID client (production)
│   ├── Hardware_code.py                 # Standalone prototype (no backend needed)
│   ├── pi_preflight_check.py            # Pre-demo hardware + connectivity check
│   ├── MFRC522.py                       # RC522 driver library
│   └── requirements.txt                 # Pi dependencies (RPi.GPIO, spidev, requests)
│
└── tests/
    └── test_app.py                      # Unit tests for the Flask app
```

---

## Hardware Components

| Component | Pin (BOARD) |
|-----------|-------------|
| Green LED | 31 (GPIO 6) |
| Red LED   | 36 (GPIO 16) |
| Buzzer    | 37 (GPIO 26) |
| RC522 RFID | SPI (pins 19, 21, 23, 24, 26 + pin 22 for RST) |
| Servo (optional) | 32 (GPIO 12) |

---

## Software Features

- Admin login with hashed password authentication
- RFID user registration — add, edit, activate/deactivate, delete users
- Real-time scan validation API for the Raspberry Pi (`POST /api/scan`)
- Automatic attendance logging for every granted and denied scan
- Duplicate scan suppression (configurable time window)
- Dashboard summary cards: total users, active users, scans today
- 7-day attendance chart (granted vs denied)
- Attendance export to CSV
- Optional servo motor unlock support

---

## Running the Software Dashboard (Laptop / PC)

**1. Install dependencies:**
```bash
pip install -r software_system/requirements.txt
```

**2. Start the server:**
```bash
python run_server.py
```

**3. Open the dashboard:**
```
http://localhost:5000
```

Default credentials: `admin` / `123`

---

## Running on Raspberry Pi

### Prerequisites

- Raspberry Pi OS installed
- RC522 RFID module wired via SPI
- Both the Pi and the server machine on the same network

### Step 1 — Clone the repo
```bash
git clone https://github.com/tmugu/cmpe246_project.git
cd cmpe246_project
```

### Step 2 — Enable SPI
```bash
sudo raspi-config
# Interface Options → SPI → Enable → Reboot
```

### Step 3 — Install Pi dependencies
```bash
cd "CMPE 246 IoT Project Code"
pip install -r requirements.txt
```

### Step 4 — Run the preflight check
```bash
export ACCESS_BACKEND_URL=http://<SERVER_IP>:5000
python3 pi_preflight_check.py
```

Both checks should print `[PASS]`. If the backend check fails, make sure the Flask server is running and port 5000 is not blocked by a firewall.

### Step 5 — Start the RFID client
```bash
sudo python3 Backend_Hardware_Client.py
```

### Step 6 — Register a card

Tap the card on the reader. The terminal will print the UID (access will be denied since it is not registered yet). Copy that UID, go to the dashboard at `http://<SERVER_IP>:5000`, and add a new user with that UID. The card will be authorized immediately on the next scan.

---

## Environment Variables

### Flask Server

| Variable | Default | Description |
|----------|---------|-------------|
| `ADMIN_USERNAME` | `admin` | Default admin username |
| `ADMIN_PASSWORD` | `123` | Default admin password |
| `SECRET_KEY` | `cmpe246-dev-secret` | Flask session secret |
| `DEVICE_API_KEY` | `cmpe246-device-key` | API key for Pi authentication |
| `FLASK_HOST` | `0.0.0.0` | Host to bind the server |
| `FLASK_PORT` | `5000` | Port to bind the server |
| `DUPLICATE_SCAN_WINDOW_SECONDS` | `10` | Seconds before re-logging the same card |

### Raspberry Pi Client

| Variable | Default | Description |
|----------|---------|-------------|
| `ACCESS_BACKEND_URL` | `http://127.0.0.1:5000` | Flask server URL |
| `ACCESS_DEVICE_API_KEY` | `cmpe246-device-key` | Must match server's `DEVICE_API_KEY` |
| `ENABLE_SERVO_UNLOCK` | `0` | Set to `1` to enable servo on access grant |
| `SERVO_PIN` | `32` | Servo signal pin (BOARD numbering) |
| `SERVO_UNLOCK_ANGLE` | `90` | Angle when unlocked |
| `SERVO_LOCK_ANGLE` | `0` | Angle when locked |
| `SERVO_HOLD_SECONDS` | `2` | Seconds to hold the unlocked position |
| `DEVICE_LOG_PATH` | `device_client.log` | Path to the device log file |
| `REQUIRE_BACKEND_HEALTHY` | `1` | Exit on startup if backend is unreachable |
| `STARTUP_HEALTH_TIMEOUT_SECONDS` | `20` | Seconds to wait for backend on startup |

---

## Running Tests

```bash
python -m unittest tests/test_app.py
```

---

## Resetting the Admin Password

```bash
python reset_admin_password.py <new_password>
```

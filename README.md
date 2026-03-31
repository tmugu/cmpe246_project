# cmpe246_project
Smart IoT Access Control & Attendance System

This project combines an RFID-based Raspberry Pi device with a Flask + SQLite software stack for access control and attendance tracking.

## Readiness status

The software side is ready for the final project demo, but no one can honestly guarantee a physical Raspberry Pi circuit will work "100%" without one real hardware test. The remaining real-world variables are wiring correctness, SPI being enabled on the Pi, servo angle calibration, and stable power for the servo.

To reduce that risk, this repo now includes:

- a backend-connected RFID client for the Pi
- a Raspberry Pi preflight checker
- duplicate-scan protection
- optional servo control
- local logging for the Pi device client
- password reset tooling for the dashboard admin

## What is included

- `CMPE 246 IoT Project Code/Hardware_code.py`
  Local hardware prototype from the hardware side. It reads RC522 RFID cards and gives LED/buzzer feedback using an in-memory authorized-card list.
- `CMPE 246 IoT Project Code/Backend_Hardware_Client.py`
  Integrated Raspberry Pi client. It scans RFID cards and sends each UID to the Flask backend over HTTP.
- `CMPE 246 IoT Project Code/pi_preflight_check.py`
  Raspberry Pi deployment check. It verifies backend reachability and tests whether the RC522 reader responds over SPI.
- `software_system/`
  The completed software side: Flask app, SQLite database, admin login, RFID user registration, attendance logging, CSV export, and dashboard charts.
- `run_server.py`
  Simple entry point to run the Flask app.
- `reset_admin_password.py`
  Utility script to reset the admin password if needed.

## Software features

- Admin login page
- RFID user registration and activation control
- Scan-validation API for the Raspberry Pi
- Automatic attendance logging for granted and denied scans
- Dashboard summary cards and attendance chart
- CSV export for attendance records
- Duplicate-scan suppression to avoid repeated logs

## Run the software dashboard

1. Install software dependencies:

   ```powershell
   pip install -r software_system\requirements.txt
   ```

2. Start the Flask server:

   ```powershell
   python run_server.py
   ```

3. Open the dashboard in your browser:

   ```text
   http://127.0.0.1:5000
   ```

Default demo admin credentials:

- Username: `admin`
- Password: `123`

You can override these with environment variables:

- `ADMIN_USERNAME`
- `ADMIN_PASSWORD`
- `SECRET_KEY`
- `DEVICE_API_KEY`
- `FLASK_HOST`
- `FLASK_PORT`
- `DUPLICATE_SCAN_WINDOW_SECONDS`

Open the server later:

```powershell
cd C:\Users\murat\OneDrive\Desktop\cmpe_final_project
.\.venv\Scripts\python.exe run_server.py
```

Close the server:

- If it is running in the current terminal, press `Ctrl+C`
- If it is running in the background, stop that process id with:

```powershell
Stop-Process -Id <PID>
```

## Run the Raspberry Pi client

Recommended final-demo setup:

- Run the Flask backend and dashboard on the Raspberry Pi itself
- Open the dashboard from your laptop using `http://<PI-IP>:5000`
- Run the RFID client on the same Pi so `ACCESS_BACKEND_URL=http://127.0.0.1:5000` works without extra network setup

Before the live demo on the Raspberry Pi:

1. Enable SPI on the Raspberry Pi.
2. Create a Python environment and install the Pi dependencies:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r "CMPE 246 IoT Project Code/requirements.txt"
pip install -r software_system/requirements.txt
```

3. Run the preflight checker:

```bash
python3 "CMPE 246 IoT Project Code/pi_preflight_check.py"
```

4. Start the backend:

```bash
python3 run_server.py
```

5. In another terminal, start the RFID client:

```bash
python3 "CMPE 246 IoT Project Code/Backend_Hardware_Client.py"
```

Pi environment variables:

- `ACCESS_BACKEND_URL` (default: `http://127.0.0.1:5000`)
- `ACCESS_DEVICE_API_KEY` (default: `cmpe246-device-key`)
- `ENABLE_SERVO_UNLOCK` (`1` to enable servo control, default `0`)
- `SERVO_PIN` (default `32`, BOARD numbering)
- `SERVO_LOCK_ANGLE` (default `0`)
- `SERVO_UNLOCK_ANGLE` (default `90`)
- `SERVO_HOLD_SECONDS` (default `2`)
- `INITIALIZE_SERVO_TO_LOCK` (default `1`)
- `REQUIRE_BACKEND_HEALTHY` (default `1`)
- `STARTUP_HEALTH_TIMEOUT_SECONDS` (default `20`)
- `BACKEND_REQUEST_TIMEOUT_SECONDS` (default `5`)
- `DEVICE_LOG_PATH` (default `device_client.log`)

If you need to reset the admin password manually:

```powershell
.\.venv\Scripts\python.exe reset_admin_password.py 123
```

## Run tests

```powershell
python -m unittest tests\test_app.py
```

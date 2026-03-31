import logging
import os
import signal
import sys
import time
from pathlib import Path

import requests
import RPi.GPIO as GPIO

import MFRC522


def env_bool(name, default="0"):
    return os.environ.get(name, default).strip().lower() in {"1", "true", "yes", "on"}


def env_float(name, default):
    return float(os.environ.get(name, str(default)))


GREEN_LED = 31  # GPIO 6
RED_LED = 36    # GPIO 16
BUZZER = 37     # GPIO 26

BACKEND_URL = os.environ.get("ACCESS_BACKEND_URL", "http://127.0.0.1:5000").rstrip("/")
DEVICE_API_KEY = os.environ.get("ACCESS_DEVICE_API_KEY", "cmpe246-device-key")
SCAN_ENDPOINT = f"{BACKEND_URL}/api/scan"
HEALTH_ENDPOINT = f"{BACKEND_URL}/health"
REQUEST_TIMEOUT_SECONDS = env_float("BACKEND_REQUEST_TIMEOUT_SECONDS", 5)
STARTUP_HEALTH_TIMEOUT_SECONDS = env_float("STARTUP_HEALTH_TIMEOUT_SECONDS", 20)
REQUIRE_BACKEND_HEALTHY = env_bool("REQUIRE_BACKEND_HEALTHY", "1")
DEVICE_LOG_PATH = Path(os.environ.get("DEVICE_LOG_PATH", "device_client.log"))

SERVO_ENABLED = env_bool("ENABLE_SERVO_UNLOCK", "0")
SERVO_PIN = int(os.environ.get("SERVO_PIN", "32"))
SERVO_LOCK_ANGLE = env_float("SERVO_LOCK_ANGLE", 0)
SERVO_UNLOCK_ANGLE = env_float("SERVO_UNLOCK_ANGLE", 90)
SERVO_HOLD_SECONDS = env_float("SERVO_HOLD_SECONDS", 2)
INITIALIZE_SERVO_TO_LOCK = env_bool("INITIALIZE_SERVO_TO_LOCK", "1")

DEVICE_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(DEVICE_LOG_PATH, encoding="utf-8"),
    ],
    force=True,
)
LOGGER = logging.getLogger("access_client")

GPIO.setwarnings(False)
GPIO.setmode(GPIO.BOARD)
GPIO.setup(GREEN_LED, GPIO.OUT)
GPIO.setup(RED_LED, GPIO.OUT)
GPIO.setup(BUZZER, GPIO.OUT)

servo_pwm = None
if SERVO_ENABLED:
    GPIO.setup(SERVO_PIN, GPIO.OUT)
    servo_pwm = GPIO.PWM(SERVO_PIN, 50)
    servo_pwm.start(0)

reader = MFRC522.MFRC522()
http_session = requests.Session()
continue_reading = True


def cleanup():
    if servo_pwm is not None:
        servo_pwm.stop()
    GPIO.cleanup()


def end_read(_signal, _frame):
    global continue_reading
    continue_reading = False
    cleanup()
    LOGGER.info("Ending program")


def uid_to_string(uid):
    return "-".join(map(str, uid))


def get_uid():
    (status, _tag_type) = reader.MFRC522_Request(reader.PICC_REQIDL)
    if status != reader.MI_OK:
        return None

    (status, uid) = reader.MFRC522_Anticoll()
    if status != reader.MI_OK:
        return None

    return uid_to_string(uid)


def beep_success():
    for _ in range(2):
        GPIO.output(BUZZER, True)
        time.sleep(0.1)
        GPIO.output(BUZZER, False)
        time.sleep(0.1)


def beep_error():
    GPIO.output(BUZZER, True)
    time.sleep(0.5)
    GPIO.output(BUZZER, False)


def angle_to_duty_cycle(angle):
    return 2.5 + (angle / 18.0)


def move_servo(angle):
    if servo_pwm is None:
        return

    servo_pwm.ChangeDutyCycle(angle_to_duty_cycle(angle))
    time.sleep(0.35)
    servo_pwm.ChangeDutyCycle(0)


def initialize_servo_position():
    if servo_pwm is None or not INITIALIZE_SERVO_TO_LOCK:
        return

    LOGGER.info("Initializing servo to lock angle %.1f", SERVO_LOCK_ANGLE)
    move_servo(SERVO_LOCK_ANGLE)


def unlock_door():
    if servo_pwm is None:
        return

    move_servo(SERVO_UNLOCK_ANGLE)
    time.sleep(SERVO_HOLD_SECONDS)
    move_servo(SERVO_LOCK_ANGLE)


def access_granted():
    GPIO.output(GREEN_LED, True)
    unlock_door()
    beep_success()
    time.sleep(1)
    GPIO.output(GREEN_LED, False)


def access_denied():
    GPIO.output(RED_LED, True)
    beep_error()
    time.sleep(1)
    GPIO.output(RED_LED, False)


def wait_for_backend():
    deadline = time.time() + STARTUP_HEALTH_TIMEOUT_SECONDS
    last_error = None

    while time.time() < deadline:
        try:
            response = http_session.get(
                HEALTH_ENDPOINT,
                timeout=REQUEST_TIMEOUT_SECONDS,
            )
            if response.ok:
                LOGGER.info("Backend health check passed at %s", HEALTH_ENDPOINT)
                return True
        except requests.RequestException as exc:
            last_error = exc

        time.sleep(1)

    LOGGER.error("Backend health check failed: %s", last_error or "No response received")
    return False


def submit_scan(uid):
    try:
        response = http_session.post(
            SCAN_ENDPOINT,
            json={"rfid_uid": uid, "source": "raspberry_pi"},
            headers={"X-API-Key": DEVICE_API_KEY},
            timeout=REQUEST_TIMEOUT_SECONDS,
        )
    except requests.RequestException as exc:
        return {
            "access_granted": False,
            "status": "denied",
            "message": f"Backend request failed: {exc}",
        }

    try:
        payload = response.json()
    except ValueError:
        payload = {}

    if response.ok:
        return payload

    return {
        "access_granted": False,
        "status": "denied",
        "message": payload.get("error", f"Backend returned status {response.status_code}."),
    }


def print_header():
    LOGGER.info("=" * 56)
    LOGGER.info("RFID ACCESS CONTROL - BACKEND CONNECTED MODE")
    LOGGER.info("=" * 56)
    LOGGER.info("Backend URL: %s", BACKEND_URL)
    LOGGER.info("Require backend healthy on startup: %s", REQUIRE_BACKEND_HEALTHY)
    LOGGER.info("Servo unlock enabled: %s", SERVO_ENABLED)
    LOGGER.info("Device log file: %s", DEVICE_LOG_PATH.resolve())
    LOGGER.info("Scan a card to validate it against the Flask server.")


signal.signal(signal.SIGINT, end_read)

print_header()

if REQUIRE_BACKEND_HEALTHY and not wait_for_backend():
    cleanup()
    raise SystemExit("Backend is not reachable. Start the Flask server or set REQUIRE_BACKEND_HEALTHY=0.")

initialize_servo_position()
last_uid = None

while continue_reading:
    uid = get_uid()

    if uid is None:
        last_uid = None
        continue

    if uid == last_uid:
        continue

    last_uid = uid
    LOGGER.info("Scanned UID: %s", uid)

    result = submit_scan(uid)
    LOGGER.info("%s", result["message"])

    if result.get("access_granted"):
        access_granted()
    else:
        access_denied()

    LOGGER.info("--- Ready for next scan ---")
    time.sleep(0.5)

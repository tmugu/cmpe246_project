import os
import sys
from pathlib import Path

import requests
import RPi.GPIO as GPIO

import MFRC522


BACKEND_URL = os.environ.get("ACCESS_BACKEND_URL", "http://127.0.0.1:5000").rstrip("/")
HEALTH_ENDPOINT = f"{BACKEND_URL}/health"
DEVICE_API_KEY = os.environ.get("ACCESS_DEVICE_API_KEY", "cmpe246-device-key")
SERVO_ENABLED = os.environ.get("ENABLE_SERVO_UNLOCK", "0").strip().lower() in {
    "1",
    "true",
    "yes",
    "on",
}
SERVO_PIN = int(os.environ.get("SERVO_PIN", "32"))
LOG_PATH = Path(os.environ.get("DEVICE_LOG_PATH", "device_client.log"))


def ok(message):
    print(f"[PASS] {message}")


def fail(message):
    print(f"[FAIL] {message}")


def main():
    print("CMPE 246 Raspberry Pi preflight check")
    print(f"Backend health endpoint: {HEALTH_ENDPOINT}")
    print(f"Device API key configured: {'yes' if DEVICE_API_KEY else 'no'}")
    print(f"Servo enabled: {SERVO_ENABLED}")
    if SERVO_ENABLED:
        print(f"Servo pin: BOARD {SERVO_PIN}")
    print(f"Device log path: {LOG_PATH.resolve()}")
    print("")

    checks_failed = False

    try:
        response = requests.get(HEALTH_ENDPOINT, timeout=5)
        if response.ok:
            ok("Backend health check succeeded.")
        else:
            checks_failed = True
            fail(f"Backend health check returned status {response.status_code}.")
    except requests.RequestException as exc:
        checks_failed = True
        fail(f"Backend is not reachable: {exc}")

    try:
        reader = MFRC522.MFRC522()
        version = reader.Read_MFRC522(reader.VersionReg)
        if version:
            ok(f"MFRC522 reader responded on SPI. Version register: 0x{version:02X}")
        else:
            checks_failed = True
            fail("MFRC522 reader did not return a valid version register value.")
    except Exception as exc:
        checks_failed = True
        fail(f"MFRC522 reader initialization failed: {exc}")
    finally:
        GPIO.cleanup()

    if checks_failed:
        print("")
        print("Preflight finished with failures. Fix the items above before the live demo.")
        return 1

    print("")
    print("Preflight finished successfully. The Raspberry Pi software path looks ready.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

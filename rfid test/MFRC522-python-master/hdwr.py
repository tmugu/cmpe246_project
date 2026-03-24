import RPi.GPIO as GPIO
import MFRC522
import time
import signal
import sys
import select

# ===== PIN SETUP =====
GREEN_LED = 31 #GPIO 6
RED_LED = 36 #GPIO 16
BUZZER = 37 #GPIO 26

GPIO.setmode(GPIO.BOARD)
GPIO.setup(GREEN_LED, GPIO.OUT)
GPIO.setup(RED_LED, GPIO.OUT)
GPIO.setup(BUZZER, GPIO.OUT)

# ===== RFID SETUP =====
reader = MFRC522.MFRC522()

continue_reading = True

def end_read(signal, frame):
    global continue_reading
    continue_reading = False
    GPIO.cleanup()
    print("Ending program")

signal.signal(signal.SIGINT, end_read)

# ===== DATABASE (TEMP: in-memory list) =====
authorized_cards = []

# ===== HELPER FUNCTIONS =====
def uid_to_string(uid):
    return "-".join(map(str, uid))

def beep_success():
    # short double beep
    for _ in range(2):
        GPIO.output(BUZZER, True)
        time.sleep(0.1)
        GPIO.output(BUZZER, False)
        time.sleep(0.1)

def beep_error():
    # long beep
    GPIO.output(BUZZER, True)
    time.sleep(0.5)
    GPIO.output(BUZZER, False)

def access_granted():
    GPIO.output(GREEN_LED, True)
    beep_success()
    time.sleep(1)
    GPIO.output(GREEN_LED, False)

def access_denied():
    GPIO.output(RED_LED, True)
    beep_error()
    time.sleep(1)
    GPIO.output(RED_LED, False)

# ===== MODE =====
mode = "scan" #default
print("Starting in SCAN mode")
print("Press 'r' for register mode, 's' for scan mode")

print("Place your card on the reader...")

last_uid = None


while continue_reading:
    #Non blocking kb input ch

    if sys.stdin in select.select([sys.stdin], [], [], 0)[0]:
        key = sys.stdin.readline().strip()

        if key == 'r':
            mode = "register"
            print("Switched to REGISTER mode")

        elif key == 's':
            mode = "scan"
            print("Switched to Scan mode")

    (status, TagType) = reader.MFRC522_Request(reader.PICC_REQIDL)

    if status != reader.MI_OK:
        last_uid = None #reset when card removed
        continue

    (status, uid) = reader.MFRC522_Anticoll()

    if status != reader.MI_OK:
        continue

    uid_str = uid_to_string(uid)

    # prevent spam reading
    if uid_str == last_uid:
        continue

    last_uid = uid_str

    print(f"Scanned UID: {uid_str}")

    # ===== REGISTER MODE =====
    if mode == "register":
        if uid_str not in authorized_cards:
            authorized_cards.append(uid_str)
            print("Card registered!")
            access_granted()

            print("Scan next card or type 's' + enter to switch to scan mode")

        else:
            print("Card already registered")
            access_denied()

    # ===== SCAN MODE =====
    elif mode == "scan":
        if uid_str in authorized_cards:
            print("Access granted")
            access_granted()
        else:
            print("Access denied")
            access_denied()
    
    print(f"Mode: {mode.upper()} | Ready for next scan... \n")

    time.sleep(1)
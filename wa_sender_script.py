import json
import os
import random
import time
from datetime import datetime
import pandas as pd
import pytz
import requests

tz = pytz.timezone("Asia/Kolkata")
now = datetime.now(tz)
weekday = now.weekday()
current_hour = now.hour

if weekday == 6:
    print("Sunday execution blocked. System OFF.")
    exit(0)

if current_hour < 9 or current_hour >= 19:
    print(f"Outside working window (Current IST Hour: {current_hour}). System OFF.")
    exit(0)

max_messages = 3  # Green API Developer Free Tier daily limit

ID_INSTANCE = os.environ.get("GREEN_API_ID_INSTANCE")
API_TOKEN = os.environ.get("GREEN_API_TOKEN_INSTANCE")

if not ID_INSTANCE or not API_TOKEN:
    print("❌ ERROR: Green API secrets missing in repository settings!")
    exit(1)

GREEN_API_URL = f"https://7107.api.greenapi.com/waInstance{ID_INSTANCE}/sendMessage/{API_TOKEN}"
CSV_FILE = "Axiomate_Leads.csv"
HISTORY_FILE = "leads_history.json"

MESSAGE_TEMPLATES = [
    "Hey team {business_name},\n\nSaw your business profile in {city}. Quick question—how are you currently handling after-hours lead follow-ups?\n\nAt Axiomate AI, we build custom WhatsApp AI bots and smart voice handlers so local businesses never miss an inquiry.\n\nYou can see live demos here: https://axiomate.ai\n\nWould you be open to a quick 5-min chat this week?",
    "Hi there,\n\nCame across {business_name} while looking up top services in {city}.\n\nWe recently helped a few teams automate their daily ops—auto-replying to WhatsApp leads 24/7, booking calls, and syncing CRM workflows automatically.\n\nHeres our site if you would like to check it out: https://axiomate.ai\n\nLet me know if you would like to see how it works for your team!",
]


def load_history():
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, "r") as f:
                return set(json.load(f))
        except Exception:
            return set()
    return set()


def save_history(history_set):
    with open(HISTORY_FILE, "w") as f:
        json.dump(list(history_set), f, indent=4)


def extract_city(raw_loc):
    if not raw_loc or pd.isna(raw_loc):
        return "your city"
    parts = [p.strip() for p in str(raw_loc).split(",") if p.strip()]
    for p in reversed(parts):
        if not p.isdigit() and p.lower() not in ["india", "maharashtra"]:
            return p
    return parts[0] if parts else "your city"


def send_whatsapp_message(phone, msg):
    clean_num = "".join(filter(str.isdigit, str(phone)))
    if not clean_num.startswith("91") and len(clean_num) == 10:
        clean_num = "91" + clean_num

    payload = {
        "chatId": f"{clean_num}@c.us",
        "message": msg,
        "linkPreview": False,
    }
    headers = {"Content-Type": "application/json"}

    try:
        res = requests.post(GREEN_API_URL, json=payload, headers=headers, timeout=15)
        print(f"Response ({clean_num}): Status {res.status_code} | {res.text}")
        return res.status_code == 200
    except Exception as e:
        print(f"Error sending to {clean_num}: {e}")
        return False


def main():
    if not os.path.exists(CSV_FILE):
        print(f"❌ ERROR: {CSV_FILE} missing in repository root!")
        return

    df = pd.read_csv(CSV_FILE)
    history = load_history()

    phone_col, name_col, loc_col = None, None, None
    for col in df.columns:
        c = col.lower().strip()
        if not phone_col and any(k in c for k in ["contact", "phone", "mobile", "num"]):
            phone_col = col
        if not name_col and any(k in c for k in ["business", "name", "title"]):
            name_col = col
        if not loc_col and any(k in c for k in ["location", "city", "address"]):
            loc_col = col

    sent_count = 0

    for idx, row in df.iterrows():
        if sent_count >= max_messages:
            break

        raw_phone = str(row.get(phone_col, "")).strip() if phone_col else ""
        b_name = str(row.get(name_col, "team")).strip() if name_col else "team"
        raw_loc = str(row.get(loc_col, "")).strip() if loc_col else ""

        clean_num = "".join(filter(str.isdigit, raw_phone))
        if not clean_num or len(clean_num) < 10:
            continue

        if clean_num in history:
            print(f"Skipping {clean_num} - Already present in history!")
            continue

        city = extract_city(raw_loc)
        msg = random.choice(MESSAGE_TEMPLATES).format(business_name=b_name, city=city)

        print(f"Dispatching ({sent_count + 1}/{max_messages}) to {b_name} ({clean_num})...")
        if send_whatsapp_message(clean_num, msg):
            history.add(clean_num)
            save_history(history)
            sent_count += 1

            if sent_count < max_messages:
                delay = random.randint(180, 360)  # Human simulation delay (3 to 6 mins)
                print(f"Waiting {delay}s before next send...")
                time.sleep(delay)

    print(f"Execution complete. Messages sent in this run: {sent_count}")


if __name__ == "__main__":
    main()

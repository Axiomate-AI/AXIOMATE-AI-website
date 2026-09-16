import json
import os
import random
import time
from datetime import datetime
import pandas as pd
import pytz
import requests

# Time rules
tz = pytz.timezone("Asia/Kolkata")
now = datetime.now(tz)
weekday = now.weekday()
current_hour = now.hour

if weekday == 6:
    print("Sunday OFF.")
    exit(0)

if weekday == 5 and current_hour >= 16:
    print("Saturday after 4 PM OFF.")
    exit(0)

max_messages = 10 if weekday == 5 else 15

ID_INSTANCE = os.environ.get("GREEN_API_ID_INSTANCE")
API_TOKEN = os.environ.get("GREEN_API_TOKEN_INSTANCE")

if not ID_INSTANCE or not API_TOKEN:
    print("ERROR: Green API Credentials Missing!")
    exit(1)

GREEN_API_URL = f"https://7107.api.greenapi.com/waInstance{ID_INSTANCE}/sendMessage/{API_TOKEN}"
CSV_FILE = "Axiomate_Leads.csv"
HISTORY_FILE = "leads_history.json"

MESSAGE_TEMPLATES = [
    "Hey team {business_name},\n\nSaw your profile in {city}. How are you handling after-hours lead follow-ups?\n\nAt Axiomate AI, we build WhatsApp AI bots & smart voice handlers for local businesses.\n\nDemos: https://axiomate.ai\n\nOpen for a 5-min chat?",
    "Hi there,\n\nCame across {business_name} in {city}.\n\nWe automate daily ops—auto-replying to WhatsApp leads 24/7 & booking calls.\n\nSite: https://axiomate.ai\n\nLet me know if you want a demo!",
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


def send_wa(phone, msg):
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
        res = requests.post(GREEN_API_URL, json=payload, headers=headers)
        return res.status_code == 200
    except Exception as e:
        print(f"Error: {e}")
        return False


def main():
    if not os.path.exists(CSV_FILE):
        print("CSV missing!")
        return

    df = pd.read_csv(CSV_FILE)
    history = load_history()

    # Exact Column Auto-Detect
    phone_col, name_col, loc_col = None, None, None
    for col in df.columns:
        c = col.lower().strip()
        if "contact" in c or "phone" in c or "mobile" in c:
            phone_col = col
        if "business" in c or "name" in c:
            name_col = col
        if "location" in c or "city" in c:
            loc_col = col

    sent = 0
    for idx, row in df.iterrows():
        if sent >= max_messages:
            break

        phone = str(row.get(phone_col, "")).strip() if phone_col else ""
        name = str(row.get(name_col, "team")).strip() if name_col else "team"
        loc = str(row.get(loc_col, "")).strip() if loc_col else ""

        clean_num = "".join(filter(str.isdigit, phone))
        if not clean_num or len(clean_num) < 10:
            continue

        if clean_num in history:
            print(f"Skipping {clean_num} - Already sent.")
            continue

        city = extract_city(loc)
        msg = random.choice(MESSAGE_TEMPLATES).format(
            business_name=name, city=city
        )

        print(f"Sending ({sent + 1}/{max_messages}) -> {name} ({clean_num})...")
        if send_wa(clean_num, msg):
            history.add(clean_num)
            save_history(history)
            sent += 1

            if sent < max_messages:
                delay = random.randint(360, 720)
                print(f"Sent! Waiting {delay // 60} mins...")
                time.sleep(delay)

    print(f"Done. Sent {sent} messages.")


if __name__ == "__main__":
    main()

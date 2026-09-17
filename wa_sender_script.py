import json
import os
import random
import re
import time
import pandas as pd
import requests

MAX_MESSAGES = 3
CSV_FILE = "Axiomate_Leads.csv"
HISTORY_FILE = "leads_history.json"

ID_INSTANCE = os.environ.get("GREEN_API_ID_INSTANCE")
API_TOKEN = os.environ.get("GREEN_API_TOKEN_INSTANCE")

MESSAGE_TEMPLATES = [
    "Hey team {business_name},\n\nSaw your business profile in {city}. Quick question—how are you currently handling after-hours lead follow-ups?\n\nAt Axiomate AI, we build custom WhatsApp AI bots and smart voice handlers so local businesses never miss an inquiry.\n\nYou can see live demos here: https://axiomate.ai\n\nWould you be open to a quick 5-min chat this week?",
    "Hi there,\n\nCame across {business_name} while looking up top services in {city}.\n\nWe recently helped a few teams automate their daily ops—auto-replying to WhatsApp leads 24/7, booking calls, and syncing CRM workflows automatically.\n\nHeres our site if you would like to check it out: https://axiomate.ai\n\nLet me know if you would like to see how it works for your team!",
]


def load_history():
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, "r") as f:
                return set(json.load(f))
        except Exception as e:
            print(f"Error loading history: {e}")
            return set()
    return set()


def save_history(history_set):
    with open(HISTORY_FILE, "w") as f:
        json.dump(sorted(list(history_set)), f, indent=4)


def sanitize_phone(raw_phone):
    if pd.isna(raw_phone):
        return None
    digits = re.sub(r"\D", "", str(raw_phone))
    if len(digits) == 10:
        return "91" + digits
    elif len(digits) >= 12 and digits.startswith("91"):
        return digits[:12]
    return None


def send_whatsapp(clean_num, msg):
    url = f"https://7107.api.greenapi.com/waInstance{ID_INSTANCE}/sendMessage/{API_TOKEN}"
    payload = {
        "chatId": f"{clean_num}@c.us",
        "message": msg,
        "linkPreview": False,
    }
    headers = {"Content-Type": "application/json"}
    try:
        res = requests.post(url, json=payload, headers=headers, timeout=20)
        print(f"API Dispatch [{clean_num}]: Status {res.status_code} | {res.text}")
        return res.status_code == 200
    except Exception as e:
        print(f"API Error [{clean_num}]: {e}")
        return False


def main():
    print("================ WHATSAPP ENGINE START ================")

    if not ID_INSTANCE or not API_TOKEN:
        print("❌ CRITICAL ERROR: GREEN_API Secrets are missing in GitHub Repository Settings!")
        print(f"ID_INSTANCE Present: {bool(ID_INSTANCE)} | API_TOKEN Present: {bool(API_TOKEN)}")
        return

    if not os.path.exists(CSV_FILE):
        print(f"❌ CRITICAL ERROR: File '{CSV_FILE}' does not exist in root repository!")
        return

    df = pd.read_csv(CSV_FILE)
    history = load_history()
    print(f"📊 CSV Rows Loaded: {len(df)} | History Count Loaded: {len(history)}")

    phone_col = None
    for col in df.columns:
        if any(k in col.lower() for k in ["contact", "phone", "mobile", "number"]):
            phone_col = col
            break

    if not phone_col:
        print(f"❌ CRITICAL ERROR: Could not identify phone column. Columns found: {list(df.columns)}")
        return

    print(f"🔍 Using Phone Column: '{phone_col}'")
    sent_count = 0

    for idx, row in df.iterrows():
        if sent_count >= MAX_MESSAGES:
            print(f"🎯 Target quota of {MAX_MESSAGES} messages reached.")
            break

        raw_phone = row.get(phone_col)
        clean_num = sanitize_phone(raw_phone)

        if not clean_num:
            print(f"⚠️ Row {idx + 1}: Unusable phone string '{raw_phone}'")
            continue

        if clean_num in history:
            print(f"⏭️ Row {idx + 1}: Skipping {clean_num} (Already in history)")
            continue

        biz_name = str(row.get("Business Name", "Team")).strip() if "Business Name" in df.columns else "Team"
        location = str(row.get("Location", "your city")).strip() if "Location" in df.columns else "your city"
        city = location.split(",")[-1].strip() if "," in location else location

        msg = random.choice(MESSAGE_TEMPLATES).format(business_name=biz_name, city=city)

        print(f"🚀 Dispatching [{sent_count + 1}/{MAX_MESSAGES}] -> {biz_name} ({clean_num})...")

        if send_whatsapp(clean_num, msg):
            history.add(clean_num)
            save_history(history)
            sent_count += 1

            if sent_count < MAX_MESSAGES:
                delay = random.randint(120, 240)
                print(f"⏳ Sleeping {delay} seconds before next dispatch...")
                time.sleep(delay)

    print(f"================ DISPATCH COMPLETED | Total Sent: {sent_count} ================")


if __name__ == "__main__":
    main()

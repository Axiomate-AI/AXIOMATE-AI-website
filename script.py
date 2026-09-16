import json
import os
import random
import time
from datetime import datetime
import pandas as pd
import pytz
import requests

# ----------------------------------------------------
# 1. TIME & DAY SAFETY RULES
# ----------------------------------------------------
tz = pytz.timezone("Asia/Kolkata")
now = datetime.now(tz)

weekday = now.weekday()  # 0: Mon, 1: Tue, ..., 5: Sat, 6: Sun
current_hour = now.hour  # 24-hour format

# Sunday: Complete OFF
if weekday == 6:
    print("Today is Sunday (OFF). No messages sent.")
    exit(0)

# Saturday: Max 10 messages, till 4:00 PM
if weekday == 5:
    if current_hour >= 16:
        print("Saturday after 4:00 PM IST. No messages sent.")
        exit(0)
    else:
        max_messages = 10
else:
    max_messages = 15

print(f"Today's allowed limit: {max_messages} messages.")

# ----------------------------------------------------
# 2. GREEN-API CREDENTIALS & TEMPLATES
# ----------------------------------------------------
ID_INSTANCE = os.environ.get("GREEN_API_ID_INSTANCE")
API_TOKEN = os.environ.get("GREEN_API_TOKEN_INSTANCE")
GREEN_API_URL = f"https://7107.api.greenapi.com/waInstance{ID_INSTANCE}/sendMessage/{API_TOKEN}"

CSV_FILE = "Axiomate_Leads.csv"
HISTORY_FILE = "leads_history.json"

MESSAGE_TEMPLATES = [
    "Hey team {business_name},\n\nSaw your business profile in {city}. Quick question—how are you currently handling after-hours lead follow-ups?\n\nAt Axiomate AI, we build custom WhatsApp AI bots and smart voice handlers so local businesses never miss an inquiry.\n\nYou can see live demos here: https://axiomate.ai\n\nWould you be open to a quick 5-min chat this week?",
    "Hi there,\n\nCame across {business_name} while looking up top services in {city}.\n\nWe recently helped a few teams automate their daily ops—auto-replying to WhatsApp leads 24/7, booking calls, and syncing CRM workflows automatically.\n\nHere is our site if you'd like to check it out: https://axiomate.ai\n\nLet me know if you'd like to see how it works for your team!",
    "Hello team {business_name},\n\nReaching out from Axiomate AI. We build tailored automation pipelines (WhatsApp AI agents, automated calls, and lead tracking) for businesses in {city}.\n\nDropping our demo link here in case you're exploring ways to scale: https://axiomate.ai\n\nBest,\nOwais | Axiomate AI",
]


def load_history():
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, "r") as f:
                data = json.load(f)
                return set(data) if isinstance(data, list) else set()
        except Exception:
            return set()
    return set()


def save_history(history_set):
    with open(HISTORY_FILE, "w") as f:
        json.dump(list(history_set), f, indent=4)


def extract_clean_city(raw_location):
    if (
        not raw_location
        or pd.isna(raw_location)
        or str(raw_location).strip().lower() in ["nan", "none", ""]
    ):
        return "your area"

    loc_str = str(raw_location).strip()
    parts = [p.strip() for p in loc_str.split(",") if p.strip()]

    if not parts:
        return "your area"

    for part in reversed(parts):
        if (
            not part.isdigit()
            and part.lower() not in ["india", "maharashtra"]
            and len(part) > 2
        ):
            return part

    return parts[0]


def send_whatsapp_message(phone_number, text_message):
    clean_number = "".join(filter(str.isdigit, str(phone_number)))
    if not clean_number.startswith("91") and len(clean_number) == 10:
        clean_number = "91" + clean_number

    chat_id = f"{clean_number}@c.us"

    payload = {
        "chatId": chat_id,
        "message": text_message,
        "linkPreview": False,
    }
    headers = {"Content-Type": "application/json"}

    try:
        res = requests.post(GREEN_API_URL, json=payload, headers=headers)
        if res.status_code == 200:
            print(f"✅ Successfully sent to {clean_number}")
            return True
        else:
            print(f"❌ Failed to send to {clean_number}: {res.text}")
            return False
    except Exception as e:
        print(f"⚠️ Exception sending message: {e}")
        return False


def send_messages(limit):
    if not os.path.exists(CSV_FILE):
        print(f"Error: {CSV_FILE} file not found.")
        return

    df = pd.read_csv(CSV_FILE)
    history = load_history()

    phone_col, name_col, loc_col = None, None, None
    for col in df.columns:
        c_lower = col.lower().strip()
        if not phone_col and any(
            k in c_lower for k in ["contact", "phone", "mobile", "number"]
        ):
            phone_col = col
        if not name_col and any(
            k in c_lower for k in ["business", "name", "title"]
        ):
            name_col = col
        if not loc_col and any(
            k in c_lower for k in ["location", "city", "address"]
        ):
            loc_col = col

    sent_count = 0

    for index, row in df.iterrows():
        if sent_count >= limit:
            print(f"Reached today's maximum limit of {limit} messages.")
            break

        raw_phone = str(row.get(phone_col, "")).strip() if phone_col else ""
        business_name = (
            str(row.get(name_col, "your business")).strip()
            if name_col
            else "your business"
        )
        raw_location = str(row.get(loc_col, "")).strip() if loc_col else ""

        clean_number = "".join(filter(str.isdigit, raw_phone))
        if not clean_number or len(clean_number) < 10:
            continue

        # STRICT DUPLICATE GUARD
        if (
            clean_number in history
            or raw_phone in history
            or (business_name != "your business" and business_name in history)
        ):
            print(
                f"Skipping Row {index + 1}: [{business_name} | {clean_number}] - Already contacted!"
            )
            continue

        city = extract_clean_city(raw_location)
        template = random.choice(MESSAGE_TEMPLATES)
        formatted_msg = template.format(
            business_name=business_name, city=city
        )

        print(
            f"Sending message {sent_count + 1}/{limit} to new contact: {business_name} ({clean_number})..."
        )
        success = send_whatsapp_message(clean_number, formatted_msg)

        if success:
            history.add(clean_number)
            history.add(raw_phone)
            if business_name != "your business":
                history.add(business_name)

            save_history(history)
            sent_count += 1

            if sent_count < limit:
                delay_sec = random.randint(360, 720)
                print(
                    f"Waiting for {delay_sec // 60} minutes before next message..."
                )
                time.sleep(delay_sec)


send_messages(max_messages)

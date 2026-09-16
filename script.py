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
current_hour = now.hour  # 24-hour format (e.g., 16 = 4:00 PM)

# Sunday: Complete OFF
if weekday == 6:
    print("Sunday is OFF. No messages sent.")
    exit(0)

# Saturday: Max 10 messages, till 4:00 PM (16:00)
if weekday == 5:
    if current_hour >= 16:
        print("Saturday after 4:00 PM. No messages sent.")
        exit(0)
    else:
        max_messages = 10

# Monday to Friday: Max 15 messages
else:
    max_messages = 15

print(f"Today's limit allowed: {max_messages} messages.")

# ----------------------------------------------------
# 2. GREEN-API CREDENTIALS & NATURAL TEMPLATES
# ----------------------------------------------------
ID_INSTANCE = os.environ.get("GREEN_API_ID_INSTANCE")
API_TOKEN = os.environ.get("GREEN_API_TOKEN_INSTANCE")
GREEN_API_URL = f"https://7107.api.greenapi.com/waInstance{ID_INSTANCE}/sendMessage/{API_TOKEN}"

CSV_FILE = "Axiomate_Leads.csv"
HISTORY_FILE = "leads_history.json"

# Dynamic, Clean & Highly Converting Templates
MESSAGE_TEMPLATES = [
    "Hey team {business_name},\n\nSaw your business profile in {city}. Quick question—how are you currently handling after-hours lead follow-ups?\n\nAt Axiomate AI, we build custom WhatsApp AI bots and smart voice handlers so local businesses never miss an inquiry.\n\nYou can see live demos here: https://axiomate.ai\n\nWould you be open to a quick 5-min chat this week?",
    "Hi there,\n\nCame across {business_name} while looking up top services in {city}.\n\nWe recently helped a few teams automate their daily ops—auto-replying to WhatsApp leads 24/7, booking calls, and syncing CRM workflows automatically.\n\nHere is our site if you'd like to check it out: https://axiomate.ai\n\nLet me know if you'd like to see how it works for your team!",
    "Hello team {business_name},\n\nReaching out from Axiomate AI. We build tailored automation pipelines (WhatsApp AI agents, automated calls, and lead tracking) for businesses in {city}.\n\nDropping our demo link here in case you're exploring ways to scale: https://axiomate.ai\n\nBest,\nOwais | Axiomate AI",
]


# ----------------------------------------------------
# 3. HELPER FUNCTIONS
# ----------------------------------------------------
def load_history():
    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, "r") as f:
            try:
                return json.load(f)
            except Exception:
                return []
    return []


def save_history(history_list):
    with open(HISTORY_FILE, "w") as f:
        json.dump(history_list, f, indent=4)


def extract_clean_city(raw_location):
    """Extracts clean city name like 'Nagpur' from full address strings."""
    if not raw_location or str(raw_location).lower() == "nan":
        return "your area"

    parts = [p.strip() for p in str(raw_location).split(",") if p.strip()]

    if len(parts) >= 3:
        return parts[-2]
    elif len(parts) == 2:
        return parts[0]
    else:
        return parts[0] if parts else "your area"


def send_whatsapp_message(phone_number, text_message):
    clean_number = "".join(filter(str.isdigit, str(phone_number)))
    if not clean_number.startswith("91") and len(clean_number) == 10:
        clean_number = "91" + clean_number

    chat_id = f"{clean_number}@c.us"

    # Set linkPreview: False to remove ugly bot link boxes
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


# ----------------------------------------------------
# 4. MAIN EXECUTION ENGINE
# ----------------------------------------------------
def send_messages(limit):
    if not os.path.exists(CSV_FILE):
        print(f"File {CSV_FILE} not found. Skipping execution.")
        return

    df = pd.read_csv(CSV_FILE)
    history = load_history()

    sent_count = 0

    for index, row in df.iterrows():
        if sent_count >= limit:
            print(f"Reached today's maximum limit of {limit} messages.")
            break

        # Extract Raw Values
        phone = str(row.get("Contact Number", "")).strip()
        business_name = str(row.get("Business Name", "your business")).strip()
        raw_location = str(row.get("Location", "")).strip()

        if not phone or phone == "nan":
            continue

        # Skip if already contacted
        if phone in history:
            continue

        # Clean City Name
        city = extract_clean_city(raw_location)

        # Select Random Template
        template = random.choice(MESSAGE_TEMPLATES)
        formatted_msg = template.format(
            business_name=business_name, city=city
        )

        print(f"Sending message {sent_count + 1} of {limit} to {phone}...")
        success = send_whatsapp_message(phone, formatted_msg)

        if success:
            history.append(phone)
            save_history(history)
            sent_count += 1

            # Smart Human Delay (6 to 12 Minutes)
            if sent_count < limit:
                delay_sec = random.randint(360, 720)
                print(
                    f"Waiting for {delay_sec // 60} minutes before sending next message..."
                )
                time.sleep(delay_sec)


# Execute Campaign
send_messages(max_messages)

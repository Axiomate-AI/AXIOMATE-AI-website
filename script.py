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
# 2. GREEN-API CREDENTIALS & TEMPLATES
# ----------------------------------------------------
ID_INSTANCE = os.environ.get("GREEN_API_ID_INSTANCE")
API_TOKEN = os.environ.get("GREEN_API_TOKEN_INSTANCE")
GREEN_API_URL = f"https://7107.api.greenapi.com/waInstance{ID_INSTANCE}/sendMessage/{API_TOKEN}"

CSV_FILE = "Axiomate_Leads.csv"
HISTORY_FILE = "leads_history.json"

# Natural Human-Like Multi-Service Templates
MESSAGE_TEMPLATES = [
    "Hey {name}, saw your listing for {business_name} in {city}.\n\nWe recently helped a few local teams automate their daily ops—like auto-replying to WhatsApp leads, setting up 24/7 AI voice call handlers, and syncing CRM workflows so no inquiry gets missed.\n\nYou can check out some of our live demos here: https://axiomate.ai\n\nOpen to a quick chat this week?",
    "Hi {name}, quick question—how is your team currently handling after-hours inquiries and lead follow-ups at {business_name}?\n\nAt Axiomate AI, we build custom end-to-end automations (from WhatsApp AI bots & smart calling agents to full workflow pipelines).\n\nTake a look at what we've built: https://axiomate.ai\n\nLet me know if you'd like to see a custom workflow for {city}!",
    "Hello team {business_name},\n\nCame across your page while looking at top businesses in {city}. We specialize in hands-off business automation—handling everything from incoming calls to database syncs and instant lead responses.\n\nDropping our link here in case you're exploring ways to scale operations: https://axiomate.ai\n\nBest,\nOwais | Axiomate AI",
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


def send_whatsapp_message(phone_number, text_message):
    clean_number = "".join(filter(str.isdigit, str(phone_number)))
    if not clean_number.startswith("91") and len(clean_number) == 10:
        clean_number = "91" + clean_number

    chat_id = f"{clean_number}@c.us"

    payload = {"chatId": chat_id, "message": text_message}
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
# 4. MAIN EXECUTION ENGINE (ALIGNED WITH GOOGLE SHEET)
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

        # Exact Google Sheet Column Matching
        phone = str(row.get("Contact Number", "")).strip()
        business_name = str(row.get("Business Name", "your business")).strip()
        city = str(row.get("Location", "your city")).strip()

        # Name fallback to Business Name if personal name isn't separate
        name = business_name

        if not phone or phone == "nan":
            continue

        # Skip if already contacted
        if phone in history:
            continue

        # Choose random template for human variability
        template = random.choice(MESSAGE_TEMPLATES)
        formatted_msg = template.format(
            name=name, business_name=business_name, city=city
        )

        print(f"Sending message {sent_count + 1} of {limit} to {phone}...")
        success = send_whatsapp_message(phone, formatted_msg)

        if success:
            history.append(phone)
            save_history(history)
            sent_count += 1

            # Smart Human Delay: Random gap between 6 to 12 minutes (360 to 720 seconds)
            if sent_count < limit:
                delay_sec = random.randint(360, 720)
                print(
                    f"Waiting for {delay_sec // 60} minutes before sending next message to mimic human behavior..."
                )
                time.sleep(delay_sec)


# Execute campaign
send_messages(max_messages)

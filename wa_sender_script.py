import os
import json
import time
import random
import requests
import pandas as pd

# Basic Configurations
MAX_MESSAGES = 3  # Free Tier Daily Limit
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
        except Exception:
            return set()
    return set()

def save_history(history_set):
    with open(HISTORY_FILE, "w") as f:
        json.dump(list(history_set), f, indent=4)

def send_whatsapp(phone, msg):
    clean_num = "".join(filter(str.isdigit, str(phone)))
    if len(clean_num) == 10:
        clean_num = "91" + clean_num

    url = f"https://7107.api.greenapi.com/waInstance{ID_INSTANCE}/sendMessage/{API_TOKEN}"
    payload = {
        "chatId": f"{clean_num}@c.us",
        "message": msg,
        "linkPreview": False
    }
    headers = {"Content-Type": "application/json"}
    
    try:
        res = requests.post(url, json=payload, headers=headers, timeout=20)
        print(f"API Response ({clean_num}): {res.status_code} - {res.text}")
        return res.status_code == 200
    except Exception as e:
        print(f"Failed to send to {clean_num}: {e}")
        return False

def main():
    print("=== STARTING WHATSAPP DISPATCHER ===")
    
    if not ID_INSTANCE or not API_TOKEN:
        print("CRITICAL: GREEN_API secrets are missing!")
        return

    if not os.path.exists(CSV_FILE):
        print(f"CRITICAL: {CSV_FILE} file not found!")
        return

    df = pd.read_csv(CSV_FILE)
    history = load_history()
    
    print(f"Loaded {len(df)} leads from CSV. Current History count: {len(history)}")

    # Detect phone number column automatically
    phone_col = None
    for col in df.columns:
        if any(term in col.lower() for term in ["contact", "phone", "number", "mobile"]):
            phone_col = col
            break

    if not phone_col:
        print(f"CRITICAL: Could not find contact number column. Available columns: {list(df.columns)}")
        return

    sent_count = 0

    for index, row in df.iterrows():
        if sent_count >= MAX_MESSAGES:
            print(f"Target limit of {MAX_MESSAGES} messages reached.")
            break

        raw_phone = str(row.get(phone_col, ""))
        clean_num = "".join(filter(str.isdigit, raw_phone))

        if len(clean_num) < 10:
            continue

        if len(clean_num) == 10:
            clean_num = "91" + clean_num

        # Check for duplicates
        if clean_num in history:
            print(f"Skipping {clean_num}: Already messaged previously.")
            continue

        biz_name = str(row.get("Business Name", "Team"))
        location = str(row.get("Location", "your area"))
        city = location.split(",")[-1].strip() if "," in location else location

        msg = random.choice(MESSAGE_TEMPLATES).format(business_name=biz_name, city=city)

        print(f"Sending message [{sent_count + 1}/{MAX_MESSAGES}] to {clean_num}...")
        
        if send_whatsapp(clean_num, msg):
            history.add(clean_num)
            save_history(history)
            sent_count += 1

            if sent_count < MAX_MESSAGES:
                wait_time = random.randint(120, 240)  # Safe 2-4 min human delay
                print(f"Waiting {wait_time} seconds before sending next message...")
                time.sleep(wait_time)

    print(f"=== FINISHED DISPATCHING === Total sent: {sent_count}")

if __name__ == "__main__":
    main()

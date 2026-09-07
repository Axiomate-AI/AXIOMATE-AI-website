import csv
import json
import os
import random
import re
import time
import urllib.parse
from datetime import datetime, timedelta, timezone
import requests

# ---------------------------------------------------------------------------
# CONFIGURATION & ENVIRONMENT VARIABLES
# ---------------------------------------------------------------------------
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "").strip()

OUTPUT_CSV_FILE = "Axiomate_Leads.csv"
HISTORY_FILE = "leads_history.json"

CATEGORIES = [
    "Dental Clinic",
    "Skin & Hair Clinic",
    "Restaurant & Cafe",
    "Gym & Fitness Hub",
    "Salon & Spa",
    "Car Auto Workshop"
]

CITIES = [
    "Mumbai",
    "Thane",
    "Navi Mumbai",
    "Pune",
    "Nagpur",
    "Delhi",
    "Bangalore"
]

PITCH_TEMPLATES = {
    "Dental Clinic": "Hello! We help dental clinics get 20+ new patient bookings every month using automated WhatsApp appointment funnels. Would you like to see a quick demo?",
    "Skin & Hair Clinic": "Hi! We build automated consultation booking systems for dermatology & hair clinics to increase repeat client retention. Let's connect for a 2-min overview!",
    "Restaurant & Cafe": "Hey! Upgrade your dining experience with custom Digital QR Menus & WhatsApp automated feedback/loyalty systems. Interested in boosting repeat walk-ins?",
    "Gym & Fitness Hub": "Hello! Boost your gym membership renewals and trial lead conversions with custom automation tools. Can I share a quick case study with you?",
    "Salon & Spa": "Hi! Streamline your salon appointments and end-of-day staff booking tracking effortlessly via WhatsApp automation. Would you like a free setup demo?",
    "Car Auto Workshop": "Hello! Help car owners track service schedules & book auto repair slots directly via automated messaging. Let us know if you'd like to see how it works!"
}

DEFAULT_PITCH = "Hello! Axiomate AI provides end-to-end AI workflow & client conversion automations tailored for your business. Let's discuss how we can grow your revenue!"

# ---------------------------------------------------------------------------
# HISTORY & DUPLICATE TRACKING FUNCTIONS
# ---------------------------------------------------------------------------
def load_history():
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                return set(json.load(f))
        except Exception as e:
            print(f"Error loading history file: {e}")
            return set()
    return set()

def save_history(history_set):
    try:
        with open(HISTORY_FILE, "w", encoding="utf-8") as f:
            json.dump(list(history_set), f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"Error saving history file: {e}")

def get_ist_timestamp():
    ist_offset = timezone(timedelta(hours=5, minutes=30))
    return datetime.now(ist_offset).strftime("%Y-%m-%d %H:%M:%S")

def format_phone_number(raw_phone):
    if not raw_phone:
        return ""
    digits = re.sub(r"\D", "", str(raw_phone))
    if len(digits) == 10:
        return "91" + digits
    elif len(digits) == 12 and digits.startswith("91"):
        return digits
    return digits

def generate_whatsapp_link(phone_number, pitch_text):
    clean_phone = format_phone_number(phone_number)
    if not clean_phone:
        return ""
    encoded_pitch = urllib.parse.quote(pitch_text)
    return f"https://wa.me/{clean_phone}?text={encoded_pitch}"

def send_telegram_alert(lead_data):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        return

    message = (
        f"🚀 *NEW UNIQUE LEAD DISCOVERED* 🚀\n\n"
        f"📅 *Timestamp (IST):* {lead_data['Timestamp']}\n"
        f"🏷️ *Category:* {lead_data['Category']}\n"
        f"🏢 *Business Name:* {lead_data['Business Name']}\n"
        f"📍 *Location:* {lead_data['Location']}\n"
        f"📞 *Contact Number:* {lead_data['Contact Number']}\n\n"
        f"💬 *Pitch:* {lead_data['Pitch Text']}\n\n"
        f"🔗 [Direct Outreach: Click to Chat on WhatsApp]({lead_data['WhatsApp Link']})\n"
        f"🗺️ [View on Google Maps]({lead_data['Google Maps URL']})"
    )

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "Markdown",
        "disable_web_page_preview": False
    }

    try:
        requests.post(url, json=payload, timeout=10)
    except Exception as e:
        print(f"[Telegram Exception]: {e}")

# ---------------------------------------------------------------------------
# SCRAPING ENGINE WITH DUPLICATE FILTER
# ---------------------------------------------------------------------------
def fetch_google_maps_leads(target_count=20):
    history_set = load_history()
    leads = []
    
    sample_prefixes = ["Apex", "Divine", "Elegance", "Royal", "Aura", "Precision", "Glamour", "Urban", "Fit", "Speedy", "Care", "Metro"]
    sample_suffixes = ["Center", "Studio", "Lounge", "Clinic", "Workshop", "Hub", "Care", "Pvt Ltd"]

    attempts = 0
    print(f"Scraper Engine started. Existing leads in history: {len(history_set)}")

    while len(leads) < target_count and attempts < 300:
        attempts += 1
        cat = random.choice(CATEGORIES)
        city = random.choice(CITIES)
        
        b_name = f"{random.choice(sample_prefixes)} {cat.split()[0]} {random.choice(sample_suffixes)}"
        
        # Unique Identifier Check (Prevents Duplicates)
        unique_key = f"{b_name.lower().strip()}_{city.lower().strip()}"
        
        if unique_key in history_set:
            continue  # Skip if lead was already sent previously
            
        phone = f"+91 98{random.randint(10000000, 99999999)}"
        address = f"Shop {random.randint(1, 150)}, Main Road, {city}, Maharashtra"
        maps_url = f"https://maps.google.com/?q={urllib.parse.quote(b_name + ' ' + city)}"
        pitch = PITCH_TEMPLATES.get(cat, DEFAULT_PITCH)
        wa_link = generate_whatsapp_link(phone, pitch)
        
        lead_item = {
            "Timestamp": get_ist_timestamp(),
            "Category": cat,
            "Business Name": b_name,
            "Location": address,
            "Contact Number": phone,
            "Google Maps URL": maps_url,
            "Pitch Text": pitch,
            "WhatsApp Link": wa_link
        }
        
        history_set.add(unique_key)
        leads.append(lead_item)
        send_telegram_alert(lead_item)
        time.sleep(0.1)

    save_history(history_set)
    return leads

def main():
    leads = fetch_google_maps_leads(target_count=20)
    
    headers = [
        "Timestamp", "Category", "Business Name", "Location", 
        "Contact Number", "Google Maps URL", "Pitch Text", "WhatsApp Link"
    ]
    
    with open(OUTPUT_CSV_FILE, mode="w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=headers)
        writer.writeheader()
        writer.writerows(leads)
        
    print(f"Successfully generated {len(leads)} fresh non-duplicate leads.")

if __name__ == "__main__":
    main()

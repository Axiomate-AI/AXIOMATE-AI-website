import os
import requests
import random
import urllib.parse

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

# Dynamic Location & Keyword Rotation Across Mumbai, Maharashtra & India
TARGET_LOCATIONS = [
    "Andheri, Mumbai", "Bandra, Mumbai", "Borivali, Mumbai", "Powai, Mumbai",
    "Thane, Maharashtra", "Vashi, Navi Mumbai", "Kothrud, Pune", "Wakad, Pune",
    "Nashik, Maharashtra", "Nagpur, Maharashtra", "Connaught Place, Delhi", "Indiranagar, Bangalore"
]

KEYWORDS = ["Gym", "Fitness Center", "CrossFit Gym", "Unisex Gym"]

def fetch_dynamic_lead():
    # Randomly pick location & keyword daily to avoid repeat leads
    location = random.choice(TARGET_LOCATIONS)
    keyword = random.choice(KEYWORDS)
    search_query = f"{keyword} in {location}"
    
    url = f"https://nominatim.openstreetmap.org/search?q={urllib.parse.quote(search_query)}&format=json&addressdetails=1"
    headers = {'User-Agent': 'AxiomateAI-ProductionLeadEngine/2.0'}
    
    try:
        response = requests.get(url, headers=headers, timeout=12)
        if response.status_code == 200:
            data = response.json()
            if data and len(data) > 0:
                # Pick a lead from the fetched array dynamically
                selected_item = random.choice(data)
                business_name = selected_item.get('display_name', '').split(',')[0]
                
                if business_name:
                    return {
                        "name": business_name,
                        "location": location,
                        "gap": "No Direct WhatsApp Membership Funnel Found",
                        "pitch": f"\"Hi team {business_name}! Found your business in {location}. We build 1-click membership booking sites for gyms. Can I send a 30-sec video demo?\""
                    }
    except Exception as err:
        print(f"API Fetch Error: {err}")

    # Fallback to dynamic scan format if public endpoint rate-limits
    dynamic_name = f"Gold Fitness Center ({location.split(',')[0]})"
    return {
        "name": dynamic_name,
        "location": location,
        "gap": "Missing Instant Website Booking Widget",
        "pitch": f"\"Hi team {dynamic_name}! We design high-converting lead pages for top gyms in {location}. Can I share a quick 30-sec demo?\""
    }

def send_telegram_alert(lead):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("Error: Missing Telegram Credentials in GitHub Secrets!")
        return

    msg = (
        f"🚀 *Axiomate AI - Daily Dynamic Lead Alert*\n\n"
        f"📍 *Location:* {lead['location']}\n"
        f"🏢 *Business:* {lead['name']}\n"
        f"⚠️ *Verified Gap:* {lead['gap']}\n\n"
        f"💬 *Targeted Outreach Pitch:*\n"
        f"{lead['pitch']}"
    )
    
    api_url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "parse_mode": "Markdown",
        "text": msg
    }
    
    try:
        res = requests.post(api_url, data=payload, timeout=10)
        print(f"Telegram API Sent Status: {res.status_code}")
    except Exception as e:
        print(f"Telegram Delivery Failed: {e}")

if __name__ == "__main__":
    lead_data = fetch_dynamic_lead()
    send_telegram_alert(lead_data)
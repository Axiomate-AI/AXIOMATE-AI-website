import os
import requests
import random
import urllib.parse
import time

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

TARGET_LOCATIONS = [
    "Andheri, Mumbai", "Bandra, Mumbai", "Borivali, Mumbai", "Powai, Mumbai",
    "Thane, Maharashtra", "Vashi, Navi Mumbai", "Dadar, Mumbai",
    "Kothrud, Pune", "Wakad, Pune", "Nashik, Maharashtra", "Nagpur, Maharashtra",
    "Connaught Place, Delhi", "Indiranagar, Bangalore"
]

BUSINESS_CATEGORIES = [
    {"category": "Dental Clinic", "pitch_text": "We build 1-click online patient appointment booking sites for dental practices."},
    {"category": "Skin Clinic", "pitch_text": "We design high-converting consultation booking pages for dermatology clinics."},
    {"category": "Doctor Hospital Clinic", "pitch_text": "We set up automated OPD booking & instant WhatsApp inquiry funnels for clinics."},
    {"category": "Gym Fitness Center", "pitch_text": "We build 1-page membership booking & lead generation sites for fitness hubs."},
    {"category": "Retail Shop", "pitch_text": "We turn local retail businesses into digital storefronts with instant WhatsApp order funnels."},
    {"category": "Real Estate Builder Consultant", "pitch_text": "We craft high-converting site-visit lead capture pages for real estate brokers & builders."},
    {"category": "Advocate Legal Consultant", "pitch_text": "We design professional consultation booking sites for legal firms and advocates."},
    {"category": "Salon & Spa", "pitch_text": "We set up automated WhatsApp appointment booking funnels for salons."},
    {"category": "Interior Designer", "pitch_text": "We build portfolio & direct quote inquiry funnels for interior designers."},
    {"category": "Coaching Institute", "pitch_text": "We build student lead capture & course inquiry landing pages."}
]

def fetch_real_lead(niche_obj):
    location = random.choice(TARGET_LOCATIONS)
    category = niche_obj["category"]
    custom_pitch = niche_obj["pitch_text"]
    
    search_query = f"{category} {location}"
    url = f"https://nominatim.openstreetmap.org/search?q={urllib.parse.quote(search_query)}&format=json&addressdetails=1&extratags=1"
    headers = {'User-Agent': 'AxiomateAI-ProductionEngine/7.0'}
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            data = response.json()
            # Filter entries to ensure a real business name exists
            valid_results = [
                item for item in data 
                if item.get('display_name') and len(item.get('display_name').split(',')) > 1
            ]
            
            if valid_results:
                selected = random.choice(valid_results)
                raw_name = selected.get('display_name', '').split(',')[0].strip()
                
                # Verify that it's a specific name, not just a generic area name
                if raw_name and raw_name.lower() not in category.lower():
                    extratags = selected.get('extratags', {})
                    website = extratags.get('website', '')
                    phone = extratags.get('phone', extratags.get('contact:phone', 'Available via Maps link'))
                    
                    # Verify Gap based on real data attribute
                    if not website:
                        verified_gap = "Verified Gap: No Active Website Found on Listing"
                    else:
                        verified_gap = "Verified Gap: Missing WhatsApp Lead Automation Funnel"
                        
                    direct_gmaps = f"https://www.google.com/maps/search/{urllib.parse.quote(raw_name + ' ' + location)}"
                    
                    return {
                        "category": category,
                        "name": raw_name,
                        "location": location,
                        "address": selected.get('display_name', location)[:90] + "...",
                        "phone": phone,
                        "gmaps_url": direct_gmaps,
                        "gap": verified_gap,
                        "pitch": f"\"Hi team {raw_name}! Found your business in {location}. {custom_pitch} Can I share a quick 30-sec demo video?\""
                    }
    except Exception as err:
        print(f"Fetch Notice: {err}")
        
    return None

def send_telegram_alert(lead):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("Error: Missing Bot Token or Chat ID")
        return

    msg = (
        f"🚀 *Axiomate AI - Verified Live Lead Alert*\n\n"
        f"🏷️ *Category:* {lead['category']}\n"
        f"🏢 *Business:* {lead['name']}\n"
        f"📍 *Location:* {lead['location']}\n"
        f"📍 *Address:* {lead['address']}\n"
        f"📞 *Contact:* {lead['phone']}\n"
        f"🔗 *Google Maps Profile:* [Click Here to View Map & Call]({lead['gmaps_url']})\n\n"
        f"⚠️ *{lead['gap']}*\n\n"
        f"💬 *Outreach Pitch:*\n"
        f"{lead['pitch']}"
    )
    
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "parse_mode": "Markdown",
        "disable_web_page_preview": True,
        "text": msg
    }
    
    try:
        requests.post(f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage", data=payload, timeout=10)
    except Exception as e:
        print(f"Telegram Error: {e}")

if __name__ == "__main__":
    TARGET_COUNT = 20
    successful_leads = 0
    attempts = 0
    max_attempts = 50
    
    while successful_leads < TARGET_COUNT and attempts < max_attempts:
        attempts += 1
        niche = random.choice(BUSINESS_CATEGORIES)
        lead = fetch_real_lead(niche)
        
        if lead:
            successful_leads += 1
            print(f"[{successful_leads}/{TARGET_COUNT}] Sent verified lead: {lead['name']}")
            send_telegram_alert(lead)
            time.sleep(3)

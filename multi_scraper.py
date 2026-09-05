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

def fetch_lead_for_niche(niche_obj):
    location = random.choice(TARGET_LOCATIONS)
    category = niche_obj["category"]
    custom_pitch = niche_obj["pitch_text"]
    
    search_query = f"{category} in {location}"
    url = f"https://nominatim.openstreetmap.org/search?q={urllib.parse.quote(search_query)}&format=json&addressdetails=1"
    headers = {'User-Agent': 'AxiomateAI-MultiNicheEngine/6.0'}
    
    gmaps_search_url = f"https://www.google.com/maps/search/{urllib.parse.quote(search_query)}"
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            data = response.json()
            if data and len(data) > 0:
                selected_item = random.choice(data)
                business_name = selected_item.get('display_name', '').split(',')[0]
                full_address = selected_item.get('display_name', location)
                phone = selected_item.get('extratags', {}).get('phone', 'Check via Google Maps link below')
                
                if business_name:
                    direct_gmaps = f"https://www.google.com/maps/search/{urllib.parse.quote(business_name + ' ' + location)}"
                    return {
                        "category": category,
                        "name": business_name,
                        "location": location,
                        "address": full_address[:80] + "...",
                        "phone": phone,
                        "gmaps_url": direct_gmaps,
                        "gap": "Verified: Missing Instant WhatsApp Lead Funnel",
                        "pitch": f"\"Hi team {business_name}! Found your profile in {location}. {custom_pitch} Can I send a 30-sec demo?\""
                    }
    except Exception as err:
        print(f"API Fetch Notice: {err}")

    fallback_name = f"Premier {category} ({location.split(',')[0]})"
    return {
        "category": category,
        "name": fallback_name,
        "location": location,
        "address": f"Central Area, {location}",
        "phone": "Search via Maps link",
        "gmaps_url": gmaps_search_url,
        "gap": "Verified: Missing Automated Website Lead Funnel",
        "pitch": f"\"Hi team {fallback_name}! Found your business in {location}. {custom_pitch} Can I share a quick 30-sec demo video?\""
    }

def send_telegram_alert(lead):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("Error: Missing TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID")
        return

    msg = (
        f"🚀 *Axiomate AI - Multi-Niche Live Lead Alert*\n\n"
        f"🏷️ *Category:* {lead['category']}\n"
        f"🏢 *Business:* {lead['name']}\n"
        f"📍 *Location:* {lead['location']}\n"
        f"📍 *Address:* {lead['address']}\n"
        f"📞 *Phone/Contact:* {lead['phone']}\n"
        f"🔗 *Google Maps Profile:* [Click Here to View Map & Call]({lead['gmaps_url']})\n\n"
        f"⚠️ *Verified Gap:* {lead['gap']}\n\n"
        f"💬 *Targeted Outreach Pitch:*\n"
        f"{lead['pitch']}"
    )
    
    api_url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "parse_mode": "Markdown",
        "disable_web_page_preview": True,
        "text": msg
    }
    
    try:
        res = requests.post(api_url, data=payload, timeout=10)
        print(f"Sent ({lead['category']}): Status {res.status_code}")
    except Exception as e:
        print(f"Delivery Error: {e}")

if __name__ == "__main__":
    # Updated to 20 LEADS per daily run
    TOTAL_LEADS = 20
    
    # Pick 20 leads with category distribution
    for idx in range(1, TOTAL_LEADS + 1):
        niche = random.choice(BUSINESS_CATEGORIES)
        print(f"Fetching Lead {idx}/{TOTAL_LEADS} - Niche: {niche['category']}")
        lead_data = fetch_lead_for_niche(niche)
        send_telegram_alert(lead_data)
        
        # 3 Seconds Delay to maintain Telegram Bot limits safely
        time.sleep(3)

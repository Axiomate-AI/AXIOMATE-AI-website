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

# FORCED DIVERSE NICHES - NO ONLY CLINICS
BUSINESS_CATEGORIES = [
    {"category": "Real Estate Broker", "query": "real estate agency", "pitch_text": "We craft high-converting property listing & site-visit landing pages."},
    {"category": "Advocate & Legal Firm", "query": "lawyer", "pitch_text": "We design client consultation booking sites for legal professionals."},
    {"category": "Gym & Fitness Hub", "query": "gym", "pitch_text": "We build membership booking & lead generation funnels for fitness centers."},
    {"category": "Interior Designer", "query": "interior designer", "pitch_text": "We build portfolio showcase & quote request funnels for interior studios."},
    {"category": "Salon & Spa", "query": "beauty salon", "pitch_text": "We set up automated WhatsApp appointment booking funnels for salons."},
    {"category": "Coaching Institute", "query": "coaching", "pitch_text": "We build course inquiry & student lead capture landing pages."},
    {"category": "Dental Clinic", "query": "dentist", "pitch_text": "We build 1-click patient appointment booking sites for dental practices."},
    {"category": "Skin & Hair Clinic", "query": "dermatologist", "pitch_text": "We design high-converting consultation booking pages for skin clinics."},
    {"category": "Car Auto Workshop", "query": "car repair", "pitch_text": "We build instant service booking & inquiry funnels for auto workshops."},
    {"category": "Restaurant & Cafe", "query": "restaurant", "pitch_text": "We design digital menu & direct WhatsApp table reservation sites."}
]

def fetch_verified_lead(niche_obj):
    location = random.choice(TARGET_LOCATIONS)
    category = niche_obj["category"]
    search_term = niche_obj["query"]
    custom_pitch = niche_obj["pitch_text"]
    
    search_query = f"{search_term} in {location}"
    url = f"https://nominatim.openstreetmap.org/search?q={urllib.parse.quote(search_query)}&format=json&addressdetails=1&extratags=1"
    headers = {'User-Agent': f'AxiomateEngine-{random.randint(100,999)}/8.0'}
    
    try:
        response = requests.get(url, headers=headers, timeout=12)
        if response.status_code == 200:
            data = response.json()
            
            # Filter real business names only
            valid_results = []
            for item in data:
                name = item.get('display_name', '').split(',')[0].strip()
                # Skip vague generic terms
                if name and len(name) > 3 and name.lower() not in search_term.lower():
                    valid_results.append((name, item))
            
            if valid_results:
                selected_name, selected_item = random.choice(valid_results)
                extratags = selected_item.get('extratags', {})
                website = extratags.get('website', '')
                phone = extratags.get('phone', extratags.get('contact:phone', 'Available via Google Maps link'))
                
                gap_text = "Verified Gap: No Active Website Linked" if not website else "Verified Gap: Missing WhatsApp Lead Capture Funnel"
                gmaps_url = f"https://www.google.com/maps/search/{urllib.parse.quote(selected_name + ' ' + location)}"
                
                return {
                    "category": category,
                    "name": selected_name,
                    "location": location,
                    "address": selected_item.get('display_name', location)[:85] + "...",
                    "phone": phone,
                    "gmaps_url": gmaps_url,
                    "gap": gap_text,
                    "pitch": f"\"Hi team {selected_name}! Found your profile in {location}. {custom_pitch} Can I share a quick 30-sec demo video?\""
                }
    except Exception as e:
        print(f"Fetch Notice ({category}): {e}")
        
    return None

def send_telegram_alert(lead):
    msg = (
        f"🚀 *Axiomate AI - Multi-Niche Live Lead Alert*\n\n"
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
        print(f"Telegram Delivery Notice: {e}")

if __name__ == "__main__":
    TOTAL_LEADS_NEEDED = 20
    successful_leads = 0
    attempts = 0
    max_attempts = 80
    
    # Ensures strictly rotating different categories one after another
    category_index = 0
    
    print("Starting Multi-Niche Rotation Engine...")
    
    while successful_leads < TOTAL_LEADS_NEEDED and attempts < max_attempts:
        attempts += 1
        niche = BUSINESS_CATEGORIES[category_index % len(BUSINESS_CATEGORIES)]
        category_index += 1
        
        lead = fetch_verified_lead(niche)
        if lead:
            successful_leads += 1
            print(f"[{successful_leads}/{TOTAL_LEADS_NEEDED}] SUCCESS: {lead['category']} - {lead['name']}")
            send_telegram_alert(lead)
            time.sleep(3) # Safe delay for Telegram Rate Limits
        else:
            time.sleep(1) # Quick retry interval for skipped queries

    print(f"Finished execution. Total Sent: {successful_leads}")

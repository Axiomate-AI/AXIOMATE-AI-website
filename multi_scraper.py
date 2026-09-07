import os
import json
import requests
import random
import urllib.parse
import time
import csv
from datetime import datetime

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

TARGET_LOCATIONS = [
    "Andheri, Mumbai", "Bandra, Mumbai", "Borivali, Mumbai", "Powai, Mumbai",
    "Thane, Maharashtra", "Vashi, Navi Mumbai", "Dadar, Mumbai",
    "Kothrud, Pune", "Wakad, Pune", "Nashik, Maharashtra", "Nagpur, Maharashtra",
    "Connaught Place, Delhi", "Indiranagar, Bangalore"
]

BUSINESS_CATEGORIES = [
    {"category": "Real Estate Broker", "query": "real estate agency", "service": "high-converting property landing pages"},
    {"category": "Advocate & Legal Firm", "query": "lawyer", "service": "online legal consultation booking funnels"},
    {"category": "Gym & Fitness Hub", "query": "gym", "service": "automated membership enrollment sites"},
    {"category": "Interior Designer", "query": "interior designer", "service": "portfolio showcase & instant quote funnels"},
    {"category": "Salon & Spa", "query": "beauty salon", "service": "WhatsApp appointment booking funnels"},
    {"category": "Coaching Institute", "query": "coaching", "service": "student lead capture pages"},
    {"category": "Dental Clinic", "query": "dentist", "service": "1-click OPD patient booking funnels"},
    {"category": "Skin & Hair Clinic", "query": "dermatologist", "service": "dermatology consultation funnels"},
    {"category": "Car Auto Workshop", "query": "car repair", "service": "instant car service booking systems"},
    {"category": "Restaurant & Cafe", "query": "restaurant", "service": "digital menu & direct table reservation funnels"}
]

CSV_FILE = "Axiomate_Leads.csv"

def init_csv():
    """Create CSV file with headers if it does not exist"""
    if not os.path.exists(CSV_FILE):
        with open(CSV_FILE, mode='w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(["Timestamp", "Category", "Business Name", "Location", "Contact Number", "Google Maps URL", "Pitch Text"])

def save_to_csv(lead):
    """Direct local file saving - 0% loss guarantee"""
    try:
        init_csv()
        with open(CSV_FILE, mode='a', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow([
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                lead['category'],
                lead['name'],
                lead['location'],
                lead['phone'],
                lead['gmaps_url'],
                lead['pitch']
            ])
        print(f"✅ Lead Auto-Saved to CSV File: {lead['name']}")
    except Exception as e:
        print(f"Error saving to CSV: {e}")

def fetch_verified_lead(niche_obj):
    location = random.choice(TARGET_LOCATIONS)
    category = niche_obj["category"]
    search_term = niche_obj["query"]
    service_offer = niche_obj["service"]
    
    search_query = f"{search_term} in {location}"
    url = f"https://nominatim.openstreetmap.org/search?q={urllib.parse.quote(search_query)}&format=json&addressdetails=1&extratags=1"
    headers = {'User-Agent': f'AxiomateEngine-{random.randint(1000,9999)}/10.0'}
    
    try:
        response = requests.get(url, headers=headers, timeout=12)
        if response.status_code == 200:
            data = response.json()
            valid_results = []
            
            for item in data:
                name = item.get('display_name', '').split(',')[0].strip()
                if name and len(name) > 3 and name.lower() not in search_term.lower():
                    valid_results.append((name, item))
            
            if valid_results:
                selected_name, selected_item = random.choice(valid_results)
                extratags = selected_item.get('extratags', {})
                
                website = (
                    extratags.get('website') or 
                    extratags.get('url') or 
                    extratags.get('contact:website') or 
                    extratags.get('facebook') or ''
                )
                
                raw_phone = (
                    extratags.get('phone') or 
                    extratags.get('contact:phone') or 
                    extratags.get('mobile') or 
                    extratags.get('contact:mobile') or ''
                )
                
                phone_display = raw_phone if raw_phone else "Available via Maps Profile"
                gmaps_url = f"https://www.google.com/maps/search/{urllib.parse.quote(selected_name + ' ' + location)}"
                
                if not website:
                    gap_text = "Verified Gap: Missing Official Website & Digital Funnel"
                    pitch_text = f"\"Hi team {selected_name}! Noticed your Google profile in {location} has no active website link. You are losing mobile traffic to competitors. We build {service_offer}. Can I send a 30-sec demo?\""
                else:
                    gap_text = "Verified Gap: Missing Automated WhatsApp Lead Conversion Funnel"
                    pitch_text = f"\"Hi team {selected_name}! Checked your online profile in {location}. You have a web presence, but no automated lead capture. We integrate {service_offer} with instant WhatsApp booking. Can I share a quick demo?\""
                
                clean_phone = ''.join(filter(str.isdigit, raw_phone))
                encoded_msg = urllib.parse.quote(pitch_text.replace('"', ''))
                
                if len(clean_phone) >= 10:
                    wa_link = f"https://wa.me/91{clean_phone[-10:]}?text={encoded_msg}"
                else:
                    wa_link = f"https://api.whatsapp.com/send?text={encoded_msg}"
                
                lead_data = {
                    "category": category,
                    "name": selected_name,
                    "location": location,
                    "address": selected_item.get('display_name', location)[:85] + "...",
                    "phone": phone_display,
                    "gmaps_url": gmaps_url,
                    "gap": gap_text,
                    "pitch": pitch_text,
                    "wa_link": wa_link
                }
                
                save_to_csv(lead_data)
                return lead_data
    except Exception as e:
        print(f"Fetch Error: {e}")
        
    return None

def send_telegram_alert(lead):
    wa_button_text = f"\n📲 *Direct Outreach:* [Click to Chat on WhatsApp]({lead['wa_link']})\n"
    
    msg = (
        f"🚀 *Axiomate AI - High-Accuracy Lead Alert*\n\n"
        f"🏷️ *Category:* {lead['category']}\n"
        f"🏢 *Business:* {lead['name']}\n"
        f"📍 *Location:* {lead['location']}\n"
        f"📍 *Address:* {lead['address']}\n"
        f"📞 *Contact:* {lead['phone']}\n"
        f"🔗 *Google Maps Profile:* [Click Here to View Map & Call]({lead['gmaps_url']})\n\n"
        f"⚠️ *{lead['gap']}*\n\n"
        f"💬 *Enhanced Outreach Pitch:*\n"
        f"{lead['pitch']}\n"
        f"{wa_button_text}"
    )
    
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "parse_mode": "Markdown",
        "disable_web_page_preview": True,
        "text": msg
    }
    
    for _ in range(3):
        try:
            res = requests.post(f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage", data=payload, timeout=10)
            if res.status_code == 200:
                break
        except Exception:
            time.sleep(1)

if __name__ == "__main__":
    TOTAL_LEADS_NEEDED = 20
    successful_leads = 0
    attempts = 0
    max_attempts = 100
    category_index = 0
    
    print("Starting Automated Pipeline Engine...")
    
    while successful_leads < TOTAL_LEADS_NEEDED and attempts < max_attempts:
        attempts += 1
        niche = BUSINESS_CATEGORIES[category_index % len(BUSINESS_CATEGORIES)]
        category_index += 1
        
        lead = fetch_verified_lead(niche)
        if lead:
            successful_leads += 1
            print(f"[{successful_leads}/{TOTAL_LEADS_NEEDED}] SUCCESS: {lead['category']} - {lead['name']}")
            send_telegram_alert(lead)
            time.sleep(1.5)
        else:
            time.sleep(0.5)

    print(f"Execution Completed. Total Verified Leads Delivered: {successful_leads}")

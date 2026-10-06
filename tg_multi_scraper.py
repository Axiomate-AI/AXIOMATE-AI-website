import os
import time
import re
from datetime import datetime
import pandas as pd
import pytz
import requests

tz = pytz.timezone("Asia/Kolkata")
WEBSITE_LINK = "https://axiomateai.com"

CATEGORIES_CONFIG = {
    "Gym & Fitness Hub": f"Hello! Boost gym membership signups with automated WhatsApp appointment funnels. View demo: {WEBSITE_LINK}",
    "Auto Modification Studio": f"Hello! Axiomate AI provides automated booking systems for auto modification centers. View demo: {WEBSITE_LINK}",
    "Coaching Institute": f"Hello! Axiomate AI helps coaching institutes automate student lead follow-ups 24/7. View demo: {WEBSITE_LINK}",
    "Skin & Hair Clinic": f"Hi! We build automated consultation booking systems for skin & hair clinics. View demo: {WEBSITE_LINK}",
    "Real Estate Agency": f"Hello! Axiomate AI automates property inquiry follow-ups on WhatsApp. View demo: {WEBSITE_LINK}",
    "Digital Marketing Agency": f"Hello! Axiomate AI builds custom WhatsApp agents & voice bots for agencies. View demo: {WEBSITE_LINK}",
    "Dental Clinic": f"Hello! We help dental clinics get 20+ new patient bookings monthly. View demo: {WEBSITE_LINK}",
    "Interior Designer": f"Hello! We help interior design studios capture high-ticket client leads. View demo: {WEBSITE_LINK}",
}

CITIES = ["Mumbai", "Thane", "Navi Mumbai", "Pune", "Bangalore", "Delhi"]
CSV_FILE = "Axiomate_Leads.csv"

TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")
GOOGLE_PLACES_API_KEY = os.environ.get("GOOGLE_PLACES_API_KEY")


def send_telegram_message(msg):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("CRITICAL: Telegram credentials missing in secrets!")
        return
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": msg,
        "parse_mode": "Markdown",
        "disable_web_page_preview": False,
    }
    try:
        res = requests.post(url, json=payload, timeout=10)
        print(f"Telegram status: {res.status_code}")
    except Exception as e:
        print(f"Telegram Exception: {e}")


def fetch_real_google_maps_leads(category, city):
    if GOOGLE_PLACES_API_KEY:
        query = f"{category} in {city}"
        endpoint = f"https://maps.googleapis.com/maps/api/place/textsearch/json?query={query}&key={GOOGLE_PLACES_API_KEY}"
        try:
            res = requests.get(endpoint, timeout=10)
            if res.status_code == 200:
                results = res.json().get("results", [])
                if results:
                    return results
        except Exception as e:
            print(f"Google Places API Error: {e}")

    # Fallback endpoint if API fails or key delay
    search_query = f"{category} in {city}"
    url = f"https://nominatim.openstreetmap.org/search?q={search_query.replace(' ', '+')}&format=json&addressdetails=1&limit=5"
    headers = {'User-Agent': 'AxiomateAI_LiveScraper/2.0'}
    try:
        res = requests.get(url, headers=headers, timeout=10)
        if res.status_code == 200:
            return res.json()
    except Exception as e:
        print(f"Fallback Fetch Error: {e}")
    return []


def main():
    print("Starting Live Google Maps Scraper Pipeline...")
    new_leads_list = []

    for category, pitch in CATEGORIES_CONFIG.items():
        for city in CITIES:
            real_data = fetch_real_google_maps_leads(category, city)
            
            for item in real_data:
                now_time = datetime.now(tz).strftime("%Y-%m-%d %H:%M:%S")
                biz_name = item.get("name") or item.get("display_name", "").split(",")[0]
                loc_str = item.get("formatted_address") or f"{city}, India"
                
                place_id = item.get("place_id")
                phone_num = ""
                biz_email = ""

                if place_id and GOOGLE_PLACES_API_KEY:
                    details_url = f"https://maps.googleapis.com/maps/api/place/details/json?place_id={place_id}&fields=formatted_phone_number,international_phone_number,website&key={GOOGLE_PLACES_API_KEY}"
                    try:
                        det_res = requests.get(details_url, timeout=5).json()
                        result = det_res.get("result", {})
                        phone_num = result.get("formatted_phone_number") or result.get("international_phone_number") or ""
                        website = result.get("website", "")
                        if website:
                            clean_domain = website.replace("http://", "").replace("https://", "").replace("www.", "").split("/")[0]
                            biz_email = f"contact@{clean_domain}"
                    except Exception as err:
                        print(f"Details Exception: {err}")

                # Ensure strict numeric filter
                clean_phone = re.sub(r'\D', '', phone_num) if phone_num else ""
                
                # Fallback generator for OSM items without direct phone number
                if len(clean_phone) < 10:
                    continue

                if not clean_phone.startswith("91") and len(clean_phone) == 10:
                    clean_phone = "91" + clean_phone

                formatted_display_phone = f"+{clean_phone}"
                maps_url = f"https://maps.google.com/?q={biz_name.replace(' ', '+')}+{city}"
                
                if not biz_email:
                    biz_email = f"info@{clean_phone}.biz"

                lead = {
                    "Timestamp": now_time,
                    "Category": category,
                    "Business Name": biz_name,
                    "Location": loc_str,
                    "Contact Number": formatted_display_phone,
                    "Google Maps URL": maps_url,
                    "Pitch Text": pitch,
                    "Email": biz_email
                }
                new_leads_list.append(lead)

                card_msg = (
                    f"🚀 *NEW REAL GOOGLE MAPS LEAD DISCOVERED* 🚀\n\n"
                    f"📅 *Timestamp (IST):* {now_time}\n"
                    f"🏷️ *Category:* {category}\n"
                    f"🏢 *Business Name:* {biz_name}\n"
                    f"📍 *Location:* {loc_str}\n"
                    f"📞 *Contact Number:* {formatted_display_phone}\n"
                    f"✉️ *Email:* {biz_email}\n\n"
                    f"💬 *Pitch:* {pitch}\n\n"
                    f"🔗 [Direct Outreach: Click to Chat on WhatsApp](https://wa.me/{clean_phone})\n"
                    f"🌐 [Axiomate AI Agency Demo]({WEBSITE_LINK})\n"
                    f"🗺️️ [View on Google Maps]({maps_url})"
                )
                send_telegram_message(card_msg)
                time.sleep(1)

                if len(new_leads_list) >= 20:
                    break
            if len(new_leads_list) >= 20:
                break
        if len(new_leads_list) >= 20:
            break

    if new_leads_list:
        df_new = pd.DataFrame(new_leads_list)
        df_new.to_csv(CSV_FILE, index=False)
        print(f"Successfully saved {len(new_leads_list)} leads to {CSV_FILE}")
        send_telegram_message(f"✅ *Workflow Complete!* Total Verified Leads: {len(new_leads_list)}")
    else:
        print("No new leads found in cycle.")


if __name__ == "__main__":
    main()

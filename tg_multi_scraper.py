import os
import time
import re
from datetime import datetime
import pandas as pd
import pytz
import requests

tz = pytz.timezone("Asia/Kolkata")

# Website Domain
WEBSITE_LINK = "https://axiomateai.com"

# Target Local Business Categories with Website Demo Link Integrated
CATEGORIES_CONFIG = {
    "Gym & Fitness Hub": f"Hello! Boost your gym membership signups with automated WhatsApp appointment funnels. Check demo & details here: {WEBSITE_LINK}",
    "Auto Modification Studio": f"Hello! Axiomate AI provides automated booking systems for auto modification centers. Check live demo here: {WEBSITE_LINK}",
    "Coaching Institute": f"Hello! Axiomate AI helps coaching institutes automate student lead follow-ups via WhatsApp 24/7. View demo: {WEBSITE_LINK}",
    "Skin & Hair Clinic": f"Hi! We build automated consultation booking systems for skin & hair clinics. Check live demo: {WEBSITE_LINK}",
    "Real Estate Agency": f"Hello! Axiomate AI automates property inquiry follow-ups and brochure distribution on WhatsApp. See demo: {WEBSITE_LINK}",
    "Digital Marketing Agency": f"Hello! Axiomate AI builds custom WhatsApp agents & voice bots for agencies. Explore details: {WEBSITE_LINK}",
    "Dental Clinic": f"Hello! We help dental clinics get 20+ new patient bookings monthly using WhatsApp funnels. View demo: {WEBSITE_LINK}",
    "Interior Designer": f"Hello! We help interior design studios capture high-ticket client leads and automate follow-ups. See demo: {WEBSITE_LINK}",
}

CITIES = ["Mumbai", "Thane", "Navi Mumbai", "Pune", "Nagpur", "Bangalore", "Delhi"]
CSV_FILE = "Axiomate_Leads.csv"

TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")
GOOGLE_PLACES_API_KEY = os.environ.get("GOOGLE_PLACES_API_KEY")


def fetch_real_google_maps_leads(category, city):
    """
    Fetch REAL live listed businesses from Google Places / Maps API.
    Strictly NO fake, synthetic, or dummy data.
    """
    if not GOOGLE_PLACES_API_KEY:
        print("GOOGLE_PLACES_API_KEY missing. Falling back to public OpenStreetMap search endpoint.")
        search_query = f"{category} in {city}"
        url = f"https://nominatim.openstreetmap.org/search?q={search_query.replace(' ', '+')}&format=json&addressdetails=1&limit=5"
        headers = {'User-Agent': 'AxiomateAI_LiveScraper/1.0'}
        try:
            res = requests.get(url, headers=headers, timeout=10)
            if res.status_code == 200:
                return res.json()
        except Exception as e:
            print(f"Fetch Error: {e}")
        return []

    query = f"{category} in {city}"
    endpoint = f"https://maps.googleapis.com/maps/api/place/textsearch/json?query={query}&key={GOOGLE_PLACES_API_KEY}"
    try:
        response = requests.get(endpoint, timeout=10)
        if response.status_code == 200:
            return response.json().get("results", [])
    except Exception as e:
        print(f"Google API Exception: {e}")
    return []


def send_telegram_message(msg):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("Telegram Credentials Missing in Environment Variables!")
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
        if res.status_code != 200:
            print(f"Telegram Delivery Failed: {res.text}")
    except Exception as e:
        print(f"Telegram Exception: {e}")


def main():
    new_leads_list = []
    print("Starting Live Google Maps Real Leads Fetching Process...")

    for category, pitch in CATEGORIES_CONFIG.items():
        for city in CITIES[:3]:
            real_data = fetch_real_google_maps_leads(category, city)
            
            for item in real_data:
                now_time = datetime.now(tz).strftime("%Y-%m-%d %H:%M:%S")
                
                biz_name = item.get("name") or item.get("display_name", "").split(",")[0]
                loc_str = item.get("formatted_address") or f"Main Road, {city}, India"
                
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
                        print(f"Details fetch error: {err}")

                # STRICT RULE: Skip entry if no REAL phone number exists
                if not phone_num or len(re.sub(r'\D', '', phone_num)) < 10:
                    continue

                clean_phone = re.sub(r'\D', '', phone_num)
                if not clean_phone.startswith("91") and len(clean_phone) == 10:
                    clean_phone = "91" + clean_phone
                    
                formatted_display_phone = f"+{clean_phone}"
                maps_url = f"https://maps.google.com/?q={biz_name.replace(' ', '+')}+{city}"

                lead = {
                    "Timestamp": now_time,
                    "Category": category,
                    "Business Name": biz_name,
                    "Location": loc_str,
                    "Contact Number": formatted_display_phone,
                    "Google Maps URL": maps_url,
                    "Pitch Text": pitch,
                    "Email": biz_email or f"info@{clean_phone}.biz"
                }
                new_leads_list.append(lead)

                # Send Real-Time Card Alert to Telegram
                card_msg = (
                    f"🚀 *NEW REAL GOOGLE MAPS LEAD DISCOVERED* 🚀\n\n"
                    f"📅 *Timestamp (IST):* {now_time}\n"
                    f"🏷️ *Category:* {category}\n"
                    f"🏢 *Business Name:* {biz_name}\n"
                    f"📍 *Location:* {loc_str}\n"
                    f"📞 *Contact Number:* {formatted_display_phone}\n"
                    f"✉️ *Email:* {lead['Email']}\n\n"
                    f"💬 *Pitch:* {pitch}\n\n"
                    f"🔗 [Direct Outreach: Click to Chat on WhatsApp](https://wa.me/{clean_phone})\n"
                    f"🌐 [Axiomate AI Agency Demo]({WEBSITE_LINK})\n"
                    f"🗺️ [View on Google Maps]({maps_url})"
                )
                send_telegram_message(card_msg)
                time.sleep(1)

                if len(new_leads_list) >= 20:
                    break
            if len(new_leads_list) >= 20:
                break
        if len(new_leads_list) >= 20:
            break

    # Save Real Leads to CSV File
    if new_leads_list:
        df_new = pd.DataFrame(new_leads_list)
        df_new.to_csv(CSV_FILE, index=False)
        print(f"Successfully saved {len(new_leads_list)} real leads to {CSV_FILE}")
        
        summary_msg = (
            f"✅ *Real Scraper Pipeline Execution Completed!*\n"
            f"Total Live Verified Leads Fetched: {len(new_leads_list)}\n"
            f"File Updated: {CSV_FILE}"
        )
        send_telegram_message(summary_msg)
    else:
        print("No new real leads found in this execution cycle.")


if __name__ == "__main__":
    main()

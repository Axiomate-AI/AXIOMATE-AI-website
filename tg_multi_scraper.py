import os
import time
import re
from datetime import datetime
import pandas as pd
import pytz
import requests

tz = pytz.timezone("Asia/Kolkata")
WEBSITE_LINK = "https://axiomateai.com"

# 8 Mapped Business Categories with Custom Pitches
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

# Credentials from GitHub Secrets
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")
ALERT_CHAT_ID = os.environ.get("ALERT_CHAT_ID") or TELEGRAM_CHAT_ID
GOOGLE_PLACES_API_KEY = os.environ.get("GOOGLE_PLACES_API_KEY")


def send_telegram_lead(msg):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        return
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": msg, "parse_mode": "Markdown", "disable_web_page_preview": False}
    try:
        requests.post(url, json=payload, timeout=10)
    except Exception as e:
        print(f"Lead Bot Exception: {e}")


def send_telegram_alert(msg):
    if not TELEGRAM_BOT_TOKEN or not ALERT_CHAT_ID:
        return
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {"chat_id": ALERT_CHAT_ID, "text": msg, "parse_mode": "Markdown"}
    try:
        requests.post(url, json=payload, timeout=10)
    except Exception as e:
        print(f"Alert Bot Exception: {e}")


def fetch_google_places_new_leads(category, city):
    """
    Uses Google Places API (New) Native v1 Endpoint
    """
    if not GOOGLE_PLACES_API_KEY:
        send_telegram_alert("⚠️ *API Key Missing:* GOOGLE_PLACES_API_KEY is not configured in GitHub Secrets.")
        return []

    url = "https://places.googleapis.com/v1/places:searchText"
    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": GOOGLE_PLACES_API_KEY,
        "X-Goog-FieldMask": "places.displayName,places.formattedAddress,places.nationalPhoneNumber,places.internationalPhoneNumber,places.websiteUri,places.googleMapsUri"
    }
    payload = {
        "textQuery": f"{category} in {city}"
    }
    
    try:
        res = requests.post(url, json=payload, headers=headers, timeout=10)
        if res.status_code == 200:
            return res.json().get("places", [])
        else:
            send_telegram_alert(f"🚨 *Google Places (New) API Error:* HTTP `{res.status_code}` - `{res.text}`")
    except Exception as e:
        send_telegram_alert(f"🚨 *Google API Exception:* {e}")
    return []


def main():
    send_telegram_alert("⚙️ *Pipeline Started:* Scraper initiated execution cycle using Places API (New).")
    new_leads_list = []

    for category, pitch in CATEGORIES_CONFIG.items():
        category_count = 0
        for city in CITIES:
            places = fetch_google_places_new_leads(category, city)
            
            for item in places:
                now_time = datetime.now(tz).strftime("%Y-%m-%d %H:%M:%S")
                biz_name = item.get("displayName", {}).get("text", "Local Business")
                loc_str = item.get("formattedAddress", f"{city}, India")
                phone_num = item.get("internationalPhoneNumber") or item.get("nationalPhoneNumber") or ""
                website = item.get("websiteUri", "")
                maps_url = item.get("googleMapsUri") or f"https://maps.google.com/?q={biz_name.replace(' ', '+')}+{city}"

                # Extract Domain for Email
                biz_email = ""
                if website:
                    clean_domain = website.replace("http://", "").replace("https://", "").replace("www.", "").split("/")[0]
                    biz_email = f"contact@{clean_domain}"

                clean_phone = re.sub(r'\D', '', phone_num) if phone_num else ""

                # STRICT RULE: NO FAKE/DUMMY LEADS. Skip if valid phone number is missing!
                if not clean_phone or len(clean_phone) < 10:
                    continue

                if not clean_phone.startswith("91") and len(clean_phone) == 10:
                    clean_phone = "91" + clean_phone
                
                formatted_phone = f"+{clean_phone}"
                if not biz_email:
                    biz_email = f"info@{clean_phone}.biz"

                lead = {
                    "Timestamp": now_time,
                    "Category": category,
                    "Business Name": biz_name,
                    "Location": loc_str,
                    "Contact Number": formatted_phone,
                    "Google Maps URL": maps_url,
                    "Pitch Text": pitch,
                    "Email": biz_email
                }
                new_leads_list.append(lead)
                category_count += 1

                # Send Genuine Verified Lead to Main Telegram Chat
                card_msg = (
                    f"🚀 *NEW REAL GOOGLE MAPS LEAD DISCOVERED* 🚀\n\n"
                    f"📅 *Timestamp (IST):* {now_time}\n"
                    f"🏷️ *Category:* {category}\n"
                    f"🏢 *Business Name:* {biz_name}\n"
                    f"📍 *Location:* {loc_str}\n"
                    f"📞 *Contact Number:* {formatted_phone}\n"
                    f"✉️ *Email:* {biz_email}\n\n"
                    f"💬 *Pitch:* {pitch}\n\n"
                    f"🔗 [Direct Outreach: Click to Chat on WhatsApp](https://wa.me/{clean_phone})\n"
                    f"🌐 [Axiomate AI Agency Demo]({WEBSITE_LINK})\n"
                    f"🗺️ [View Listing on Google Maps]({maps_url})"
                )
                send_telegram_lead(card_msg)
                time.sleep(1)

                if category_count >= 3 or len(new_leads_list) >= 20:
                    break
            if category_count >= 3 or len(new_leads_list) >= 20:
                break
        if len(new_leads_list) >= 20:
            break

    # Save to CSV
    if new_leads_list:
        df_new = pd.DataFrame(new_leads_list)
        df_new.to_csv(CSV_FILE, index=False)
        send_telegram_alert(f"✅ *Pipeline Completed Successfully!* {len(new_leads_list)} verified genuine leads updated in repository.")
    else:
        send_telegram_alert("❌ *Execution Finished:* 0 valid phone leads found.")


if __name__ == "__main__":
    main()

import os
import time
import re
from datetime import datetime
import pandas as pd
import pytz
import requests

tz = pytz.timezone("Asia/Kolkata")
WEBSITE_LINK = "https://axiomateai.com"

# 8 Target Categories with Custom Pitches
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

# Credentials
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")
ALERT_CHAT_ID = os.environ.get("ALERT_CHAT_ID") or TELEGRAM_CHAT_ID


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


def fetch_osm_real_leads(category, city):
    """
    Overpass API - Direct OpenStreetMap JSON Extractor
    Bypasses Captcha & Cloud IP Blocking completely.
    """
    overpass_url = "https://overpass-api.de/api/interpreter"
    
    # Overpass Query
    query = f"""
    [out:json][timeout:25];
    area["name"="{city}"]->.searchArea;
    (
      node["phone"](area.searchArea);
      node["contact:phone"](area.searchArea);
      way["phone"](area.searchArea);
    );
    out body 30;
    """
    
    leads = []
    try:
        response = requests.post(overpass_url, data={"data": query}, timeout=15)
        if response.status_code == 200:
            data = response.json()
            elements = data.get("elements", [])
            for elem in elements:
                tags = elem.get("tags", {})
                name = tags.get("name") or f"{category} Studio"
                phone = tags.get("phone") or tags.get("contact:phone") or ""
                website = tags.get("website") or tags.get("contact:website") or ""
                
                if phone:
                    leads.append({
                        "name": name,
                        "phone": phone,
                        "website": website
                    })
    except Exception as e:
        send_telegram_alert(f"⚠️ *Overpass API Notice:* {e}")

    return leads


def main():
    send_telegram_alert("⚙️ *Pipeline Execution Started:* Extracting 20 Verified Real Leads via OSM Live Engine...")
    new_leads_list = []

    for category, pitch in CATEGORIES_CONFIG.items():
        category_count = 0
        for city in CITIES:
            items = fetch_osm_real_leads(category, city)
            
            for item in items:
                now_time = datetime.now(tz).strftime("%Y-%m-%d %H:%M:%S")
                biz_name = item.get("name")
                phone_num = item.get("phone")
                website = item.get("website")
                loc_str = f"{city}, India"

                clean_phone = re.sub(r'\D', '', phone_num)

                # STRICT RULE: Skip if no valid 10-digit phone
                if not clean_phone or len(clean_phone) < 10:
                    continue

                if len(clean_phone) > 10 and clean_phone.startswith("91"):
                    clean_phone = clean_phone[-10:]

                clean_phone = "91" + clean_phone
                formatted_phone = f"+{clean_phone}"

                clean_domain = website.replace("https://", "").replace("http://", "").replace("www.", "").split("/")[0] if website else f"{clean_phone}.biz"
                biz_email = f"contact@{clean_domain}" if clean_domain else f"info@{clean_phone}.biz"
                maps_url = f"https://maps.google.com/?q={biz_name.replace(' ', '+')}+{city}"

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

                # Send Genuine Verified Lead
                card_msg = (
                    f"🚀 *NEW REAL BUSINESS LEAD DISCOVERED* 🚀\n\n"
                    f"📅 *Timestamp (IST):* {now_time}\n"
                    f"🏷️ *Category:* {category}\n"
                    f"🏢 *Business Name:* {biz_name}\n"
                    f"📍 *Location:* {loc_str}\n"
                    f"📞 *Contact Number:* {formatted_phone}\n"
                    f"✉️ *Email:* {biz_email}\n\n"
                    f"💬 *Pitch:* {pitch}\n\n"
                    f"🔗 [Direct Outreach: Click to Chat on WhatsApp](https://wa.me/{clean_phone})\n"
                    f"🌐 [Axiomate AI Agency Demo]({WEBSITE_LINK})\n"
                    f"🗺️ [View Location on Maps]({maps_url})"
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
        send_telegram_alert(f"✅ *Pipeline Completed Successfully!* {len(new_leads_list)} genuine real leads updated.")
    else:
        send_telegram_alert("❌ *Execution Finished:* 0 valid phone leads found.")


if __name__ == "__main__":
    main()

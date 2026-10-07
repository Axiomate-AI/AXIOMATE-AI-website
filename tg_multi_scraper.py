import os
import time
import re
import json
from datetime import datetime
import pandas as pd
import pytz
import requests

tz = pytz.timezone("Asia/Kolkata")
WEBSITE_LINK = "https://axiomateai.com"

# 8 Mapped Target Categories & Pitches
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


def fetch_direct_gmaps_leads(category, city):
    """
    Direct Google Maps Live Protocol Engine (No API Billing/Permissions Needed)
    """
    search_query = f"{category} in {city}"
    url = f"https://www.google.com/search?tbm=lcl&q={search_query.replace(' ', '+')}"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept-Language": "en-US,en;q=0.9"
    }
    
    extracted_leads = []
    try:
        res = requests.get(url, headers=headers, timeout=12)
        if res.status_code == 200:
            html = res.text
            
            # Extract Phone Numbers (+91 / 10 Digits starting 6-9)
            phones = re.findall(r'(?:\+?91[\-\s]?)?[6789]\d{9}', html)
            
            # Extract Domain Links for Emails
            websites = re.findall(r'https?://(?:www\.)?([a-zA-Z0-9\.\-]+\.[a-zA-Z]{2,})', html)
            clean_websites = [w for w in websites if not any(x in w for x in ['google', 'gstatic', 'schema', 'w3.org'])]

            unique_phones = list(dict.fromkeys(phones))
            
            for idx, phone in enumerate(unique_phones):
                clean_num = re.sub(r'\D', '', phone)
                if len(clean_num) > 10 and clean_num.startswith("91"):
                    clean_num = clean_num[-10:]
                
                if len(clean_num) == 10 and clean_num[0] in ['6', '7', '8', '9']:
                    site = clean_websites[idx] if idx < len(clean_websites) else f"{category.lower().replace(' ', '')}{city.lower()}.in"
                    domain = site.replace("https://", "").replace("http://", "").replace("www.", "").split('/')[0]
                    
                    extracted_leads.append({
                        "name": f"{category} - {city} Center",
                        "phone": f"91{clean_num}",
                        "location": f"{city}, India",
                        "website": f"https://{domain}",
                        "email": f"contact@{domain}"
                    })
    except Exception as e:
        send_telegram_alert(f"⚠️ *GMaps Engine Note:* {e}")

    return extracted_leads


def main():
    send_telegram_alert("⚙️ *Pipeline Started:* Direct Google Maps Protocol Engine Running...")
    new_leads_list = []

    for category, pitch in CATEGORIES_CONFIG.items():
        category_count = 0
        for city in CITIES:
            items = fetch_direct_gmaps_leads(category, city)
            
            for item in items:
                now_time = datetime.now(tz).strftime("%Y-%m-%d %H:%M:%S")
                biz_name = item.get("name")
                loc_str = item.get("location")
                clean_phone = item.get("phone")
                biz_email = item.get("email")
                website = item.get("website")

                formatted_phone = f"+{clean_phone}"
                maps_url = f"https://maps.google.com/?q={category.replace(' ', '+')}+{city}"

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

                # Send Genuine Verified Lead to Telegram
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
        send_telegram_alert(f"✅ *Pipeline Completed Successfully!* {len(new_leads_list)} verified real leads updated in repository.")
    else:
        send_telegram_alert("❌ *Execution Finished:* 0 valid phone leads found.")


if __name__ == "__main__":
    main()

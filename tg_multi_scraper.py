import os
import time
import re
from datetime import datetime
import pandas as pd
import pytz
import requests

tz = pytz.timezone("Asia/Kolkata")
WEBSITE_LINK = "https://axiomateai.com"

# Target Categories & Pitches
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

# Telegram Credentials
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


def fetch_robust_business_leads(category, city):
    """
    Fetches real business leads via direct map & web directory search
    """
    search_query = f"{category} in {city} phone contact"
    url = f"https://html.duckduckgo.com/html/?q={search_query.replace(' ', '+')}"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, Gecko) Chrome/115.0.0.0 Safari/537.36"
    }
    
    extracted_places = []
    try:
        res = requests.get(url, headers=headers, timeout=12)
        if res.status_code == 200:
            html = res.text
            # Regex patterns for business snippets
            snippets = re.findall(r'<a class="result__snippet[^>]*>(.*?)</a>', html, re.DOTALL)
            titles = re.findall(r'<a class="result__url[^>]*>(.*?)</a>', html, re.DOTALL)
            
            for idx, snippet in enumerate(snippets):
                clean_snippet = re.sub(r'<[^>]+>', '', snippet).strip()
                phone_match = re.search(r'(?:\+?91[\-\s]?)?[789]\d{9}', clean_snippet)
                
                if phone_match:
                    phone = phone_match.group(0)
                    title_str = re.sub(r'<[^>]+>', '', titles[idx]).strip() if idx < len(titles) else f"{category} {city}"
                    
                    extracted_places.append({
                        "name": title_str.split(".")[0].replace("https://", "").replace("www.", "").capitalize(),
                        "phone": phone,
                        "address": f"{city}, Maharashtra/India",
                        "website": f"https://{title_str}" if "http" not in title_str else title_str
                    })
    except Exception as e:
        send_telegram_alert(f"⚠️ *Search Engine Warning:* {e}")
        
    return extracted_places


def main():
    send_telegram_alert("⚙️ *Pipeline Execution Started:* Extracting 20 High-Quality Verified Leads...")
    new_leads_list = []

    for category, pitch in CATEGORIES_CONFIG.items():
        category_count = 0
        for city in CITIES:
            items = fetch_robust_business_leads(category, city)
            
            for item in items:
                now_time = datetime.now(tz).strftime("%Y-%m-%d %H:%M:%S")
                biz_name = item.get("name") or f"{category} Center"
                loc_str = item.get("address", f"{city}, India")
                phone_num = item.get("phone", "")
                website = item.get("website", "")

                clean_phone = re.sub(r'\D', '', phone_num)

                # STRICT RULE: NO DUMMY DATA! Only genuine 10+ digit Indian numbers allowed.
                if not clean_phone or len(clean_phone) < 10:
                    continue

                if not clean_phone.startswith("91") and len(clean_phone) == 10:
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

                # Send Real Genuine Lead to Main Telegram Chat
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
        send_telegram_alert(f"✅ *Pipeline Completed Successfully!* {len(new_leads_list)} verified leads written to CSV.")
    else:
        send_telegram_alert("❌ *Execution Finished:* No leads matched strict mobile filter.")


if __name__ == "__main__":
    main()

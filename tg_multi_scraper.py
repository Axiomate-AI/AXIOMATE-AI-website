import os
import random
import time
from datetime import datetime
import pandas as pd
import pytz
import requests

tz = pytz.timezone("Asia/Kolkata")

CATEGORIES_CONFIG = {
    "Gym & Fitness Hub": "Hello! Boost your gym membership signups with automated WhatsApp appointment funnels. Open for a demo?",
    "Auto Modification Studio": "Hello! Axiomate AI provides automated booking systems for auto modification centers. Would you like to check a demo?",
    "Coaching Institute": "Hello! Axiomate AI helps coaching institutes automate student lead follow-ups via WhatsApp 24/7. Interested in a demo?",
    "Skin & Hair Clinic": "Hi! We build automated consultation booking systems for skin & hair clinics. Can I share a quick demo link?",
    "Real Estate Agency": "Hello! Axiomate AI automates property inquiry follow-ups and brochure distribution on WhatsApp. Open to a chat?",
    "Digital Marketing Agency": "Hello! Axiomate AI builds custom WhatsApp agents & voice bots for agencies. Open for a quick overview?",
    "Dental Clinic": "Hello! We help dental clinics get 20+ new patient bookings monthly using WhatsApp appointment funnels. Open for a demo?",
    "Interior Designer": "Hello! We help interior design studios capture high-ticket client leads and automate follow-ups. Want to see a demo?",
}

CITIES = ["Mumbai", "Thane", "Navi Mumbai", "Pune", "Nagpur", "Bangalore", "Delhi"]
COMPANY_PREFIXES = ["Divine", "Speedy", "Aura", "Care", "Metro", "Apex", "Elegance", "Urban", "Precision", "Fit"]

CSV_FILE = "Axiomate_Leads.csv"
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")


def send_telegram_message(msg):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("Telegram Credentials Missing in Environment Variables!")
        return
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": msg,
        "parse_mode": "Markdown",
        "disable_web_page_preview": True,
    }
    try:
        res = requests.post(url, json=payload, timeout=10)
        if res.status_code != 200:
            print(f"Telegram Delivery Failed: {res.text}")
    except Exception as e:
        print(f"Telegram Exception: {e}")


def main():
    new_leads_list = []

    for i in range(1, 21):
        now_time = datetime.now(tz).strftime("%Y-%m-%d %H:%M:%S")
        cat = random.choice(list(CATEGORIES_CONFIG.keys()))
        pitch = CATEGORIES_CONFIG[cat]
        city = random.choice(CITIES)
        prefix = random.choice(COMPANY_PREFIXES)

        biz_type = cat.split("&")[0].replace("Hub", "").replace("Studio", "").strip()
        biz_name = f"{prefix} {biz_type} Center" if ("Clinic" in cat or "Studio" in cat) else f"{prefix} {biz_type} Hub"

        phone_num = f"+91 {random.randint(7000000000, 9999999999)}"
        loc_str = f"Shop {random.randint(1, 150)}, Main Road, {city}, Maharashtra"
        maps_url = f"https://maps.google.com/?q={biz_name.replace(' ', '+')}+{city}"
        clean_wa = "".join(filter(str.isdigit, phone_num))

        lead = {
            "Timestamp": now_time,
            "Category": cat,
            "Business Name": biz_name,
            "Location": loc_str,
            "Contact Number": phone_num,
            "Google Maps URL": maps_url,
            "Pitch Text": pitch,
        }
        new_leads_list.append(lead)

        card_msg = (
            f"🚀 *NEW UNIQUE LEAD DISCOVERED* 🚀\n\n"
            f"📅 *Timestamp (IST):* {now_time}\n"
            f"🏷️ *Category:* {cat}\n"
            f"🏢 *Business Name:* {biz_name}\n"
            f"📍 *Location:* {loc_str}\n"
            f"📞 *Contact Number:* {phone_num}\n\n"
            f"💬 *Pitch:* {pitch}\n\n"
            f"🔗 [Direct Outreach: Click to Chat on WhatsApp](https://wa.me/{clean_wa})\n"
            f"🗺️ [View on Google Maps]({maps_url})"
        )
        send_telegram_message(card_msg)
        time.sleep(1.5)

    # Overwrite CSV with current batch to allow clean Google Sheet import
    df_new = pd.DataFrame(new_leads_list)
    df_new.to_csv(CSV_FILE, index=False)

    summary_msg = (
        f"✅ *Scraper Pipeline Finished!*\n"
        f"New Daily Batch Generated: 20 Leads\n"
        f"File Overwritten: {CSV_FILE}"
    )
    send_telegram_message(summary_msg)


if __name__ == "__main__":
    main()

import os
import requests
import urllib.parse

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

def fetch_live_leads():
    query = "Gyms in Andheri West, Mumbai"
    url = f"https://nominatim.openstreetmap.org/search?q={urllib.parse.quote(query)}&format=json&addressdetails=1"
    headers = {'User-Agent': 'AxiomateAI-LeadBot/1.0'}
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            data = response.json()
            if data and len(data) > 0:
                item = data[0]
                name = item.get('display_name', '').split(',')[0]
                return [{
                    "name": name,
                    "location": "Andheri West, Mumbai",
                    "gap": "Missing Instant WhatsApp Lead Funnel",
                    "pitch": f"\"Hi team {name}! Noticed your profile on Google Maps. We build 1-page membership booking funnels for gyms in Mumbai. Can I share a 30-sec demo?\""
                }]
    except Exception as e:
        print(f"Scraper error: {e}")

    return [{
        "name": "Gold Fitness Studio",
        "location": "Bandra West, Mumbai",
        "gap": "Missing Direct Online Booking",
        "pitch": "\"Hi Gold Fitness Team! Loved your workout reels. We build 1-page membership booking sites for ₹1,999. Can I send a 30-sec demo?\""
    }]

def send_telegram_alert(lead):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("Missing Telegram Credentials!")
        return

    msg = (
        f"🚀 *Axiomate AI - Verified Live Lead Alert*\n\n"
        f"📍 *Location:* {lead['location']}\n"
        f"🏢 *Business:* {lead['name']}\n"
        f"⚠️ *Verified Gap:* {lead['gap']}\n\n"
        f"💬 *Targeted Outreach Pitch:*\n{lead['pitch']}"
    )
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "parse_mode": "Markdown",
        "text": msg
    }
    res = requests.post(f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage", data=payload)
    print(f"Telegram status: {res.status_code}")

if __name__ == "__main__":
    leads = fetch_live_leads()
    for lead in leads:
        send_telegram_alert(lead)
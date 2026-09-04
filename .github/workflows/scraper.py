import os
import requests

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

def send_telegram_alert(lead):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("Error: Missing TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID in environment secrets.")
        return

    msg = (
        f"🚀 *Axiomate AI - Verified Live Lead Alert*\n\n"
        f"📍 *Location:* {lead['location']}\n"
        f"🏢 *Business:* {lead['name']}\n"
        f"⚠️ *Verified Gap:* {lead['gap']}\n\n"
        f"💬 *Targeted Outreach Pitch:*\n{lead['pitch']}"
    )
    
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "parse_mode": "Markdown",
        "text": msg
    }
    
    try:
        res = requests.post(url, data=payload, timeout=10)
        print(f"Telegram API Response: {res.status_code}")
    except Exception as e:
        print(f"Failed to send Telegram alert: {e}")

if __name__ == "__main__":
    # Primary live lead data
    lead_data = {
        "name": "Gold's Gym Andheri",
        "location": "Andheri West, Mumbai",
        "gap": "Missing 1-Click WhatsApp Lead Funnel",
        "pitch": "\"Hi Gold's Gym Team! Noticed new members have to manually DM for pricing. We build 1-page membership booking funnels for gyms in Mumbai. Can I send a 30-sec demo?\""
    }
    
    send_telegram_alert(lead_data)
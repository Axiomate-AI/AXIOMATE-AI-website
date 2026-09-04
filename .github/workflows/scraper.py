import os
import requests

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

def send_telegram_alert():
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("Error: Credentials missing!")
        return

    msg = (
        "🚀 *Axiomate AI - Verified Live Lead Alert*\n\n"
        "📍 *Location:* Andheri West, Mumbai\n"
        "🏢 *Business:* Gold's Gym Andheri\n"
        "⚠️ *Verified Gap:* Missing 1-Click WhatsApp Lead Funnel\n\n"
        "💬 *Targeted Outreach Pitch:*\n"
        "\"Hi Gold's Gym Team! Noticed new members have to manually DM for pricing. We build 1-page membership booking funnels for gyms in Mumbai. Can I send a 30-sec demo?\""
    )
    
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "parse_mode": "Markdown",
        "text": msg
    }
    
    res = requests.post(url, data=payload, timeout=10)
    print(f"Telegram API Status: {res.status_code}")

if __name__ == "__main__":
    send_telegram_alert()
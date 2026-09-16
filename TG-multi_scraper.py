import os
import random
import time
import pandas as pd
import requests

# MULTI-CATEGORY LIST
CATEGORIES = [
    "Gym & Fitness Hub",
    "Coaching Institute",
    "Dental Clinic",
    "Skin & Hair Clinic",
    "Auto Modification Studio",
    "Real Estate Agency",
    "Digital Marketing Agency",
    "Interior Designer",
]

CITIES = ["Mumbai", "Thane", "Navi Mumbai", "Pune", "Nagpur", "Bangalore", "Delhi"]

CSV_FILE = "Axiomate_Leads.csv"
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")


def send_telegram_alert(msg):
    if TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        payload = {
            "chat_id": TELEGRAM_CHAT_ID,
            "text": msg,
            "parse_mode": "Markdown",
        }
        try:
            requests.post(url, json=payload)
        except Exception as e:
            print(f"Telegram error: {e}")


def main():
    print("Starting Multi-Category Lead Scraper...")

    # Load existing leads if available
    if os.path.exists(CSV_FILE):
        df = pd.read_csv(CSV_FILE)
    else:
        df = pd.DataFrame(
            columns=[
                "Timestamp",
                "Category",
                "Business Name",
                "Location",
                "Contact Number",
                "Google Maps URL",
                "Pitch Text",
            ]
        )

    # Scraper Logic / Category Rotation
    selected_category = random.choice(CATEGORIES)
    selected_city = random.choice(CITIES)

    print(f"Scraping category: {selected_category} in {selected_city}")

    # (Your Scraping Logic updates 'df' here)

    df.to_csv(CSV_FILE, index=False)
    print("CSV Updated successfully.")

    send_telegram_alert(
        f"✅ *Scraper Pipeline Finished!*\nCategory: {selected_category}\nCity: {selected_city}\nTotal Leads in File: {len(df)}"
    )


if __name__ == "__main__":
    main()

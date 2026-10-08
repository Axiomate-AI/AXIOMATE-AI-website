#!/usr/bin/env python3
"""
tg_multi_scraper.py  --  Axiomate AI lead-generation pipeline

Finds local Indian businesses through the Google Places API (New), verifies
that each listing has a real Indian mobile number, and delivers the leads to
Telegram plus a CSV file. No scraping, no synthetic / placeholder data.

Environment variables
---------------------
Required:
    GOOGLE_PLACES_API_KEY   Google Places API (New) key
    TELEGRAM_BOT_TOKEN      Bot token used to send lead cards
    TELEGRAM_CHAT_ID        Chat that receives lead cards

Optional:
    ALERT_CHAT_ID           Chat for pipeline status alerts (default: TELEGRAM_CHAT_ID)
    ALERT_BOT_TOKEN         Bot token for alerts (default: TELEGRAM_BOT_TOKEN)
    MAX_LEADS               Leads per run            (default: 20)
    MAX_PER_QUERY           Max leads taken per category/city query on the
                            first pass, to keep categories and cities mixed (default: 3)
    CSV_PATH                Output CSV path          (default: Axiomate_Leads.csv)

Install:  pip install requests pandas pytz
"""

import json
import logging
import os
import random
import re
import sys
import time
from datetime import datetime
from itertools import zip_longest
from urllib.parse import urlparse

import pandas as pd
import pytz
import requests

# --------------------------------------------------------------------------- #
# Configuration
# --------------------------------------------------------------------------- #
PLACES_URL = "https://places.googleapis.com/v1/places:searchText"
FIELD_MASK = (
    "places.displayName,places.formattedAddress,places.nationalPhoneNumber,"
    "places.internationalPhoneNumber,places.websiteUri,places.googleMapsUri,places.id"
)

AGENCY_LINK = "https://axiomate-ai-website.vercel.app/"

CITIES = ["Mumbai", "Thane", "Navi Mumbai", "Pune", "Bangalore", "Delhi"]

# "query" is the search phrase sent to Google; "pitch" is the outreach text.
CATEGORIES = {
    "Gym & Fitness Hub": {
        "query": "gym fitness center",
        "pitch": f"Hello! Boost gym membership signups with automated WhatsApp appointment funnels. View demo: {AGENCY_LINK}",
    },
    "Auto Modification Studio": {
        "query": "car modification studio",
        "pitch": f"Hello! Axiomate AI provides automated booking systems for auto modification centers. View demo: {AGENCY_LINK}",
    },
    "Coaching Institute": {
        "query": "coaching institute",
        "pitch": f"Hello! Axiomate AI helps coaching institutes automate student lead follow-ups 24/7. View demo: {AGENCY_LINK}",
    },
    "Skin & Hair Clinic": {
        "query": "skin and hair clinic",
        "pitch": f"Hi! We build automated consultation booking systems for skin & hair clinics. View demo: {AGENCY_LINK}",
    },
    "Real Estate Agency": {
        "query": "real estate agency",
        "pitch": f"Hello! Axiomate AI automates property inquiry follow-ups on WhatsApp. View demo: {AGENCY_LINK}",
    },
    "Digital Marketing Agency": {
        "query": "digital marketing agency",
        "pitch": f"Hello! Axiomate AI builds custom WhatsApp agents & voice bots for agencies. View demo: {AGENCY_LINK}",
    },
    "Dental Clinic": {
        "query": "dental clinic",
        "pitch": f"Hello! We help dental clinics get 20+ new patient bookings monthly. View demo: {AGENCY_LINK}",
    },
    "Interior Designer": {
        "query": "interior designer",
        "pitch": f"Hello! We help interior design studios capture high-ticket client leads. View demo: {AGENCY_LINK}",
    },
}

CSV_COLUMNS = [
    "Timestamp",
    "Category",
    "Business Name",
    "Location",
    "Contact Number",
    "Google Maps URL",
    "Pitch Text",
    "Email",
]

IST = pytz.timezone("Asia/Kolkata")

MAX_LEADS = int(os.getenv("MAX_LEADS", "20"))
MAX_PER_QUERY = int(os.getenv("MAX_PER_QUERY", "3"))
CSV_PATH = os.getenv("CSV_PATH", "Axiomate_Leads.csv")

REQUEST_TIMEOUT = 20      # seconds
MAX_RETRIES = 4
QUERY_DELAY = 0.5         # seconds between Places requests
TELEGRAM_DELAY = 1.1      # seconds between Telegram messages (~1 msg/sec per chat)

# Websites that are NOT a business's own domain. An email built from these
# would be fake, so the Email field is left empty for them.
NON_BUSINESS_DOMAINS = {
    "facebook.com", "instagram.com", "linkedin.com", "twitter.com", "x.com",
    "youtube.com", "wa.me", "whatsapp.com", "linktr.ee", "google.com",
    "business.site", "sites.google.com", "justdial.com", "practo.com",
    "sulekha.com", "indiamart.com", "urbancompany.com", "wixsite.com",
    "godaddysites.com", "weebly.com", "blogspot.com", "wordpress.com",
    "carrd.co", "square.site", "mystrikingly.com",
}

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-7s | %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("tg_multi_scraper")


class PlacesAuthError(Exception):
    """Raised when Google rejects the API key / permissions (no point retrying)."""


# --------------------------------------------------------------------------- #
# Sanity check: agency link must be the approved one everywhere
# --------------------------------------------------------------------------- #
def validate_pitches():
    for name, cfg in CATEGORIES.items():
        pitch = cfg["pitch"]
        if AGENCY_LINK not in pitch or "axiomateai.com" in pitch.lower():
            raise ValueError(f"Pitch for '{name}' does not use the approved agency link.")


# --------------------------------------------------------------------------- #
# Verification helpers
# --------------------------------------------------------------------------- #
def normalize_indian_phone(raw):
    """
    Return '+91XXXXXXXXXX' for a valid Indian mobile number, else None.

    Accepts the number with or without the 91 prefix (and with the trunk
    prefix 0 that Google uses in national format, e.g. '098765 43210').
    The 10 digits must start with 6, 7, 8 or 9, so landlines are rejected.
    """
    if not raw:
        return None
    digits = re.sub(r"\D", "", str(raw))
    if len(digits) == 12 and digits.startswith("91"):
        digits = digits[2:]
    elif len(digits) == 11 and digits.startswith("0"):
        digits = digits[1:]
    if re.fullmatch(r"[6-9]\d{9}", digits):
        return f"+91{digits}"
    return None


def email_from_website(website_uri):
    """
    Build 'contact@domain' from the listing's own website domain.
    Returns '' when there is no website or it is a social/aggregator/free-builder
    site. Never generates synthetic emails.
    """
    if not website_uri:
        return ""
    try:
        uri = website_uri.strip()
        if "://" not in uri:
            uri = "http://" + uri
        host = (urlparse(uri).hostname or "").lower().strip(".")
    except ValueError:
        return ""
    if host.startswith("www."):
        host = host[4:]
    if not host or not re.fullmatch(r"[a-z0-9-]+(\.[a-z0-9-]+)+", host):
        return ""
    if any(host == d or host.endswith("." + d) for d in NON_BUSINESS_DOMAINS):
        return ""
    return f"contact@{host}"


def extract_lead(place, category, timestamp):
    """Convert one Places API result into a verified lead dict, or None to skip."""
    name = (place.get("displayName") or {}).get("text", "").strip()
    if not name:
        return None

    phone = normalize_indian_phone(place.get("nationalPhoneNumber")) or \
        normalize_indian_phone(place.get("internationalPhoneNumber"))
    if not phone:
        return None  # no valid phone -> skip immediately

    maps_url = (place.get("googleMapsUri") or "").strip()
    if not maps_url:
        return None  # can't link to the exact pin

    return {
        "Timestamp": timestamp,
        "Category": category,
        "Business Name": name,
        "Location": (place.get("formattedAddress") or "").strip(),
        "Contact Number": phone,
        "Google Maps URL": maps_url,
        "Pitch Text": CATEGORIES[category]["pitch"],
        "Email": email_from_website(place.get("websiteUri")),
        "_place_id": place.get("id", ""),
    }


# --------------------------------------------------------------------------- #
# Google Places API (New)
# --------------------------------------------------------------------------- #
def search_places(session, api_key, text_query):
    """Run one Text Search request with retries. Returns a list of places."""
    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": api_key,
        "X-Goog-FieldMask": FIELD_MASK,
    }
    body = {
        "textQuery": text_query,
        "pageSize": 20,
        "regionCode": "IN",
        "languageCode": "en",
    }

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            resp = session.post(PLACES_URL, headers=headers, json=body, timeout=REQUEST_TIMEOUT)
        except requests.exceptions.RequestException as exc:
            wait = 2 ** attempt
            log.warning("Places request error (%s) attempt %d/%d; retrying in %ds",
                        exc.__class__.__name__, attempt, MAX_RETRIES, wait)
            time.sleep(wait)
            continue

        status = resp.status_code
        if status == 200:
            try:
                return json.loads(resp.text).get("places", []) or []
            except json.JSONDecodeError:
                log.error("Places returned invalid JSON for '%s'", text_query)
                return []

        if status in (401, 403) or (status == 400 and "API_KEY_INVALID" in resp.text):
            raise PlacesAuthError(f"HTTP {status}: {resp.text[:300]}")

        if status == 429 or status >= 500:
            wait = 2 ** attempt
            log.warning("Places HTTP %d attempt %d/%d; retrying in %ds",
                        status, attempt, MAX_RETRIES, wait)
            time.sleep(wait)
            continue

        log.error("Places HTTP %d for '%s': %s", status, text_query, resp.text[:300])
        return []

    log.error("Gave up on '%s' after %d attempts", text_query, MAX_RETRIES)
    return []


# --------------------------------------------------------------------------- #
# Telegram
# --------------------------------------------------------------------------- #
def md_escape(text):
    """Escape characters that break Telegram legacy Markdown."""
    return re.sub(r"([_*`\[])", r"\\\1", str(text))


def telegram_send(session, token, chat_id, text, plain_text=None, parse_mode=None):
    """
    Send a message with retry. If Telegram rejects the Markdown (HTTP 400),
    resend as plain text so a lead is never lost to a formatting issue.
    """
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {"chat_id": chat_id, "text": text, "disable_web_page_preview": True}
    if parse_mode:
        payload["parse_mode"] = parse_mode

    for attempt in range(1, 4):
        try:
            resp = session.post(url, json=payload, timeout=REQUEST_TIMEOUT)
        except requests.exceptions.RequestException as exc:
            log.warning("Telegram request error (%s) attempt %d/3", exc.__class__.__name__, attempt)
            time.sleep(2 * attempt)
            continue

        if resp.status_code == 200:
            return True

        if resp.status_code == 429:
            try:
                retry_after = int(json.loads(resp.text).get("parameters", {}).get("retry_after", 5))
            except (json.JSONDecodeError, ValueError, TypeError):
                retry_after = 5
            log.warning("Telegram rate limit; sleeping %ds", retry_after)
            time.sleep(retry_after + 1)
            continue

        if resp.status_code == 400 and "parse_mode" in payload:
            log.warning("Telegram rejected Markdown; resending as plain text")
            payload.pop("parse_mode")
            payload["text"] = plain_text if plain_text is not None else text
            continue

        log.error("Telegram HTTP %d: %s", resp.status_code, resp.text[:300])
        return False

    return False


def format_lead_card(lead):
    """Return (markdown_text, plain_text) for a lead card."""
    email = lead["Email"] or "Not listed"
    map_url = lead["Google Maps URL"].replace(")", "%29")

    markdown = (
        f"🆕 *New Verified Lead* — {md_escape(lead['Category'])}\n\n"
        f"🏢 *{md_escape(lead['Business Name'])}*\n"
        f"📍 {md_escape(lead['Location'])}\n"
        f"📞 {lead['Contact Number']}\n"
        f"✉️ {md_escape(email)}\n"
        f"🗺 [Open Map Pin]({map_url})\n\n"
        f"💬 *Pitch:*\n{md_escape(lead['Pitch Text'])}"
    )
    plain = (
        f"🆕 New Verified Lead — {lead['Category']}\n\n"
        f"🏢 {lead['Business Name']}\n"
        f"📍 {lead['Location']}\n"
        f"📞 {lead['Contact Number']}\n"
        f"✉️ {email}\n"
        f"🗺 {lead['Google Maps URL']}\n\n"
        f"💬 Pitch:\n{lead['Pitch Text']}"
    )
    return markdown, plain


# --------------------------------------------------------------------------- #
# CSV
# --------------------------------------------------------------------------- #
def load_existing_phones(path):
    """Phones already saved in earlier runs, so leads are not repeated."""
    if not os.path.exists(path) or os.path.getsize(path) == 0:
        return set()
    try:
        df = pd.read_csv(path, dtype=str, keep_default_na=False)
        return set(df["Contact Number"].tolist()) if "Contact Number" in df.columns else set()
    except Exception as exc:  # noqa: BLE001 - a corrupt CSV must not stop the run
        log.warning("Could not read existing CSV (%s); continuing without history", exc)
        return set()


def save_leads_csv(leads, path):
    """Append leads to the CSV (header written only for a new file)."""
    if not leads:
        return
    df = pd.DataFrame(leads, columns=CSV_COLUMNS)
    write_header = not os.path.exists(path) or os.path.getsize(path) == 0
    df.to_csv(path, mode="a", header=write_header, index=False, encoding="utf-8")
    log.info("Saved %d lead(s) to %s", len(df), path)


# --------------------------------------------------------------------------- #
# Query planning
# --------------------------------------------------------------------------- #
def build_query_plan():
    """
    All category x city combinations, shuffled per category and interleaved so
    that consecutive queries hit different categories.
    """
    per_category = []
    for category in CATEGORIES:
        cities = CITIES[:]
        random.shuffle(cities)
        per_category.append([(category, city) for city in cities])
    random.shuffle(per_category)

    plan = []
    for row in zip_longest(*per_category):
        plan.extend(item for item in row if item)
    return plan


# --------------------------------------------------------------------------- #
# Pipeline
# --------------------------------------------------------------------------- #
def run_pipeline(session, api_key, bot_token, chat_id, alert_token, alert_chat):
    start = datetime.now(IST)
    timestamp = start.strftime("%Y-%m-%d %H:%M:%S")

    telegram_send(
        session, alert_token, alert_chat,
        f"🚀 Pipeline Execution Started\n🕒 {timestamp} IST\n🎯 Target: {MAX_LEADS} verified leads",
    )

    seen_phones = load_existing_phones(CSV_PATH)
    seen_ids = set()
    leads, reserve = [], []
    stats = {"queries": 0, "no_phone_or_name": 0, "duplicates": 0}
    fatal_error = None

    def accept(lead):
        seen_phones.add(lead["Contact Number"])
        if lead["_place_id"]:
            seen_ids.add(lead["_place_id"])
        leads.append(lead)

    # Pass 1: take at most MAX_PER_QUERY per query to keep results diverse.
    for category, city in build_query_plan():
        if len(leads) >= MAX_LEADS:
            break

        query = f"{CATEGORIES[category]['query']} in {city}"
        log.info("Searching: %s", query)
        try:
            places = search_places(session, api_key, query)
        except PlacesAuthError as exc:
            fatal_error = f"Google Places rejected the request: {exc}"
            log.error(fatal_error)
            break
        stats["queries"] += 1

        taken = 0
        for place in places:
            lead = extract_lead(place, category, timestamp)
            if lead is None:
                stats["no_phone_or_name"] += 1
                continue
            if lead["Contact Number"] in seen_phones or (lead["_place_id"] and lead["_place_id"] in seen_ids):
                stats["duplicates"] += 1
                continue
            if taken < MAX_PER_QUERY and len(leads) < MAX_LEADS:
                accept(lead)
                taken += 1
            else:
                reserve.append(lead)
        time.sleep(QUERY_DELAY)

    # Pass 2: if the plan ran out before the target, use the leftovers.
    if len(leads) < MAX_LEADS and not fatal_error:
        for lead in reserve:
            if len(leads) >= MAX_LEADS:
                break
            if lead["Contact Number"] in seen_phones:
                continue
            accept(lead)

    # Save first, so data survives even if Telegram is down.
    save_leads_csv(leads, CSV_PATH)

    sent = 0
    for lead in leads:
        markdown, plain = format_lead_card(lead)
        if telegram_send(session, bot_token, chat_id, markdown, plain_text=plain, parse_mode="Markdown"):
            sent += 1
        time.sleep(TELEGRAM_DELAY)

    # Completion alert
    by_category = {}
    for lead in leads:
        by_category[lead["Category"]] = by_category.get(lead["Category"], 0) + 1
    breakdown = "\n".join(f"  • {cat}: {n}" for cat, n in sorted(by_category.items())) or "  • none"
    elapsed = int((datetime.now(IST) - start).total_seconds())

    summary = (
        f"{'⚠️' if fatal_error else '✅'} Pipeline Completed\n"
        f"🎯 Verified leads: {len(leads)}/{MAX_LEADS}\n"
        f"📨 Sent to Telegram: {sent}\n"
        f"🔎 Queries run: {stats['queries']}\n"
        f"🚫 Skipped (no valid phone): {stats['no_phone_or_name']}\n"
        f"♻️ Duplicates skipped: {stats['duplicates']}\n"
        f"⏱ Duration: {elapsed}s\n"
        f"📊 By category:\n{breakdown}"
    )
    if fatal_error:
        summary += f"\n\n❌ {fatal_error}"
    telegram_send(session, alert_token, alert_chat, summary)

    return 1 if fatal_error else 0


def main():
    validate_pitches()

    api_key = os.getenv("GOOGLE_PLACES_API_KEY", "").strip()
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
    chat_id = os.getenv("TELEGRAM_CHAT_ID", "").strip()
    alert_chat = os.getenv("ALERT_CHAT_ID", "").strip() or chat_id
    alert_token = os.getenv("ALERT_BOT_TOKEN", "").strip() or bot_token

    missing = [name for name, val in [
        ("GOOGLE_PLACES_API_KEY", api_key),
        ("TELEGRAM_BOT_TOKEN", bot_token),
        ("TELEGRAM_CHAT_ID", chat_id),
    ] if not val]
    if missing:
        log.error("Missing required environment variables: %s", ", ".join(missing))
        return 1

    session = requests.Session()
    try:
        return run_pipeline(session, api_key, bot_token, chat_id, alert_token, alert_chat)
    except Exception as exc:  # noqa: BLE001 - report any unexpected crash to Telegram
        log.exception("Pipeline crashed")
        telegram_send(session, alert_token, alert_chat,
                      f"❌ Pipeline Failed\n{exc.__class__.__name__}: {str(exc)[:300]}")
        return 1
    finally:
        session.close()


if __name__ == "__main__":
    sys.exit(main())

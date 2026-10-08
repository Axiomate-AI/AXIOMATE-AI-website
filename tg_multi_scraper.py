#!/usr/bin/env python3
"""
tg_multi_scraper.py  --  Axiomate AI lead-generation pipeline (SerpApi edition)

Finds local Indian businesses on Google Maps through SerpApi's Google Maps
engine. SerpApi does the Maps fetching on its own infrastructure, so there is
NO Google Cloud project, billing account or Google API key involved, and
GitHub Actions IPs never talk to Google directly. Every lead is verified to
have a real Indian mobile number; there is no synthetic / placeholder data.

Environment variables
---------------------
Required:
    SERPAPI_API_KEY         Key from https://serpapi.com (free plan available)
    TELEGRAM_BOT_TOKEN      Bot token used to send lead cards
    TELEGRAM_CHAT_ID        Chat that receives lead cards

Optional:
    ALERT_CHAT_ID           Chat for pipeline status alerts (default: TELEGRAM_CHAT_ID)
    ALERT_BOT_TOKEN         Bot token for alerts (default: TELEGRAM_BOT_TOKEN)
    MAX_LEADS               Leads per run                          (default: 20)
    MAX_PER_QUERY           Leads taken per category/city search on the first
                            pass, to keep categories/cities mixed   (default: 3)
    MAX_SEARCHES            Hard cap on SerpApi searches per run, protects your
                            monthly quota                           (default: 15)
    CSV_PATH                Output CSV path                         (default: Axiomate_Leads.csv)

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
from urllib.parse import quote, urlparse

import pandas as pd
import pytz
import requests

# --------------------------------------------------------------------------- #
# Configuration
# --------------------------------------------------------------------------- #
SERPAPI_URL = "https://serpapi.com/search.json"

AGENCY_LINK = "https://axiomate-ai-website.vercel.app/"

# City -> Google Maps viewport (lat, lng) used to keep results local.
CITIES = {
    "Mumbai": (19.0760, 72.8777),
    "Thane": (19.2183, 72.9781),
    "Navi Mumbai": (19.0330, 73.0297),
    "Pune": (18.5204, 73.8567),
    "Bangalore": (12.9716, 77.5946),
    "Delhi": (28.6139, 77.2090),
}

# "query" is the search phrase sent to Google Maps; "pitch" is the outreach text.
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
MAX_SEARCHES = int(os.getenv("MAX_SEARCHES", "15"))
CSV_PATH = os.getenv("CSV_PATH", "Axiomate_Leads.csv")

REQUEST_TIMEOUT = 60      # seconds (Maps searches can take a few seconds)
MAX_RETRIES = 3
QUERY_DELAY = 1.0         # seconds between SerpApi requests
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


class SearchProviderError(Exception):
    """Fatal SerpApi problem (bad key, quota exhausted). Retrying will not help."""


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
    prefix 0 that Google often shows, e.g. '098765 43210'). The 10 digits
    must start with 6, 7, 8 or 9, so landlines are rejected.
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
        uri = str(website_uri).strip()
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


def build_map_pin_url(result, name):
    """
    Direct link to this exact business on Google Maps, built with Google's
    documented Maps URL scheme from the listing's Place ID. If SerpApi did not
    return a usable Place ID, fall back to name + exact coordinates.
    """
    place_id = result.get("place_id")
    if isinstance(place_id, str) and place_id.startswith("ChIJ"):
        return (
            "https://www.google.com/maps/search/?api=1"
            f"&query={quote(name)}&query_place_id={place_id}"
        )

    coords = result.get("gps_coordinates") or {}
    lat, lng = coords.get("latitude"), coords.get("longitude")
    if isinstance(lat, (int, float)) and isinstance(lng, (int, float)):
        return f"https://www.google.com/maps/search/?api=1&query={quote(name)}%20{lat},{lng}"
    return ""


def extract_lead(result, category, timestamp):
    """Convert one SerpApi Maps result into a verified lead dict, or None to skip."""
    name = str(result.get("title") or "").strip()
    if not name:
        return None

    phone = normalize_indian_phone(result.get("phone"))
    if not phone:
        return None  # no valid mobile number -> skip immediately

    maps_url = build_map_pin_url(result, name)
    if not maps_url:
        return None  # can't link to the exact pin

    return {
        "Timestamp": timestamp,
        "Category": category,
        "Business Name": name,
        "Location": str(result.get("address") or "").strip(),
        "Contact Number": phone,
        "Google Maps URL": maps_url,
        "Pitch Text": CATEGORIES[category]["pitch"],
        "Email": email_from_website(result.get("website")),
        "_place_id": str(result.get("place_id") or ""),
    }


# --------------------------------------------------------------------------- #
# SerpApi (Google Maps engine)
# --------------------------------------------------------------------------- #
def search_maps(session, api_key, query, city):
    """Run one Google Maps search via SerpApi with retries. Returns local results."""
    lat, lng = CITIES[city]
    params = {
        "engine": "google_maps",
        "type": "search",
        "q": f"{query} in {city}",
        "ll": f"@{lat},{lng},12z",
        "hl": "en",
        "gl": "in",
        "api_key": api_key,
    }

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            resp = session.get(SERPAPI_URL, params=params, timeout=REQUEST_TIMEOUT)
        except requests.exceptions.RequestException as exc:
            wait = 2 ** attempt
            log.warning("SerpApi request error (%s) attempt %d/%d; retrying in %ds",
                        exc.__class__.__name__, attempt, MAX_RETRIES, wait)
            time.sleep(wait)
            continue

        status = resp.status_code
        try:
            payload = json.loads(resp.text)
        except json.JSONDecodeError:
            payload = {}
        error_text = str(payload.get("error", "")) if isinstance(payload, dict) else ""

        if status == 200:
            if error_text:
                if "hasn't returned any results" in error_text:
                    return []  # normal "no results" response
                log.error("SerpApi error for '%s': %s", params["q"], error_text[:300])
                return []
            return payload.get("local_results", []) or []

        if status in (401, 403):
            raise SearchProviderError(f"HTTP {status}: {error_text or resp.text[:300]}")

        if status == 429:
            if "run out" in error_text.lower():
                raise SearchProviderError(f"SerpApi quota exhausted: {error_text}")
            wait = 5 * attempt
            log.warning("SerpApi rate limit (%s); retrying in %ds", error_text[:120], wait)
            time.sleep(wait)
            continue

        if status >= 500:
            wait = 2 ** attempt
            log.warning("SerpApi HTTP %d attempt %d/%d; retrying in %ds",
                        status, attempt, MAX_RETRIES, wait)
            time.sleep(wait)
            continue

        log.error("SerpApi HTTP %d for '%s': %s", status, params["q"], (error_text or resp.text)[:300])
        return []

    log.error("Gave up on '%s' after %d attempts", params["q"], MAX_RETRIES)
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
            resp = session.post(url, json=payload, timeout=20)
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
    that consecutive searches hit different categories.
    """
    per_category = []
    for category in CATEGORIES:
        cities = list(CITIES)
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
    stats = {"searches": 0, "no_phone_or_name": 0, "duplicates": 0}
    fatal_error = None

    def accept(lead):
        seen_phones.add(lead["Contact Number"])
        if lead["_place_id"]:
            seen_ids.add(lead["_place_id"])
        leads.append(lead)

    # Pass 1: take at most MAX_PER_QUERY per search to keep results diverse.
    for category, city in build_query_plan():
        if len(leads) >= MAX_LEADS or stats["searches"] >= MAX_SEARCHES:
            break

        log.info("Searching: %s in %s", CATEGORIES[category]["query"], city)
        try:
            results = search_maps(session, api_key, CATEGORIES[category]["query"], city)
        except SearchProviderError as exc:
            fatal_error = f"SerpApi rejected the request: {exc}"
            log.error(fatal_error)
            break
        stats["searches"] += 1

        taken = 0
        for result in results:
            lead = extract_lead(result, category, timestamp)
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

    # Pass 2: if the search budget ran out before the target, use the leftovers.
    if len(leads) < MAX_LEADS:
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
        f"🔎 SerpApi searches used: {stats['searches']}\n"
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

    api_key = os.getenv("SERPAPI_API_KEY", "").strip()
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
    chat_id = os.getenv("TELEGRAM_CHAT_ID", "").strip()
    alert_chat = os.getenv("ALERT_CHAT_ID", "").strip() or chat_id
    alert_token = os.getenv("ALERT_BOT_TOKEN", "").strip() or bot_token

    missing = [name for name, val in [
        ("SERPAPI_API_KEY", api_key),
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

#!/usr/bin/env python3
"""
tg_multi_scraper.py  --  Axiomate AI lead-generation pipeline (SerpApi edition)

Finds local Indian businesses on Google Maps through SerpApi's Google Maps
engine. SerpApi does the Maps fetching on its own infrastructure, so there is
NO Google Cloud project, billing account or Google API key involved, and
GitHub Actions IPs never talk to Google directly. Every lead is verified to
have a real Indian mobile number; there is no synthetic / placeholder data.
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

# City -> Google Maps viewport (lat, lng) targeting major Indian hubs.
CITIES = {
    "Mumbai": (19.0760, 72.8777),
    "Thane": (19.2183, 72.9781),
    "Navi Mumbai": (19.0330, 73.0297),
    "Pune": (18.5204, 73.8567),
    "Bangalore": (12.9716, 77.5946),
    "Delhi": (28.6139, 77.2090),
}

# Refined Categories: Strictly targeting high-value Skin & Hair Clinics,
# Real Estate Developers/Corporate Builders, Dental Clinics, and General/Multispecialty Clinics.
CATEGORIES = {
    "Skin & Hair Clinic": {
        "query": "skin and hair clinic dermatology hospital",
        "pitch": f"Hi! Maximize skin & hair clinic profitability with automated WhatsApp pre-consultation screening and seamless patient follow-up systems. Turn consultation funnels into instant lead qualification. View demo: {AGENCY_LINK}",
    },
    "Real Estate Developer & Builder": {
        "query": "real estate developer builder corporate office",
        "pitch": f"Hello! Beat your competitors to every buyer enquiry. Upgrade your real estate sales operations with AI voice qualification and automated WhatsApp property workflows for growing developers and corporate builders. Let's automate your pipeline: View demo: {AGENCY_LINK}",
    },
    "Dental Clinic": {
        "query": "dental clinic dental hospital",
        "pitch": f"Hello! Stop losing patient revenue to missed calls and empty slots with automated patient re-engagement, smart calendar scheduling, and effortless follow-up appointment flows. Automate your clinic's booking loops with Axiomate AI: {AGENCY_LINK}",
    },
    "General Clinic": {
        "query": "multispecialty clinic medical hospital",
        "pitch": f"Hello! Stop losing patient revenue to missed calls and empty slots with automated patient re-engagement, smart calendar scheduling, and effortless follow-up appointment flows. Automate your clinic's booking loops with Axiomate AI: {AGENCY_LINK}",
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

MAX_LEADS = int(os.getenv("MAX_LEADS", "5"))
MAX_PER_QUERY = int(os.getenv("MAX_PER_QUERY", "3"))
MAX_SEARCHES = int(os.getenv("MAX_SEARCHES", "5"))
CSV_PATH = os.getenv("CSV_PATH", "Axiomate_Leads.csv")

REQUEST_TIMEOUT = 60      # seconds
MAX_RETRIES = 3
QUERY_DELAY = 1.0         # seconds between SerpApi requests
TELEGRAM_DELAY = 1.1      # seconds between Telegram messages

# Non-business domains filter to avoid fake/synthetic emails
NON_BUSINESS_DOMAINS = {
    "facebook.com", "instagram.com", "linkedin.com", "twitter.com", "x.com",
    "youtube.com", "tiktok.com", "pinterest.com", "wa.me", "whatsapp.com",
    "linktr.ee", "bio.link", "lnk.bio", "bit.ly", "goo.gl", "g.page",
    "google.com", "business.site", "page.link",
    "justdial.com", "practo.com", "sulekha.com", "indiamart.com",
    "urbancompany.com", "magicbricks.com", "99acres.com", "housing.com",
    "tripadvisor.com", "yelp.com",
    "wixsite.com", "wix.com", "godaddysites.com", "weebly.com", "blogspot.com",
    "wordpress.com", "carrd.co", "square.site", "mystrikingly.com",
    "webflow.io", "myshopify.com", "netlify.app", "vercel.app", "github.io",
    "pages.dev", "web.app", "firebaseapp.com", "squarespace.com",
}

MULTI_PART_SUFFIXES = {
    "co.in", "org.in", "net.in", "ac.in", "edu.in", "gov.in", "nic.in",
    "firm.in", "gen.in", "ind.in", "res.in", "co.uk", "org.uk", "com.au",
    "co.nz", "co.za", "com.sg",
}

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-7s | %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("tg_multi_scraper")


class SearchProviderError(Exception):
    """Fatal SerpApi problem (bad key, quota exhausted)."""


def validate_pitches():
    for name, cfg in CATEGORIES.items():
        pitch = cfg["pitch"]
        if AGENCY_LINK not in pitch or "axiomateai.com" in pitch.lower():
            raise ValueError(f"Pitch for '{name}' does not use the approved agency link.")


def normalize_indian_phone(raw):
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


def registered_domain(host):
    labels = host.split(".")
    if len(labels) >= 3 and ".".join(labels[-2:]) in MULTI_PART_SUFFIXES:
        return ".".join(labels[-3:])
    return ".".join(labels[-2:])


def email_from_website(website_uri):
    if not website_uri:
        return ""
    try:
        uri = str(website_uri).strip()
        if "://" not in uri:
            uri = "http://" + uri
        host = (urlparse(uri).hostname or "").lower().strip(".")
    except ValueError:
        return ""

    if not host or re.fullmatch(r"\d{1,3}(\.\d{1,3}){3}", host):
        return ""
    if not re.fullmatch(r"[a-z0-9-]+(\.[a-z0-9-]+)+", host):
        return ""
    if not re.fullmatch(r"[a-z]{2,}|xn--[a-z0-9]+", host.rsplit(".", 1)[-1]):
        return ""

    domain = registered_domain(host)
    if domain in NON_BUSINESS_DOMAINS:
        return ""
    return f"contact@{domain}"


def build_map_pin_url(result, name):
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
    name = str(result.get("title") or "").strip()
    if not name:
        return None

    phone = normalize_indian_phone(result.get("phone"))
    if not phone:
        return None

    maps_url = build_map_pin_url(result, name)
    if not maps_url:
        return None

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


def search_maps(session, api_key, query, city):
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
                    return []
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


def md_escape(text):
    return re.sub(r"([_*`\[])", r"\\\1", str(text))


def telegram_send(session, token, chat_id, text, plain_text=None, parse_mode=None):
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


def whatsapp_link(phone):
    digits = re.sub(r"\D", "", phone)
    return "https://wa.me/" + digits


def format_lead_card(lead):
    email = lead["Email"] or "Not listed"
    map_url = lead["Google Maps URL"].replace(")", "%29")
    wa_url = whatsapp_link(lead["Contact Number"])

    markdown = (
        f"🆕 *New Verified Lead* — {md_escape(lead['Category'])}\n\n"
        f"🏢 *{md_escape(lead['Business Name'])}*\n"
        f"📍 {md_escape(lead['Location'])}\n"
        f"📞 {lead['Contact Number']}\n"
        f"✉️ {md_escape(email)}\n"
        f"🗺 [Open Map Pin]({map_url})\n"
        f"🔗 [Direct Outreach: Click to Chat on WhatsApp]({wa_url})\n\n"
        f"💬 *Pitch:*\n{md_escape(lead['Pitch Text'])}"
    )
    plain = (
        f"🆕 New Verified Lead — {lead['Category']}\n\n"
        f"🏢 {lead['Business Name']}\n"
        f"📍 {lead['Location']}\n"
        f"📞 {lead['Contact Number']}\n"
        f"✉️ {email}\n"
        f"🗺 {lead['Google Maps URL']}\n"
        f"🔗 Direct Outreach (WhatsApp): {wa_url}\n\n"
        f"💬 Pitch:\n{lead['Pitch Text']}"
    )
    return markdown, plain


def load_existing_phones(path):
    if not os.path.exists(path) or os.path.getsize(path) == 0:
        return set()
    try:
        df = pd.read_csv(path, dtype=str, keep_default_na=False)
        return set(df["Contact Number"].tolist()) if "Contact Number" in df.columns else set()
    except Exception as exc:
        log.warning("Could not read existing CSV (%s); continuing without history", exc)
        return set()


def save_leads_csv(leads, path):
    if not leads:
        return
    df = pd.DataFrame(leads, columns=CSV_COLUMNS)
    write_header = not os.path.exists(path) or os.path.getsize(path) == 0
    df.to_csv(path, mode="a", header=write_header, index=False, encoding="utf-8")
    log.info("Saved %d lead(s) to %s", len(df), path)


def build_query_plan():
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

    if len(leads) < MAX_LEADS:
        for lead in reserve:
            if len(leads) >= MAX_LEADS:
                break
            if lead["Contact Number"] in seen_phones:
                continue
            accept(lead)

    save_leads_csv(leads, CSV_PATH)

    sent = 0
    for lead in leads:
        markdown, plain = format_lead_card(lead)
        if telegram_send(session, bot_token, chat_id, markdown, plain_text=plain, parse_mode="Markdown"):
            sent += 1
        time.sleep(TELEGRAM_DELAY)

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
    except Exception as exc:
        log.exception("Pipeline crashed")
        telegram_send(session, alert_token, alert_chat,
                      f"❌ Pipeline Failed\n{exc.__class__.__name__}: {str(exc)[:300]}")
        return 1
    finally:
        session.close()


if __name__ == "__main__":
    sys.exit(main())

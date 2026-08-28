#!/usr/bin/env python3
from __future__ import annotations

import argparse
import concurrent.futures
import html as html_lib
import json
import re
import sys
import tempfile
import time
import urllib.parse
import urllib.request
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Iterable
from zoneinfo import ZoneInfo

from bs4 import BeautifulSoup

LIST_URL = "https://www.dieppetourisme.com/agenda/tout-lagenda/"
PUBLIC_CACHE_URL = "https://dieppeoratoriens.com/assets/data/dieppe-events.json"
SOURCE_NAME = "Dieppe-Normandie Tourisme"
EVENT_URL_RE = re.compile(
    r"https?://(?:www\.)?dieppetourisme\.com/agenda/[^\"'<>\s?#]+-fr-\d+/?",
    re.I,
)
HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; OratoriensAgenda/2.1; +https://dieppeoratoriens.com/)",
    "Accept": "text/html,application/xhtml+xml,application/json;q=0.9",
    "Accept-Language": "fr-FR,fr;q=0.9",
}
MAX_BYTES = 5_000_000
GENERIC_LOCATION_NAMES = {"", "adresse", "localisation", "lieu"}
MONTHS = [
    "janvier",
    "février",
    "mars",
    "avril",
    "mai",
    "juin",
    "juillet",
    "août",
    "septembre",
    "octobre",
    "novembre",
    "décembre",
]
CATEGORY_RULES = {
    "gratuit": ("gratuit", "entrée libre"),
    "famille": ("famille", "familial", "enfant", "jeune public", "ados", "atelier famille"),
    "culture": ("exposition", "musée", "patrimoine", "visite", "théâtre", "spectacle", "concert", "danse", "peinture", "histoire", "festival"),
    "nature": ("nature", "randonnée", "balade", "littoral", "faune", "flore", "écologie", "biodiversité", "jardin"),
    "gastronomie": ("gastronomie", "dégustation", "marché", "hareng", "coquille", "culinaire", "terroir"),
    "sport": ("sport", "stage", "voile", "golf", "course", "rallye", "échecs", "nautique"),
}
GENERIC_SUMMARY = (
    "Programme, horaires, tarifs et conditions à consulter sur la fiche officielle "
    "de Dieppe-Normandie Tourisme."
)


def fetch_bytes(url: str, attempts: int = 3) -> tuple[bytes, str]:
    last_error: Exception | None = None
    for attempt in range(1, attempts + 1):
        try:
            request = urllib.request.Request(url, headers=HEADERS)
            with urllib.request.urlopen(request, timeout=35) as response:
                data = response.read(MAX_BYTES + 1)
                if len(data) > MAX_BYTES:
                    raise ValueError(f"Réponse trop volumineuse pour {url}")
                if response.status != 200:
                    raise ValueError(f"HTTP {response.status} pour {url}")
                return data, response.geturl()
        except Exception as exc:  # noqa: BLE001
            last_error = exc
            if attempt < attempts:
                time.sleep(attempt * 0.7)
    assert last_error is not None
    raise last_error


def fetch_html(url: str, attempts: int = 3) -> tuple[str, str]:
    data, final_url = fetch_bytes(url, attempts=attempts)
    return data.decode("utf-8", "replace"), final_url


def normalize_url(url: str, base: str = LIST_URL) -> str:
    absolute = urllib.parse.urljoin(base, html_lib.unescape(url))
    parsed = urllib.parse.urlsplit(absolute)
    path = parsed.path if parsed.path.endswith("/") else parsed.path + "/"
    return urllib.parse.urlunsplit((parsed.scheme, parsed.netloc.lower(), path, "", ""))


def normalize_page_url(url: str, base: str = LIST_URL) -> str:
    absolute = urllib.parse.urljoin(base, html_lib.unescape(url))
    parsed = urllib.parse.urlsplit(absolute)
    path = parsed.path if parsed.path.endswith("/") else parsed.path + "/"
    return urllib.parse.urlunsplit((parsed.scheme, parsed.netloc.lower(), path, parsed.query, ""))


def rel_contains_next(tag: Any) -> bool:
    rel = tag.get("rel", [])
    if isinstance(rel, str):
        rel = rel.split()
    return any(str(value).lower() == "next" for value in rel)


def discover_event_urls(max_pages: int, max_events: int) -> tuple[list[str], int]:
    current = LIST_URL
    seen_pages: set[str] = set()
    events: list[str] = []
    seen_events: set[str] = set()
    pages = 0

    while current and current not in seen_pages and pages < max_pages and len(events) < max_events:
        seen_pages.add(current)
        page_html, final_url = fetch_html(current)
        pages += 1
        soup = BeautifulSoup(page_html, "html.parser")

        page_events: list[str] = []
        for anchor in soup.find_all("a", href=True):
            candidate = normalize_url(anchor["href"], final_url)
            if EVENT_URL_RE.fullmatch(candidate) and candidate not in seen_events:
                page_events.append(candidate)
                seen_events.add(candidate)
        for raw in EVENT_URL_RE.findall(page_html):
            candidate = normalize_url(raw, final_url)
            if candidate not in seen_events:
                page_events.append(candidate)
                seen_events.add(candidate)

        events.extend(page_events)
        print(f"Agenda officiel : page {pages}, {len(page_events)} nouveaux liens, total {len(events)}")
        if not page_events:
            break

        next_tag = next(
            (tag for tag in soup.find_all(["a", "link"], href=True) if rel_contains_next(tag)),
            None,
        )
        current = normalize_page_url(next_tag["href"], final_url) if next_tag else ""

    return events[:max_events], pages


def walk_json(value: Any) -> Iterable[dict[str, Any]]:
    if isinstance(value, dict):
        yield value
        for child in value.values():
            yield from walk_json(child)
    elif isinstance(value, list):
        for child in value:
            yield from walk_json(child)


def type_is_event(value: Any) -> bool:
    values = value if isinstance(value, list) else [value]
    return any(str(item).lower().endswith("event") for item in values if item)


def extract_event_node(soup: BeautifulSoup, expected_url: str) -> dict[str, Any] | None:
    candidates: list[dict[str, Any]] = []
    for script in soup.find_all("script", attrs={"type": "application/ld+json"}):
        raw = script.string or script.get_text()
        try:
            payload = json.loads(raw)
        except Exception:  # noqa: BLE001
            continue
        for node in walk_json(payload):
            if type_is_event(node.get("@type")):
                candidates.append(node)
    if not candidates:
        return None
    expected = normalize_url(expected_url)
    for node in candidates:
        node_url = node.get("url")
        if isinstance(node_url, str) and normalize_url(node_url) == expected:
            return node
    return candidates[0]


def clean_text(value: Any) -> str:
    if value is None:
        return ""
    text = BeautifulSoup(str(value), "html.parser").get_text(" ", strip=True)
    return re.sub(r"\s+", " ", html_lib.unescape(text)).strip()


def iso_date(value: Any) -> str:
    match = re.match(r"^(\d{4}-\d{2}-\d{2})", str(value or ""))
    return match.group(1) if match else ""


def iso_time(value: Any) -> str:
    match = re.match(r"^\d{4}-\d{2}-\d{2}T(\d{2}):(\d{2})", str(value or ""))
    return f"{match.group(1)}:{match.group(2)}" if match else ""


def human_date(start: str, end: str, start_time: str = "", end_time: str = "") -> str:
    first = date.fromisoformat(start)
    last = date.fromisoformat(end or start)
    if first == last:
        label = f"{first.day} {MONTHS[first.month - 1]} {first.year}"
        if start_time:
            hour, minute = start_time.split(":")
            label += f" · {int(hour)} h" + (f" {minute}" if minute != "00" else "")
            if end_time and end_time != start_time:
                ehour, eminute = end_time.split(":")
                label += f"–{int(ehour)} h" + (f" {eminute}" if eminute != "00" else "")
        return label
    if first.year == last.year and first.month == last.month:
        return f"{first.day}–{last.day} {MONTHS[first.month - 1]} {first.year}"
    if first.year == last.year:
        return f"{first.day} {MONTHS[first.month - 1]}–{last.day} {MONTHS[last.month - 1]} {first.year}"
    return f"{first.day} {MONTHS[first.month - 1]} {first.year}–{last.day} {MONTHS[last.month - 1]} {last.year}"


def location_payload(value: Any) -> tuple[str, dict[str, str]]:
    if isinstance(value, list):
        value = next((item for item in value if isinstance(item, dict)), {})
    if not isinstance(value, dict):
        value = {}
    name = clean_text(value.get("name"))
    address = value.get("address")
    if isinstance(address, str):
        fields = {"street": clean_text(address), "postal_code": "", "city": "", "country": "FR"}
    elif isinstance(address, dict):
        fields = {
            "street": clean_text(address.get("streetAddress")),
            "postal_code": clean_text(address.get("postalCode")),
            "city": clean_text(address.get("addressLocality")),
            "country": clean_text(address.get("addressCountry")) or "FR",
        }
    else:
        fields = {"street": "", "postal_code": "", "city": "", "country": "FR"}

    parts: list[str] = []
    if name.lower() not in GENERIC_LOCATION_NAMES:
        parts.append(name)
    locality = " ".join(part for part in (fields["postal_code"], fields["city"]) if part)
    if fields["street"] and fields["street"].lower() not in {part.lower() for part in parts}:
        parts.append(fields["street"])
    if locality:
        parts.append(locality)
    display = " · ".join(dict.fromkeys(parts)) or "Dieppe et ses environs"
    return display, fields


def categories_for(title: str, source_description: str) -> list[str]:
    haystack = f"{title} {source_description}".lower()
    categories = [name for name, words in CATEGORY_RULES.items() if any(word in haystack for word in words)]
    return categories or ["culture"]


def parse_detail(url: str) -> dict[str, Any]:
    page_html, final_url = fetch_html(url)
    soup = BeautifulSoup(page_html, "html.parser")
    node = extract_event_node(soup, final_url)
    if node is None:
        raise ValueError("Aucune donnée structurée Event")

    title = clean_text(node.get("name")) or clean_text(soup.find("h1"))
    start_raw = node.get("startDate")
    end_raw = node.get("endDate") or start_raw
    start = iso_date(start_raw)
    end = iso_date(end_raw)
    status = clean_text(node.get("eventStatus"))
    if not title or not start or not end:
        raise ValueError("Titre ou dates absents")
    if status.lower().endswith("eventcancelled"):
        raise ValueError("Événement annulé")

    source_description = clean_text(node.get("description"))
    if not source_description:
        meta = soup.find("meta", attrs={"name": "description"})
        source_description = clean_text(meta.get("content", "") if meta else "")
    place, address = location_payload(node.get("location"))
    categories = categories_for(title, source_description)
    canonical = normalize_url(str(node.get("url") or final_url))
    fetched_at = datetime.now(timezone.utc).isoformat()

    return {
        "id": canonical.rstrip("/").rsplit("-fr-", 1)[-1],
        "title": title,
        "start": start,
        "end": end,
        "start_time": iso_time(start_raw),
        "end_time": iso_time(end_raw),
        "date_label": human_date(start, end, iso_time(start_raw), iso_time(end_raw)),
        "place": place,
        "address": address,
        "description": GENERIC_SUMMARY,
        "url": canonical,
        "categories": categories,
        "free": "gratuit" in categories,
        "source": SOURCE_NAME,
        "fetched_at": fetched_at,
    }


def validate_payload(payload: Any) -> dict[str, Any] | None:
    if not isinstance(payload, dict):
        return None
    events = payload.get("events")
    if not isinstance(events, list) or len(events) < 5:
        return None
    if not all(isinstance(item, dict) and item.get("url") and item.get("start") and item.get("end") for item in events):
        return None
    return payload


def load_json_file(path: Path) -> dict[str, Any] | None:
    try:
        return validate_payload(json.loads(path.read_text(encoding="utf-8")))
    except Exception:  # noqa: BLE001
        return None


def load_public_cache(url: str) -> dict[str, Any] | None:
    try:
        data, _ = fetch_bytes(url, attempts=1)
        payload = validate_payload(json.loads(data.decode("utf-8")))
        if payload:
            print(f"Agenda officiel : cache public chargé ({payload.get('event_count', len(payload['events']))} événements).")
        return payload
    except Exception as exc:  # noqa: BLE001
        print(f"Agenda officiel : aucun cache public utilisable ({type(exc).__name__}).")
        return None


def age_seconds(raw: Any) -> float:
    if not isinstance(raw, str):
        return float("inf")
    try:
        moment = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        return float("inf")
    return max(0.0, (datetime.now(timezone.utc) - moment.astimezone(timezone.utc)).total_seconds())


def write_atomic(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, delete=False) as handle:
        handle.write(text)
        temp_path = Path(handle.name)
    temp_path.replace(path)


def build_payload(
    previous: dict[str, Any] | None,
    max_pages: int,
    max_events: int,
    workers: int,
    detail_max_age: int,
    max_refresh: int,
) -> dict[str, Any]:
    urls, pages = discover_event_urls(max_pages=max_pages, max_events=max_events)
    if len(urls) < 5:
        raise RuntimeError(f"Seulement {len(urls)} liens événements découverts")

    previous_by_url = {
        normalize_url(str(event["url"])): event
        for event in (previous or {}).get("events", [])
        if isinstance(event, dict) and event.get("url")
    }
    now_iso = datetime.now(timezone.utc).isoformat()
    new_urls = [url for url in urls if url not in previous_by_url]
    stale_urls = [
        url
        for url in urls
        if url in previous_by_url and age_seconds(previous_by_url[url].get("fetched_at")) > detail_max_age
    ]
    refresh_urls = new_urls + stale_urls[:max_refresh]
    refresh_set = set(refresh_urls)
    print(
        "Agenda officiel : "
        f"{len(new_urls)} nouvelle(s) fiche(s), {len(stale_urls)} fiche(s) ancienne(s), "
        f"{len(refresh_urls)} fiche(s) à télécharger."
    )

    fetched: dict[str, dict[str, Any]] = {}
    failures: list[str] = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=max(1, workers)) as executor:
        future_map = {executor.submit(parse_detail, url): url for url in refresh_urls}
        for future in concurrent.futures.as_completed(future_map):
            url = future_map[future]
            try:
                fetched[url] = future.result()
            except Exception as exc:  # noqa: BLE001
                failures.append(f"{url}: {type(exc).__name__}")

    merged: list[dict[str, Any]] = []
    for url in urls:
        event = fetched.get(url) or previous_by_url.get(url)
        if event:
            normalized = dict(event)
            normalized["url"] = url
            normalized.setdefault("description", GENERIC_SUMMARY)
            normalized.setdefault("fetched_at", now_iso if url in refresh_set else (previous or {}).get("generated_at", now_iso))
            merged.append(normalized)

    today = datetime.now(ZoneInfo("Europe/Paris")).date().isoformat()
    upcoming = [event for event in merged if str(event.get("end", "")) >= today]
    deduped: dict[str, dict[str, Any]] = {str(event["url"]): event for event in upcoming}
    events = list(deduped.values())
    events.sort(
        key=lambda event: (
            0 if str(event["start"]) <= today <= str(event["end"]) else 1,
            str(event["start"]),
            str(event["title"]).casefold(),
        )
    )
    events = events[:max_events]

    if len(events) < 5:
        raise RuntimeError(f"Import insuffisant : {len(events)} événements à venir")

    return {
        "schema_version": 3,
        "source": SOURCE_NAME,
        "source_url": LIST_URL,
        "generated_at": now_iso,
        "refresh_interval_minutes": 15,
        "detail_refresh_hours": round(detail_max_age / 3600, 2),
        "listing_pages_scanned": pages,
        "links_discovered": len(urls),
        "new_links": len(new_urls),
        "details_refreshed": len(fetched),
        "detail_failures": failures[:30],
        "event_count": len(events),
        "events": events,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Importe les événements officiels de Dieppe-Normandie Tourisme")
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--bootstrap-url", default=PUBLIC_CACHE_URL)
    parser.add_argument("--max-pages", type=int, default=10)
    parser.add_argument("--max-events", type=int, default=96)
    parser.add_argument("--workers", type=int, default=6)
    parser.add_argument("--detail-max-age", type=int, default=43200)
    parser.add_argument("--max-refresh", type=int, default=18)
    args = parser.parse_args()

    previous = load_json_file(args.output) if args.output.exists() else None
    if previous is None and args.bootstrap_url:
        previous = load_public_cache(args.bootstrap_url)

    try:
        payload = build_payload(
            previous=previous,
            max_pages=args.max_pages,
            max_events=args.max_events,
            workers=args.workers,
            detail_max_age=args.detail_max_age,
            max_refresh=args.max_refresh,
        )
        write_atomic(args.output, payload)
        print(
            "Agenda officiel importé : "
            f"{payload['event_count']} événements, {payload['listing_pages_scanned']} pages, "
            f"{payload['new_links']} nouveau(x), {payload['details_refreshed']} fiche(s) actualisée(s), "
            f"{len(payload['detail_failures'])} échec(s)."
        )
        return 0
    except Exception as exc:  # noqa: BLE001
        if previous:
            fallback = dict(previous)
            fallback["last_check_failed_at"] = datetime.now(timezone.utc).isoformat()
            fallback["last_check_error"] = type(exc).__name__
            write_atomic(args.output, fallback)
            print(
                f"AVERTISSEMENT : import live en échec ({type(exc).__name__}: {exc}). "
                f"Conservation du dernier cache valide de {previous.get('generated_at')}.",
                file=sys.stderr,
            )
            return 0
        print(f"ERREUR : aucun agenda importé et aucun cache valide ({type(exc).__name__}: {exc}).", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

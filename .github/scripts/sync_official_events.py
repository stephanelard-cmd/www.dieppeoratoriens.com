#!/usr/bin/env python3
from __future__ import annotations

import argparse
import concurrent.futures
import html as html_lib
import json
import os
import re
import sys
import tempfile
import time
import urllib.parse
import urllib.request
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Iterable

from bs4 import BeautifulSoup

LIST_URL = "https://www.dieppetourisme.com/agenda/tout-lagenda/"
SOURCE_NAME = "Dieppe-Normandie Tourisme"
EVENT_URL_RE = re.compile(
    r"https?://(?:www\.)?dieppetourisme\.com/agenda/[^\"'<>\s?#]+-fr-\d+/?",
    re.I,
)
HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; OratoriensAgenda/2.0; +https://dieppeoratoriens.com/)",
    "Accept": "text/html,application/xhtml+xml",
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


def fetch_html(url: str, attempts: int = 3) -> tuple[str, str]:
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
                return data.decode("utf-8", "replace"), response.geturl()
        except Exception as exc:  # noqa: BLE001
            last_error = exc
            if attempt < attempts:
                time.sleep(attempt * 0.7)
    assert last_error is not None
    raise last_error


def normalize_url(url: str, base: str = LIST_URL) -> str:
    absolute = urllib.parse.urljoin(base, html_lib.unescape(url))
    parsed = urllib.parse.urlsplit(absolute)
    clean = urllib.parse.urlunsplit((parsed.scheme, parsed.netloc.lower(), parsed.path, "", ""))
    return clean if clean.endswith("/") else clean + "/"


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
        current = normalize_url(next_tag["href"], final_url) if next_tag else ""

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


def short_description(text: str, limit: int = 300) -> str:
    text = clean_text(text)
    if len(text) <= limit:
        return text
    cut = text[: limit + 1]
    boundary = max(cut.rfind(". "), cut.rfind("! "), cut.rfind("? "), cut.rfind("; "))
    if boundary >= int(limit * 0.55):
        return cut[: boundary + 1].strip()
    boundary = cut.rfind(" ")
    return cut[:boundary].rstrip(" ,;:-") + "…"


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


def first_image(value: Any) -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, list):
        return next((item for item in value if isinstance(item, str)), "")
    if isinstance(value, dict):
        for key in ("url", "contentUrl"):
            if isinstance(value.get(key), str):
                return value[key]
    return ""


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


def categories_for(title: str, description: str, page_text: str) -> list[str]:
    haystack = f"{title} {description} {page_text[:20000]}".lower()
    categories = [name for name, words in CATEGORY_RULES.items() if any(word in haystack for word in words)]
    return categories or ["culture"]


def parse_detail(url: str) -> dict[str, Any] | None:
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
    if not title or not start or not end:
        raise ValueError("Titre ou dates absents")

    description = short_description(clean_text(node.get("description")))
    if not description:
        meta = soup.find("meta", attrs={"name": "description"})
        description = short_description(meta.get("content", "") if meta else "")
    place, address = location_payload(node.get("location"))
    page_text = soup.get_text(" ", strip=True)
    categories = categories_for(title, description, page_text)
    canonical = normalize_url(str(node.get("url") or final_url))

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
        "description": description,
        "url": canonical,
        "image": first_image(node.get("image")),
        "categories": categories,
        "free": "gratuit" in categories,
        "source": SOURCE_NAME,
    }


def validate_cache(path: Path) -> dict[str, Any] | None:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return None
    events = payload.get("events")
    if not isinstance(events, list) or len(events) < 5:
        return None
    if not all(isinstance(item, dict) and item.get("url") and item.get("start") and item.get("end") for item in events):
        return None
    return payload


def cache_age_seconds(payload: dict[str, Any]) -> float:
    raw = payload.get("generated_at")
    if not isinstance(raw, str):
        return float("inf")
    try:
        generated = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        return float("inf")
    return max(0.0, (datetime.now(timezone.utc) - generated.astimezone(timezone.utc)).total_seconds())


def write_atomic(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, delete=False) as handle:
        handle.write(text)
        temp_path = Path(handle.name)
    temp_path.replace(path)


def build_payload(max_pages: int, max_events: int, workers: int) -> dict[str, Any]:
    urls, pages = discover_event_urls(max_pages=max_pages, max_events=max_events)
    if len(urls) < 5:
        raise RuntimeError(f"Seulement {len(urls)} liens événements découverts")

    parsed: list[dict[str, Any]] = []
    failures: list[str] = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=max(1, workers)) as executor:
        future_map = {executor.submit(parse_detail, url): url for url in urls}
        for future in concurrent.futures.as_completed(future_map):
            url = future_map[future]
            try:
                event = future.result()
                if event:
                    parsed.append(event)
            except Exception as exc:  # noqa: BLE001
                failures.append(f"{url}: {type(exc).__name__}")

    today = date.today().isoformat()
    upcoming = [event for event in parsed if event["end"] >= today]
    deduped: dict[str, dict[str, Any]] = {event["url"]: event for event in upcoming}
    events = list(deduped.values())
    events.sort(key=lambda event: (0 if event["start"] <= today <= event["end"] else 1, event["start"], event["title"].casefold()))
    events = events[:max_events]

    if len(events) < 5:
        raise RuntimeError(f"Import insuffisant : {len(events)} événements à venir")

    now = datetime.now(timezone.utc).isoformat()
    return {
        "schema_version": 2,
        "source": SOURCE_NAME,
        "source_url": LIST_URL,
        "generated_at": now,
        "refresh_interval_hours": 6,
        "listing_pages_scanned": pages,
        "links_discovered": len(urls),
        "detail_failures": failures[:20],
        "event_count": len(events),
        "events": events,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Importe les événements officiels de Dieppe-Normandie Tourisme")
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--max-age", type=int, default=21600)
    parser.add_argument("--max-pages", type=int, default=8)
    parser.add_argument("--max-events", type=int, default=72)
    parser.add_argument("--workers", type=int, default=4)
    args = parser.parse_args()

    existing = validate_cache(args.output) if args.output.exists() else None
    if existing and args.max_age > 0 and cache_age_seconds(existing) <= args.max_age:
        print(f"Agenda officiel : cache frais utilisé ({existing['event_count']} événements).")
        return 0

    try:
        payload = build_payload(args.max_pages, args.max_events, args.workers)
        write_atomic(args.output, payload)
        print(
            "Agenda officiel importé : "
            f"{payload['event_count']} événements, {payload['listing_pages_scanned']} pages, "
            f"{len(payload['detail_failures'])} fiche(s) en échec."
        )
        return 0
    except Exception as exc:  # noqa: BLE001
        if existing:
            print(
                f"AVERTISSEMENT : import live en échec ({type(exc).__name__}: {exc}). "
                f"Conservation du dernier cache valide de {existing.get('generated_at')}.",
                file=sys.stderr,
            )
            return 0
        print(f"ERREUR : aucun agenda importé et aucun cache valide ({type(exc).__name__}: {exc}).", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

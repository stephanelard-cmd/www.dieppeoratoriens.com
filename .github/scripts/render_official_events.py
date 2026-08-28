#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from bs4 import BeautifulSoup

BASE = "https://dieppeoratoriens.com"
SOURCE_URL = "https://www.dieppetourisme.com/agenda/tout-lagenda/"


def parse_generated_at(raw: str) -> datetime:
    return datetime.fromisoformat(raw.replace("Z", "+00:00")).astimezone(ZoneInfo("Europe/Paris"))


def add_text_tag(soup: BeautifulSoup, parent, name: str, text: str, **attrs):
    tag = soup.new_tag(name, **attrs)
    tag.string = text
    parent.append(tag)
    return tag


def build_card(soup: BeautifulSoup, event: dict) -> object:
    article = soup.new_tag("article")
    article["class"] = ["card", "event-card"]
    article["data-category"] = " ".join(event.get("categories") or ["culture"])
    article["data-event-end"] = event["end"]
    article["data-official-event"] = "true"
    article["data-event-id"] = str(event.get("id") or "")

    add_text_tag(soup, article, "p", event["date_label"], attrs={"class": "event-date"})
    add_text_tag(soup, article, "h3", event["title"])
    add_text_tag(soup, article, "p", event.get("place") or "Dieppe et ses environs", attrs={"class": "event-place"})
    add_text_tag(soup, article, "p", event.get("description") or "Consultez la fiche officielle pour les détails et les horaires.")

    link = soup.new_tag("a", href=event["url"])
    link["class"] = ["event-link"]
    link["rel"] = ["external", "noopener"]
    link["target"] = "_blank"
    link.string = "Consulter la fiche officielle"
    article.append(link)
    return article


def event_schema(event: dict) -> dict:
    address = event.get("address") or {}
    location = {
        "@type": "Place",
        "name": event.get("place") or "Dieppe et ses environs",
        "address": {
            "@type": "PostalAddress",
            "streetAddress": address.get("street") or "",
            "postalCode": address.get("postal_code") or "",
            "addressLocality": address.get("city") or "Dieppe",
            "addressRegion": "Normandie",
            "addressCountry": address.get("country") or "FR",
        },
    }
    node = {
        "@type": "Event",
        "name": event["title"],
        "description": event.get("description") or "",
        "startDate": event["start"],
        "endDate": event["end"],
        "eventStatus": "https://schema.org/EventScheduled",
        "eventAttendanceMode": "https://schema.org/OfflineEventAttendanceMode",
        "location": location,
        "url": event["url"],
        "sameAs": event["url"],
        "organizer": {"@type": "Organization", "name": "Dieppe-Normandie Tourisme", "url": SOURCE_URL},
    }
    if event.get("image"):
        node["image"] = [event["image"]]
    if event.get("free"):
        node["isAccessibleForFree"] = True
    return node


def remove_dynamic_schema(soup: BeautifulSoup) -> None:
    for script in list(soup.find_all("script", attrs={"type": "application/ld+json"})):
        text = script.string or script.get_text()
        if '"Event"' in text or "'Event'" in text or "agenda-dieppe.html#webpage" in text:
            script.decompose()


def run_multilingual_generator(site_root: Path) -> None:
    generator = Path(__file__).with_name("generate_multilingual_site.py")
    if not generator.exists():
        raise SystemExit(f"Générateur multilingue introuvable : {generator}")
    subprocess.run([sys.executable, str(generator), str(site_root)], check=True)

    flag_enhancer = Path(__file__).with_name("add_visible_language_flags.py")
    if not flag_enhancer.exists():
        raise SystemExit(f"Générateur de drapeaux introuvable : {flag_enhancer}")
    subprocess.run([sys.executable, str(flag_enhancer), str(site_root)], check=True)


def main() -> int:
    parser = argparse.ArgumentParser(description="Injecte l’agenda officiel importé dans la page publique")
    parser.add_argument("--site-root", required=True, type=Path)
    parser.add_argument("--input", required=True, type=Path)
    args = parser.parse_args()

    payload = json.loads(args.input.read_text(encoding="utf-8"))
    events = payload.get("events")
    if not isinstance(events, list) or len(events) < 5:
        raise SystemExit("Le fichier d’agenda ne contient pas assez d’événements valides.")

    page_path = args.site_root / "agenda-dieppe.html"
    if not page_path.exists():
        raise SystemExit(f"Page agenda introuvable : {page_path}")
    soup = BeautifulSoup(page_path.read_text(encoding="utf-8"), "html.parser")

    grid = soup.select_one(".event-grid")
    if grid is None:
        raise SystemExit("Grille des événements introuvable.")
    grid.clear()
    for event in events:
        grid.append(build_card(soup, event))

    section = soup.select_one("#manifestations")
    if section:
        section["data-agenda-source"] = "dieppe-normandie-tourisme"
        section["data-agenda-generated-at"] = payload["generated_at"]
        eyebrow = section.select_one(".eyebrow")
        if eyebrow:
            eyebrow.string = "Import automatique de l’agenda officiel"
        heading = section.find("h2")
        if heading:
            old = section.select_one(".agenda-source-status")
            if old:
                old.decompose()
            generated = parse_generated_at(payload["generated_at"])
            status = soup.new_tag("p")
            status["class"] = ["lead", "agenda-source-status"]
            source_link = soup.new_tag("a", href=payload.get("source_url") or SOURCE_URL)
            source_link["rel"] = ["external", "noopener"]
            source_link["target"] = "_blank"
            source_link.string = "Dieppe-Normandie Tourisme"
            status.append(f"{len(events)} manifestations importées automatiquement depuis ")
            status.append(source_link)
            status.append(
                f". Dernière synchronisation : {generated.strftime('%d/%m/%Y à %H h %M')}. "
                "Les horaires et éventuelles annulations restent à vérifier sur chaque fiche officielle."
            )
            heading.insert_after(status)

    hero_lead = soup.select_one(".page-hero .lead")
    if hero_lead:
        hero_lead.string = (
            "Les manifestations publiées par l’Office de Tourisme Dieppe-Normandie sont importées automatiquement. "
            "Les événements terminés sont masqués et les nouvelles publications apparaissent lors de la prochaine synchronisation."
        )

    remove_dynamic_schema(soup)
    graph = [
        {
            "@type": "WebPage",
            "@id": BASE + "/agenda-dieppe.html#webpage",
            "url": BASE + "/agenda-dieppe.html",
            "name": "Agenda des manifestations à Dieppe et ses environs",
            "description": "Manifestations importées automatiquement depuis l’agenda officiel de Dieppe-Normandie Tourisme.",
            "inLanguage": "fr-FR",
            "dateModified": payload["generated_at"],
            "isBasedOn": payload.get("source_url") or SOURCE_URL,
        },
        *[event_schema(event) for event in events],
    ]
    structured = soup.new_tag("script")
    structured["type"] = "application/ld+json"
    structured.string = json.dumps({"@context": "https://schema.org", "@graph": graph}, ensure_ascii=False, separators=(",", ":"))
    soup.head.append(structured)

    for tag in list(soup.find_all("meta", attrs={"name": "dieppe-events-generated-at"})):
        tag.decompose()
    marker = soup.new_tag("meta")
    marker["name"] = "dieppe-events-generated-at"
    marker["content"] = payload["generated_at"]
    soup.head.append(marker)

    page_path.write_text(str(soup), encoding="utf-8")

    public_json = args.site_root / "assets" / "data" / "dieppe-events.json"
    public_json.parent.mkdir(parents=True, exist_ok=True)
    public_json.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    run_multilingual_generator(args.site_root)
    print(f"Agenda public rendu avec {len(events)} événements officiels importés.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

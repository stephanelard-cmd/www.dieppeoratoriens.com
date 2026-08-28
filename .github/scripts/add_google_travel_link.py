#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from pathlib import Path

from bs4 import BeautifulSoup

GOOGLE_TRAVEL_URL = "https://www.google.com/travel/hotels/entity/CiUImtD374PqipuLARCo_-edhOnv5PwBGg0vZy8xMWtqNW1kOXNiEAI"
CSS_MARKER = "/* google-travel-link-v1 */"
CSS = r'''
/* google-travel-link-v1 */
.google-travel-callout{display:flex;align-items:center;justify-content:space-between;gap:1.4rem;margin:1.25rem 0 0;padding:1.45rem 1.55rem;border:1px solid var(--line);border-radius:var(--radius);background:linear-gradient(135deg,#fff 0%,#eef6f7 100%);box-shadow:0 8px 30px rgba(24,52,62,.06)}
.google-travel-callout h2{font-family:Georgia,serif;font-size:clamp(1.45rem,2.5vw,2rem);line-height:1.1;margin:.2rem 0 .45rem}
.google-travel-callout p{max-width:760px;margin:0;color:var(--muted)}
.google-travel-callout .btn{flex:0 0 auto;text-align:center}
@media(max-width:760px){.google-travel-callout{align-items:flex-start;flex-direction:column}.google-travel-callout .btn{width:100%}}
'''


def append_css(soup: BeautifulSoup) -> None:
    style = soup.find("style")
    if style is None:
        style = soup.new_tag("style")
        if soup.head:
            soup.head.append(style)
        else:
            soup.insert(0, style)
    existing = style.string or style.get_text()
    if CSS_MARKER not in existing:
        style.string = existing.rstrip() + "\n" + CSS.strip() + "\n"


def add_same_as(soup: BeautifulSoup) -> None:
    for script in soup.find_all("script", attrs={"type": "application/ld+json"}):
        raw = script.string or script.get_text()
        try:
            payload = json.loads(raw)
        except Exception:
            continue
        nodes = payload.get("@graph") if isinstance(payload, dict) else None
        if not isinstance(nodes, list):
            nodes = [payload] if isinstance(payload, dict) else []
        changed = False
        for node in nodes:
            if not isinstance(node, dict):
                continue
            node_type = node.get("@type")
            types = node_type if isinstance(node_type, list) else [node_type]
            if "LodgingBusiness" not in types:
                continue
            same_as = node.get("sameAs")
            if isinstance(same_as, str):
                same_as = [same_as]
            elif not isinstance(same_as, list):
                same_as = []
            if GOOGLE_TRAVEL_URL not in same_as:
                same_as.append(GOOGLE_TRAVEL_URL)
                node["sameAs"] = same_as
                changed = True
        if changed:
            script.string = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))


def build_callout(soup: BeautifulSoup):
    callout = soup.new_tag(
        "aside",
        id="google-travel",
        attrs={"class": "google-travel-callout", "aria-label": "Fiche Google Travel de l’hébergement"},
    )
    content = soup.new_tag("div")
    eyebrow = soup.new_tag("div", attrs={"class": "eyebrow"})
    eyebrow.string = "Google Travel"
    title = soup.new_tag("h2")
    title.string = "Retrouvez l’hébergement sur Google"
    paragraph = soup.new_tag("p")
    paragraph.string = (
        "Consultez la fiche Google Travel, les photos et la note agrégée à partir de sites de voyage partenaires. "
        "Ces évaluations ne sont pas des avis Google natifs et ne sont pas vérifiées par Google."
    )
    content.extend([eyebrow, title, paragraph])

    link = soup.new_tag(
        "a",
        href=GOOGLE_TRAVEL_URL,
        target="_blank",
        rel="external nofollow noopener",
        attrs={"class": "btn btn-primary", "aria-label": "Voir Oratoriens Henri IV sur Google Travel"},
    )
    link.string = "Voir l’hébergement sur Google"
    callout.extend([content, link])
    return callout


def main() -> int:
    root = Path(sys.argv[1] if len(sys.argv) > 1 else "_site").resolve()
    page = root / "avis-localisation.html"
    if not page.exists():
        raise SystemExit(f"Page introuvable : {page}")

    soup = BeautifulSoup(page.read_text(encoding="utf-8"), "html.parser")
    platforms = soup.select_one("main .platforms")
    if platforms is None:
        raise SystemExit("Le bloc des plateformes est introuvable.")

    old = soup.find(id="google-travel")
    if old is not None:
        old.decompose()
    platforms.insert_after(build_callout(soup))

    notice = platforms.find_next("p", class_="notice")
    if notice is not None:
        notice.string = (
            "Les notes Booking.com et Airbnb proviennent de leurs plateformes respectives. "
            "Google Travel agrège des évaluations issues de sites de voyage partenaires : elles ne constituent pas des avis Google natifs."
        )

    append_css(soup)
    add_same_as(soup)
    page.write_text(str(soup), encoding="utf-8")

    rendered = page.read_text(encoding="utf-8")
    checks = [
        'id="google-travel"',
        "Voir l’hébergement sur Google",
        GOOGLE_TRAVEL_URL,
        CSS_MARKER,
    ]
    missing = [value for value in checks if value not in rendered]
    if missing:
        raise SystemExit(f"Contrôle Google Travel incomplet : {missing}")

    print("Lien Google Travel ajouté à la page Avis & plan.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

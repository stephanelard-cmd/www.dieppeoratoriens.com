#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from pathlib import Path

from bs4 import BeautifulSoup

DESCRIPTION = (
    "Photos du studio-mezzanine Oratoriens Henri IV à Dieppe : "
    "vue sur le port, façade historique, séjour, mezzanine et cuisine équipée."
)

LABELS = {
    "photo-1.webp": {
        "caption": "Vue sur le port",
        "alt": "Vue sur le port de Dieppe depuis l’appartement Oratoriens Henri IV",
    },
    "photo-2.webp": {
        "caption": "Façade des Oratoriens",
        "alt": "Façade historique de l’immeuble des Oratoriens, quai Henri IV à Dieppe",
    },
    "photo-3.webp": {
        "caption": "Séjour",
        "alt": "Séjour lumineux avec canapé et table à manger face au port de Dieppe",
    },
    "photo-4.webp": {
        "caption": "Vue depuis la mezzanine",
        "alt": "Vue du séjour depuis la mezzanine de l’appartement Oratoriens Henri IV",
    },
    "photo-5.webp": {
        "caption": "Cuisine équipée",
        "alt": "Cuisine équipée ouverte sur le séjour et l’espace repas",
    },
}


def update_jsonld(soup: BeautifulSoup) -> None:
    for script in soup.find_all("script", attrs={"type": "application/ld+json"}):
        raw = script.string or script.get_text()
        try:
            payload = json.loads(raw)
        except Exception:
            continue

        changed = False
        nodes = payload.get("@graph") if isinstance(payload, dict) else None
        if isinstance(nodes, list):
            for node in nodes:
                if not isinstance(node, dict):
                    continue
                node_type = node.get("@type")
                node_url = str(node.get("url", ""))
                if node_type == "WebPage" and node_url.endswith("/galerie.html"):
                    node["description"] = DESCRIPTION
                    changed = True
        if changed:
            script.string = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))


def main() -> int:
    if len(sys.argv) != 2:
        raise SystemExit("Usage: fix_gallery_labels.py <site-root>")

    root = Path(sys.argv[1]).resolve()
    page = root / "galerie.html"
    if not page.exists():
        raise SystemExit(f"Galerie introuvable : {page}")

    soup = BeautifulSoup(page.read_text(encoding="utf-8"), "html.parser")
    figures = soup.select(".gallery figure")
    if len(figures) != 5:
        raise SystemExit(f"Nombre inattendu de photos dans la galerie : {len(figures)}")

    seen: list[str] = []
    for figure in figures:
        image = figure.find("img", attrs={"data-gallery": True})
        caption = figure.find("figcaption")
        if image is None or caption is None:
            raise SystemExit("Structure de galerie incomplète")

        filename = Path(str(image.get("src", ""))).name
        data = LABELS.get(filename)
        if data is None:
            raise SystemExit(f"Photo inconnue dans la galerie : {filename}")
        image["alt"] = data["alt"]
        caption.string = data["caption"]
        seen.append(filename)

    expected_order = list(LABELS)
    if seen != expected_order:
        raise SystemExit(f"Ordre des photos inattendu : {seen} au lieu de {expected_order}")

    for tag in soup.find_all("meta"):
        if tag.get("name") in {"description", "twitter:description"} or tag.get("property") == "og:description":
            tag["content"] = DESCRIPTION

    update_jsonld(soup)
    page.write_text(str(soup), encoding="utf-8")

    check = BeautifulSoup(page.read_text(encoding="utf-8"), "html.parser")
    captions = [node.get_text(" ", strip=True) for node in check.select(".gallery figcaption")]
    expected_captions = [LABELS[name]["caption"] for name in expected_order]
    if captions != expected_captions:
        raise SystemExit(f"Légendes finales invalides : {captions}")
    if "Salle d’eau" in page.read_text(encoding="utf-8"):
        raise SystemExit("L’ancienne légende erronée « Salle d’eau » subsiste dans la galerie")

    print("Galerie corrigée : " + " | ".join(captions))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path

from bs4 import BeautifulSoup

MARKER = "/* visible-language-flags-v2 */"

FLAGS = {
    "fr": {
        "label": "Français",
        "file": "fr.svg",
        "svg": """<svg xmlns=\"http://www.w3.org/2000/svg\" viewBox=\"0 0 60 40\" role=\"img\" aria-label=\"Drapeau français\"><rect width=\"20\" height=\"40\" x=\"0\" fill=\"#0055A4\"/><rect width=\"20\" height=\"40\" x=\"20\" fill=\"#FFFFFF\"/><rect width=\"20\" height=\"40\" x=\"40\" fill=\"#EF4135\"/></svg>""",
    },
    "en": {
        "label": "English",
        "file": "gb.svg",
        "svg": """<svg xmlns=\"http://www.w3.org/2000/svg\" viewBox=\"0 0 60 36\" role=\"img\" aria-label=\"United Kingdom flag\"><rect width=\"60\" height=\"36\" fill=\"#012169\"/><path d=\"M0 0L60 36M60 0L0 36\" stroke=\"#FFFFFF\" stroke-width=\"8\"/><path d=\"M0 0L60 36M60 0L0 36\" stroke=\"#C8102E\" stroke-width=\"4\"/><path d=\"M30 0V36M0 18H60\" stroke=\"#FFFFFF\" stroke-width=\"12\"/><path d=\"M30 0V36M0 18H60\" stroke=\"#C8102E\" stroke-width=\"7\"/></svg>""",
    },
    "de": {
        "label": "Deutsch",
        "file": "de.svg",
        "svg": """<svg xmlns=\"http://www.w3.org/2000/svg\" viewBox=\"0 0 60 36\" role=\"img\" aria-label=\"Deutsche Flagge\"><rect width=\"60\" height=\"12\" y=\"0\" fill=\"#000000\"/><rect width=\"60\" height=\"12\" y=\"12\" fill=\"#DD0000\"/><rect width=\"60\" height=\"12\" y=\"24\" fill=\"#FFCE00\"/></svg>""",
    },
    "es": {
        "label": "Español",
        "file": "es.svg",
        "svg": """<svg xmlns=\"http://www.w3.org/2000/svg\" viewBox=\"0 0 60 40\" role=\"img\" aria-label=\"Bandera española\"><rect width=\"60\" height=\"40\" fill=\"#AA151B\"/><rect width=\"60\" height=\"20\" y=\"10\" fill=\"#F1BF00\"/></svg>""",
    },
}

CSS = r"""
/* visible-language-flags-v2 */
.site-header .brand{order:1}
.site-header .menu{order:2;margin-left:auto}
.site-header .language-switcher{order:3}
.site-header .menu-toggle{order:4}
.language-switcher.language-switcher-v2{display:flex;align-items:center;justify-content:center;gap:.32rem;flex:0 0 auto;margin-left:.55rem;padding:.28rem .36rem;border:1px solid rgba(24,52,62,.15);border-radius:12px;background:rgba(255,255,255,.92);box-shadow:0 5px 18px rgba(24,52,62,.07)}
.language-switcher.language-switcher-v2 a{position:relative;display:inline-flex;align-items:center;justify-content:center;width:40px;height:32px;padding:4px 5px;border:1px solid rgba(24,52,62,.18);border-radius:8px;background:#fff;text-decoration:none;font-size:0;line-height:1;box-shadow:none;transition:transform .18s ease,border-color .18s ease,background .18s ease,box-shadow .18s ease}
.language-switcher.language-switcher-v2 a:hover,.language-switcher.language-switcher-v2 a:focus-visible{transform:translateY(-1px);border-color:var(--sea);background:#eef6f7;box-shadow:0 4px 12px rgba(11,97,120,.16)}
.language-switcher.language-switcher-v2 a[aria-current="page"]{border:2px solid var(--sea);background:#dfeff2;box-shadow:0 0 0 1px rgba(11,97,120,.12)}
.language-switcher.language-switcher-v2 .flag-image{display:block;width:28px;height:19px;object-fit:cover;border-radius:2px;box-shadow:0 0 0 1px rgba(0,0,0,.16)}
.language-switcher.language-switcher-v2 .language-code{position:absolute;width:1px;height:1px;padding:0;margin:-1px;overflow:hidden;clip:rect(0,0,0,0);white-space:nowrap;border:0}
@media(min-width:1121px){.site-header .menu{gap:clamp(.62rem,.9vw,1.05rem)}.site-header .menu a{font-size:.9rem}}
@media(max-width:1120px){.language-switcher.language-switcher-v2{margin-left:auto}.site-header .menu-toggle{margin-left:.15rem}}
@media(max-width:520px){.language-switcher.language-switcher-v2{gap:.2rem;padding:.22rem .26rem}.language-switcher.language-switcher-v2 a{width:35px;height:29px;padding:3px 4px}.language-switcher.language-switcher-v2 .flag-image{width:25px;height:17px}.site-header .brand{font-size:.96rem}}
"""


def write_flag_assets(site_root: Path) -> None:
    output = site_root / "assets" / "flags"
    output.mkdir(parents=True, exist_ok=True)
    for data in FLAGS.values():
        (output / data["file"]).write_text(data["svg"] + "\n", encoding="utf-8")


def inject_css(soup: BeautifulSoup) -> None:
    styles = soup.find_all("style")
    style = styles[-1] if styles else None
    if style is None:
        style = soup.new_tag("style")
        if soup.head:
            soup.head.append(style)
        else:
            soup.insert(0, style)
    existing = style.string or style.get_text()
    if MARKER not in existing:
        style.string = existing.rstrip() + "\n" + CSS.strip() + "\n"


def replace_switcher(soup: BeautifulSoup) -> bool:
    switcher = soup.select_one("nav.language-switcher")
    if switcher is None:
        return False

    classes = list(switcher.get("class") or [])
    if "language-switcher-v2" not in classes:
        classes.append("language-switcher-v2")
    switcher["class"] = classes

    found: set[str] = set()
    for link in switcher.find_all("a", recursive=False):
        lang = (link.get("lang") or "").lower()
        data = FLAGS.get(lang)
        if data is None:
            continue
        found.add(lang)
        link.clear()
        image = soup.new_tag(
            "img",
            src=f"/assets/flags/{data['file']}",
            alt="",
            width="28",
            height="19",
            decoding="async",
            attrs={"class": "flag-image", "aria-hidden": "true"},
        )
        text = soup.new_tag("span", attrs={"class": "language-code"})
        text.string = data["label"]
        link.extend([image, text])
        link["aria-label"] = data["label"]
        link["title"] = data["label"]

    missing = set(FLAGS) - found
    if missing:
        raise RuntimeError(f"Langues absentes du sélecteur : {sorted(missing)}")
    inject_css(soup)
    return True


def main() -> int:
    site_root = Path(sys.argv[1] if len(sys.argv) > 1 else "_site").resolve()
    if not site_root.exists():
        raise SystemExit(f"Racine du site introuvable : {site_root}")

    write_flag_assets(site_root)
    updated = 0
    for page in sorted(site_root.rglob("*.html")):
        soup = BeautifulSoup(page.read_text(encoding="utf-8"), "html.parser")
        if not replace_switcher(soup):
            continue
        page.write_text(str(soup), encoding="utf-8")
        updated += 1

    if updated < 40:
        raise SystemExit(f"Seulement {updated} pages contiennent le sélecteur de langues.")

    for code, data in FLAGS.items():
        asset = site_root / "assets" / "flags" / data["file"]
        if not asset.exists() or asset.stat().st_size < 100:
            raise SystemExit(f"Drapeau {code} invalide : {asset}")

    home = (site_root / "index.html").read_text(encoding="utf-8")
    required = [
        "language-switcher-v2",
        "/assets/flags/fr.svg",
        "/assets/flags/gb.svg",
        "/assets/flags/de.svg",
        "/assets/flags/es.svg",
    ]
    missing = [value for value in required if value not in home]
    if missing:
        raise SystemExit(f"Contrôle des drapeaux incomplet : {missing}")

    print(f"Drapeaux SVG visibles ajoutés sur {updated} pages : français, anglais, allemand et espagnol.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

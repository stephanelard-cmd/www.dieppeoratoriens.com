#!/usr/bin/env python3
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from bs4 import BeautifulSoup

MARKER = "/* layout-alignment-fixes-v3 */"

CSS = r'''
/* office-tourism-centering-v2 */
/* layout-alignment-fixes-v3 */
#office-tourisme > .wrap.two{align-items:stretch}
#office-tourisme .contact-list{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:.85rem;align-items:stretch}
#office-tourisme .contact-list p{display:flex;min-width:0;min-height:136px;margin:0;flex-direction:column;align-items:center;justify-content:center;text-align:center;padding:1rem .72rem;overflow:hidden}
#office-tourisme .contact-list strong{display:block;width:100%;margin:0 0 .5rem;letter-spacing:.02em;text-align:center}
#office-tourisme .contact-list br{display:none}
#office-tourisme .contact-list a{display:block;width:100%;max-width:100%;margin:0 auto;text-align:center;white-space:normal;overflow-wrap:anywhere;word-break:normal}
#office-tourisme .contact-list .office-email-card a{font-size:clamp(.82rem,1.08vw,.95rem);line-height:1.35}
#office-tourisme .actions{justify-content:center}
#office-tourisme .office-card{display:flex;height:100%;flex-direction:column;align-items:center;justify-content:center;text-align:center;padding:clamp(1.35rem,2.4vw,2rem)}
#office-tourisme .office-card .local-tag{align-self:center;margin-right:auto;margin-left:auto;text-align:center}
#office-tourisme .office-card h3{width:100%;text-align:center}
#office-tourisme .office-card ul{width:min(100%,34rem);margin:1rem auto;padding-left:1.4rem;text-align:left}
#office-tourisme .office-card li{margin:.62rem 0;padding-left:.15rem}
#office-tourisme .office-card .notice{width:100%;max-width:34rem;margin:1rem auto 0;text-align:center}
.calendar-shell{grid-template-columns:minmax(330px,360px) minmax(0,1fr);gap:1.5rem;align-items:start}
.calendar-shell>*{min-width:0}
.calendar-info{padding:clamp(1.55rem,2vw,1.9rem);overflow:hidden}
.calendar-info h2{max-width:100%;margin:0 0 1.2rem;font-size:clamp(2.15rem,3vw,2.72rem);line-height:1.02;overflow-wrap:normal;word-break:normal;hyphens:none}
.calendar{min-width:0;padding:1.25rem 1rem;overflow:hidden}
.cal-toolbar{display:grid;grid-template-columns:48px minmax(0,1fr) 48px;align-items:center;gap:clamp(.55rem,1.5vw,1rem);margin-bottom:1.2rem}
.cal-toolbar h2{min-width:0;margin:0;text-align:center;font-size:clamp(2.15rem,4vw,3.45rem);line-height:1.05}
.cal-toolbar .cal-nav-button{display:grid;width:42px;height:42px;min-width:42px;min-height:42px;margin:0;padding:0;place-items:center;justify-self:center;line-height:1}
.cal-toolbar .cal-chevron{display:block;font-family:Arial,sans-serif;font-size:1.75rem;font-weight:400;line-height:1;transform:translateY(-1px)}
@media(max-width:1050px){.calendar-shell{grid-template-columns:1fr}.calendar-info{position:static}.calendar-info h2{font-size:clamp(2.2rem,6vw,3rem)}}
@media(max-width:980px){#office-tourisme .office-card{margin-top:.5rem}#office-tourisme .contact-list p{min-height:112px}}
@media(max-width:720px){#office-tourisme .contact-list{grid-template-columns:1fr}#office-tourisme .contact-list p{min-height:0;padding:1rem}#office-tourisme .office-card ul{padding-left:1.2rem}.cal-toolbar{grid-template-columns:42px minmax(0,1fr) 42px}.cal-toolbar .cal-nav-button{width:38px;height:38px;min-width:38px;min-height:38px}.cal-toolbar h2{font-size:clamp(1.9rem,9vw,2.75rem)}}
'''


def run_companion_script(name: str, root: Path) -> None:
    script = Path(__file__).with_name(name)
    if not script.exists():
        raise SystemExit(f"Script complémentaire introuvable : {script}")
    subprocess.run([sys.executable, str(script), str(root)], check=True)


def append_css_to_style(soup: BeautifulSoup) -> None:
    style = soup.find("style")
    if style is None:
        style = soup.new_tag("style")
        if soup.head:
            soup.head.append(style)
        else:
            soup.insert(0, style)
    existing = style.string or style.get_text()
    if MARKER not in existing:
        style.string = existing.rstrip() + "\n" + CSS.strip() + "\n"


def apply_dom_fixes(soup: BeautifulSoup) -> None:
    email = soup.select_one('#office-tourisme a[href^="mailto:contact@dieppetourisme.com"]')
    if email is not None:
        card = email.find_parent("p")
        if card is not None:
            classes = list(card.get("class") or [])
            if "office-email-card" not in classes:
                classes.append("office-email-card")
            card["class"] = classes

    for selector, glyph in (("#prev", "‹"), ("#next", "›")):
        button = soup.select_one(selector)
        if button is None:
            continue
        classes = list(button.get("class") or [])
        if "cal-nav-button" not in classes:
            classes.append("cal-nav-button")
        button["class"] = classes
        button.clear()
        chevron = soup.new_tag("span", attrs={"class": "cal-chevron", "aria-hidden": "true"})
        chevron.string = glyph
        button.append(chevron)


def update_html_pages(root: Path) -> int:
    updated = 0
    for page in sorted(root.rglob("*.html")):
        soup = BeautifulSoup(page.read_text(encoding="utf-8"), "html.parser")
        has_office = soup.select_one("#office-tourisme") is not None
        has_calendar = soup.select_one(".calendar-shell") is not None
        if not has_office and not has_calendar:
            continue
        append_css_to_style(soup)
        apply_dom_fixes(soup)
        page.write_text(str(soup), encoding="utf-8")
        updated += 1
    return updated


def main() -> int:
    root = Path(sys.argv[1] if len(sys.argv) > 1 else "_site").resolve()
    office_page = root / "decouvrir-dieppe.html"
    calendar_page = root / "disponibilites.html"
    css_path = root / "assets/css/site.css"

    for page in (office_page, calendar_page):
        if not page.exists():
            raise SystemExit(f"Page introuvable : {page}")
    if not css_path.exists():
        raise SystemExit(f"Feuille de style introuvable : {css_path}")

    css = css_path.read_text(encoding="utf-8")
    if MARKER not in css:
        css_path.write_text(css.rstrip() + "\n" + CSS.strip() + "\n", encoding="utf-8")

    updated = update_html_pages(root)
    if updated < 2:
        raise SystemExit(f"Seulement {updated} page(s) ont reçu les corrections d’alignement.")

    office_html = office_page.read_text(encoding="utf-8")
    calendar_html = calendar_page.read_text(encoding="utf-8")
    required_office = (MARKER, "office-email-card", "overflow-wrap:anywhere")
    required_calendar = (MARKER, "cal-nav-button", "cal-chevron", "grid-template-columns:minmax(330px,360px)")
    missing = [value for value in required_office if value not in office_html]
    missing += [value for value in required_calendar if value not in calendar_html]
    if missing:
        raise SystemExit(f"Contrôle des corrections d’alignement incomplet : {missing}")

    run_companion_script("fix_gallery_labels.py", root)
    run_companion_script("add_google_travel_link.py", root)

    print(
        "Centrage corrigé : courriel de l’Office de Tourisme, panneau de réservation "
        "et commandes du calendrier."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

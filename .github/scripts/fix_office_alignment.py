#!/usr/bin/env python3
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

MARKER = "/* office-tourism-centering-v2 */"

CSS = r'''
/* office-tourism-centering-v2 */
#office-tourisme > .wrap.two{align-items:stretch}
#office-tourisme .contact-list p{display:flex;min-width:0;min-height:124px;flex-direction:column;align-items:center;justify-content:center;text-align:center;padding:1rem .85rem;overflow-wrap:anywhere}
#office-tourisme .contact-list strong{display:block;margin-bottom:.55rem;letter-spacing:.02em}
#office-tourisme .contact-list a{max-width:100%;text-align:center;overflow-wrap:anywhere}
#office-tourisme .actions{justify-content:center}
#office-tourisme .office-card{display:flex;height:100%;flex-direction:column;align-items:center;justify-content:center;text-align:center;padding:clamp(1.35rem,2.4vw,2rem)}
#office-tourisme .office-card .local-tag{align-self:center;margin-right:auto;margin-left:auto;text-align:center}
#office-tourisme .office-card h3{width:100%;text-align:center}
#office-tourisme .office-card ul{width:min(100%,34rem);margin:1rem auto;padding-left:1.4rem;text-align:left}
#office-tourisme .office-card li{margin:.62rem 0;padding-left:.15rem}
#office-tourisme .office-card .notice{width:100%;max-width:34rem;margin:1rem auto 0;text-align:center}
@media(max-width:980px){#office-tourisme .office-card{margin-top:.5rem}#office-tourisme .contact-list p{min-height:104px}}
@media(max-width:640px){#office-tourisme .contact-list{gap:.65rem}#office-tourisme .contact-list p{min-height:0;padding:.9rem}#office-tourisme .office-card ul{padding-left:1.2rem}}
'''


def main() -> int:
    root = Path(sys.argv[1] if len(sys.argv) > 1 else "_site").resolve()
    page = root / "decouvrir-dieppe.html"
    css_path = root / "assets/css/site.css"

    if not page.exists():
        raise SystemExit(f"Page introuvable : {page}")
    if not css_path.exists():
        raise SystemExit(f"Feuille de style introuvable : {css_path}")

    html = page.read_text(encoding="utf-8")
    if 'id="office-tourisme"' not in html:
        raise SystemExit("La section Office de Tourisme est absente de la page.")

    css = css_path.read_text(encoding="utf-8")
    if MARKER not in css:
        css_path.write_text(css.rstrip() + "\n" + CSS.strip() + "\n", encoding="utf-8")

    gallery_script = Path(__file__).with_name("fix_gallery_labels.py")
    if not gallery_script.exists():
        raise SystemExit(f"Script de correction de la galerie introuvable : {gallery_script}")
    subprocess.run([sys.executable, str(gallery_script), str(root)], check=True)

    print("Centrage de la section Office de Tourisme appliqué.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

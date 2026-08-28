#!/usr/bin/env python3
from __future__ import annotations

import base64
import gzip
from pathlib import Path

HERE = Path(__file__).resolve().parent
PARTS = sorted(HERE.glob("i18n_payload.part.*"))

if not PARTS:
    raise SystemExit("Payload de traduction introuvable.")

encoded = "".join(part.read_text(encoding="ascii").strip() for part in PARTS)
source = gzip.decompress(base64.b64decode(encoded)).decode("utf-8")

if "Site multilingue généré" not in source:
    raise SystemExit("Le moteur de traduction reconstitué est incomplet.")

exec(
    compile(source, str(HERE / "generate_multilingual_site.source.py"), "exec"),
    {"__name__": "__main__", "__file__": str(HERE / "generate_multilingual_site.source.py")},
)

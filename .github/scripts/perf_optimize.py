from __future__ import annotations

import json
import re
from pathlib import Path

from PIL import Image

ROOT = Path("_site")


def get_hero() -> str | None:
    data = ROOT / "assets/data/photos.json"
    if not data.exists():
        return None
    try:
        payload = json.loads(data.read_text(encoding="utf-8"))
        gallery = payload.get("gallery", [])
        for url in gallery:
            if isinstance(url, str) and url.startswith("/") and (ROOT / url.lstrip("/")).exists():
                return url
    except Exception:
        return None
    return None


def build_hero_variants(hero: str) -> list[tuple[str, int, int]]:
    src = ROOT / hero.lstrip("/")
    if not src.exists():
        return []
    variants: list[tuple[str, int, int]] = []
    with Image.open(src) as original:
        image = original.convert("RGB")
        for width in (480, 768):
            if image.width <= width:
                continue
            height = max(1, round(image.height * width / image.width))
            url = f"/assets/photos/hero-{width}.webp"
            target = ROOT / url.lstrip("/")
            image.resize((width, height), Image.Resampling.LANCZOS).save(
                target, "WEBP", quality=78, method=6
            )
            variants.append((url, width, height))
        variants.append((hero, image.width, image.height))
    return variants


def inline_global_assets(text: str) -> str:
    css_file = ROOT / "assets/css/site.css"
    if css_file.exists():
        css = css_file.read_text(encoding="utf-8").strip()
        text = re.sub(
            r'<link\b(?=[^>]*href=["\']/assets/css/site\.css["\'])(?=[^>]*rel=["\']stylesheet["\'])[^>]*?/?>',
            f"<style>{css}</style>",
            text,
            count=1,
            flags=re.I,
        )

    js_file = ROOT / "assets/js/site.js"
    if js_file.exists():
        js = js_file.read_text(encoding="utf-8").strip()
        text = re.sub(
            r'<script\b[^>]*src=["\']/assets/js/site\.js["\'][^>]*></script>',
            f"<script>{js}</script>",
            text,
            count=1,
            flags=re.I,
        )
    return text


def optimize_home(text: str, hero: str, variants: list[tuple[str, int, int]]) -> str:
    if not variants:
        return text
    srcset = ", ".join(f"{url} {width}w" for url, width, _ in variants)
    preferred = next((url for url, width, _ in variants if width == 768), hero)
    full = variants[-1]

    preload = (
        f'<link rel="preload" as="image" href="{preferred}" type="image/webp" '
        f'fetchpriority="high" imagesrcset="{srcset}" imagesizes="100vw"/>'
    )
    text = re.sub(
        r'<link\b(?=[^>]*rel=["\']preload["\'])(?=[^>]*as=["\']image["\'])[^>]*?/?>',
        preload,
        text,
        count=1,
        flags=re.I,
    )

    hero_img = (
        f'<img alt="Appartement Oratoriens Henri IV à Dieppe" data-hero '
        f'fetchpriority="high" decoding="async" src="{preferred}" '
        f'srcset="{srcset}" sizes="100vw" width="{full[1]}" height="{full[2]}"/>'
    )
    text = re.sub(
        r'<img\b[^>]*\bdata-hero(?:=["\'][^"\']*["\'])?[^>]*?/?>',
        hero_img,
        text,
        count=1,
        flags=re.I,
    )
    return text


def main() -> None:
    hero = get_hero()
    variants = build_hero_variants(hero) if hero else []
    for path in ROOT.rglob("*.html"):
        text = path.read_text(encoding="utf-8")
        if path == ROOT / "index.html" and hero:
            text = optimize_home(text, hero, variants)
        text = inline_global_assets(text)
        path.write_text(text, encoding="utf-8")

    home = (ROOT / "index.html").read_text(encoding="utf-8")
    if '/assets/css/site.css' in home or '/assets/js/site.js' in home:
        raise SystemExit("Les assets globaux n'ont pas été intégrés au HTML")
    if variants and "hero-480.webp" not in home:
        raise SystemExit("Le srcset responsive du hero est absent")
    print(f"Performance critique optimisée : {len(variants)} variantes hero, CSS/JS globaux inline")


if __name__ == "__main__":
    main()

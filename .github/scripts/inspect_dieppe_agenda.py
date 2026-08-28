#!/usr/bin/env python3
from __future__ import annotations

import json
import re
import urllib.request
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup

URL = "https://www.dieppetourisme.com/agenda/tout-lagenda/"
EVENT_RE = re.compile(r"https?://(?:www\.)?dieppetourisme\.com/agenda/[^\"'<>\s?#]+-fr-\d+/?", re.I)
HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; OratoriensAgenda/1.0; +https://dieppeoratoriens.com/)",
    "Accept": "text/html,application/xhtml+xml",
    "Accept-Language": "fr-FR,fr;q=0.9",
}


def fetch(url: str) -> tuple[str, str, int]:
    request = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(request, timeout=30) as response:
        html = response.read(5_000_000).decode("utf-8", "replace")
        return html, response.geturl(), response.status


def walk_json(value):
    if isinstance(value, dict):
        yield value
        for child in value.values():
            yield from walk_json(child)
    elif isinstance(value, list):
        for child in value:
            yield from walk_json(child)


def main() -> int:
    html, final_url, status = fetch(URL)
    print("HTTP", status, "URL", final_url, "bytes", len(html))

    soup = BeautifulSoup(html, "html.parser")
    ordered_links: list[str] = []
    seen: set[str] = set()
    for anchor in soup.find_all("a", href=True):
        href = urljoin(URL, anchor["href"])
        if EVENT_RE.fullmatch(href) and href not in seen:
            ordered_links.append(href)
            seen.add(href)
    for href in EVENT_RE.findall(html):
        if href not in seen:
            ordered_links.append(href)
            seen.add(href)

    print("EVENT_LINK_COUNT", len(ordered_links))
    for href in ordered_links[:100]:
        print("EVENT", href)

    first_anchor = next(
        (a for a in soup.find_all("a", href=True) if EVENT_RE.fullmatch(urljoin(URL, a["href"]))),
        None,
    )
    if first_anchor:
        parent = first_anchor
        for _ in range(5):
            if parent.parent is None:
                break
            parent = parent.parent
            classes = " ".join(parent.get("class", []))
            if any(term in classes.lower() for term in ("card", "playlist", "sheet", "item", "tourism")):
                break
        snippet = re.sub(r"\s+", " ", str(parent))
        print("FIRST_CARD_HTML", snippet[:7000])

    print("REL_NEXT")
    for tag in soup.find_all(["a", "link"], href=True):
        rel = " ".join(tag.get("rel", [])) if isinstance(tag.get("rel"), list) else str(tag.get("rel", ""))
        href = urljoin(URL, tag["href"])
        if "next" in rel.lower() or re.search(r"(?:page|paged|pagination|offset|start|listpage)=?\d+|/page/\d+", href, re.I):
            print("PAGINATION", rel, href, tag.get_text(" ", strip=True)[:100])

    print("FORMS")
    for form in soup.find_all("form"):
        action = urljoin(URL, form.get("action") or URL)
        names = [node.get("name") for node in form.find_all(["input", "select", "button"]) if node.get("name")]
        if any(term in (action + " " + " ".join(names)).lower() for term in ("agenda", "event", "search", "filter", "page")):
            print("FORM", form.get("method", "get"), action, names[:30])

    print("SCRIPTS")
    for script in soup.find_all("script"):
        src = script.get("src")
        if src:
            absolute = urljoin(URL, src)
            if any(term in absolute.lower() for term in ("agenda", "tour", "api", "search", "list", "app", "main", "front")):
                print("SCRIPT_SRC", absolute)
        else:
            text = script.string or script.get_text(" ", strip=True)
            low = text.lower()
            if any(term in low for term in ("apidae", "tourinsoft", "agenda", "pagination", "loadmore", "load_more", "api/", "ajax")):
                compact = re.sub(r"\s+", " ", text)
                print("INLINE", compact[:2000])

    print("DATA_ATTRIBUTES")
    for tag in soup.find_all(True):
        attrs = " ".join(f"{k}={v}" for k, v in tag.attrs.items() if k.startswith("data-"))
        if attrs and any(term in attrs.lower() for term in ("agenda", "event", "page", "api", "ajax", "search", "listing")):
            print("DATA", tag.name, attrs[:1000])

    if ordered_links:
        detail_url = ordered_links[0]
        detail_html, detail_final, detail_status = fetch(detail_url)
        detail = BeautifulSoup(detail_html, "html.parser")
        print("DETAIL_HTTP", detail_status, detail_final, "bytes", len(detail_html))
        print("DETAIL_TITLE", detail.find("h1").get_text(" ", strip=True) if detail.find("h1") else "")
        for meta_key in ("description", "og:description", "og:image"):
            tag = detail.find("meta", attrs={"name": meta_key}) or detail.find("meta", attrs={"property": meta_key})
            if tag:
                print("DETAIL_META", meta_key, tag.get("content", "")[:1000])
        for tag in detail.find_all(True):
            if tag.has_attr("datetime") or tag.get("itemprop") in {"startDate", "endDate", "location"}:
                print("DETAIL_DATE_TAG", tag.name, dict(tag.attrs), tag.get_text(" ", strip=True)[:300])
        for anchor in detail.find_all("a", href=True):
            href = anchor["href"]
            if "calendar.google" in href or "google.com/calendar" in href or "dates=" in href:
                print("DETAIL_CALENDAR_LINK", href)
        for script in detail.find_all("script", attrs={"type": "application/ld+json"}):
            try:
                payload = json.loads(script.string or script.get_text())
            except Exception:
                continue
            for node in walk_json(payload):
                node_type = node.get("@type")
                types = node_type if isinstance(node_type, list) else [node_type]
                if any(str(t).lower() == "event" for t in types):
                    print("DETAIL_EVENT_JSONLD", json.dumps(node, ensure_ascii=False)[:6000])
        for pattern in (r'"startDate"\s*:\s*"([^"]+)"', r'"endDate"\s*:\s*"([^"]+)"'):
            found = re.findall(pattern, detail_html, flags=re.I)
            print("DETAIL_REGEX", pattern, found[:20])

    parsed = urlparse(URL)
    print("HOST", parsed.netloc)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
from __future__ import annotations

import re
import urllib.request
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup

URL = "https://www.dieppetourisme.com/agenda/tout-lagenda/"
EVENT_RE = re.compile(r"https?://(?:www\.)?dieppetourisme\.com/agenda/[^\"'<>\s?#]+-fr-\d+/?", re.I)


def main() -> int:
    request = urllib.request.Request(
        URL,
        headers={
            "User-Agent": "Mozilla/5.0 (compatible; OratoriensAgenda/1.0; +https://dieppeoratoriens.com/)",
            "Accept": "text/html,application/xhtml+xml",
            "Accept-Language": "fr-FR,fr;q=0.9",
        },
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        html = response.read(5_000_000).decode("utf-8", "replace")
        print("HTTP", response.status, "URL", response.geturl(), "bytes", len(html))

    soup = BeautifulSoup(html, "html.parser")
    links = set(EVENT_RE.findall(html))
    for anchor in soup.find_all("a", href=True):
        href = urljoin(URL, anchor["href"])
        if EVENT_RE.fullmatch(href):
            links.add(href)
    print("EVENT_LINK_COUNT", len(links))
    for href in sorted(links)[:100]:
        print("EVENT", href)

    print("REL_NEXT")
    for tag in soup.find_all(["a", "link"], href=True):
        rel = " ".join(tag.get("rel", [])) if isinstance(tag.get("rel"), list) else str(tag.get("rel", ""))
        href = urljoin(URL, tag["href"])
        if "next" in rel.lower() or re.search(r"(?:page|paged|pagination|offset|start)=?\d+|/page/\d+", href, re.I):
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

    parsed = urlparse(URL)
    print("HOST", parsed.netloc)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

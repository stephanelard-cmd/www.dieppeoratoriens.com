from __future__ import annotations
import json, re
from datetime import date
from pathlib import Path
from urllib.parse import urljoin

BASE = "https://dieppeoratoriens.com"
ROOT = Path("_site")

SEO = {
    "index.html": ("Location appartement Dieppe port | Oratoriens Henri IV", "Location de vacances à Dieppe face au port : studio-mezzanine d’environ 35 m², jusqu’à 5 voyageurs, près de la plage, du marché et des restaurants.", "/"),
    "hebergement.html": ("Appartement à Dieppe face au port | Oratoriens Henri IV", "Découvrez l’appartement Oratoriens Henri IV à Dieppe : studio-mezzanine équipé, jusqu’à 5 voyageurs, quai Henri IV, proche plage et centre-ville.", "/hebergement.html"),
    "galerie.html": ("Photos appartement Dieppe port | Oratoriens Henri IV", "Photos du studio-mezzanine Oratoriens Henri IV à Dieppe : séjour, mezzanine, cuisine, salle d’eau et vue sur le port.", "/galerie.html"),
    "disponibilites.html": ("Location Dieppe : disponibilités | Oratoriens Henri IV", "Consultez les disponibilités de l’appartement Oratoriens Henri IV à Dieppe, synchronisées avec Booking.com et Airbnb.", "/disponibilites.html"),
    "avis-localisation.html": ("Appartement Dieppe centre : avis & localisation | Oratoriens", "Avis voyageurs, adresse et localisation de l’appartement Oratoriens Henri IV sur le port de Dieppe, près de la plage, du marché et du centre.", "/avis-localisation.html"),
    "informations.html": ("Séjour à Dieppe : informations pratiques | Oratoriens Henri IV", "Informations pratiques pour votre séjour à Oratoriens Henri IV à Dieppe : arrivée, départ, équipements, animaux et règles du logement.", "/informations.html"),
    "classement-equipements.html": ("Équipements appartement Dieppe | Oratoriens Henri IV", "Équipements et informations de contrôle du studio-mezzanine Oratoriens Henri IV à Dieppe, quai Henri IV.", "/classement-equipements.html"),
    "mentions-legales.html": ("Mentions légales | Oratoriens Henri IV Dieppe", "Mentions légales du site officiel Oratoriens Henri IV, location de vacances à Dieppe.", "/mentions-legales.html"),
    "confidentialite.html": ("Confidentialité | Oratoriens Henri IV Dieppe", "Politique de confidentialité du site officiel Oratoriens Henri IV à Dieppe.", "/confidentialite.html"),
    "en/index.html": ("Dieppe holiday apartment on the harbour | Oratoriens Henri IV", "Holiday apartment in central Dieppe facing the harbour: mezzanine studio for up to five guests, close to the beach, market and restaurants.", "/en/"),
    "404.html": ("Page introuvable | Oratoriens Henri IV Dieppe", "Page introuvable sur le site Oratoriens Henri IV à Dieppe.", "/404.html"),
}

def esc_attr(s: str) -> str:
    return s.replace("&", "&amp;").replace('"', "&quot;").replace("<", "&lt;").replace(">", "&gt;")

def strip_meta(text: str, attr: str, key: str) -> str:
    pat = rf'<meta\b(?=[^>]*\b{attr}=["\']{re.escape(key)}["\'])[^>]*?/?>'
    return re.sub(pat, "", text, flags=re.I)

def add_head(text: str, snippet: str) -> str:
    return text.replace("</head>", snippet + "</head>", 1)

def image_dimensions(url_path: str):
    if not url_path.startswith("/"):
        return None
    p = ROOT / url_path.lstrip("/")
    if not p.exists() or p.suffix.lower() not in {".webp", ".jpg", ".jpeg", ".png"}:
        return None
    try:
        from PIL import Image
        with Image.open(p) as im:
            return im.width, im.height
    except Exception:
        return None

def load_photos() -> list[str]:
    p = ROOT / "assets/data/photos.json"
    gallery = []
    if p.exists():
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
            gallery = [x for x in data.get("gallery", []) if isinstance(x, str) and x.startswith("/") and (ROOT / x.lstrip("/")).exists()]
        except Exception:
            pass
    return gallery

def business_graph(page_url: str, title: str, description: str, photos: list[str], lang: str):
    lodging = {
        "@type": "LodgingBusiness", "@id": BASE + "/#lodging", "name": "Oratoriens Henri IV", "url": BASE + "/",
        "description": "Location de vacances sur le quai Henri IV à Dieppe, face au port et à proximité de la plage, du marché, des restaurants et du centre-ville.",
        "image": [urljoin(BASE, p) for p in photos],
        "address": {"@type": "PostalAddress", "streetAddress": "31–33 quai Henri IV", "postalCode": "76200", "addressLocality": "Dieppe", "addressRegion": "Normandie", "addressCountry": "FR"},
        "geo": {"@type": "GeoCoordinates", "latitude": 49.928033, "longitude": 1.080668},
        "hasMap": "https://www.google.com/maps/search/?api=1&query=31-33+quai+Henri+IV+76200+Dieppe",
        "sameAs": ["https://www.booking.com/hotel/fr/oratoriens-henri-iv.fr.html", "https://www.airbnb.fr/rooms/992531447842701708"],
        "petsAllowed": True, "checkinTime": "15:00", "checkoutTime": "11:00", "knowsLanguage": ["fr-FR", "en"],
        "amenityFeature": [
            {"@type": "LocationFeatureSpecification", "name": "Wi-Fi haut débit", "value": True},
            {"@type": "LocationFeatureSpecification", "name": "Cuisine équipée", "value": True},
            {"@type": "LocationFeatureSpecification", "name": "Lave-linge", "value": True},
            {"@type": "LocationFeatureSpecification", "name": "Sèche-linge", "value": True},
            {"@type": "LocationFeatureSpecification", "name": "Animaux admis", "value": True},
        ],
    }
    graph = [lodging, {"@type": "WebPage", "@id": page_url + "#webpage", "url": page_url, "name": title, "description": description, "inLanguage": lang, "about": {"@id": BASE + "/#lodging"}}]
    if page_url == BASE + "/":
        graph.insert(0, {"@type": "WebSite", "@id": BASE + "/#website", "url": BASE + "/", "name": "Oratoriens Henri IV Dieppe", "inLanguage": ["fr-FR", "en"]})
    return {"@context": "https://schema.org", "@graph": graph}

def optimize_html(path: Path, rel: str, photos: list[str], hero: str):
    title, desc, canonical_path = SEO[rel]
    canonical = BASE + canonical_path
    lang = "en" if rel.startswith("en/") else "fr-FR"
    og_locale = "en_GB" if rel.startswith("en/") else "fr_FR"
    text = path.read_text(encoding="utf-8")
    text = text.replace('href="/index.html"', 'href="/"')
    text = re.sub(r"<title>.*?</title>", f"<title>{title}</title>", text, count=1, flags=re.I | re.S)
    text = re.sub(r'<meta\b(?=[^>]*\bname=["\']description["\'])[^>]*?/?>', "", text, flags=re.I)
    text = re.sub(r'<link\b(?=[^>]*\brel=["\']canonical["\'])[^>]*?/?>', "", text, flags=re.I)
    for attr, key in [("name", "robots"), ("name", "theme-color"), ("property", "og:site_name"), ("property", "og:locale"), ("property", "og:title"), ("property", "og:description"), ("property", "og:url"), ("property", "og:image"), ("name", "twitter:card"), ("name", "twitter:title"), ("name", "twitter:description"), ("name", "twitter:image")]:
        text = strip_meta(text, attr, key)
    text = re.sub(r'<link\b(?=[^>]*\bhreflang=)[^>]*?/?>', "", text, flags=re.I)
    robots = "noindex,follow" if rel == "404.html" else "index,follow,max-image-preview:large,max-snippet:-1,max-video-preview:-1"
    og_image = urljoin(BASE, hero)
    tags = (f'<meta name="description" content="{esc_attr(desc)}"/><meta name="robots" content="{robots}"/><meta name="theme-color" content="#18343e"/>'
            f'<link rel="canonical" href="{canonical}"/><meta property="og:site_name" content="Oratoriens Henri IV Dieppe"/><meta property="og:locale" content="{og_locale}"/>'
            f'<meta property="og:title" content="{esc_attr(title)}"/><meta property="og:description" content="{esc_attr(desc)}"/><meta property="og:url" content="{canonical}"/><meta property="og:image" content="{og_image}"/>'
            f'<meta name="twitter:card" content="summary_large_image"/><meta name="twitter:title" content="{esc_attr(title)}"/><meta name="twitter:description" content="{esc_attr(desc)}"/><meta name="twitter:image" content="{og_image}"/>')
    if rel in {"index.html", "en/index.html"}:
        tags += f'<link rel="alternate" hreflang="fr-FR" href="{BASE}/"/><link rel="alternate" hreflang="en" href="{BASE}/en/"/><link rel="alternate" hreflang="x-default" href="{BASE}/"/>'
    if rel == "index.html" and hero.endswith(".webp"):
        tags += f'<link rel="preload" as="image" href="{hero}" type="image/webp" fetchpriority="high"/>'
    text = add_head(text, tags)
    text = re.sub(r'<script\s+type=["\']application/ld\+json["\']>.*?</script>', "", text, count=1, flags=re.I | re.S)
    if rel != "404.html":
        graph = json.dumps(business_graph(canonical, title, desc, photos, lang), ensure_ascii=False, separators=(",", ":"))
        text = add_head(text, f'<script type="application/ld+json">{graph}</script>')
    if rel == "index.html":
        text = text.replace('<h1>Le port devant vous.<br/>Dieppe à vos pieds.</h1>', '<h1>Location de vacances à Dieppe face au port</h1><p class="hero-kicker">Le port devant vous. Dieppe à vos pieds.</p>')
        local_section = ('<section class="section local-seo"><div class="wrap"><div class="eyebrow">Dieppe centre et bord de mer</div><h2>Un appartement entre le port, la plage et le marché de Dieppe</h2>'
                         '<p class="lead">Pour un week-end ou quelques jours à Dieppe, Oratoriens Henri IV permet de rejoindre à pied le port, la plage de Dieppe, le marché, le château-musée, les restaurants du quai Henri IV et les commerces du centre-ville.</p>'
                         '<p>La gare de Dieppe est également accessible depuis le centre. Cette situation convient aussi bien à une escapade en bord de mer qu’à un séjour sans voiture, avec les principaux lieux de visite regroupés autour du port et du front de mer.</p>'
                         '<div class="actions"><a class="btn btn-primary" href="/avis-localisation.html">Voir la localisation</a><a class="btn btn-outline" href="/informations.html">Préparer le séjour</a></div></div></section>')
        marker = '<section class="section"><div class="wrap"><div class="eyebrow">Réserver</div>'
        if local_section not in text and marker in text:
            text = text.replace(marker, local_section + marker, 1)
        dims = image_dimensions(hero)
        if dims:
            text = re.sub(r'<img\b[^>]*\bdata-hero(?:=["\'][^"\']*["\'])?[^>]*?/?>', f'<img alt="Appartement Oratoriens Henri IV à Dieppe" data-hero fetchpriority="high" decoding="async" src="{hero}" width="{dims[0]}" height="{dims[1]}"/>', text, count=1, flags=re.I)
    if rel == "galerie.html":
        tags_found = list(re.finditer(r'<img\b[^>]*\bdata-gallery(?:=["\'][^"\']*["\'])?[^>]*?/?>', text, flags=re.I))
        for i in range(len(tags_found)-1, -1, -1):
            m = tags_found[i]
            if i >= len(photos):
                continue
            src = photos[i]
            old = m.group(0)
            altm = re.search(r'alt=["\']([^"\']*)["\']', old)
            alt = altm.group(1) if altm else "Appartement Oratoriens Henri IV à Dieppe"
            dims = image_dimensions(src) or (1280, 850)
            loading = "eager" if i == 0 else "lazy"
            priority = "high" if i == 0 else "low"
            new = f'<img alt="{esc_attr(alt)}" data-gallery decoding="async" fetchpriority="{priority}" height="{dims[1]}" loading="{loading}" src="{src}" width="{dims[0]}"/>'
            text = text[:m.start()] + new + text[m.end():]
    if rel == "disponibilites.html":
        text = text.replace('<div class="calendar">', '<div class="calendar" role="region" aria-labelledby="cal-month">').replace('<div class="week">', '<div class="week" role="row">')
        text = re.sub(r'<div>(Lun|Mar|Mer|Jeu|Ven|Sam|Dim)</div>', r'<div role="columnheader">\1</div>', text)
        text = text.replace('<div class="days" id="cal-days"></div>', '<div class="days" id="cal-days" role="rowgroup"></div>').replace('id="calendar-status"', 'id="calendar-status" aria-live="polite"')
    if rel == "en/index.html":
        for a,b in {'>Aller au contenu<':'>Skip to content<','aria-label="Navigation principale"':'aria-label="Main navigation"','>Accueil<':'>Home<','>Le logement<':'>Apartment<','>Disponibilités<':'>Availability<','>Avis &amp; plan<':'>Reviews &amp; map<','>Réserver<':'>Book<','Un pied-à-terre de caractère sur le quai Henri IV, au cœur du port historique.':'A characterful place to stay on Quai Henri IV, in the heart of Dieppe harbour.','>Adresse<':'>Address<','>Plan et itinéraire<':'>Map and directions<','>Informations<':'>Information<','>Règles du séjour<':'>Stay information<','>Mentions légales<':'>Legal notice<','>Confidentialité<':'>Privacy<','>Classement &amp; équipements<':'>Facilities &amp; classification<'}.items():
            text = text.replace(a,b)
    text = re.sub(r'<div class="icon">([^<]+)</div>', r'<div class="icon" aria-hidden="true">\1</div>', text)
    path.write_text(text, encoding="utf-8")

def update_assets(photos: list[str]):
    css = ROOT / "assets/css/site.css"
    if css.exists():
        s = css.read_text(encoding="utf-8").replace("--gold:#b58a4e", "--gold:#76501d")
        additions = '.hero-kicker{font-family:Georgia,serif;font-size:clamp(1.35rem,2.3vw,2rem);margin:.2rem 0 1rem;color:#fff}a:focus-visible,button:focus-visible{outline:3px solid #0b6178;outline-offset:3px}@media(prefers-reduced-motion:reduce){html{scroll-behavior:auto}.gallery img{transition:none}}'
        if additions not in s:
            s += additions
        css.write_text(s, encoding="utf-8")
    js = ROOT / "assets/js/site.js"
    if js.exists():
        js.write_text("const toggle=document.querySelector('.menu-toggle');const menu=document.querySelector('.menu');if(toggle&&menu){toggle.addEventListener('click',()=>{const o=menu.classList.toggle('open');toggle.setAttribute('aria-expanded',String(o));});}const y=document.querySelector('[data-year]');if(y)y.textContent=new Date().getFullYear();\n", encoding="utf-8")
    cal = ROOT / "assets/js/calendar.js"
    if cal.exists():
        s = cal.read_text(encoding="utf-8").replace("el.className='day';", "el.className='day';el.setAttribute('role','gridcell');")
        cal.write_text(s, encoding="utf-8")
    urls = [("/","daily"),("/hebergement.html","monthly"),("/galerie.html","monthly"),("/disponibilites.html","daily"),("/avis-localisation.html","monthly"),("/informations.html","monthly"),("/classement-equipements.html","yearly"),("/mentions-legales.html","yearly"),("/confidentialite.html","yearly"),("/en/","monthly")]
    today = date.today().isoformat()
    out = ['<?xml version="1.0" encoding="UTF-8"?>','<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" xmlns:image="http://www.google.com/schemas/sitemap-image/1.1" xmlns:xhtml="http://www.w3.org/1999/xhtml">']
    for loc,freq in urls:
        out += ['<url>',f'<loc>{BASE}{loc}</loc><lastmod>{today}</lastmod><changefreq>{freq}</changefreq>']
        if loc == "/":
            out += [f'<xhtml:link rel="alternate" hreflang="fr-FR" href="{BASE}/"/>',f'<xhtml:link rel="alternate" hreflang="en" href="{BASE}/en/"/>',f'<xhtml:link rel="alternate" hreflang="x-default" href="{BASE}/"/>']
        if loc in {"/", "/galerie.html"}:
            out += [f'<image:image><image:loc>{urljoin(BASE,p)}</image:loc></image:image>' for p in photos]
        out.append('</url>')
    out.append('</urlset>')
    (ROOT / "sitemap.xml").write_text("\n".join(out)+"\n", encoding="utf-8")
    (ROOT / "robots.txt").write_text("User-agent: *\nAllow: /\nSitemap: https://dieppeoratoriens.com/sitemap.xml\n", encoding="utf-8")

def main():
    if not ROOT.exists():
        raise SystemExit("_site introuvable")
    photos = load_photos()
    hero = photos[0] if photos else "/assets/images/facade-fallback.svg"
    update_assets(photos)
    for rel in SEO:
        p = ROOT / rel
        if p.exists():
            optimize_html(p, rel, photos, hero)
    print(f"SEO/Lighthouse optimisation appliquée: {len(photos)} photos locales, hero={hero}")

if __name__ == "__main__":
    main()

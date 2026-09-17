#!/usr/bin/env python3
"""Apply the September 2026 inspection after the legacy multilingual generator.

Only public accommodation facts are included. Original PDFs contain private
contact details and must not be copied into the public repository or site.
The receipt date is unknown: report the decision and its 15-day condition, but
do not emit an unconditional starRating or an invented effective/expiry date.
"""
from __future__ import annotations

import argparse
import json
from html import escape
from pathlib import Path
from urllib.parse import urlparse
import xml.etree.ElementTree as ET

from bs4 import BeautifulSoup, NavigableString

BASE = "https://dieppeoratoriens.com"
DATE = "2026-09-17"
COPY = json.loads(Path(__file__).with_suffix('.json').read_text(encoding='utf-8'))
PAGES = ('index.html', 'hebergement.html', 'classement-equipements.html', 'informations.html', 'mentions-legales.html')


def fragment(html):
    return BeautifulSoup(html, 'html.parser')


def paragraph(text, css=''):
    return f'<p class="{css}">{escape(text)}</p>'


def items(values):
    return '<ul class="feature-list">' + ''.join(f'<li>{escape(x)}</li>' for x in values) + '</ul>'


def section(title, body, alternate=False, element_id=''):
    css = 'section section-alt' if alternate else 'section'
    return f'<section class="{css}" id="{element_id}"><div class="wrap"><h2>{escape(title)}</h2>{body}</div></section>'


def card(title, text):
    return f'<article class="card"><h3>{escape(title)}</h3>{paragraph(text)}</article>'


def links(d, prefix):
    return (f'<div class="actions"><a class="btn btn-primary" href="{prefix}/classement-equipements.html">{escape(d["titles"][8])}</a>'
            f'<a class="btn btn-outline" href="{prefix}/disponibilites.html">{escape(d["titles"][9])}</a></div>')


def classification_main(d, prefix):
    t = d['titles']
    return (
        '<main id="contenu" data-classification="2026-09-17">'
        f'<section class="page-hero"><div class="wrap"><h1>{escape(t[0])}</h1>{paragraph(d["decision"], "lead")}{paragraph(d["delay"], "notice")}</div></section>'
        + section(t[1], paragraph(d['capacity'], 'notice') + '<div class="card-grid">'
                  + card('31 m²', d['surface']) + card('149 / 154', d['mandatory']) + card('78 points' if prefix not in ('/de', '/es') else ('78 Punkte' if prefix == '/de' else '78 puntos'), d['optional']) + '</div>')
        + section(d['equipment_title'], items(d['equipment']) + paragraph(d['laundry']), True)
        + section(t[5], paragraph(d['access']) + items(d['limits']), element_id='accessibilite')
        + section(t[6], paragraph(d['eco']), True)
        + section(t[7], paragraph(d['history']) + paragraph(d['source']) + links(d, prefix))
        + '</main>'
    )


def accommodation_main(d, prefix):
    t = d['titles']
    cards = [(t[11], d['capacity']), (t[12], d['kitchen']), (t[13], d['bathroom']),
             (t[14], d['laundry']), (t[15], d['media']), (t[16], d['thermal'])]
    return (
        '<main id="contenu" data-classification="2026-09-17">'
        f'<section class="page-hero"><div class="wrap"><h1>{escape(t[10])}</h1>{paragraph(d["surface"], "lead")}{paragraph(d["badge"], "notice")}{links(d,prefix)}</div></section>'
        + section(d['equipment_title'], '<div class="card-grid">' + ''.join(card(a,b) for a,b in cards) + '</div>')
        + section(t[5], paragraph(d['access']) + items(d['limits']), True, 'accessibilite')
        + section(t[1], paragraph(d['decision']) + paragraph(d['delay']) + links(d, prefix))
        + '</main>'
    )


def replace_text(tag, value):
    if tag is None:
        raise ValueError('Required content anchor is missing')
    tag.clear()
    tag.append(value)


def patch_home(soup, d, prefix):
    hero = soup.select_one('.hero-content')
    paras = hero.find_all('p', recursive=False)
    lead = next(p for p in paras if 'hero-kicker' not in p.get('class', []))
    replace_text(lead, d['hero'])
    facts = soup.select('.quickfacts .fact')
    replace_text(facts[0].strong, '31 m²')
    replace_text(facts[0].span, d['surface_short'])
    # Show the classified capacity here; explain the commercial capacity below.
    replace_text(facts[1].strong, {'':'2 personnes', '/en':'2 people', '/de':'2 Personen', '/es':'2 personas'}[prefix])
    facts[1].span.clear()
    facts[1].span.append(d['badge'])
    features = soup.select_one('main .feature-list')
    features.replace_with(fragment(items([d['equipment'][0], d['equipment'][3], d['equipment'][8], d['equipment'][2], d['equipment'][9], d['equipment'][10]])).ul)
    notice = soup.select_one('main .card .notice')
    config = notice.parent
    replace_text(config.find('p', recursive=False), d['capacity'])
    notice.clear()
    notice.append(d['decision'] + ' ')
    link = soup.new_tag('a', href=prefix + '/classement-equipements.html')
    link.string = d['titles'][8]
    notice.append(link)
    kitchen_card = soup.select('.section-alt .card-grid .card')[1]
    replace_text(kitchen_card.p, d['kitchen'])
    soup.main['data-classification'] = DATE


def patch_info(soup, d, prefix):
    legal = soup.select_one('.legal')
    headings = legal.find_all('h2', recursive=False)
    if len(headings) != 9:
        raise ValueError('Practical information structure has changed')
    replace_text(headings[1].find_next_sibling('p'), d['capacity'])
    replace_text(headings[5].find_next_sibling('p'), d['access'])
    replace_text(headings[7].find_next_sibling('p'), ' '.join(d['limits']))
    for html in [f'<h2>{escape(d["titles"][14])}</h2>', paragraph(d['laundry']),
                 f'<h2>{escape(d["badge"])}</h2>', paragraph(d['decision']), paragraph(d['delay']), links(d,prefix)]:
        legal.append(fragment(html))
    soup.main['data-classification'] = DATE


def patch_legal(soup, d, prefix):
    legal = soup.select_one('.legal')
    heading = legal.find_all('h2', recursive=False)[-1]
    replace_text(heading, d['badge'])
    replace_text(heading.find_next_sibling('p'), d['decision'] + ' ' + d['delay'] + ' ' + d['capacity'])
    legal.append(fragment(links(d, prefix)))
    soup.main['data-classification'] = DATE


def graph_nodes(payload):
    if isinstance(payload, list):
        for value in payload:
            yield from graph_nodes(value)
    elif isinstance(payload, dict):
        yield payload
        for value in payload.values():
            if isinstance(value, (dict, list)):
                yield from graph_nodes(value)


def patch_schema(soup, d, prefix, filename):
    canonical = soup.find('link', rel='canonical')
    page_url = canonical['href'] if canonical else BASE + prefix + '/' + filename
    for script in soup.find_all('script', type='application/ld+json'):
        payload = json.loads(script.string or script.get_text())
        for node in graph_nodes(payload):
            types = node.get('@type', [])
            types = [types] if isinstance(types, str) else types
            if 'LodgingBusiness' in types or 'VacationRental' in types:
                node['address']['streetAddress'] = '31 quai Henri IV'
                node['description'] = d['hero'] + ' ' + d['capacity']
                # No starRating until the receipt-dependent finality is confirmed.
                node.pop('starRating', None)
                node.pop('floorSize', None)
                node['subjectOf'] = {
                    '@type': 'WebPage', '@id': BASE + prefix + '/classement-equipements.html#webpage',
                    'url': BASE + prefix + '/classement-equipements.html',
                    'name': d['badge'], 'description': d['decision'] + ' ' + d['delay'],
                    'dateModified': DATE,
                }
                node['amenityFeature'] = [{'@type': 'LocationFeatureSpecification', 'name': x, 'value': True}
                                          for x in (d['equipment'][0], d['equipment'][2], d['equipment'][3], d['equipment'][4], d['equipment'][9], d['equipment'][10])]
            if 'WebPage' in types and node.get('url') == page_url and filename in d['meta']:
                node['name'], node['description'] = d['meta'][filename]
                node['dateModified'] = DATE
        script.string = json.dumps(payload, ensure_ascii=False, separators=(',', ':'))


def patch_metadata(soup, d, filename):
    if filename not in d['meta']:
        return
    title, description = d['meta'][filename]
    soup.title.string = title
    for attr, key, value in [('name','description',description), ('property','og:title',title),
                            ('property','og:description',description), ('name','twitter:title',title),
                            ('name','twitter:description',description)]:
        tags = soup.find_all('meta', attrs={attr:key})
        if not tags:
            tag = soup.new_tag('meta', attrs={attr:key})
            soup.head.append(tag)
            tags = [tag]
        tags[0]['content'] = value
        for extra in tags[1:]:
            extra.decompose()


def apply(root):
    count = 0
    for path in sorted(root.rglob('*.html')):
        soup = BeautifulSoup(path.read_text(encoding='utf-8'), 'html.parser')
        if not soup.main or not soup.head:
            continue
        lang = soup.html.get('lang', 'fr').split('-')[0]
        if lang not in COPY:
            continue
        d = COPY[lang]
        prefix = '' if lang == 'fr' else '/' + lang
        if soup.select_one('meta[name="classification-source-date"]'):
            continue
        for node in list(soup.find_all(string=True)):
            if node.parent.name not in ('script', 'style') and '31–33' in str(node):
                node.replace_with(NavigableString(str(node).replace('31–33', '31')))
        if soup.select_one('.topbar'):
            replace_text(soup.select_one('.topbar'), d['topbar'])
        if path.name == 'classement-equipements.html':
            soup.main.replace_with(fragment(classification_main(d, prefix)).main)
        elif path.name == 'hebergement.html':
            soup.main.replace_with(fragment(accommodation_main(d, prefix)).main)
        elif path.name == 'index.html':
            patch_home(soup, d, prefix)
        elif path.name == 'informations.html':
            patch_info(soup, d, prefix)
        elif path.name == 'mentions-legales.html':
            patch_legal(soup, d, prefix)
        patch_metadata(soup, d, path.name)
        patch_schema(soup, d, prefix, path.name)
        soup.head.append(soup.new_tag('meta', attrs={'name':'classification-source-date', 'content':DATE}))
        path.write_text(str(soup), encoding='utf-8')
        count += 1
    # Record a real editorial modification date, independent of calendar refreshes.
    sitemap = root / 'sitemap.xml'
    if sitemap.exists():
        ns = {'s':'http://www.sitemaps.org/schemas/sitemap/0.9'}
        tree = ET.parse(sitemap)
        ET.register_namespace('', ns['s'])
        ET.register_namespace('xhtml', 'http://www.w3.org/1999/xhtml')
        ET.register_namespace('image', 'http://www.google.com/schemas/sitemap-image/1.1')
        for url in tree.getroot().findall('s:url', ns):
            loc = url.find('s:loc', ns).text
            filename = urlparse(loc).path.rsplit('/',1)[-1] or 'index.html'
            if filename in PAGES:
                modified = url.find('s:lastmod', ns)
                if modified is None:
                    modified = ET.SubElement(url, '{'+ns['s']+'}lastmod')
                modified.text = DATE
        tree.write(sitemap, encoding='utf-8', xml_declaration=True)
    print(f'September 2026 inspection applied to {count} pages.')


def verify(root):
    checked = 0
    for lang, d in COPY.items():
        folder = root if lang == 'fr' else root / lang
        for filename in PAGES:
            path = folder / filename
            soup = BeautifulSoup(path.read_text(encoding='utf-8'), 'html.parser')
            assert soup.main.get('data-classification') == DATE, path
            assert d['capacity'] in soup.get_text(), path
            assert len(soup.find_all('h1')) == 1, path
            assert len(soup.find_all('link',rel='canonical')) == 1, path
            assert len(soup.find_all('link',hreflang=True)) == 5, path
            if filename in d['meta']:
                assert soup.title.get_text() == d['meta'][filename][0], path
                assert soup.find('meta',attrs={'name':'description'})['content'] == d['meta'][filename][1], path
            if filename == 'classement-equipements.html':
                for value in ('149 / 154', '31 m²', d['decision'], d['delay'], d['access'], d['optional']):
                    assert value in soup.get_text(), (path,value)
            if filename != 'mentions-legales.html':
                assert '2019' not in soup.get_text() or filename == 'classement-equipements.html', path
            for script in soup.find_all('script',type='application/ld+json'):
                for node in graph_nodes(json.loads(script.string or script.get_text())):
                    assert 'starRating' not in node, path
            for link in soup.main.find_all('a',href=True):
                href = link['href']
                if href.startswith('/'):
                    target = root / urlparse(href).path.lstrip('/')
                    assert target.exists() or (target / 'index.html').exists(), (path, href)
            checked += 1
    for path in root.rglob('*.html'):
        text = path.read_text(encoding='utf-8')
        for private in ('stephaneelard@aol.com', '0612855059', '9 rue du Docteur Leray'):
            assert private not in text, path
    ET.parse(root / 'sitemap.xml')
    print(f'Classification content, languages, metadata, privacy and links verified: {checked} key pages.')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('site_root',type=Path)
    parser.add_argument('--check',action='store_true')
    args = parser.parse_args()
    if not args.check:
        apply(args.site_root)
    verify(args.site_root)


if __name__ == '__main__':
    main()

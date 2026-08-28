#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from datetime import date
from html import escape
from pathlib import Path
from urllib.parse import quote_plus

from bs4 import BeautifulSoup

BASE = "https://dieppeoratoriens.com"
OFFICE_URL = "https://www.dieppetourisme.com/sejourner/pratique/loffice-de-tourisme/"
AGENDA_URL = "https://www.dieppetourisme.com/agenda/"
RESTAURANTS_URL = "https://www.dieppetourisme.com/sejourner/des-restaurants-pour-tous-les-gouts/tous-les-restaurants/"

NEARBY = [
    {
        "icon": "⚓",
        "title": "Port de plaisance, Pont Ango et quais",
        "time": "0 à 5 min à pied",
        "text": "Commencez par longer le quai Henri IV, observer les bateaux et rejoindre le pont levant Jehan Ango. C’est la promenade la plus simple pour prendre ses repères dès l’arrivée.",
        "official": "https://www.dieppetourisme.com/bouger/visiter/pont-ango-dieppe-fr-4164870/",
        "map": "Pont Jehan Ango, Dieppe",
    },
    {
        "icon": "🐟",
        "title": "Marché aux poissons et arrivages du port",
        "time": "3 à 7 min à pied",
        "text": "Autour du Pont Ango, les étals suivent les marées, la météo et les arrivages. À privilégier le matin pour l’ambiance maritime et les produits de saison.",
        "official": "https://www.dieppetourisme.com/sejourner/marches-saveurs-locales/les-marches-aux-poissons/",
        "map": "Marché aux poissons, Dieppe",
    },
    {
        "icon": "🧺",
        "title": "Grand marché de Dieppe",
        "time": "5 à 8 min à pied",
        "text": "Le samedi matin, le centre se remplit de producteurs et de marchands. Les petits marchés ont aussi lieu le mardi et le jeudi matin, place Nationale.",
        "official": "https://www.dieppetourisme.com/sejourner/marches-saveurs-locales/les-marches-du-terroir/",
        "map": "Place Nationale, Dieppe",
    },
    {
        "icon": "⛪",
        "title": "Église Saint-Jacques et centre historique",
        "time": "6 à 10 min à pied",
        "text": "Une halte majeure pour comprendre l’histoire maritime de Dieppe, Jehan Ango et les voyages des navigateurs dieppois. Poursuivez par la Grande Rue et la place du Puits-Salé.",
        "official": "https://www.dieppetourisme.com/bouger/visiter/eglise-saint-jacques-dieppe-fr-3027529/",
        "map": "Église Saint-Jacques, Dieppe",
    },
    {
        "icon": "🐠",
        "title": "ESTRAN – Cité de la Mer",
        "time": "10 à 15 min à pied",
        "text": "Le meilleur choix en famille ou par temps couvert : environnement marin, métiers de la mer, aquariums et patrimoine maritime, au 37 rue de l’Asile Thomas.",
        "official": "https://www.dieppetourisme.com/bouger/visiter/estran-cite-de-la-mer-dieppe-fr-3027814/",
        "map": "ESTRAN Cité de la Mer, Dieppe",
    },
    {
        "icon": "🌊",
        "title": "Plage, pelouses et loisirs nautiques",
        "time": "8 à 15 min à pied",
        "text": "Promenade sur les galets et les huit hectares de pelouses. En été, le Point Plage propose selon la météo kayak, paddle, voile et autres activités.",
        "official": "https://www.dieppetourisme.com/decouvrir/sevader-le-long-des-plages/dieppe/",
        "map": "Plage de Dieppe",
    },
    {
        "icon": "🏰",
        "title": "Château-Musée de Dieppe",
        "time": "18 à 25 min à pied",
        "text": "Montez pour le panorama, puis découvrez les collections consacrées à l’histoire, aux arts et à la vocation maritime de Dieppe. La montée est soutenue mais la vue la récompense.",
        "official": "https://www.dieppetourisme.com/bouger/visiter/musee-de-dieppe-chateau-dieppe-fr-3027618/",
        "map": "Musée de Dieppe Château, rue de Chastes",
    },
    {
        "icon": "🇨🇦",
        "title": "Mémorial du 19 août 1942",
        "time": "15 à 20 min à pied",
        "text": "Dans l’ancien théâtre municipal, archives, objets et témoignages retracent l’opération Jubilee et les liens profonds entre Dieppe et le Canada.",
        "official": "https://www.dieppetourisme.com/bouger/visiter/memorial-du-19-aout-1942-dieppe-fr-3027820/",
        "map": "Mémorial du 19 août 1942, Dieppe",
    },
]

FARTHER = [
    {
        "icon": "🎨",
        "title": "Varengeville : église Saint-Valéry et cimetière marin",
        "time": "Environ 20 min en voiture",
        "text": "Notre priorité hors de Dieppe : panorama sur les falaises, vitrail de Georges Braque, tombe du peintre et paysages associés à Claude Monet.",
        "official": "https://www.dieppetourisme.com/bouger/visiter/eglise-saint-valery-et-cimetiere-marin-varengeville-sur-mer-fr-3027684/",
        "map": "Église Saint-Valéry et cimetière marin, Varengeville-sur-Mer",
    },
    {
        "icon": "🌺",
        "title": "Jardin Shamrock",
        "time": "Environ 20 min en voiture",
        "text": "À choisir pendant la belle saison pour sa collection nationale d’hydrangéas : environ 1 500 plantes différentes dans un jardin d’inspiration anglaise.",
        "official": "https://www.dieppetourisme.com/bouger/visiter/jardin-shamrock-varengeville-sur-mer-fr-3027531/",
        "map": "Jardin Shamrock, Varengeville-sur-Mer",
    },
    {
        "icon": "🏡",
        "title": "Château et potager de Miromesnil",
        "time": "Environ 20 min en voiture",
        "text": "Une demi-journée patrimoine et jardins : demeure des XVIe et XVIIe siècles, lieu de naissance de Guy de Maupassant, parc, chapelle et potager remarquable.",
        "official": "https://www.dieppetourisme.com/bouger/visiter/chateau-et-potager-de-miromesnil-tourville-sur-arques-fr-3027564/",
        "map": "Château de Miromesnil, Tourville-sur-Arques",
    },
    {
        "icon": "🌳",
        "title": "Offranville et parc William Farcy",
        "time": "Environ 20 min en voiture",
        "text": "Un village agréable à combiner avec le parc floral, le clocher tors et une balade sur l’ancienne voie ferrée aménagée pour les mobilités douces.",
        "official": "https://www.dieppetourisme.com/decouvrir/prendre-lair/decouverte-des-villages-typiques/offranville/",
        "map": "Parc William Farcy, Offranville",
    },
    {
        "icon": "🥾",
        "title": "Cap d’Ailly et plage de Sainte-Marguerite",
        "time": "Environ 25 min en voiture",
        "text": "Pour un bol d’air : landes, mares, falaises et plage. Vérifiez la météo, les marées et l’état des sentiers avant de partir.",
        "official": "https://www.dieppetourisme.com/decouvrir/sevader-le-long-des-plages/sainte-marguerite-sur-mer/",
        "map": "Phare d'Ailly, Sainte-Marguerite-sur-Mer",
    },
    {
        "icon": "🕊️",
        "title": "Cimetière canadien des Vertus et Pourville",
        "time": "Environ 15 à 20 min en voiture",
        "text": "Une étape de mémoire à associer à la plage de Pourville et, selon la saison, au mini-golf du front de mer.",
        "official": "https://www.dieppetourisme.com/bouger/visiter/dieppe-canadian-war-cemetery-dit-cimetiere-canadien-des-vertus-hautot-sur-mer-fr-3027716/",
        "map": "Dieppe Canadian War Cemetery, Hautot-sur-Mer",
    },
]

RESTAURANTS = [
    {
        "title": "Le New Haven",
        "tag": "Poissons & fruits de mer",
        "address": "53 quai Henri IV",
        "why": "Le choix classique face au port pour une cuisine traditionnelle centrée sur les produits régionaux, les poissons et les fruits de mer.",
        "official": "https://www.dieppetourisme.com/sejourner/des-restaurants-pour-tous-les-gouts/tous-les-restaurants/le-new-haven-dieppe-fr-3027652/",
    },
    {
        "title": "Le Jehan Ango – La Pêcherie Dieppoise",
        "tag": "Pêche locale & cuisine maison",
        "address": "20 quai du Carénage",
        "why": "Très pratique près de l’Office de Tourisme, avec une carte principalement consacrée aux poissons et fruits de mer issus de la pêche locale.",
        "official": "https://www.dieppetourisme.com/sejourner/des-restaurants-pour-tous-les-gouts/tous-les-restaurants/le-jehan-ango-la-pecherie-dieppoise-dieppe-fr-6663647/",
    },
    {
        "title": "Bistrot des Barrières",
        "tag": "Cuisine responsable",
        "address": "5–7 arcades de la Poissonnerie",
        "why": "Une bonne option pour les circuits courts : produits de la mer dieppois, légumes biologiques, terrasse et possibilité de plat végétarien.",
        "official": "https://www.dieppetourisme.com/sejourner/des-restaurants-pour-tous-les-gouts/tous-les-restaurants/bistrot-des-barrieres-dieppe-fr-3027568/",
    },
    {
        "title": "Chez Khean",
        "tag": "Cuisine locale & vietnamienne",
        "address": "97 quai Henri IV",
        "why": "À retenir pour un groupe aux goûts variés : spécialités dieppoises, cuisine vietnamienne, terrasse sur le port et option végétarienne.",
        "official": "https://www.dieppetourisme.com/sejourner/des-restaurants-pour-tous-les-gouts/tous-les-restaurants/chez-khean-dieppe-fr-6321632/",
    },
    {
        "title": "Les Ursulines",
        "tag": "Vegan, végétarien & brunch",
        "address": "129 quai Henri IV",
        "why": "L’adresse la plus évidente pour une cuisine végétale : coffee-shop vegan, plats du jour saisonniers, desserts et brunch dominical annoncé.",
        "official": "https://www.dieppetourisme.com/sejourner/des-restaurants-pour-tous-les-gouts/tous-les-restaurants/les-ursulines-dieppe-fr-4303543/",
    },
    {
        "title": "Le Turbot",
        "tag": "Cuisine française traditionnelle",
        "address": "14 quai de la Cale",
        "why": "Une adresse de quai à considérer pour un repas traditionnel dans l’ambiance du port.",
        "official": "https://www.dieppetourisme.com/sejourner/des-restaurants-pour-tous-les-gouts/tous-les-restaurants/le-turbot-dieppe-fr-6689136/",
    },
]

EVENTS = [
    {"start": "2026-08-28", "end": "2026-08-28", "date": "28 août · 17 h–minuit", "title": "Marché nocturne", "place": "Quai Henri IV", "category": "gratuit gastronomie famille", "text": "Artisans, produits du terroir et créations locales au coucher du soleil, juste devant l’appartement.", "url": "https://www.dieppetourisme.com/agenda/marche-nocturne-dieppe-fr-6262501/"},
    {"start": "2026-08-21", "end": "2026-08-30", "date": "21–30 août", "title": "Festival international d’échecs", "place": "Salle des Congrès, Dieppe", "category": "gratuit famille sport", "text": "Le rendez-vous dieppois des joueurs d’échecs, à deux pas de la mer.", "url": "https://www.dieppetourisme.com/agenda/echecs-22eme-festival-international-de-dieppe-dieppe-fr-6254811/"},
    {"start": "2026-08-29", "end": "2026-08-30", "date": "29–30 août", "title": "Stage de voilier habitable", "place": "Cercle de la Voile de Dieppe", "category": "sport mer", "text": "Découverte de la navigation en équipage, sous réserve des disponibilités et de la météo.", "url": "https://www.dieppetourisme.com/agenda/stage-voilier-habitable-dieppe-fr-6499566/"},
    {"start": "2026-09-02", "end": "2026-09-02", "date": "2 septembre · 17 h–18 h 30", "title": "La flore du littoral", "place": "Sainte-Marguerite-sur-Mer", "category": "gratuit nature", "text": "Balade naturaliste sur les plantes adaptées aux falaises, embruns et pelouses littorales. Réservation obligatoire.", "url": "https://www.dieppetourisme.com/agenda/balade-natualiste-la-flore-du-littoral-de-sainte-marguerite-sur-mer-sainte-marguerite-sur-mer-fr-6727479/"},
    {"start": "2026-09-06", "end": "2026-09-06", "date": "6 septembre", "title": "Fête des associations et du sport", "place": "Parc François-Mitterrand", "category": "gratuit famille sport", "text": "Démonstrations et rencontres avec les associations et clubs sportifs dieppois.", "url": "https://www.dieppetourisme.com/agenda/animation-fete-des-associations-et-du-sport-dieppe-fr-6262500/"},
    {"start": "2026-09-12", "end": "2026-09-12", "date": "12 septembre · 14 h–16 h", "title": "Les prairies de fin d’été", "place": "Bois de Rosendal, Dieppe", "category": "gratuit nature famille", "text": "Sortie guidée sur les dernières floraisons, les insectes et les signes de l’automne. Réservation obligatoire.", "url": "https://www.dieppetourisme.com/agenda/sortie-nature-les-prairies-de-fin-dete-dieppe-fr-6332620/"},
    {"start": "2026-09-18", "end": "2026-09-19", "date": "18–19 septembre · 19 h 30", "title": "Festival La Machine à Boujoux", "place": "Neuville-lès-Dieppe", "category": "musique festival", "text": "Deux soirées de musiques indépendantes : rock, punk, post-punk, shoegaze et autres scènes alternatives.", "url": "https://www.dieppetourisme.com/agenda/festival-la-machine-a-boujoux-dieppe-fr-6555662/"},
    {"start": "2026-09-19", "end": "2026-09-20", "date": "19–20 septembre", "title": "Journées européennes du patrimoine", "place": "Divers lieux à Dieppe et alentour", "category": "gratuit culture famille", "text": "Ouvertures, visites et animations dans des lieux patrimoniaux. Consultez le programme officiel à l’approche du week-end.", "url": "https://www.dieppetourisme.com/agenda/journees-europeennes-du-patrimoine-2026-dieppe-fr-6254787/"},
    {"start": "2026-09-19", "end": "2026-09-19", "date": "19 septembre", "title": "Les Impressionnantes", "place": "Musée de Dieppe", "category": "gratuit culture spectacle", "text": "Spectacle mêlant théâtre, danse, musique et body-painting autour des pionnières de l’impressionnisme.", "url": "https://www.dieppetourisme.com/agenda/spectacle-impressionniste-2026-les-impressionnantes-dieppe-fr-6091782/"},
    {"start": "2026-09-19", "end": "2026-10-31", "date": "19 septembre–31 octobre", "title": "Exposition Véronique Beorchia-Otero", "place": "Tour d’Ivoire, rue de la Barre", "category": "gratuit culture exposition", "text": "Sculptures et créations en céramique, du jeudi au samedi selon les horaires publiés par l’organisateur.", "url": "https://www.dieppetourisme.com/agenda/exposition-veronique-beorchia-otero-dieppe-fr-6680172/"},
    {"start": "2026-09-25", "end": "2026-11-08", "date": "25 septembre–8 novembre", "title": "Grande Roue", "place": "Quai Henri IV", "category": "famille attraction", "text": "Panorama sur le port, le château, les falaises et le littoral depuis une grande roue installée sur le quai.", "url": "https://www.dieppetourisme.com/agenda/attraction-grande-roue-dieppe-fr-6252518/"},
    {"start": "2026-09-27", "end": "2026-09-27", "date": "27 septembre · 9 h–18 h", "title": "Marché à la brocante et collections", "place": "Front de mer", "category": "gratuit famille marché", "text": "Une journée de chine auprès d’exposants professionnels sur le boulevard du front de mer.", "url": "https://www.dieppetourisme.com/agenda/marche-a-la-brocante-et-collections-dieppe-fr-6323698/"},
    {"start": "2026-09-27", "end": "2026-09-27", "date": "27 septembre · 14 h–16 h", "title": "Découverte du Cap d’Ailly", "place": "Sainte-Marguerite-sur-Mer", "category": "gratuit nature famille", "text": "Balade guidée dans les landes et mares du Cap d’Ailly. Réservation obligatoire auprès de l’Office de Tourisme.", "url": "https://www.dieppetourisme.com/agenda/balade-nature-decouverte-du-site-remarquable-du-cap-dailly-sainte-marguerite-sur-mer-fr-6727465/"},
    {"start": "2026-10-10", "end": "2026-10-11", "date": "10–11 octobre", "title": "Dieppe Festi-Vintage & Rallye historique", "place": "Pelouses et front de mer", "category": "gratuit famille festival automobile", "text": "Véhicules anciens, campement, concerts, animations et rallye historique sur les routes de la région.", "url": "https://www.dieppetourisme.com/agenda/festival-dieppe-festi-vintage-dieppe-fr-6231506/"},
    {"start": "2026-10-21", "end": "2026-10-21", "date": "21 octobre · 14 h 30–16 h", "title": "Visite familiale de Miromesnil", "place": "Château de Miromesnil", "category": "famille culture", "text": "Visite sensorielle adaptée aux enfants, avec découverte du château et passage par le potager. Réservation conseillée.", "url": "https://www.dieppetourisme.com/agenda/visite-famille-visite-familiale-du-chateau-de-miromesnil-tourville-sur-arques-fr-6305134/"},
    {"start": "2026-11-14", "end": "2026-11-15", "date": "14–15 novembre", "title": "Foire aux Harengs et à la Coquille Saint-Jacques", "place": "Quai Henri IV", "category": "gratuit gastronomie famille festival", "text": "La grande fête maritime de l’automne : dégustations, marché, animations et ambiance populaire directement sur le quai.", "url": "https://www.dieppetourisme.com/agenda/evenement-56eme-foire-aux-harengs-et-a-la-coquille-saint-jacques-dieppe-fr-6206183/"},
]

OFFICE_SCHEMA = {
    "@type": "TouristInformationCenter",
    "@id": BASE + "/decouvrir-dieppe.html#office-tourisme",
    "name": "Office de Tourisme Dieppe-Normandie",
    "url": OFFICE_URL,
    "telephone": "+33 2 32 14 40 60",
    "email": "contact@dieppetourisme.com",
    "address": {"@type": "PostalAddress", "streetAddress": "Pont Jehan Ango – Quai du Carénage", "postalCode": "76200", "addressLocality": "Dieppe", "addressCountry": "FR"},
}


def maps_url(query: str) -> str:
    return "https://www.google.com/maps/search/?api=1&query=" + quote_plus(query)


def external_button(url: str, label: str, primary: bool = False) -> str:
    cls = "btn btn-primary" if primary else "btn btn-outline"
    return f'<a class="{cls}" href="{escape(url, quote=True)}" rel="external noopener" target="_blank">{escape(label)}</a>'


def activity_cards(items: list[dict[str, str]]) -> str:
    cards = []
    for item in items:
        cards.append(
            f'''<article class="card local-card">
                <div class="icon" aria-hidden="true">{item["icon"]}</div>
                <p class="local-time">{escape(item["time"])}</p>
                <h3>{escape(item["title"])}</h3>
                <p>{escape(item["text"])}</p>
                <div class="mini-actions">
                    <a href="{escape(item["official"], quote=True)}" rel="external noopener" target="_blank">Infos officielles</a>
                    <a href="{escape(maps_url(item["map"]), quote=True)}" rel="external noopener" target="_blank">Itinéraire</a>
                </div>
            </article>'''
        )
    return "".join(cards)


def restaurant_cards() -> str:
    cards = []
    for item in RESTAURANTS:
        cards.append(
            f'''<article class="card restaurant-card">
                <p class="local-tag">{escape(item["tag"])}</p>
                <h3>{escape(item["title"])}</h3>
                <p class="local-address">{escape(item["address"])}</p>
                <p>{escape(item["why"])}</p>
                <div class="mini-actions">
                    <a href="{escape(item["official"], quote=True)}" rel="external noopener" target="_blank">Fiche officielle</a>
                    <a href="{escape(maps_url(item["title"] + ", Dieppe"), quote=True)}" rel="external noopener" target="_blank">Carte</a>
                </div>
            </article>'''
        )
    return "".join(cards)


def event_cards() -> str:
    cards = []
    for event in EVENTS:
        cards.append(
            f'''<article class="card event-card" data-category="{escape(event["category"], quote=True)}" data-event-end="{event["end"]}">
                <p class="event-date">{escape(event["date"])}</p>
                <h3>{escape(event["title"])}</h3>
                <p class="event-place">{escape(event["place"])}</p>
                <p>{escape(event["text"])}</p>
                <a class="event-link" href="{escape(event["url"], quote=True)}" rel="external noopener" target="_blank">Consulter la fiche officielle</a>
            </article>'''
        )
    return "".join(cards)


GUIDE_MAIN = f'''<main id="contenu">
<section class="page-hero"><div class="wrap">
<div class="breadcrumbs"><a href="/">Accueil</a> / Découvrir Dieppe</div>
<div class="eyebrow">Le carnet d’adresses des Oratoriens</div>
<h1>Que faire et où manger autour de l’appartement</h1>
<p class="lead">Une sélection pensée depuis le 31–33 quai Henri IV : les incontournables accessibles à pied, les excursions qui valent le détour et des restaurants adaptés à différentes envies.</p>
</div></section>
<section class="section" id="office-tourisme"><div class="wrap two">
<div><div class="eyebrow">À quelques minutes du logement</div><h2>Office de Tourisme Dieppe-Normandie</h2>
<p class="lead">L’équipe peut préparer un programme personnalisé, réserver certaines visites et fournir cartes, brochures et conseils selon la météo.</p>
<div class="contact-list"><p><strong>Adresse</strong><br/>Pont Jehan Ango – Quai du Carénage<br/>76200 Dieppe</p><p><strong>Téléphone</strong><br/><a href="tel:+33232144060">02 32 14 40 60</a></p><p><strong>Courriel</strong><br/><a href="mailto:contact@dieppetourisme.com">contact@dieppetourisme.com</a></p></div>
<div class="actions">{external_button(OFFICE_URL, "Site et horaires officiels", True)}{external_button(maps_url("Office de Tourisme Dieppe-Normandie, Pont Jehan Ango"), "Itinéraire")}</div></div>
<aside class="card office-card"><p class="local-tag">Horaires publiés pour 2026</p><h3>Avant de vous déplacer</h3><ul>
<li><strong>Jusqu’au 30 août :</strong> lundi–samedi 9 h–13 h et 14 h–19 h ; dimanche et jours fériés 9 h–13 h et 14 h–18 h.</li>
<li><strong>31 août–26 septembre :</strong> lundi–samedi 9 h–13 h et 14 h–18 h ; dimanche 9 h–13 h et 14 h–17 h.</li>
<li><strong>28 septembre–31 décembre :</strong> lundi–samedi 9 h–13 h et 14 h–17 h ; fermeture habituelle le dimanche, sauf exceptions annoncées.</li></ul>
<p class="notice">Les horaires peuvent changer : vérifiez toujours la page officielle le jour de votre visite.</p></aside>
</div></section>
<section class="section section-alt" id="a-pied"><div class="wrap"><div class="eyebrow">Sans voiture</div><h2>Nos incontournables autour du quai Henri IV</h2><p class="lead">Les temps de marche sont indicatifs et varient selon votre rythme. Le château est plus éloigné et nécessite une montée.</p><div class="local-grid">{activity_cards(NEARBY)}</div></div></section>
<section class="section"><div class="wrap"><div class="eyebrow">Selon votre programme</div><h2>Trois itinéraires simples</h2><div class="card-grid">
<article class="card"><div class="icon" aria-hidden="true">👨‍👩‍👧‍👦</div><h3>En famille ou sous la pluie</h3><p>ESTRAN – Cité de la Mer, déjeuner sur le port, puis Château-Musée ou jeu de piste autour de Jehan Ango.</p></article>
<article class="card"><div class="icon" aria-hidden="true">🏛️</div><h3>Histoire et patrimoine</h3><p>Église Saint-Jacques, centre reconstruit, Mémorial du 19 août 1942, puis panorama du château.</p></article>
<article class="card"><div class="icon" aria-hidden="true">🌅</div><h3>Grand air et bord de mer</h3><p>Marché du matin, plage et pelouses, balade en rosalie ou activité nautique, puis coucher de soleil sur le quai.</p></article>
</div></div></section>
<section class="section section-alt" id="alentours"><div class="wrap"><div class="eyebrow">À explorer en voiture</div><h2>Les meilleurs détours dans les environs</h2><p class="lead">Les durées sont des estimations hors circulation. Regroupez Varengeville, Shamrock et Sainte-Marguerite sur une même journée.</p><div class="local-grid">{activity_cards(FARTHER)}</div></div></section>
<section class="section" id="restaurants"><div class="wrap"><div class="eyebrow">À table</div><h2>Nos restaurants recommandés autour du port</h2><p class="lead">Cette sélection privilégie la proximité, la variété et l’identité locale ; ce n’est pas un classement exhaustif. Réservez et vérifiez les jours d’ouverture, surtout le dimanche et hors saison.</p><div class="local-grid restaurant-grid">{restaurant_cards()}</div><div class="actions">{external_button(RESTAURANTS_URL, "Voir l’annuaire officiel des restaurants", True)}<a class="btn btn-outline" href="/agenda-dieppe.html">Voir les manifestations</a></div></div></section>
<section class="section section-alt"><div class="wrap two"><div><div class="eyebrow">Le conseil des Oratoriens</div><h2>Adaptez la journée à la météo et aux marées</h2><p>À Dieppe, une bonne journée peut alterner patrimoine, marché, promenade et produits de la mer. Pour les falaises, plages et activités nautiques, vérifiez toujours les conditions, les marées et les éventuelles restrictions d’accès.</p></div>
<div class="card"><h3>Liens pratiques</h3><p><a href="{AGENDA_URL}" rel="external noopener" target="_blank">Agenda officiel Dieppe-Normandie</a><br/><a href="https://www.dieppetourisme.com/sejourner/pratique/plans-brochures/" rel="external noopener" target="_blank">Plans et brochures</a><br/><a href="https://www.dieppetourisme.com/sejourner/pratique/se-deplacer/" rel="external noopener" target="_blank">Se déplacer dans la destination</a></p></div></div></section>
</main>'''

AGENDA_MAIN = f'''<main id="contenu">
<section class="page-hero"><div class="wrap"><div class="breadcrumbs"><a href="/">Accueil</a> / Agenda</div><div class="eyebrow">Dieppe et ses environs</div><h1>Calendrier des manifestations</h1><p class="lead">Les rendez-vous marquants autour du port, du centre-ville et des communes voisines. Les événements terminés sont masqués automatiquement.</p></div></section>
<section class="section"><div class="wrap two"><div><div class="eyebrow">La source de référence</div><h2>L’agenda officiel Dieppe-Normandie</h2><p class="lead">La programmation évolue toute l’année. Pour les horaires de dernière minute, les réservations et les annulations, consultez toujours la fiche officielle de l’événement.</p><div class="actions">{external_button(AGENDA_URL, "Ouvrir tout l’agenda officiel", True)}<a class="btn btn-outline" href="/decouvrir-dieppe.html">Activités & restaurants</a></div></div>
<aside class="card"><p class="local-tag">Rendez-vous récurrents</p><h3>Les marchés du centre</h3><ul><li><strong>Mardi et jeudi, 8 h 30–12 h 30 :</strong> petit marché, place Nationale.</li><li><strong>Samedi, 8 h 30–13 h :</strong> grand marché dans le centre-ville.</li><li><strong>Samedi, 13 h–17 h :</strong> marchands ambulants, Grande Rue et place Nationale.</li><li><strong>Marché aux poissons :</strong> autour du Pont Ango, selon les marées, la météo et les arrivages.</li></ul></aside></div></section>
<section class="section section-alt" id="manifestations"><div class="wrap"><div class="eyebrow">Sélection mise à jour le 28 août 2026</div><h2>Les prochains rendez-vous</h2>
<div class="event-filters" aria-label="Filtrer les événements"><button class="filter-button is-active" type="button" data-filter="all">Tout</button><button class="filter-button" type="button" data-filter="gratuit">Gratuit</button><button class="filter-button" type="button" data-filter="famille">Famille</button><button class="filter-button" type="button" data-filter="culture">Culture</button><button class="filter-button" type="button" data-filter="nature">Nature</button><button class="filter-button" type="button" data-filter="gastronomie">Gastronomie</button></div>
<p id="event-status" class="event-status" aria-live="polite"></p><div class="local-grid event-grid">{event_cards()}</div><div class="notice event-empty" hidden><strong>Aucun événement de cette sélection ne reste à venir.</strong><br/>La programmation complète et actualisée reste disponible sur l’agenda officiel Dieppe-Normandie.</div></div></section>
<section class="section"><div class="wrap two"><div><div class="eyebrow">À ne pas manquer</div><h2>Les grands temps forts depuis l’appartement</h2><p><strong>La Foire aux Harengs et à la Coquille Saint-Jacques</strong> se déroule directement sur le quai Henri IV : l’appartement est au cœur de l’événement. La Grande Roue, les marchés nocturnes et plusieurs animations portuaires sont également organisés à quelques mètres.</p></div>
<div class="card"><h3>Conseils pratiques</h3><ul><li>Réservez les sorties nature et visites à jauge limitée.</li><li>Prévoyez davantage de temps pour circuler lors des grands événements.</li><li>Vérifiez le stationnement, la météo et les horaires le jour même.</li></ul></div></div></section>
</main>'''

AGENDA_JS = r'''
<script>
(() => {
  const cards = [...document.querySelectorAll(".event-card")];
  const buttons = [...document.querySelectorAll("[data-filter]")];
  const empty = document.querySelector(".event-empty");
  const status = document.querySelector("#event-status");
  let active = "all";
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  function refresh() {
    let visible = 0;
    cards.forEach((card) => {
      const end = new Date(`${card.dataset.eventEnd}T23:59:59`);
      const upcoming = end >= today;
      const categories = (card.dataset.category || "").split(/\s+/);
      const matches = active === "all" || categories.includes(active);
      card.hidden = !(upcoming && matches);
      if (!card.hidden) visible += 1;
    });
    if (empty) empty.hidden = visible !== 0;
    if (status) status.textContent = `${visible} événement${visible > 1 ? "s" : ""} affiché${visible > 1 ? "s" : ""}.`;
  }
  buttons.forEach((button) => {
    button.addEventListener("click", () => {
      active = button.dataset.filter || "all";
      buttons.forEach((item) => {
        const selected = item === button;
        item.classList.toggle("is-active", selected);
        item.setAttribute("aria-pressed", String(selected));
      });
      refresh();
    });
  });
  refresh();
})();
</script>'''

CSS = r'''
/* local-guide-v1 */
.local-grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:1.15rem;margin-top:1.6rem}
.local-card,.restaurant-card,.event-card{display:flex;flex-direction:column;min-height:100%}
.local-card h3,.restaurant-card h3,.event-card h3{margin:.2rem 0 .55rem}
.local-time,.local-tag,.event-date{display:inline-flex;align-self:flex-start;margin:0 0 .45rem;padding:.28rem .62rem;border-radius:999px;background:#eef3f2;color:#18343e;font-size:.82rem;font-weight:750;letter-spacing:.015em}
.local-tag{background:#f5ead8;color:#694817}
.local-address,.event-place{font-weight:700;color:#35515a;margin:.05rem 0 .6rem}
.mini-actions{display:flex;flex-wrap:wrap;gap:.75rem;margin-top:auto;padding-top:.9rem}
.mini-actions a,.event-link{font-weight:750;text-decoration:underline;text-underline-offset:3px}
.contact-list{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:.8rem;margin:1.3rem 0}
.contact-list p{margin:0;padding:1rem;border:1px solid rgba(24,52,62,.16);border-radius:14px;background:#fff}
.office-card ul,.event-card ul{padding-left:1.15rem}
.restaurant-grid{grid-template-columns:repeat(3,minmax(0,1fr))}
.event-filters{display:flex;flex-wrap:wrap;gap:.55rem;margin:1.1rem 0}
.filter-button{border:1px solid #18343e;background:#fff;color:#18343e;border-radius:999px;padding:.55rem .9rem;font:inherit;font-weight:750;cursor:pointer}
.filter-button:hover,.filter-button:focus-visible,.filter-button.is-active{background:#18343e;color:#fff}
.event-status{min-height:1.5rem;color:#4e6269;font-weight:650}
.event-card[hidden]{display:none}
.event-link{margin-top:auto;padding-top:.9rem}
.event-empty{margin-top:1.25rem}
#local-guide-home .card-grid{margin-top:1.2rem}
@media(max-width:980px){.local-grid,.restaurant-grid{grid-template-columns:repeat(2,minmax(0,1fr))}.contact-list{grid-template-columns:1fr}}
@media(max-width:640px){.local-grid,.restaurant-grid{grid-template-columns:1fr}.event-filters{overflow-x:auto;flex-wrap:nowrap;padding-bottom:.3rem}.filter-button{white-space:nowrap}}
'''


def schema_for_guide() -> dict:
    items = []
    position = 1
    for item in NEARBY + FARTHER:
        items.append({"@type": "ListItem", "position": position, "item": {"@type": "TouristAttraction", "name": item["title"], "url": item["official"]}})
        position += 1
    for item in RESTAURANTS:
        items.append({"@type": "ListItem", "position": position, "item": {"@type": "Restaurant", "name": item["title"], "address": item["address"] + ", 76200 Dieppe", "url": item["official"]}})
        position += 1
    return {"@context": "https://schema.org", "@graph": [{"@type": "WebPage", "@id": BASE + "/decouvrir-dieppe.html#webpage", "url": BASE + "/decouvrir-dieppe.html", "name": "Que faire à Dieppe : activités, restaurants et excursions", "inLanguage": "fr-FR"}, OFFICE_SCHEMA, {"@type": "ItemList", "name": "Activités et restaurants recommandés autour des Oratoriens Henri IV", "itemListElement": items}]}


def schema_for_agenda() -> dict:
    event_nodes = []
    for event in EVENTS:
        event_nodes.append({"@type": "Event", "name": event["title"], "startDate": event["start"], "endDate": event["end"], "eventStatus": "https://schema.org/EventScheduled", "eventAttendanceMode": "https://schema.org/OfflineEventAttendanceMode", "location": {"@type": "Place", "name": event["place"], "address": {"@type": "PostalAddress", "addressLocality": "Dieppe", "addressRegion": "Normandie", "addressCountry": "FR"}}, "url": event["url"]})
    return {"@context": "https://schema.org", "@graph": [{"@type": "WebPage", "@id": BASE + "/agenda-dieppe.html#webpage", "url": BASE + "/agenda-dieppe.html", "name": "Agenda des manifestations à Dieppe et ses environs", "inLanguage": "fr-FR", "dateModified": "2026-08-28"}, *event_nodes]}


def set_metadata(soup: BeautifulSoup, title: str, description: str, canonical: str, schema: dict) -> None:
    head = soup.head
    if head is None:
        head = soup.new_tag("head")
        soup.html.insert(0, head)
    if soup.title:
        soup.title.string = title
    else:
        tag = soup.new_tag("title")
        tag.string = title
        head.append(tag)
    for tag in list(head.find_all("meta")):
        if tag.get("name") in {"description", "robots"} or tag.get("property", "").startswith("og:") or tag.get("name", "").startswith("twitter:"):
            tag.decompose()
    for tag in list(head.find_all("link", rel="canonical")):
        tag.decompose()
    for tag in list(head.find_all("script", attrs={"type": "application/ld+json"})):
        tag.decompose()
    desc = soup.new_tag("meta")
    desc["name"] = "description"
    desc["content"] = description
    head.append(desc)
    robots = soup.new_tag("meta")
    robots["name"] = "robots"
    robots["content"] = "index,follow,max-image-preview:large,max-snippet:-1,max-video-preview:-1"
    head.append(robots)
    canon = soup.new_tag("link")
    canon["rel"] = "canonical"
    canon["href"] = canonical
    head.append(canon)
    for prop, content in (("og:type", "website"), ("og:site_name", "Oratoriens Henri IV Dieppe"), ("og:locale", "fr_FR"), ("og:title", title), ("og:description", description), ("og:url", canonical)):
        tag = soup.new_tag("meta")
        tag["property"] = prop
        tag["content"] = content
        head.append(tag)
    structured = soup.new_tag("script")
    structured["type"] = "application/ld+json"
    structured.string = json.dumps(schema, ensure_ascii=False, separators=(",", ":"))
    head.append(structured)


def clone_page(root: Path, filename: str, main_html: str, title: str, description: str, schema: dict, extra_script: str = "") -> None:
    template = root / "informations.html"
    if not template.exists():
        raise SystemExit(f"Modèle introuvable : {template}")
    soup = BeautifulSoup(template.read_text(encoding="utf-8"), "html.parser")
    old_main = soup.find("main", id="contenu") or soup.find("main")
    new_main = BeautifulSoup(main_html, "html.parser").find("main")
    if old_main is None or new_main is None:
        raise SystemExit("Structure HTML du modèle non reconnue")
    old_main.replace_with(new_main)
    if extra_script and soup.body:
        fragment = BeautifulSoup(extra_script, "html.parser")
        for child in list(fragment.contents):
            soup.body.append(child)
    set_metadata(soup, title, description, BASE + "/" + filename, schema)
    (root / filename).write_text(str(soup), encoding="utf-8")


def patch_navigation(root: Path) -> None:
    for path in root.rglob("*.html"):
        soup = BeautifulSoup(path.read_text(encoding="utf-8"), "html.parser")
        changed = False
        is_en = "/en/" in path.as_posix()
        menu = soup.select_one(".menu")
        if menu:
            wanted = [("/decouvrir-dieppe.html", "Local guide" if is_en else "Découvrir"), ("/agenda-dieppe.html", "Events" if is_en else "Agenda")]
            hrefs = {a.get("href") for a in menu.find_all("a")}
            booking = next((a for a in menu.find_all("a") if a.get_text(" ", strip=True).lower() in {"réserver", "book"} or "booking" in (a.get("href") or "").lower() or "airbnb" in (a.get("href") or "").lower()), None)
            for href, label in wanted:
                if href in hrefs:
                    continue
                link = soup.new_tag("a", href=href)
                link.string = label
                if booking:
                    booking.insert_before(link)
                else:
                    menu.append(link)
                changed = True
        footer_block = None
        for block in soup.select(".footer-grid > div"):
            strong = block.find("strong")
            if strong and strong.get_text(" ", strip=True).lower() in {"informations", "information"}:
                footer_block = block
                break
        if footer_block:
            paragraph = footer_block.find("p") or soup.new_tag("p")
            if paragraph.parent is None:
                footer_block.append(paragraph)
            footer_links = [("/decouvrir-dieppe.html", "Local guide" if is_en else "Découvrir Dieppe"), ("/agenda-dieppe.html", "Events calendar" if is_en else "Agenda des manifestations")]
            existing = {a.get("href") for a in paragraph.find_all("a")}
            for href, label in footer_links:
                if href in existing:
                    continue
                paragraph.append(soup.new_tag("br"))
                a = soup.new_tag("a", href=href)
                a.string = label
                paragraph.append(a)
                changed = True
        if changed:
            path.write_text(str(soup), encoding="utf-8")


def patch_home(root: Path) -> None:
    path = root / "index.html"
    if not path.exists():
        return
    soup = BeautifulSoup(path.read_text(encoding="utf-8"), "html.parser")
    main = soup.find("main", id="contenu") or soup.find("main")
    if main is None or soup.find(id="local-guide-home"):
        return
    section_html = '''<section class="section section-alt" id="local-guide-home"><div class="wrap"><div class="eyebrow">Votre séjour à Dieppe</div><h2>Activités, restaurants et manifestations</h2><p class="lead">Préparez chaque journée depuis le quai Henri IV grâce à notre sélection d’adresses accessibles à pied, d’excursions et de rendez-vous locaux.</p><div class="card-grid"><article class="card"><div class="icon" aria-hidden="true">🧭</div><h3>Découvrir Dieppe</h3><p>Office de Tourisme, incontournables, excursions, restaurants et conseils selon la météo.</p><a class="btn btn-primary" href="/decouvrir-dieppe.html">Ouvrir le guide local</a></article><article class="card"><div class="icon" aria-hidden="true">📅</div><h3>Agenda des manifestations</h3><p>Marchés, festivals, sorties nature, patrimoine et grands rendez-vous du quai Henri IV.</p><a class="btn btn-primary" href="/agenda-dieppe.html">Consulter l’agenda</a></article></div></div></section>'''
    section = BeautifulSoup(section_html, "html.parser").find("section")
    sections = main.find_all("section", recursive=False)
    if sections:
        sections[-1].insert_before(section)
    else:
        main.append(section)
    path.write_text(str(soup), encoding="utf-8")


def patch_css(root: Path) -> None:
    path = root / "assets/css/site.css"
    if not path.exists():
        return
    text = path.read_text(encoding="utf-8")
    if "/* local-guide-v1 */" not in text:
        path.write_text(text.rstrip() + "\n" + CSS.strip() + "\n", encoding="utf-8")


def patch_sitemap(root: Path) -> None:
    path = root / "sitemap.xml"
    if not path.exists():
        return
    text = path.read_text(encoding="utf-8")
    today = date.today().isoformat()
    additions = []
    for url, freq in ((BASE + "/decouvrir-dieppe.html", "monthly"), (BASE + "/agenda-dieppe.html", "weekly")):
        if f"<loc>{url}</loc>" not in text:
            additions.append(f"<url><loc>{url}</loc><lastmod>{today}</lastmod><changefreq>{freq}</changefreq></url>")
    if additions:
        path.write_text(text.replace("</urlset>", "\n" + "\n".join(additions) + "\n</urlset>"), encoding="utf-8")


def refresh_new_page_metadata(root: Path) -> None:
    pages = [
        ("decouvrir-dieppe.html", "Que faire à Dieppe : activités & restaurants | Oratoriens", "Office de Tourisme, activités à pied, excursions et restaurants recommandés autour de l’appartement Oratoriens Henri IV à Dieppe.", schema_for_guide()),
        ("agenda-dieppe.html", "Agenda Dieppe 2026 : manifestations & événements | Oratoriens", "Calendrier des manifestations à Dieppe et dans les environs : marchés, festivals, sorties nature, patrimoine et événements du quai Henri IV.", schema_for_agenda()),
    ]
    for filename, title, description, schema in pages:
        path = root / filename
        if not path.exists():
            continue
        soup = BeautifulSoup(path.read_text(encoding="utf-8"), "html.parser")
        set_metadata(soup, title, description, BASE + "/" + filename, schema)
        path.write_text(str(soup), encoding="utf-8")


def main() -> int:
    if len(sys.argv) < 2:
        raise SystemExit("Usage: local_guide.py <site-root> [--finalize]")
    root = Path(sys.argv[1]).resolve()
    finalize = "--finalize" in sys.argv[2:]
    if not root.exists():
        raise SystemExit(f"Racine du site introuvable : {root}")
    if not finalize:
        clone_page(root, "decouvrir-dieppe.html", GUIDE_MAIN, "Que faire à Dieppe : activités & restaurants | Oratoriens", "Office de Tourisme, activités à pied, excursions et restaurants recommandés autour de l’appartement Oratoriens Henri IV à Dieppe.", schema_for_guide())
        clone_page(root, "agenda-dieppe.html", AGENDA_MAIN, "Agenda Dieppe 2026 : manifestations & événements | Oratoriens", "Calendrier des manifestations à Dieppe et dans les environs : marchés, festivals, sorties nature, patrimoine et événements du quai Henri IV.", schema_for_agenda(), AGENDA_JS)
        patch_home(root)
    patch_navigation(root)
    patch_css(root)
    refresh_new_page_metadata(root)
    patch_sitemap(root)
    print(f"Guide local et agenda ajoutés dans {root} (finalize={finalize}).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

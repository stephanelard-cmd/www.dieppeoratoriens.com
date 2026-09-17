# Oratoriens Henri IV — Dieppe

Dépôt du site officiel **https://dieppeoratoriens.com**. Le nom technique du dépôt est `www.dieppeoratoriens.com`, mais le domaine public reste `dieppeoratoriens.com`.

## Déploiement

Le site est publié par GitHub Actions. Le workflow :

- reconstruit le paquet source vérifié par SHA-256 ;
- récupère les périodes occupées des calendriers Booking.com et Airbnb ;
- optimise les photographies ;
- publie le site sur GitHub Pages ;
- s’exécute à chaque modification et toutes les 15 minutes.

## Secrets requis

Deux secrets Actions doivent être définis dans les paramètres du dépôt :

- `AIRBNB_ICAL_URL`
- `BOOKING_ICAL_URL`

Les URL iCal privées ne doivent jamais être enregistrées dans un fichier du dépôt. Tant que les deux secrets ne sont pas présents, le site reste publiable mais le calendrier indique clairement que la synchronisation est en cours d’activation. Si une source échoue après configuration, le nouveau déploiement est interrompu et la dernière version valide reste en ligne.

## Domaine

Le fichier `CNAME` contenu dans le site déclare `dieppeoratoriens.com`. La zone DNS est gérée chez OVHcloud.

## Classement

Le site présente la décision SMTR du 17 septembre 2026 : 2 étoiles pour une capacité classée de 2 personnes, après visite favorable du 16 septembre. Elle prévoit cinq ans et un délai de refus de 15 jours après réception. La date de réception n’étant pas documentée, aucune date d’acquisition ou d’expiration précise ni balise `starRating` inconditionnelle n’est inventée. Le classement est distinct de la capacité commerciale des annonces, jusqu’à 5 voyageurs.

La grille 2026 mesure 31 m² hors salle d’eau et WC (studio 25 m², mezzanine 6 m²), avec 149/154 points obligatoires et 78 points à la carte pour 29 requis. Le ventilateur de plafond ne doit pas être décrit comme une climatisation. Les critères lave-linge/sèche-linge sont non applicables, sans constat d’absence. Les services de linge et ménage sont proposés, sans promesse de gratuité.

Les contenus publics français, anglais, allemands et espagnols sont dans `.github/scripts/classification_2026.json`. Le script `classification_2026.py` les applique **après** la génération multilingue à chaque construction, pour empêcher la réapparition du classement de 2019. Il actualise les pages, métadonnées, données structurées, adresse et dates éditoriales du sitemap, puis vérifie les 20 pages principales. Contrôle séparé : `python .github/scripts/classification_2026.py _site --check`.

Les PDF sources contiennent des coordonnées privées et ne sont pas publiés. La page de classement en donne une synthèse factuelle. L’ancien classement de 2019 reste mentionné uniquement à titre historique sur cette page.

<!-- Diagnostic temporaire du déploiement GitHub Pages, 21 août 2026. -->
<!-- Contrôle ponctuel de la synchronisation des calendriers, 21 août 2026. -->

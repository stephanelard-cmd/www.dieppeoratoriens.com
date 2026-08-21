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

Le site distingue la capacité actuellement affichée sur les plateformes, jusqu’à 5 voyageurs, de l’ancien classement 2 étoiles attribué en 2019 pour 4 personnes et arrivé à échéance le 31 octobre 2024.

<!-- Diagnostic temporaire du déploiement GitHub Pages, 21 août 2026. -->

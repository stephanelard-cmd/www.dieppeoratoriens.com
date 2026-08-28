# Vérification des calendriers iCal

Les URL iCal Airbnb et Booking.com sont enregistrées exclusivement comme secrets GitHub Actions sous les noms :

- `AIRBNB_ICAL_URL`
- `BOOKING_ICAL_URL`

Le workflow de déploiement doit lire les deux flux, fusionner leurs périodes indisponibles et publier uniquement les dates bloquées dans `assets/data/availability.json`. Aucune URL privée ni donnée nominative ne doit apparaître dans le site public.

Dernière demande de contrôle : 28 août 2026.

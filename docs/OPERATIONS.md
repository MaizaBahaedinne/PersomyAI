# Exploitation

## Créer les deux administrateurs

Chaque administrateur a son propre compte `SUPER_ADMIN`. Aucun mot de passe par défaut n'existe : la commande demande le mot de passe sans l'afficher.

```bash
docker compose exec backend python -m app.cli create-admin --email prenom1@exemple.com --name "Prénom Nom 1"
docker compose exec backend python -m app.cli create-admin --email prenom2@exemple.com --name "Prénom Nom 2" --language en
```

Le mot de passe doit contenir au moins 12 caractères, avec lettres et chiffres. L'opération est enregistrée dans le journal d'audit (`user.bootstrap_admin`, sans mot de passe). Un tableau de bord affiche une alerte tant qu'un seul `SUPER_ADMIN` actif existe.

En cas de perte d'accès des deux administrateurs, créer un nouveau `SUPER_ADMIN` avec la même commande (accès serveur requis).

## Sauvegarde

```bash
./scripts/backup.sh   # backups/persomy-<horodatage>.dump (pg_dump -Fc), 14 dernières conservées
```

À planifier (cron) et à copier hors du VPS. Les fichiers contiennent des données sensibles : permissions `600`, stockage chiffré recommandé.

## Restauration

```bash
./scripts/restore.sh backups/persomy-XXXX.dump
```

Demande de confirmation, sauvegarde de sécurité préalable, arrêt/redémarrage du backend. Tester régulièrement la restauration sur une base de test.

## Supervision

- `docker compose ps` (état et santé), `docker compose logs -f backend` (logs JSON).
- Tableau de bord : état API/base, échecs de connexion 24 h, alertes.
- Journal d'audit dans l'interface (`Administration > Journal d'audit`).

## Incidents courants

| Symptôme | Piste |
| --- | --- |
| 429 à la connexion | Anti force brute actif ; attendre `Retry-After` (15 min max) |
| 403 `origin_not_allowed` | `TRUSTED_ORIGINS` ne contient pas l'origine du navigateur |
| 403 `csrf_invalid` | Cookie `persomy_csrf` absent : se reconnecter |
| Backend `unhealthy` | `docker compose logs backend` (connexion base, migration) |
| Cookie non posé | `COOKIE_SECURE=true` exige HTTPS |

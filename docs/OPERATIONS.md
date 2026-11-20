# Exploitation

## Créer les deux administrateurs

Chaque administrateur a son propre compte `SUPER_ADMIN`. Aucun mot de passe par défaut n'existe : la commande demande le mot de passe sans l'afficher.

```bash
docker compose exec backend python -m app.cli create-admin --email prenom1@exemple.com --name "Prénom Nom 1"
docker compose exec backend python -m app.cli create-admin --email prenom2@exemple.com --name "Prénom Nom 2" --language en
```

Le mot de passe doit contenir au moins 12 caractères, avec lettres et chiffres. L'opération est enregistrée dans le journal d'audit (`user.bootstrap_admin`, sans mot de passe). Un tableau de bord affiche une alerte tant qu'un seul `SUPER_ADMIN` actif existe.

En cas de perte d'accès des deux administrateurs, créer un nouveau `SUPER_ADMIN` avec la même commande (accès serveur requis).

## Injecter les agents business (10 profils)

Depuis le VPS :

```bash
cd /opt/persomy-v2
git pull --ff-only
DOCKER="sudo docker" ./scripts/seed-business-agents.sh
```

Le script est idempotent : il crée les agents manquants et met à jour ceux qui existent deja
(missions, permissions, outils, limites et budgets).
## Sauvegarde

```bash
./scripts/backup.sh   # backups/persomy-<horodatage>.dump (pg_dump -Fc), 14 dernières conservées
DOCKER="sudo docker" ./scripts/backup.sh   # si l'utilisateur n'est pas dans le groupe docker
```

Le script écrit dans un fichier temporaire, vérifie l'archive (`pg_restore --list`) puis la valide : une sauvegarde incomplète n'est jamais conservée. Fichiers en `600`.

### Planification (cron)

Exemple, tous les jours à 03:15 (à adapter au chemin d'installation ; `sudo crontab -e` si Docker exige les droits root) :

```cron
15 3 * * * cd /opt/persomy-v2 && DOCKER=docker ./scripts/backup.sh >> /var/log/persomy-backup.log 2>&1
```

Cette ligne n'a jamais été exécutée sur le VPS : lancer le script à la main une première fois et vérifier le fichier créé avant de planifier. Copier ensuite `backups/` **hors du VPS** (les sauvegardes locales ne protègent pas d'une perte du serveur). Les fichiers contiennent des données sensibles : stockage chiffré recommandé. Sauvegarder aussi `.env`, en particulier `TWO_FACTOR_KEY`, séparément et hors du VPS.

## Authentification à deux facteurs

`TWO_FACTOR_KEY` doit être définie dans `.env` (clé Fernet) :

```bash
docker compose exec backend python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

Recréer le conteneur backend après modification de `.env`. Chaque administrateur active ensuite la 2FA dans Paramètres > Sécurité.

Appareil perdu, codes de secours épuisés, ou clé `TWO_FACTOR_KEY` changée :

```bash
docker compose exec backend python -m app.cli reset-2fa --email prenom@exemple.com
```

La commande désactive la 2FA du compte, supprime ses codes de secours, révoque ses sessions et l'écrit dans l'audit (`auth.2fa_reset`).

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

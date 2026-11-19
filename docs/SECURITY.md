# Sécurité

## Mesures implémentées (testées)

| Sujet | Mise en œuvre |
| --- | --- |
| Mots de passe | Argon2id (`argon2-cffi`), jamais stockés ni journalisés en clair ; 12 caractères minimum avec lettres et chiffres |
| Sessions | Jeton opaque de 256 bits (`secrets`), seule l'empreinte SHA-256 est en base ; durée absolue 12 h, inactivité 120 min (configurables) |
| Cookies | `HttpOnly`, `Secure`, `SameSite=Lax` pour la session ; aucun jeton en `localStorage` |
| CSRF | Jeton par session (empreinte en base) envoyé dans `X-CSRF-Token` + contrôle de l'en-tête `Origin` sur les requêtes modifiantes |
| Force brute | 5 échecs/15 min par compte, 20 par IP ; réponse 429 + `Retry-After` ; message d'erreur identique pour compte inconnu, mot de passe faux ou compte désactivé ; hachage factice pour égaliser les temps |
| Permissions | Rôles `SUPER_ADMIN`, `ADMIN`, `OPERATOR`, `VIEWER` ; permissions contrôlées par dépendance serveur ; l'interface ne fait que masquer |
| Comptes privilégiés | Seul un `SUPER_ADMIN` crée/modifie/désactive un compte `ADMIN` ou `SUPER_ADMIN` ou réinitialise un mot de passe ; auto-modification de rôle/statut interdite ; le dernier `SUPER_ADMIN` actif est protégé |
| Révocation | Désactivation, changement de rôle ou de mot de passe révoquent les sessions |
| Audit | `audit_events` en ajout seul (aucune route de modification), sans secret |
| Validation | Schémas Pydantic stricts, erreurs 422 homogènes |
| Documentation API | Désactivée en production (`APP_ENV=production`) |
| En-têtes | `X-Content-Type-Options`, `X-Frame-Options: DENY`, `Referrer-Policy`, HSTS (Caddy) |
| Infrastructure | PostgreSQL non exposé ; conteneurs applicatifs non-root ; `.env` ignoré par git |
| Agents IA | Identité technique (`agt_…`) sans compte, mot de passe ni session ; créés en DRAFT, autonomie 1, budget 0, aucune permission ni outil ; catalogue de permissions d'agent séparé des permissions humaines (aucune permission d'administration ni de paiement) ; permissions, outils, autonomie et budget réservés au `SUPER_ADMIN` ; configuration JSON refusant les clés de type secret ; révocation d'accès ; suppression limitée aux agents DRAFT/DISABLED ; chaque action auditée |
| Arrêt d'urgence | Un `ADMIN` suspend tous les agents actifs et bloque toute activation ; seul un `SUPER_ADMIN` le lève ; état persisté en base (`system_settings`) et audité |
| Orchestrateur | Validation humaine obligatoire si l'autonomie de l'agent est inférieure à 3 ou si la permission exigée est critique (`email:send`, `social:publish`, permission inconnue = critique) ; règle des quatre yeux pour les tâches critiques (l'approbateur ne peut être ni le créateur ni le demandeur) ; validation à usage unique, effacée par toute modification du contenu ; exécution refusée (et auditée) en cas d'arrêt d'urgence, d'agent non actif, de permission non accordée, de quota journalier dépassé (échecs comptés) ou de budget mensuel épuisé (fournisseurs payants) ; tâche réservée de façon atomique avant l'appel ; erreurs du fournisseur : seul le code est conservé ; l'audit ne contient ni consigne ni résultat |
| Fournisseur IA | Registre vide : aucun appel IA n'est possible tant qu'un fournisseur n'est pas implémenté et configuré (`AI_PROVIDER`) ; rien n'est simulé |

## Initialisation des administrateurs

Aucun mot de passe par défaut. Les comptes sont créés via la CLI interactive (mot de passe saisi sans écho). Voir [OPERATIONS.md](OPERATIONS.md).

## Authentification à deux facteurs

TOTP (RFC 6238 : SHA-1, 6 chiffres, 30 s, tolérance ±1 pas), implémenté avec la bibliothèque standard. Facultatif par compte : **non imposé**, un administrateur qui ne l'active pas n'est pas protégé.

- Secret chiffré en base (Fernet) avec la clé `TWO_FACTOR_KEY` (variable d'environnement). Sans clé valide, la 2FA est indisponible (409 `two_factor_unavailable`) et rien n'est écrit en clair.
- Activation en deux temps (mot de passe, puis code valide) ; l'activation révoque les autres sessions.
- Anti-rejeu : un pas TOTP n'est accepté qu'une fois (mise à jour atomique de `users.two_factor_last_step`).
- 10 codes de secours (`xxxxx-xxxxx`), stockés sous forme d'empreintes SHA-256, usage unique, affichés une seule fois, régénérables.
- Un mauvais code compte comme un échec de connexion (anti force brute, 429). Un mauvais mot de passe ne révèle jamais l'existence de la 2FA.
- Désactivation et régénération exigent mot de passe + code.
- L'audit n'enregistre jamais le secret ni un code (`auth.2fa_setup`, `auth.2fa_enable`, `auth.2fa_disable`, `auth.2fa_recovery_regenerate`, `auth.2fa_reset`, `second_factor` dans `auth.login`).
- Appareil perdu ou clé `TWO_FACTOR_KEY` changée : `python -m app.cli reset-2fa --email …` (accès serveur ; désactive la 2FA, supprime les codes de secours, révoque les sessions, audité).
- **Sauvegarder `TWO_FACTOR_KEY` hors du VPS** : sans elle, les secrets existants sont inutilisables (reprise via `reset-2fa`).
- Limites : pas de QR code (saisie manuelle de la clé), vérifié uniquement avec SQLite en test.

## Risques restants

- Les migrations et l'API n'ont pas été exécutées contre PostgreSQL 17 dans l'environnement de développement (SQLite uniquement) : à vérifier lors de la première installation (voir DEPLOYMENT).
- Docker n'était pas disponible localement : les images et `docker-compose.yml` n'ont pas été construits ni lancés.
- `--forwarded-allow-ips "*"` suppose que le backend n'est joignable que par Caddy/frontend (réseau Docker interne, aucun port publié).
- Pas encore de limitation de débit globale par IP au-delà du login (à traiter côté Caddy ou middleware).
- Le chiffrement des futures clés API (fournisseurs IA) reste à concevoir.
- Pas de rotation/archivage automatique du journal d'audit.
- 2FA facultative (non obligatoire pour les administrateurs) ; récupération de compte uniquement par la CLI (accès serveur).
- Les permissions d'agent sont appliquées par l'orchestrateur au moment de l'exécution d'une tâche, mais aucun fournisseur IA réel n'existe : ces garde-fous sont testés avec un faux fournisseur de test uniquement, jamais avec un vrai modèle.
- L'exécution est synchrone (délai `AI_TIMEOUT_SECONDS`) : une tâche RUNNING interrompue (arrêt du processus) reste bloquée jusqu'à sa réouverture manuelle après 15 minutes.
- Les niveaux d'autonomie 1 et 2 ont aujourd'hui le même effet (validation requise) ; seul le niveau 3 permet l'exécution sans validation pour une permission non critique.

## Opérations soumises à validation humaine (cible)

Paiements, virements, suppression de données importantes, modification des permissions administrateur, publication externe sensible, engagement contractuel, modification de l'infrastructure de production, révocation du dernier accès administrateur. Aucune de ces actions n'est automatisable dans le code actuel.

# Roadmap

Légende : TERMINÉ ET TESTÉ · DÉVELOPPÉ MAIS NON TESTÉ · PARTIELLEMENT IMPLÉMENTÉ · NON IMPLÉMENTÉ · BLOQUÉ

| Phase | Contenu | État |
| --- | --- | --- |
| 0 — Audit | Dépôt vide, code historique uniquement sur le VPS ; décision : repartir de zéro avec la pile décrite | TERMINÉ |
| 1 — Fondation | Auth, sessions, CSRF, anti force brute, rôles, audit, CLI administrateurs, migration 0001 | TERMINÉ ET TESTÉ (SQLite ; PostgreSQL non vérifié) |
| 2 — Centre de contrôle | Tableau de bord réel, navigation, utilisateurs, paramètres, alertes | TERMINÉ ET TESTÉ (partiel : pas de table de notifications persistantes ; les alertes sont calculées) |
| 3 — Agents IA | Agents, identités techniques, permissions, outils, historique, arrêt d'urgence, compteurs réels au tableau de bord | TERMINÉ ET TESTÉ (gestion uniquement ; aucune exécution de tâche ni appel IA ; SQLite, PostgreSQL non vérifié) |
| 4 — Orchestrateur | Missions, tâches, validation humaine (quatre yeux pour les permissions critiques), quotas, budget, arrêt d'urgence, interface `Provider` IA, historique d'exécution | PARTIELLEMENT IMPLÉMENTÉ : gestion, validation et garde-fous développés et testés (SQLite) ; aucun fournisseur IA réel, donc aucune exécution effective ; PostgreSQL non vérifié |
| 5 — Automatisations | Workflows, déclencheurs, anti-boucle | PARTIELLEMENT IMPLÉMENTÉ : configuration CRUD, statuts, simulation de déclenchement et garde-fou anti-boucle développés et testés (SQLite) ; exécution métier réelle non branchée |
| 6 — Départements | CRM, finance (lecture/simulation), RH | PARTIELLEMENT IMPLÉMENTÉ : synthèse des agents par département + CRM + finance + équipe RH (annuaire/indicateurs) ; RH avancé non implémenté |
| 7 — Analytics | Indicateurs et rapports calculés sur données réelles | NON IMPLÉMENTÉ |
| 8 — Finalisation | Audit sécurité complet, tests Docker/PostgreSQL, optimisation | PARTIELLEMENT IMPLÉMENTÉ (scripts et docs prêts ; rien exécuté sur Docker/VPS) |

## Prochaines étapes recommandées

1. Valider la reprise du code historique du VPS (le cas échéant) pour éviter toute perte fonctionnelle.
2. Exécuter la suite de tests contre PostgreSQL 17 (service Docker) et valider `docker compose config/build`.
3. Phase 4 (suite) : implémenter un premier fournisseur IA réel (clés côté serveur chiffrées, jamais renvoyées au frontend) en l'enregistrant dans `providers._REGISTRY` ; exécution asynchrone (file de tâches) à la place de l'exécution synchrone actuelle ; distinguer les niveaux d'autonomie 1 et 2 (aujourd'hui identiques : validation requise sous le niveau 3).
4. Départements : aujourd'hui un catalogue en code (`modules/departments/catalog.py`) ; table dédiée quand ils porteront des données propres.
5. 2FA : TOTP et codes de secours développés (voir SECURITY.md). Reste à : la rendre obligatoire pour les administrateurs (aujourd'hui facultative), afficher un QR code, la vérifier sur PostgreSQL / VPS.

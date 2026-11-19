# Roadmap

Légende : TERMINÉ ET TESTÉ · DÉVELOPPÉ MAIS NON TESTÉ · PARTIELLEMENT IMPLÉMENTÉ · NON IMPLÉMENTÉ · BLOQUÉ

| Phase | Contenu | État |
| --- | --- | --- |
| 0 — Audit | Dépôt vide, code historique uniquement sur le VPS ; décision : repartir de zéro avec la pile décrite | TERMINÉ |
| 1 — Fondation | Auth, sessions, CSRF, anti force brute, rôles, audit, CLI administrateurs, migration 0001 | TERMINÉ ET TESTÉ (SQLite ; PostgreSQL non vérifié) |
| 2 — Centre de contrôle | Tableau de bord réel, navigation, utilisateurs, paramètres, alertes | TERMINÉ ET TESTÉ (partiel : pas de table de notifications persistantes ; les alertes sont calculées) |
| 3 — Agents IA | Agents, identités techniques, permissions, outils, historique, arrêt d'urgence, compteurs réels au tableau de bord | TERMINÉ ET TESTÉ (gestion uniquement ; aucune exécution de tâche ni appel IA ; SQLite, PostgreSQL non vérifié) |
| 4 — Orchestrateur | Missions, attribution, validation humaine, interface fournisseurs IA | NON IMPLÉMENTÉ |
| 5 — Automatisations | Workflows, déclencheurs, anti-boucle | NON IMPLÉMENTÉ |
| 6 — Départements | CRM, finance (lecture/simulation), RH | NON IMPLÉMENTÉ |
| 7 — Analytics | Indicateurs et rapports calculés sur données réelles | NON IMPLÉMENTÉ |
| 8 — Finalisation | Audit sécurité complet, tests Docker/PostgreSQL, optimisation | PARTIELLEMENT IMPLÉMENTÉ (scripts et docs prêts ; rien exécuté sur Docker/VPS) |

## Prochaines étapes recommandées

1. Valider la reprise du code historique du VPS (le cas échéant) pour éviter toute perte fonctionnelle.
2. Exécuter la suite de tests contre PostgreSQL 17 (service Docker) et valider `docker compose config/build`.
3. Phase 4 : `tasks`, `task_runs`, file de validation humaine (les permissions critiques `email:send` et `social:publish` y seront soumises), interface `Provider` IA ; l'exécution doit respecter l'arrêt d'urgence et les quotas `max_actions_per_day` / `monthly_budget_cents` déjà portés par les agents.
4. Départements : aujourd'hui un catalogue en code (`modules/departments/catalog.py`) ; table dédiée quand ils porteront des données propres.
5. 2FA (TOTP) sur les comptes administrateurs.

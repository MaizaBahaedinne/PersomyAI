# Vision

Persomy AI est un système d'exploitation d'entreprise assisté par IA : deux administrateurs humains (`SUPER_ADMIN`) supervisent des agents IA spécialisés, organisés par départements (direction, commercial, marketing, communication, service client, opérations, finance, RH, R&D, gestion de projets).

## Principes

1. **Contrôle humain d'abord.** Les agents n'obtiennent jamais automatiquement de droits administrateur.
2. **Données réelles uniquement.** Aucun indicateur fictif ; un module non développé est affiché comme « en préparation ».
3. **Sécurité par conception.** Permissions vérifiées côté serveur, journal d'audit en ajout seul.
4. **Indépendance des fournisseurs IA.** Une interface commune permettra de brancher OpenAI, Anthropic, Google ou des modèles locaux sans réécrire les agents.
5. **Évolution progressive.** Chaque module est livré testé et documenté.

## Niveaux d'autonomie des agents (cible)

| Niveau | Description |
| --- | --- |
| 1 — Supervisé | L'agent propose, un humain valide. |
| 2 — Autonomie limitée | Actions préautorisées, réversibles et bornées. |
| 3 — Autonomie avancée | Processus complets dans un périmètre défini, avec quotas, journalisation et arrêt d'urgence. |

Restent **toujours soumis à validation humaine explicite** : paiements, virements, suppression de données importantes, modification des permissions administrateur, publication externe sensible, engagement contractuel, modification de l'infrastructure de production, révocation du dernier accès administrateur.

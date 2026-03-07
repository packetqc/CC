---
name: documentation
description: Skill de documentation. Lit la methodology documentation avant d'exécuter les tâches de documentation système ou utilisateur.
---

## Skill Documentation

Ce skill est invoqué automatiquement par le knowledge-validation quand l'utilisateur sélectionne une option du Knowledge Documentation (D1, D2, ou D3/Tous).

### Pré-exécution

Avant d'exécuter toute tâche de documentation, lire la methodology spécifique :
```
methodology/methodology-documentation.md
```

Cette lecture se fait via l'outil Read. Elle charge les instructions spécialisées pour la tâche à accomplir, sans encombrer la mémoire avec toutes les methodologies du système.

### Tâches disponibles

- **D1 — Documentation système** : Suivre la section "Documentation système" de la methodology.
- **D2 — Documentation utilisateur** : Suivre la section "Documentation utilisateur" de la methodology.
- **D3 — Tous** : Exécuter D1 puis D2 en séquence.

### Résultat

Retourne "Vrai" si la documentation a été complétée avec succès, "Faux" sinon.

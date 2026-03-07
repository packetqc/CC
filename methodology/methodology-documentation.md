# Méthodologie : Documentation | Methodology: Documentation

## Objectif | Objective

FR: Cette méthodologie guide l'exécution des tâches de documentation — système et utilisateur. Elle est lue automatiquement par Claude avant d'exécuter une fonction du Knowledge Documentation. Elle hérite des principes de `documentation-generation.md` (projet knowledge) et les adapte au contexte de ce projet.

EN: This methodology guides the execution of documentation tasks — system and user. It is automatically read by Claude before executing a Documentation Knowledge function. It inherits principles from `documentation-generation.md` (knowledge project) and adapts them to this project's context.

---

## Documentation système | System documentation

La documentation système couvre les fichiers essentiels, les méthodologies, et la structure du projet.

### Fichiers essentiels — Mise à jour universelle | Essential Files Update

**Chaque opération qui produit un livrable** (nouvelle méthodologie, nouveau skill, correction structurelle, évolution) **DOIT évaluer les fichiers essentiels pour mise à jour.** C'est une obligation héritée — aucune méthodologie n'en est exemptée.

| Fichier | Mettre à jour quand | Quoi mettre à jour |
|---------|---------------------|-------------------|
| `README.md` | Description, stats clés, ou structure change | Description, badges, résumé des fonctionnalités |
| `NEWS.md` | Tout livrable produit | Nouvelle entrée sous la section projet (date, changement, version) |
| `PLAN.md` | Nouvelle fonctionnalité, capacité, ou changement roadmap | Table What's New et/ou section Ongoing |
| `LINKS.md` | Nouvelle URL de page web créée | Ajouter URL aux sections Essentials ou Hubs; mettre à jour les compteurs |
| `VERSION.md` | Évolution knowledge ou changement structurel | Mettre à jour version/sous-version |
| `CLAUDE.md` | Nouvelle publication, commande, ou évolution | Table publications, table commandes, ou Knowledge Evolution |
| `CHANGELOG.md` | Issue créée ou PR fusionné | Ajouter entrée à la section date courante (issue/PR, type, titre, labels) |
| `STORIES.md` | Success story capturée OU publication web mise à jour | Ajouter entrée à la table Stories Index avec catégorie et date |

### Principe d'héritage | Inheritance Principle

Chaque fichier dans `methodology/` est un **enfant** de cette méta-méthodologie. Quand une opération spécifique s'exécute, elle hérite de la checklist universelle :

```
[étapes spécifiques à la méthodologie]
    → produire livrable (fichiers, PRs, publications)
    → PUIS : évaluer fichiers essentiels pour mise à jour
    → PUIS : commit et livrer tous les changements ensemble
```

### La règle simple

Si tu as changé quelque chose, vérifie si les fichiers essentiels doivent le savoir :
- Nouvelle méthodologie? → NEWS.md + CLAUDE.md
- Nouveau skill? → NEWS.md + CLAUDE.md
- Nouvelle capacité? → NEWS.md + PLAN.md
- Correction structurelle? → NEWS.md
- Nouveau success story? → STORIES.md + NEWS.md

**Les fichiers essentiels sont la mémoire du système** — si un changement n'y est pas reflété, il n'a pas eu lieu du point de vue de l'utilisateur.

---

## Documentation utilisateur | User documentation

La documentation utilisateur couvre les guides, tutoriels et documents créés pour les consommateurs du système (pas les développeurs).

### Principes

1. **Le "pourquoi" avant le "quoi"** — Chaque document commence par expliquer le besoin avant la solution
2. **Bilingue par défaut** — FR et EN, contenu technique en anglais (identifiants, code)
3. **Mind map obligatoire** — Chaque document inclut un diagramme mind map après l'abstract pour ancrage visuel
4. **Diagrammes au service du narratif** — Pas décoratifs, chaque diagramme supporte une explication

### Style d'écriture

| Convention | Quand | Exemple |
|------------|-------|---------|
| **Gras** | Première mention d'un concept clé | **Compilation incrémentale** |
| *Italiques* | Analogie, métaphore, qualités nommées | la qualité *autosuffisant* |
| `Backticks` | Code, fichiers, commandes | `methodology/session-protocol.md` |
| Tiret em (—) | Détail parenthétique | le système — conçu pour l'autonomie — s'adapte |

---

## Related

- `methodology/metrics-compilation.md` — Routine de compilation des métriques
- `methodology/time-compilation.md` — Routine de compilation du temps
- `.claude/skills/github/SKILL.md` — Protocole commentaires temps réel bidirectionnels

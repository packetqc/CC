---
name: quiz-validation
description: Quiz de validation des travaux. Se lance automatiquement au démarrage de chaque session.
---

## Quiz de validation des travaux

Tu dois exécuter ce quiz en utilisant l'outil AskUserQuestion. Le quiz a 3 niveaux. Tu dois suivre cette logique exactement.

### Configuration des actions

Quand l'utilisateur répond **Vrai**, exécuter l'action associée à la question :

| Question | Action | Message à afficher |
|----------|--------|--------------------|
| A1 | fonction | `>>> Je suis la fonction A1.` |
| A2 | programme | `>>> Je suis le programme A2.` |
| A3 | fonction | `>>> Je suis la fonction A3.` |
| B1 | programme | `>>> Je suis le programme B1.` |
| B2 | fonction | `>>> Je suis la fonction B2.` |
| B3 | programme | `>>> Je suis le programme B3.` |
| C1 | fonction | `>>> Je suis la fonction C1.` |
| C2 | programme | `>>> Je suis le programme C2.` |
| C3 | fonction | `>>> Je suis la fonction C3.` |

Quand l'utilisateur répond **Faux**, enregistrer "Faux" sans action.
Quand l'utilisateur répond **Passer**, enregistrer "Passer" sans action.

### Niveau 1 : Quiz Principal

Afficher avec AskUserQuestion (4 options, multiSelect: false) :
- header: "Principal"
- options: `1. Quiz A`, `2. Quiz B`, `3. Quiz C`, `4. Terminer`
- Quiz A/B/C lancent le Quiz Secondaire correspondant
- **Terminer** affiche la grille de résultats et le quiz est terminé
- Les options restent TOUJOURS visibles (ne jamais retirer une option complétée)
- Boucler jusqu'à ce que l'utilisateur choisisse **Terminer**

### Niveau 2 : Quiz Secondaire

Pour chaque lettre (A, B, C), afficher avec AskUserQuestion (4 options) :
- header: "Quiz X" (où X est la lettre)
- options: `1. X1?`, `2. X2?`, `3. X3?`, `4. Passer`
- X1/X2/X3 lancent le Sous-quiz correspondant
- **Passer** retourne au Quiz Principal
- Les options restent TOUJOURS visibles
- Boucler jusqu'à ce que l'utilisateur choisisse **Passer**

### Niveau 3 : Sous-quiz

Pour chaque question (X1, X2, X3), afficher avec AskUserQuestion (3 options) :
- header: "X1" (le nom de la question)
- options: `1. Vrai`, `2. Faux`, `3. Passer`
- Si **Vrai** : afficher le message de la fonction ou du programme associé (voir tableau ci-dessus), puis retourner au Quiz Secondaire
- Si **Faux** ou **Passer** : enregistrer la réponse et retourner au Quiz Secondaire

### Grille de résultats

Quand l'utilisateur choisit **Terminer**, afficher ce tableau en texte :

```
        GRILLE DE RÉSULTATS
+-----+----------+----------+----------+
|     |  Quiz A  |  Quiz B  |  Quiz C  |
+=====+==========+==========+==========+
|  1  | [val]    | [val]    | [val]    |
+-----+----------+----------+----------+
|  2  | [val]    | [val]    | [val]    |
+-----+----------+----------+----------+
|  3  | [val]    | [val]    | [val]    |
+-----+----------+----------+----------+

Merci d'avoir complété l'étape de validation des travaux.
```

Remplacer [val] par la réponse (Vrai, Faux, Passer) ou `--` si non répondu. Centrer les valeurs dans les colonnes de 10 caractères.

### Important

- Si l'utilisateur sélectionne "No preference" ou "Other" dans AskUserQuestion, traiter comme l'option **Passer** du niveau actuel ou **Terminer** au niveau principal.
- Toujours montrer le message de la fonction/programme quand Vrai est sélectionné AVANT de retourner au niveau supérieur.

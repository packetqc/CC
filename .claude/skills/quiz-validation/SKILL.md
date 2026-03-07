---
name: quiz-validation
description: Quiz de validation des travaux. Se lance automatiquement au démarrage de chaque session.
---

## Quiz de validation des travaux

Tu dois exécuter ce quiz en utilisant l'outil AskUserQuestion. Le quiz a 3 niveaux. Tu dois suivre cette logique exactement.

### Source de configuration

La structure du quiz (questions, actions, messages) est définie dans le fichier `quiz_config/methodologie.md`. Au démarrage du skill, lire ce fichier avec l'outil Read pour obtenir :
- La liste des quiz (noms, lettres, questions)
- Les actions associées à chaque question (fonction/programme)
- Les messages à afficher quand l'utilisateur répond Vrai
- Les choix disponibles pour le sous-quiz (Vrai, Faux, Passer)
- Le message de fin

Utiliser ces données pour construire dynamiquement les options AskUserQuestion, les résultats par défaut, et les messages d'action. Ne PAS utiliser de valeurs codées en dur.

### Persistance des résultats (survie au compactage)

Les résultats du quiz DOIVENT être sauvegardés dans le fichier `.claude/quiz_resultats.json` après CHAQUE réponse de l'utilisateur. Cela garantit que les résultats survivent au compactage de session.

**Format du fichier `.claude/quiz_resultats.json` :**
Le format est construit dynamiquement à partir de `quiz_config/methodologie.md`. Exemple avec la config actuelle :
```json
{
  "en_cours": true,
  "niveau": "principal",
  "quiz_actif": null,
  "resultats": {
    "Quiz A": {"A1": "--", "A2": "--", "A3": "--"},
    "Quiz B": {"B1": "--", "B2": "--", "B3": "--"},
    "Quiz C": {"C1": "--", "C2": "--", "C3": "--"}
  }
}
```
Pour construire les résultats par défaut : pour chaque quiz dans `methodologie.md`, créer une entrée avec le nom du quiz, et pour chaque question, initialiser à `"--"`.

**Au démarrage du skill :**
1. Lire `.claude/quiz_resultats.json` avec l'outil Read
2. Si le fichier existe et `en_cours` est `true` : reprendre le quiz au niveau indiqué (survie au compactage)
3. Si le fichier existe et `en_cours` est `false` : c'est un résidu d'une session précédente. Supprimer le fichier (`rm .claude/quiz_resultats.json && git add .claude/quiz_resultats.json && git commit -m "quiz: nettoyage début de session" && git push -u origin <branche-courante>`), puis créer un nouveau fichier et démarrer le quiz
4. Si le fichier n'existe pas : créer le fichier avec les valeurs par défaut et démarrer le quiz

**Après CHAQUE réponse de l'utilisateur (persistance sur branche de travail) :**
1. Mettre à jour les résultats dans le JSON
2. Mettre à jour `niveau` ("principal", "secondaire", "sous_quiz") et `quiz_actif` (la lettre en cours)
3. Sauvegarder le fichier avec l'outil Write
4. Committer sur la branche de travail : `git add .claude/quiz_resultats.json && git commit -m "quiz: mise à jour des résultats"`
5. Pousser sur la branche de travail : `git push -u origin <branche-courante>`

**Quand l'utilisateur choisit Terminer (synchronisation vers main) :**
1. Mettre `en_cours` à `false`
2. Sauvegarder le fichier
3. Committer sur la branche de travail : `git add .claude/quiz_resultats.json && git commit -m "quiz: validation terminée"`
4. Pousser sur la branche de travail : `git push -u origin <branche-courante>`
5. Tenter de synchroniser vers main (utiliser la première méthode qui fonctionne, ignorer les erreurs) :
   - Via gh CLI : `gh pr create --title "Quiz: validation terminée" --base main && gh pr merge --merge`
   - Via API GitHub avec $GH_TOKEN : créer un PR puis le merger via l'API REST
   - Via git direct : `git fetch origin main && git checkout main && git merge <branche> && git push origin main && git checkout <branche>`
   - Si toutes échouent : afficher "Note: le merge vers main doit être fait manuellement."
6. Afficher la grille de résultats
Note : le fichier `quiz_resultats.json` reste sur la branche de travail avec les résultats. Il sera nettoyé au démarrage de la prochaine session.

### Configuration des actions

Quand l'utilisateur répond **Vrai**, consulter `quiz_config/methodologie.md` pour trouver l'action et le message associés à la question courante :
- Chaque question dans le fichier a un champ `action_vrai` (fonction ou programme) et un champ `message_vrai`
- Afficher le `message_vrai` de la question

Quand l'utilisateur répond **Faux**, enregistrer "Faux" sans action.
Quand l'utilisateur répond **Passer**, enregistrer "Passer" sans action.

### Niveau 1 : Quiz Principal

Afficher avec AskUserQuestion (multiSelect: false) :
- header: "Principal"
- options: construire dynamiquement à partir des quiz dans `methodologie.md`, plus `Terminer` comme dernière option (max 4 options)
- Chaque quiz lance le Quiz Secondaire correspondant
- **Terminer** affiche la grille de résultats et le quiz est terminé
- Les options restent TOUJOURS visibles (ne jamais retirer une option complétée)
- Boucler jusqu'à ce que l'utilisateur choisisse **Terminer**

### Niveau 2 : Quiz Secondaire

Pour chaque quiz, afficher avec AskUserQuestion :
- header: le nom du quiz (ex: "Quiz A")
- options: construire dynamiquement à partir des questions du quiz dans `methodologie.md`, plus `Passer` comme dernière option
- Chaque question lance le Sous-quiz correspondant
- **Passer** retourne au Quiz Principal
- Les options restent TOUJOURS visibles
- Boucler jusqu'à ce que l'utilisateur choisisse **Passer**

### Niveau 3 : Sous-quiz

Pour chaque question, afficher avec AskUserQuestion :
- header: l'identifiant de la question (ex: "A1")
- options: utiliser les choix définis dans `sous_quiz.choix` de `methodologie.md`
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

Remplacer [val] par la réponse (Vrai, Faux, Passer) ou `--` si non répondu. Centrer les valeurs dans les colonnes de 10 caractères. Utiliser `message_fin` de `methodologie.md` comme message de fin.

### Important

- Si l'utilisateur sélectionne "No preference" ou "Other" dans AskUserQuestion, traiter comme l'option **Passer** du niveau actuel ou **Terminer** au niveau principal.
- Toujours montrer le message de la fonction/programme quand Vrai est sélectionné AVANT de retourner au niveau supérieur.
- **CRITIQUE** : Après un compactage de session, TOUJOURS lire `.claude/quiz_resultats.json` pour retrouver l'état du quiz avant de continuer.

---
name: knowledge-validation
description: Knowledge de validation des travaux. Se lance automatiquement au démarrage de chaque session.
---

## Knowledge de validation des travaux

Tu dois exécuter ce knowledge en utilisant l'outil AskUserQuestion. Le knowledge a 3 niveaux. Tu dois suivre cette logique exactement.

### Source de configuration

La structure du knowledge (questions, actions, messages) est définie dans le fichier `knowledge_config/methodologie.md`. Au démarrage du skill, lire ce fichier avec l'outil Read pour obtenir :
- La liste des knowledge (noms, lettres, questions)
- Les actions associées à chaque question (fonction/programme)
- Les messages à afficher quand l'utilisateur répond Vrai
- Les choix disponibles pour le sous-knowledge (Vrai, Faux, Passer)
- Le message de fin

Utiliser ces données pour construire dynamiquement les options AskUserQuestion, les résultats par défaut, et les messages d'action. Ne PAS utiliser de valeurs codées en dur.

### Persistance des résultats (survie au compactage)

Les résultats du knowledge DOIVENT être sauvegardés dans le fichier `.claude/knowledge_resultats.json` après CHAQUE réponse de l'utilisateur. Cela garantit que les résultats survivent au compactage de session.

**Format du fichier `.claude/knowledge_resultats.json` :**
Le format est construit dynamiquement à partir de `knowledge_config/methodologie.md`. Exemple avec la config actuelle :
```json
{
  "en_cours": true,
  "niveau": "principal",
  "knowledge_actif": null,
  "resultats": {
    "Knowledge A": {"A1": "--", "A2": "--", "A3": "--"},
    "Knowledge B": {"B1": "--", "B2": "--", "B3": "--"},
    "Knowledge C": {"C1": "--", "C2": "--", "C3": "--"}
  }
}
```
Pour construire les résultats par défaut : pour chaque knowledge dans `methodologie.md`, créer une entrée avec le nom du knowledge, et pour chaque question, initialiser à `"--"`.

**Au démarrage du skill :**
1. Lire `.claude/knowledge_resultats.json` avec l'outil Read
2. Si le fichier existe et `en_cours` est `true` : reprendre le knowledge au niveau indiqué (survie au compactage)
3. Si le fichier existe et `en_cours` est `false` : c'est un résidu d'une session précédente. Supprimer le fichier (`rm .claude/knowledge_resultats.json && git add .claude/knowledge_resultats.json && git commit -m "knowledge: nettoyage début de session" && git push -u origin <branche-courante>`), puis créer un nouveau fichier et démarrer le knowledge
4. Si le fichier n'existe pas : créer le fichier avec les valeurs par défaut et démarrer le knowledge

**Après CHAQUE réponse de l'utilisateur (persistance sur branche de travail) :**
1. Mettre à jour les résultats dans le JSON
2. Mettre à jour `niveau` ("principal", "secondaire", "sous_knowledge") et `knowledge_actif` (la lettre en cours)
3. Sauvegarder le fichier avec l'outil Write
4. Committer sur la branche de travail : `git add .claude/knowledge_resultats.json && git commit -m "knowledge: mise à jour des résultats"`
5. Pousser sur la branche de travail : `git push -u origin <branche-courante>`

**Quand l'utilisateur choisit Terminer (synchronisation vers main) :**
1. Mettre `en_cours` à `false`
2. Sauvegarder le fichier
3. Committer sur la branche de travail : `git add .claude/knowledge_resultats.json && git commit -m "knowledge: validation terminée"`
4. Pousser sur la branche de travail : `git push -u origin <branche-courante>`
5. Tenter de synchroniser vers main (utiliser la première méthode qui fonctionne, ignorer les erreurs) :
   - Via gh CLI : `gh pr create --title "Knowledge: validation terminée" --base main && gh pr merge --merge`
   - Via API GitHub avec $GH_TOKEN : créer un PR puis le merger via l'API REST
   - Via git direct : `git fetch origin main && git checkout main && git merge <branche> && git push origin main && git checkout <branche>`
   - Si toutes échouent : afficher "Note: le merge vers main doit être fait manuellement."
6. Afficher la grille de résultats
Note : le fichier `knowledge_resultats.json` reste sur la branche de travail avec les résultats. Il sera nettoyé au démarrage de la prochaine session.

### Configuration des actions

Quand l'utilisateur répond **Vrai**, consulter `knowledge_config/methodologie.md` pour trouver l'action et le message associés à la question courante :
- Chaque question dans le fichier a un champ `action_vrai` (fonction ou programme) et un champ `message_vrai`
- Afficher le `message_vrai` de la question

Quand l'utilisateur répond **Faux**, enregistrer "Faux" sans action.
Quand l'utilisateur répond **Passer**, enregistrer "Passer" sans action.

### Niveau 1 : Knowledge Principal

Afficher avec AskUserQuestion (multiSelect: false) :
- header: "Principal"
- options: construire dynamiquement à partir des knowledge dans `methodologie.md`, plus `Terminer` comme dernière option (max 4 options)
- Chaque knowledge lance le Knowledge Secondaire correspondant
- **Terminer** affiche la grille de résultats et le knowledge est terminé
- Les options restent TOUJOURS visibles (ne jamais retirer une option complétée)
- Boucler jusqu'à ce que l'utilisateur choisisse **Terminer**

### Niveau 2 : Knowledge Secondaire

Pour chaque knowledge, afficher avec AskUserQuestion :
- header: le nom du knowledge (ex: "Knowledge A")
- options: construire dynamiquement à partir des questions du knowledge dans `methodologie.md`, plus `Passer` comme dernière option
- Pour les questions de type `executer_demande`, afficher le label "Exécuter la demande" au lieu de l'identifiant de la question (ex: au lieu de "A3", afficher "Exécuter la demande")
- Chaque question lance le Sous-knowledge correspondant
- **Passer** retourne au Knowledge Principal
- Les options restent TOUJOURS visibles
- Boucler jusqu'à ce que l'utilisateur choisisse **Passer**

### Niveau 3 : Sous-knowledge

Pour chaque question, vérifier d'abord le type d'action dans `methodologie.md` :

**Si l'action est `executer_demande` (ex: A3) :**
- Ne PAS afficher de choix Vrai/Faux/Passer à l'utilisateur
- Cette option est entièrement programmatique et non modifiable par l'humain dans le fichier de configuration
- Capturer le message initial de l'utilisateur au démarrage de la session (la première demande qu'il a tapée)
- Appeler le skill `commande-utilisateur` via l'outil Skill en lui passant la chaîne en argument : `skill: "commande-utilisateur", args: "message initial de l'utilisateur"`
- Le skill `commande-utilisateur` exécute `executer_demande.py` et retourne le résultat
- Selon le résultat retourné par le skill : enregistrer "Vrai" ou "Faux" pour cette question
- Retourner automatiquement au Knowledge Secondaire

**Pour toutes les autres actions (fonction, programme) :**
- Afficher avec AskUserQuestion :
  - header: l'identifiant de la question (ex: "A1")
  - options: utiliser les choix définis dans `sous_knowledge.choix` de `methodologie.md`
  - Si **Vrai** : afficher le message de la fonction ou du programme associé (voir tableau ci-dessus), puis retourner au Knowledge Secondaire
  - Si **Faux** ou **Passer** : enregistrer la réponse et retourner au Knowledge Secondaire

### Grille de résultats

Quand l'utilisateur choisit **Terminer**, afficher ce tableau en texte :

```
        GRILLE DE RÉSULTATS
+-----+----------+----------+----------+
|     |  Knw A   |  Knw B   |  Knw C   |
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
- **CRITIQUE** : Après un compactage de session, TOUJOURS lire `.claude/knowledge_resultats.json` pour retrouver l'état du knowledge avant de continuer.

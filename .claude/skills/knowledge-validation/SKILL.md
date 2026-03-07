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

**Exception hardcodée :** La 3e question du 1er knowledge est TOUJOURS de type `executer_demande`, peu importe son ID ou ce qui est écrit dans `methodologie.md`. Cette règle est programmatique et prioritaire sur le contenu du fichier de configuration.

### Persistance des résultats (survie au compactage)

Les résultats du knowledge DOIVENT être sauvegardés dans le fichier `.claude/knowledge_resultats.json` après CHAQUE réponse de l'utilisateur. Cela garantit que les résultats survivent au compactage de session.

**Format du fichier `.claude/knowledge_resultats.json` :**
Le format est construit dynamiquement à partir de `knowledge_config/methodologie.md`. Exemple avec la config actuelle :
```json
{
  "en_cours": true,
  "niveau": "principal",
  "knowledge_actif": null,
  "page_principal": 0,
  "page_secondaire": 0,
  "demande_executee": false,
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

### Système de pagination

AskUserQuestion est limité à 4 options (2 à 4). Pour supporter un nombre illimité d'éléments dans `methodologie.md`, un système de pagination est utilisé aux niveaux principal et secondaire.

**Règle de pagination (identique aux deux niveaux) :**
- Calculer le nombre total d'éléments (knowledge ou questions) depuis `methodologie.md`
- Chaque niveau a une option de contrôle fixe en dernière position :
  - **Niveau principal** : `Terminer` (toujours en dernière position)
  - **Niveau secondaire** : `Passer` (toujours en dernière position)
- Si total ≤ 2 : afficher tous les éléments + option de contrôle (2 ou 3 options, pas de pagination)
- Si total = 3 : afficher les 3 éléments + option de contrôle (4 options, pas de pagination)
- Si total > 3 : pagination nécessaire
  - **Page intermédiaire** : 2 éléments + `Suivant ▸` + option de contrôle (4 options)
  - **Dernière page** : éléments restants (1 à 3) + option de contrôle (2 à 4 options, pas de `Suivant ▸`)
- Maintenir un index de page courant dans `.claude/knowledge_resultats.json` : champs `page_principal` et `page_secondaire` (défaut: 0)

**Persistance de la page :** Après chaque navigation de page, sauvegarder l'index dans le JSON et committer/pousser comme pour toute autre mise à jour.

### Niveau 1 : Knowledge Principal

**Mode initial (demande_executee = false) :**
- Afficher avec AskUserQuestion (multiSelect: false) :
  - header: "Principal"
  - options: `Exécuter la demande` + `Terminer` (2 options seulement)
- L'utilisateur DOIT exécuter sa demande avant d'accéder au questionnaire de validation
- Quand l'utilisateur choisit `Exécuter la demande` : appeler le skill `commande-utilisateur` avec le message initial de session, enregistrer le résultat (Vrai/Faux) dans la 3e question du 1er knowledge, puis mettre `demande_executee` à `true`
- **Terminer** affiche la grille de résultats et le knowledge est terminé

**Mode complet (demande_executee = true) :**
- Afficher avec AskUserQuestion (multiSelect: false) :
  - header: "Principal"
  - La 1re option est TOUJOURS `Exécuter la demande` (permet de relancer la demande)
  - Suivie des knowledge lus depuis `methodologie.md`
  - Appliquer la pagination sur l'ensemble (Exécuter la demande + knowledge) avec `Terminer` comme option de contrôle
- Si l'utilisateur choisit `Exécuter la demande` : relancer l'exécution et mettre à jour le résultat
- Si l'utilisateur choisit un knowledge : lancer le Knowledge Secondaire correspondant (questionnaire de validation)
- Si l'utilisateur choisit `Suivant ▸` : incrémenter la page et réafficher
- **Terminer** affiche la grille de résultats et le knowledge est terminé
- Les options restent TOUJOURS visibles (ne jamais retirer une option complétée)
- Boucler jusqu'à ce que l'utilisateur choisisse **Terminer**

### Niveau 2 : Knowledge Secondaire

Pour chaque knowledge, afficher avec AskUserQuestion :
- header: le nom du knowledge (ex: "Knowledge A")
- Lire toutes les questions du knowledge depuis `methodologie.md`
- Appliquer la pagination (voir règle ci-dessus) avec `Passer` comme option de contrôle
- Si l'utilisateur choisit `Suivant ▸` : incrémenter la page (revenir à 0 après la dernière page) et réafficher
- Pour les questions de type `executer_demande`, afficher le label "Exécuter la demande" au lieu de l'identifiant de la question
- Chaque question lance le Sous-knowledge correspondant
- **Passer** retourne au Knowledge Principal (et remet `page_secondaire` à 0)
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

Quand l'utilisateur choisit **Terminer**, construire et afficher un tableau dynamique basé sur les knowledge et questions présents dans `methodologie.md` :

- **Colonnes** : une par knowledge trouvé (ex: Knw A, Knw B, Knw C, Knw D...)
- **Lignes** : autant que le nombre maximum de questions parmi tous les knowledge
- **Valeurs** : remplacer par la réponse (Vrai, Faux, Passer) ou `--` si non répondu
- **Largeur de colonne** : 10 caractères, valeurs centrées

Exemple avec 3 knowledge de 3 questions chacun :
```
        GRILLE DE RÉSULTATS
+-----+----------+----------+----------+
|     |  Knw A   |  Knw B   |  Knw C   |
+=====+==========+==========+==========+
|  1  |   Vrai   |    --    |  Faux    |
+-----+----------+----------+----------+
|  2  |    --    |   Vrai   |    --    |
+-----+----------+----------+----------+
|  3  |  Passer  |    --    |   Vrai   |
+-----+----------+----------+----------+
```

Exemple avec 5 knowledge dont certains ont des nombres de questions différents :
```
        GRILLE DE RÉSULTATS
+-----+----------+----------+----------+----------+----------+
|     |  Knw A   |  Knw B   |  Knw C   |  Knw D   |  Knw E   |
+=====+==========+==========+==========+==========+==========+
|  1  |   Vrai   |    --    |  Faux    |   Vrai   |    --    |
+-----+----------+----------+----------+----------+----------+
|  2  |    --    |   Vrai   |    --    |    --    |   Vrai   |
+-----+----------+----------+----------+----------+----------+
|  3  |  Passer  |    --    |   Vrai   |          |    --    |
+-----+----------+----------+----------+----------+----------+
|  4  |          |          |          |          |  Faux    |
+-----+----------+----------+----------+----------+----------+
```
(cellules vides si le knowledge n'a pas autant de questions)

Utiliser `message_fin` de `methodologie.md` comme message de fin après la grille.

### Important

- Si l'utilisateur sélectionne "No preference", "Other" ou **Skip** dans AskUserQuestion : au niveau principal, traiter comme **Terminer** ; au niveau secondaire, traiter comme retour au Knowledge Principal.
- Toujours montrer le message de la fonction/programme quand Vrai est sélectionné AVANT de retourner au niveau supérieur.
- **CRITIQUE** : Après un compactage de session, TOUJOURS lire `.claude/knowledge_resultats.json` pour retrouver l'état du knowledge avant de continuer.

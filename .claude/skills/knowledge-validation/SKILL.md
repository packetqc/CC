---
name: knowledge-validation
description: Knowledge de validation des travaux. Se lance automatiquement au démarrage de chaque session.
---

## Knowledge de validation des travaux

Tu dois exécuter ce knowledge en utilisant l'outil AskUserQuestion. Le knowledge a 3 niveaux. Tu dois suivre cette logique exactement.

### Source de configuration

La structure du knowledge (questions, actions, messages) est définie dans le fichier `knowledge_config/methodology-knowledge.md`. Au démarrage du skill, lire ce fichier avec l'outil Read pour obtenir :
- La liste des knowledge (noms, lettres, questions)
- Les actions associées à chaque question (fonction/programme)
- Les messages à afficher quand l'utilisateur répond Vrai
- Les choix disponibles pour le sous-knowledge (Vrai, Faux, Passer)
- Le message de fin

Utiliser ces données pour construire dynamiquement les options AskUserQuestion, les résultats par défaut, et les messages d'action. Ne PAS utiliser de valeurs codées en dur.

**Exception hardcodée :** La 3e question du 1er knowledge est TOUJOURS de type `executer_demande`, peu importe son ID ou ce qui est écrit dans `methodology-knowledge.md`. Cette règle est programmatique et prioritaire sur le contenu du fichier de configuration.

### Persistance des résultats (survie au compactage)

Les résultats du knowledge DOIVENT être sauvegardés dans le fichier `.claude/knowledge_resultats.json` après CHAQUE réponse de l'utilisateur. Cela garantit que les résultats survivent au compactage de session.

**Format du fichier `.claude/knowledge_resultats.json` :**
Le format est construit dynamiquement à partir de `knowledge_config/methodology-knowledge.md`. Exemple avec la config actuelle :
```json
{
  "en_cours": true,
  "niveau": "principal",
  "knowledge_actif": null,
  "page_principal": 0,
  "page_secondaire": 0,
  "demande_executee": false,
  "demande_reformulee": null,
  "resultats": {
    "Knowledge A": {"A1": "--", "A2": "--", "A3": "--"},
    "Knowledge B": {"B1": "--", "B2": "--", "B3": "--"},
    "Knowledge C": {"C1": "--", "C2": "--", "C3": "--"}
  }
}
```
Pour construire les résultats par défaut : pour chaque knowledge dans `methodology-knowledge.md`, créer une entrée avec le nom du knowledge, et pour chaque question, initialiser à `"--"`.

**Au démarrage du skill :**
1. Lire `.claude/knowledge_resultats.json` avec l'outil Read
2. Si le fichier existe et `en_cours` est `true` : reprendre le knowledge au niveau indiqué (survie au compactage)
3. Si le fichier existe et `en_cours` est `false` : c'est un résidu d'une session précédente. Supprimer le fichier (`rm .claude/knowledge_resultats.json && git add .claude/knowledge_resultats.json && git commit -m "knowledge: nettoyage début de session" && git push -u origin <branche-courante>`), puis créer un nouveau fichier et démarrer le knowledge
4. Si le fichier n'existe pas : créer le fichier avec les valeurs par défaut et démarrer le knowledge
5. **Pré-remplissage (God Mode)** : Après l'étape 1-4, chercher un bloc JSON de pré-remplissage dans cet ordre de priorité :
   - **Source 1 — Message inline** : Analyser le message initial de l'utilisateur. Si le message contient un bloc JSON `{"resultats": {...}}` (sur une ligne séparée, après la demande), l'extraire. La demande est le texte AVANT le bloc JSON.
   - **Source 2 — Fichier** : Si aucun JSON inline trouvé, vérifier si le fichier `.claude/knowledge_prerempli.json` existe (via Read).
   - **Si aucune source trouvée** : pas de pré-remplissage, continuer normalement.

   Le format attendu (identique pour les deux sources) :
      ```json
      {
        "resultats": {
          "Knowledge A": {"A1": "Vrai", "A2": "Faux"},
          "Knowledge B": {"B1": "Vrai"}
        }
      }
      ```
      Seules les clés présentes sont fusionnées. Les questions absentes restent à `"--"`.

   **Appliquer le pré-remplissage :**
   a. Fusionner les valeurs dans `knowledge_resultats.json` : pour chaque knowledge et chaque question présente dans le pré-rempli, remplacer la valeur `"--"` par la valeur fournie (Vrai, Faux, ou Passer)
   b. Sauvegarder `knowledge_resultats.json` mis à jour
   c. Si source fichier : supprimer le fichier pré-rempli `rm -f .claude/knowledge_prerempli.json`
   d. Committer : `git add .claude/knowledge_resultats.json && git rm -f --cached .claude/knowledge_prerempli.json 2>/dev/null; git commit -m "knowledge: pré-remplissage appliqué"`

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

Quand l'utilisateur répond **Vrai**, consulter `knowledge_config/methodology-knowledge.md` pour trouver l'action et le message associés à la question courante :
- Chaque question dans le fichier a un champ `action_vrai` (fonction ou programme) et un champ `message_vrai`
- Afficher le `message_vrai` de la question

Quand l'utilisateur répond **Faux**, enregistrer "Faux" sans action.
Quand l'utilisateur répond **Passer**, enregistrer "Passer" sans action.

### Système de pagination

AskUserQuestion est limité à 4 options (2 à 4). Pour supporter un nombre illimité d'éléments dans `methodology-knowledge.md`, un système de pagination est utilisé aux niveaux principal et secondaire.

**Règle de pagination (identique aux deux niveaux) :**
- Calculer le nombre total d'éléments (knowledge ou questions) depuis `methodology-knowledge.md`
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
  - options: le 1er knowledge uniquement + `Terminer` (2 options)
- L'utilisateur doit d'abord entrer dans le 1er knowledge, où la 3e question (executer_demande) permet d'exécuter sa demande
- Mettre `demande_executee` à `true` **UNIQUEMENT** quand l'exécution retourne **Vrai** (succès). Si Faux, `demande_executee` reste `false`.
- **Terminer** affiche la grille de résultats et le knowledge est terminé

**Mode complet (demande_executee = true) :**
- Afficher avec AskUserQuestion (multiSelect: false) :
  - header: "Principal"
  - Tous les knowledge lus depuis `methodology-knowledge.md` (le 1er knowledge reste toujours accessible pour relancer l'exécution via sa 3e question)
  - Appliquer la pagination avec `Terminer` comme option de contrôle
- Si l'utilisateur choisit un knowledge : lancer le Knowledge Secondaire correspondant (questionnaire de validation)
- Si l'utilisateur choisit `Suivant ▸` : incrémenter la page et réafficher
- **Terminer** affiche la grille de résultats et le knowledge est terminé
- Les options restent TOUJOURS visibles (ne jamais retirer une option complétée)
- Boucler jusqu'à ce que l'utilisateur choisisse **Terminer**

### Niveau 2 : Knowledge Secondaire

Pour chaque knowledge, afficher avec AskUserQuestion :
- header: le nom du knowledge (ex: "Knowledge A")
- Lire toutes les questions du knowledge depuis `methodology-knowledge.md`
- Appliquer la pagination (voir règle ci-dessus) avec `Passer` comme option de contrôle
- Si l'utilisateur choisit `Suivant ▸` : incrémenter la page (revenir à 0 après la dernière page) et réafficher
- Pour les questions de type `executer_demande`, afficher le label "Exécuter la demande" au lieu de l'identifiant de la question
- Chaque question lance le Sous-knowledge correspondant
- **Passer** retourne au Knowledge Principal (et remet `page_secondaire` à 0)
- Les options restent TOUJOURS visibles
- Boucler jusqu'à ce que l'utilisateur choisisse **Passer**

**Retour après reformulation :**
Si on entre dans le Knowledge Secondaire et que `demande_reformulee` est non `null` dans `knowledge_resultats.json`, cela signifie que l'utilisateur a reformulé sa demande après un échec. Dans ce cas :
- Afficher le message : "Vos réponses précédentes sont conservées. Vous pouvez les raffiner avant de procéder à l'exécution."
- Les questions déjà répondues restent accessibles pour raffinement optionnel
- Les prérequis de `executer_demande` sont déjà satisfaits (les réponses précédentes comptent)

### Niveau 3 : Sous-knowledge

**Saut automatique des questions pré-remplies :**
Avant d'afficher le choix Vrai/Faux/Passer, vérifier dans `knowledge_resultats.json` si la question a déjà une réponse (≠ `"--"`). Si oui :
- Afficher : `"[question] : déjà répondu → [valeur]"` (ex: `"A1 : déjà répondu → Vrai"`)
- Ne PAS demander de choix à l'utilisateur
- Retourner directement au Knowledge Secondaire
- L'utilisateur peut toujours re-sélectionner manuellement cette question au niveau 2 pour **écraser** la valeur pré-remplie (dans ce cas, afficher normalement le choix Vrai/Faux/Passer avec une option supplémentaire "Garder [valeur actuelle]")

Pour chaque question, vérifier d'abord le type d'action dans `methodology-knowledge.md` :

**Si l'action est `executer_demande` (ex: A3) :**
- **Prérequis** : vérifier que TOUTES les questions qui précèdent dans ce même knowledge ont été répondues (pas de `"--"`). Si une ou plusieurs questions précédentes n'ont pas été répondues :
  - Afficher un message d'avertissement : "Vous devez répondre aux questions précédentes avant d'exécuter la demande."
  - Retourner au Knowledge Secondaire sans exécuter
- Ne PAS afficher de choix Vrai/Faux/Passer à l'utilisateur
- Cette option est entièrement programmatique et non modifiable par l'humain dans le fichier de configuration
- **Déterminer la demande à exécuter** : lire `demande_reformulee` dans `knowledge_resultats.json`. Si non `null`, utiliser cette valeur. Sinon, utiliser le message initial de l'utilisateur au démarrage de la session.
- **Collecter le contexte** : lire dans `knowledge_resultats.json` les réponses de TOUTES les questions qui précèdent dans ce knowledge. Par exemple, si on exécute A3, collecter les réponses de A1 et A2. Construire un objet JSON : `{"A1": "Vrai", "A2": "Faux"}`. Ce contexte sera transmis au programme via `--context`.

**Checkpoint — Vérification pré-exécution (survie à la compaction) :**
Avant de lancer l'exécution, vérifier s'il existe déjà un checkpoint :
```
python3 executer_demande.py --status
```
- **Si checkpoint existe avec `phase: "termine"`** : une exécution précédente s'est terminée (probablement avant une compaction). Ne pas relancer. Lire directement le résultat dans `details.resultat` du checkpoint et dans `.claude/preuve_execution.json`, puis passer à l'étape 4 (vérification de preuve).
- **Si checkpoint existe avec `phase: "en_cours"`** : le programme tournait quand la compaction a eu lieu. Vérifier `.claude/preuve_execution.json` :
  - Si preuve existe → le programme a fini entre-temps → lire le résultat
  - Si pas de preuve → exécution interrompue → relancer l'exécution (étape 1)
- **Si checkpoint existe avec `phase: "pre_execution"`** : le programme n'a pas encore démarré → continuer normalement (étape 1)
- **Si pas de checkpoint** : première exécution → continuer normalement (étape 1)

**Exécution inline (NE PAS utiliser l'outil Skill) :**
L'exécution se fait **directement dans le flow du knowledge-validation** sans appeler de sous-skill. Cela évite les frontières de tour qui interrompent le flow. Toutes les étapes ci-dessous s'enchaînent dans le MÊME tour de réponse.

**Rollback — Snapshot git avant exécution :**
1. Avant d'exécuter, supprimer toute preuve précédente : `rm -f .claude/preuve_execution.json`
2. Créer un snapshot : `git stash --include-untracked -m "snapshot-avant-execution"`
3. **Classifier et router la demande (inline)** :
   a. Lire les routes disponibles : `python3 executer_demande.py --list-routes`
   b. Classifier l'intention de la demande en analysant sémantiquement :
      - Les identifiants de route, descriptions, syntaxe officielle
      - Les mots-clés comme indices (pas comme critères absolus)
      - Détection de syntaxe exacte (ex: `project create Mon Titre` → route `project-create`)
      - Détection en langage naturel (ex: "peux-tu créer le projet X" → route `project-create`, param title = "X")
      - **Règles de matching des commandes multi-mots :**
        - Analyser le champ `syntaxe` de chaque route pour distinguer les commandes simples (un seul mot, ex: `build`) des commandes composées (multi-mots, ex: `project create [title]`)
        - Pour les commandes composées : la demande DOIT contenir tous les mots de la commande (ex: "project create") pour matcher. Le mot primaire seul (ex: "project") ne suffit PAS — il pourrait correspondre à d'autres sous-commandes futures (project view, project list, etc.)
        - Pour les commandes simples (un seul mot, sans sous-commande) : un match sur ce mot unique est suffisant
        - Si la demande contient un mot primaire de commande composée mais sans sous-commande spécifique → **aucune route ne correspond** → traiter comme pas de match
   c. **Si une route correspond** : exécuter via Bash :
      - Sans paramètres : `python3 executer_demande.py --route <id> --context '<json_contexte>'`
      - Avec paramètres : `python3 executer_demande.py --route <id> --args "<valeur>" --context '<json_contexte>'`
      - Toujours passer `--context` avec le JSON des réponses précédentes
   d. **Si aucune route ne correspond** (ex: "bonjour", "project" seul) : ne rien exécuter → Résultat = **Faux**
   e. **Règles strictes** : NE JAMAIS répondre à la demande, NE JAMAIS inventer une route, NE JAMAIS créer le fichier preuve_execution.json
4. Vérifier la preuve d'exécution :
   - Lire le fichier `.claude/preuve_execution.json` avec l'outil Read
   - **Si le fichier EXISTE** : vérifier `execution_reelle` est `true` et `code_retour` est cohérent. Le `token` SHA-256 prouve l'authenticité.
   - **Si le fichier N'EXISTE PAS** : → Résultat = **Faux**
5. Déterminer le résultat :
   - **Vrai** (preuve existe ET `code_retour` = 0) :
     - Supprimer le stash : `git stash drop`
     - Nettoyer : `rm -f .claude/journal_actions.json .claude/preuve_execution.json .claude/checkpoint_execution.json`
     - Enregistrer "Vrai" pour cette question
     - Mettre `demande_executee` à `true`
     - Effacer `demande_reformulee` (remettre à `null` dans `knowledge_resultats.json`)
     - Sauvegarder résultats → **retourner au Knowledge Principal** (niveau 1, mode complet)
   - **Faux** (pas de preuve OU `code_retour` != 0) :
     - Exécuter le rollback : `python3 executer_demande.py --rollback`
     - Restaurer les fichiers : `git checkout . && git clean -fd`
     - Restaurer le stash : `git stash pop`
     - Nettoyer : `rm -f .claude/preuve_execution.json`
     - Enregistrer "Faux" pour cette question
     - Sauvegarder résultats → proposer la reformulation (voir ci-dessous)

**Reformulation après échec :**
Quand l'exécution retourne Faux, NE PAS retourner directement au Knowledge Secondaire. À la place :
1. Afficher avec AskUserQuestion :
   - header: "Reformuler"
   - question: "L'exécution a échoué. Souhaitez-vous reformuler votre demande ?"
   - options:
     - `Reformuler` (description: "Tapez votre nouvelle demande via le champ texte 'Other'")
     - `Continuer sans reformuler` (description: "Conserver le résultat Faux et retourner au quiz")
2. Si l'utilisateur choisit **"Other"** (champ texte libre) : c'est sa nouvelle demande reformulée
   - Sauvegarder le texte saisi comme `demande_reformulee` dans `knowledge_resultats.json`
   - **Retourner au Knowledge Secondaire** (pas directement à l'exécution)
   - Afficher le message : "Vos réponses précédentes sont conservées. Vous pouvez les raffiner avant de procéder à l'exécution."
   - Les questions déjà répondues (ex: A1, A2) restent accessibles pour raffinement mais ne bloquent PAS l'accès à "Exécuter la demande" (les prérequis sont déjà satisfaits)
   - Quand l'utilisateur choisit "Exécuter la demande" (A3), utiliser la `demande_reformulee` au lieu de la demande initiale
3. Si l'utilisateur choisit **"Reformuler"** : lui redemander via AskUserQuestion avec un champ texte
4. Si l'utilisateur choisit **"Continuer sans reformuler"** : conserver Faux, retourner au Knowledge Secondaire
- Retourner automatiquement au Knowledge Secondaire

**Gestion de la demande reformulée :**
- Le champ `demande_reformulee` dans `knowledge_resultats.json` contient la dernière reformulation (ou `null` si pas de reformulation)
- Lors de l'exécution (A3), la priorité est : `demande_reformulee` > demande initiale de session
- Après une exécution **Vrai**, effacer `demande_reformulee` (remettre à `null`)
- Après une nouvelle reformulation, écraser la valeur précédente

**Pour toutes les autres actions (fonction, programme) :**
- Afficher avec AskUserQuestion :
  - header: l'identifiant de la question (ex: "A1")
  - options: utiliser les choix définis dans `sous_knowledge.choix` de `methodology-knowledge.md`
  - Si **Vrai** : afficher le message de la fonction ou du programme associé (voir tableau ci-dessus), puis retourner au Knowledge Secondaire
  - Si **Faux** ou **Passer** : enregistrer la réponse et retourner au Knowledge Secondaire

### Grille de résultats

Quand l'utilisateur choisit **Terminer**, construire et afficher un tableau dynamique basé sur les knowledge et questions présents dans `methodology-knowledge.md` :

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

Utiliser `message_fin` de `methodology-knowledge.md` comme message de fin après la grille.

### Important

- Si l'utilisateur sélectionne "No preference", "Other" ou **Skip** dans AskUserQuestion : au niveau principal, traiter comme **Terminer** ; au niveau secondaire, traiter comme retour au Knowledge Principal.
- Toujours montrer le message de la fonction/programme quand Vrai est sélectionné AVANT de retourner au niveau supérieur.
- **CRITIQUE** : Après un compactage de session, TOUJOURS lire `.claude/knowledge_resultats.json` pour retrouver l'état du knowledge avant de continuer.

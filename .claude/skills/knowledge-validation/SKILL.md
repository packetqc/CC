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
- Les choix disponibles pour le sous-knowledge (Vrai, Faux, Passer / True, False, Skip)
- Le message de fin

**Format bilingue :** Le fichier de configuration supporte le français et l'anglais :
- **Titre** : `# Titre FR | Title EN`
- **Messages** : préfixés `FR:` et `EN:` sur des lignes séparées
- **Noms de knowledge** : `### Nom FR | Name EN (lettre: X)` — optionnel : `(lettre: X, methodology: methodology-name)` pour associer une méthodologie spécifique (fichier `knowledge_config/methodologies/<methodology-name>.md`)
- **Tableaux** : 6 colonnes — `| ID | Choix FR | Choix EN | Action | Message FR | Message EN |`
  - `ID` : identifiant technique (A1, B2, D1...)
  - `Choix FR` / `Choix EN` : label affiché dans AskUserQuestion selon la langue
  - `Action` : type d'action (fonction, programme, executer_demande)
  - `Message FR` / `Message EN` : message affiché quand l'utilisateur répond Vrai
- **Choix du sous-knowledge** : `FR: Vrai, Faux, Passer` / `EN: True, False, Skip`

Le parseur (`knowledge_config/__init__.py`) accepte un paramètre `langue` ("fr" ou "en") et retourne les données dans la langue sélectionnée. Par défaut : "fr". Chaque question retournée contient un champ `choix` (le label bilingue) en plus de `id`, `action_vrai`, `message_vrai`.

**Pour AskUserQuestion**, utiliser le champ `choix` comme label des options (au lieu de l'ID brut). L'ID reste utilisé pour les clés internes et la grille de résultats.

Utiliser ces données pour construire dynamiquement les options AskUserQuestion, les résultats par défaut, et les messages d'action. Ne PAS utiliser de valeurs codées en dur.

**Exception hardcodée :** La **dernière** question du 1er knowledge est TOUJOURS de type `executer_demande`, peu importe son ID ou ce qui est écrit dans `methodology-knowledge.md`. Cette règle est programmatique et prioritaire sur le contenu du fichier de configuration.

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
5. **Pré-remplissage (God Mode)** : Après l'étape 1-4, analyser le message initial de l'utilisateur. Si le message contient un bloc JSON `{"resultats": {...}}` (sur une ligne séparée, après la demande), l'extraire. La demande est le texte AVANT le bloc JSON.
   - **Si aucun JSON trouvé dans le message** : pas de pré-remplissage, continuer normalement.
   - **IMPORTANT** : Ne JAMAIS lire de fichier sur disque comme source de pré-remplissage. Le fichier `.claude/knowledge_prerempli.json.example` est un template de référence pour l'utilisateur uniquement.

   Le format attendu :
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
   c. Committer : `git add .claude/knowledge_resultats.json && git commit -m "knowledge: pré-remplissage appliqué"`

**Après CHAQUE réponse de l'utilisateur (persistance sur branche de travail) :**
1. Mettre à jour les résultats dans le JSON
2. Mettre à jour `niveau` ("principal", "secondaire", "sous_knowledge") et `knowledge_actif` (la lettre en cours)
3. Sauvegarder le fichier avec l'outil Write
4. Committer sur la branche de travail : `git add .claude/knowledge_resultats.json && git commit -m "knowledge: mise à jour des résultats"`
5. Pousser sur la branche de travail : `git push -u origin <branche-courante>`

**Quand l'utilisateur fait Skip au niveau principal (synchronisation vers main) :**
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
7. Exécuter `compilation_metriques(resultats)` depuis `knowledge_skills.py` — si des changements de métriques sont détectés, met `_documentation_requise = True`
8. Exécuter `compilation_temps(resultats)` depuis `knowledge_skills.py` — si des changements de temps sont détectés, met `_documentation_requise = True`
9. Exécuter `pre_sauvegarde(resultats)` depuis `knowledge_skills.py` — **Pré-sauvegarde** : exécute les règles de conformité. Première sous-fonction : `confirmation_documentation` (compare le flag interne avec le résultat de l'étape Documentation du quiz). D'autres règles suivront.
10. Exécuter `sauvegarde(resultats)` depuis `knowledge_skills.py`
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
- Il n'y a plus d'option de contrôle fixe (Terminer/Passer) dans les choix — le bouton **Skip** natif de AskUserQuestion remplit ce rôle
- Si total = 1 : entrée automatique (pas de menu — voir mode initial du principal)
- Si total ≤ 4 : afficher tous les éléments (2 à 4 options, pas de pagination)
- Si total > 4 : pagination nécessaire
  - **Page intermédiaire** : 3 éléments + `Suivant ▸` (4 options)
  - **Dernière page** : éléments restants (2 à 4 options, pas de `Suivant ▸`)
- Maintenir un index de page courant dans `.claude/knowledge_resultats.json` : champs `page_principal` et `page_secondaire` (défaut: 0)

**Persistance de la page :** Après chaque navigation de page, sauvegarder l'index dans le JSON et committer/pousser comme pour toute autre mise à jour.

### Niveau 1 : Knowledge Principal

**Mode initial (demande_executee = false) :**
- **Entrée automatique** : puisqu'il n'y a qu'un seul knowledge disponible (le 1er), entrer directement dans le Knowledge Secondaire correspondant sans afficher de menu principal. AskUserQuestion exige minimum 2 options, et avec un seul élément sans option de contrôle, le menu serait impossible.
- L'utilisateur doit d'abord passer par le 1er knowledge, où la 3e question (executer_demande) permet d'exécuter sa demande
- Mettre `demande_executee` à `true` **UNIQUEMENT** quand l'exécution retourne **Vrai** (succès). Si Faux, `demande_executee` reste `false`.
- Quand l'utilisateur fait **Skip** au niveau secondaire en mode initial, traiter comme **Terminer** (afficher grille et finir) plutôt que retourner au principal (puisque le principal n'a qu'un seul élément)

**Mode complet (demande_executee = true) :**
- Afficher avec AskUserQuestion (multiSelect: false) :
  - header: "Principal"
  - question: format `"Choisir. (Si vous avez terminé, appuyez sur Skip)"` — en anglais : `"Choose. (If you are done, press Skip)"`
  - Tous les knowledge lus depuis `methodology-knowledge.md` (le 1er knowledge reste toujours accessible pour relancer l'exécution via sa 3e question)
  - **Description des options** : utiliser une chaîne vide `""` comme description pour chaque option au niveau principal. Ne PAS afficher "Knowledge A", "Knowledge B", etc. en sous-titre.
  - Appliquer la pagination sans option de contrôle (Skip natif remplace Terminer)
- Si l'utilisateur choisit un knowledge : lancer le Knowledge Secondaire correspondant (questionnaire de validation)
- Si l'utilisateur choisit `Suivant ▸` : incrémenter la page et réafficher
- **Skip** (bouton natif) affiche la grille de résultats et le knowledge est terminé
- Les options restent TOUJOURS visibles (ne jamais retirer une option complétée)
- Boucler jusqu'à ce que l'utilisateur choisisse **Skip**

### Niveau 2 : Knowledge Secondaire

Pour chaque knowledge, afficher avec AskUserQuestion :
- header: le nom du knowledge (ex: "Knowledge A")
- question: format `"Choisir parmi les options suivantes. (Pour passer, appuyez sur Skip)"` — en anglais : `"Choose from the following options. (To skip, press Skip)"`
- Lire toutes les questions du knowledge depuis `methodology-knowledge.md`
- Appliquer la pagination sans option de contrôle (Skip natif remplace Passer)
- Si l'utilisateur choisit `Suivant ▸` : incrémenter la page (revenir à 0 après la dernière page) et réafficher
- Pour les questions de type `executer_demande`, afficher le label "Exécuter la demande" au lieu de l'identifiant de la question
- Chaque question lance le Sous-knowledge correspondant
- **Skip** (bouton natif) retourne au Knowledge Principal (et remet `page_secondaire` à 0)
- Les options restent TOUJOURS visibles
- Boucler jusqu'à ce que l'utilisateur choisisse **Skip**

**Retour après reformulation :**
Si on entre dans le Knowledge Secondaire et que `demande_reformulee` est non `null` dans `knowledge_resultats.json`, cela signifie que l'utilisateur a reformulé sa demande après un échec. Dans ce cas :
- Afficher le message : "Vos réponses précédentes sont conservées. Vous pouvez les raffiner avant de procéder à l'exécution."
- Les questions déjà répondues restent accessibles pour raffinement optionnel
- Les prérequis de `executer_demande` sont déjà satisfaits (les réponses précédentes comptent)

### Règle critique : toujours afficher le menu secondaire

**IMPORTANT** : Le menu du Knowledge Secondaire (niveau 2) doit TOUJOURS être affiché avec AskUserQuestion et attendre le choix explicite de l'utilisateur, même si toutes les questions sont pré-remplies. Le système ne doit JAMAIS itérer automatiquement à travers les questions pré-remplies. Le flow est :
1. Afficher le menu secondaire → attendre que l'utilisateur clique sur une option
2. Si l'utilisateur clique sur une question pré-remplie → niveau 3 affiche "déjà répondu" et retourne au menu secondaire
3. Si l'utilisateur clique sur "Exécuter la demande" → lancer l'exécution
4. Si l'utilisateur fait Skip → retourner au principal ou terminer

Les questions pré-remplies sont affichées dans le menu avec un indicateur visuel (ex: "A1 ✓" dans la description) mais ne déclenchent AUCUN comportement automatique. C'est l'utilisateur qui décide quand exécuter.

### Niveau 3 : Sous-knowledge

**Saut automatique des questions pré-remplies :**
Quand l'utilisateur sélectionne explicitement une question pré-remplie au niveau 2, vérifier dans `knowledge_resultats.json` si la question a déjà une réponse (≠ `"--"`). Si oui :
- Afficher : `"[question] : déjà répondu → [valeur]"` (ex: `"A1 : déjà répondu → Vrai"`)
- Ne PAS demander de choix à l'utilisateur
- Retourner directement au Knowledge Secondaire (qui DOIT se réafficher et attendre un nouveau choix)
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

**Si l'action est `tous` (ex: D3) :**
- Cette action est **programmatique** — ne PAS afficher de choix Vrai/Faux/Passer
- Quand l'utilisateur sélectionne cette option au niveau secondaire :
  1. Itérer automatiquement à travers TOUTES les autres questions du même knowledge (celles qui ne sont PAS de type `tous`)
  2. Pour chaque question : exécuter l'action associée comme si l'utilisateur avait répondu **Vrai** (afficher le message, déclencher la fonction/programme)
  3. Pour chaque question : enregistrer "Vrai" si l'exécution a réussi, "Faux" si elle a échoué
  4. **Évaluer le résultat global :**
     - **Si TOUTES les questions ont réussi (toutes Vrai)** :
       - Enregistrer "Vrai" pour la question `tous` elle-même
       - Afficher le message associé à la question `tous`
       - **Retourner directement au Knowledge Principal** (pas au secondaire — tout est fait, inutile de rester)
     - **Si AU MOINS UNE question a échoué (au moins un Faux)** :
       - Enregistrer "Faux" pour la question `tous`
       - Afficher un récapitulatif des résultats : pour chaque question, indiquer le statut (Vrai/Faux)
       - **Rester au Knowledge Secondaire** pour permettre à l'utilisateur de re-sélectionner individuellement les questions en échec et de les relancer (ex: système externe indisponible, timeout, etc.)
- Ce type d'action est **réutilisable** par n'importe quel knowledge qui souhaite offrir un raccourci "tout faire d'un coup"

**Pour toutes les autres actions (fonction, programme) :**
- **Lecture de methodology pré-exécution** : avant d'exécuter l'action, vérifier si le knowledge parent a un champ `methodology` dans sa configuration (ex: `methodology: methodology-documentation` dans le header du knowledge). Si oui :
  1. Lire le fichier `knowledge_config/methodologies/<methodology>.md` avec l'outil Read (ex: `knowledge_config/methodologies/methodology-documentation.md`)
  2. Utiliser les instructions de cette methodology pour guider l'exécution de la fonction/programme
  3. Cela permet à Claude d'être spécialisé pour la tâche sans charger toutes les methodologies en mémoire
- Si pas de champ `methodology` : exécuter normalement sans lecture supplémentaire
- Afficher avec AskUserQuestion :
  - header: l'identifiant de la question (ex: "A1")
  - options: utiliser les choix définis dans `sous_knowledge.choix` de `methodology-knowledge.md`
  - Si **Vrai** : afficher le message de la fonction ou du programme associé (voir tableau ci-dessus), puis retourner au Knowledge Secondaire
  - Si **Faux** ou **Passer** : enregistrer la réponse et retourner au Knowledge Secondaire

### Grille de résultats

Quand l'utilisateur fait **Skip** au niveau principal, construire et afficher un tableau dynamique basé sur les knowledge et questions présents dans `methodology-knowledge.md` :

- **Lignes** : une par knowledge trouvé (ex: Knw A, Knw B, Knw C, Knw D...)
- **Colonnes** : autant que le nombre maximum de questions parmi tous les knowledge (numérotées 1, 2, 3...)
- **Valeurs** : remplacer par la réponse (Vrai, Faux, Passer) ou `--` si non répondu
- **Largeur de colonne** : 10 caractères, valeurs centrées

Exemple avec 3 knowledge de 3 questions chacun :
```
        GRILLE DE RÉSULTATS
+-------+----------+----------+----------+
|       |    1     |    2     |    3     |
+=======+==========+==========+==========+
| Knw A |   Vrai   |    --    |  Passer  |
+-------+----------+----------+----------+
| Knw B |    --    |   Vrai   |    --    |
+-------+----------+----------+----------+
| Knw C |  Faux    |    --    |   Vrai   |
+-------+----------+----------+----------+
```

Exemple avec 5 knowledge dont certains ont des nombres de questions différents :
```
        GRILLE DE RÉSULTATS
+-------+----------+----------+----------+----------+
|       |    1     |    2     |    3     |    4     |
+=======+==========+==========+==========+==========+
| Knw A |   Vrai   |    --    |  Passer  |          |
+-------+----------+----------+----------+----------+
| Knw B |    --    |   Vrai   |    --    |          |
+-------+----------+----------+----------+----------+
| Knw C |  Faux    |    --    |   Vrai   |          |
+-------+----------+----------+----------+----------+
| Knw D |   Vrai   |    --    |          |          |
+-------+----------+----------+----------+----------+
| Knw E |    --    |   Vrai   |    --    |  Faux    |
+-------+----------+----------+----------+----------+
```
(cellules vides si le knowledge n'a pas autant de questions)

**Message de fin conditionnel :** Après la grille, vérifier si toutes les questions de tous les knowledge ont été répondues (aucune valeur `"--"` dans les résultats) :
- **Si complet** (aucun `"--"`) : afficher `message_fin_complet` de `methodology-knowledge.md`
- **Si incomplet** (au moins un `"--"`) : afficher `message_fin_incomplet` de `methodology-knowledge.md`

**Fonctions post-grille :** Ces fonctions (définies dans `knowledge_skills.py`) sont appelées par le flux knowledge-validation aux étapes 7-10 ci-dessus :
1. `compilation_metriques(resultats)` — Compile les métriques. Si des changements sont détectés, met `_documentation_requise = True`
2. `compilation_temps(resultats)` — Compile le temps. Si des changements sont détectés, met `_documentation_requise = True`
3. `pre_sauvegarde(resultats)` — Étape 9 : exécute les règles de conformité pré-sauvegarde. Première sous-fonction : `confirmation_documentation`. D'autres règles suivront.
4. `sauvegarde(resultats)` — Sauvegarde les résultats

**Mécanisme du flag `_documentation_requise` — cycle de vie :**
1. **Exécution démarre (A3)** → `reset_documentation_requise()` → flag = `False` (ardoise propre — on ne sait pas encore s'il y aura des changements)
2. **Compilations** (étapes 7-8) → détectent des changements → `set_documentation_requise()` → flag = `True` (documentation requise car changements détectés)
3. **`confirmation_documentation`** (sous-fonction de `pre_sauvegarde`, étape 9) → **compare deux valeurs** :
   - Le flag interne `_documentation_requise` (True si les compilations ont détecté des changements)
   - Le résultat de l'étape Documentation dans le quiz (dernière rangée du tableau des résultats = dernier knowledge au niveau principal, à venir)
   - **Flag `False`** → passe (pas de changements, rien à documenter)
   - **Flag `True` + résultat doc `Vrai`** → passe (l'utilisateur a documenté)
   - **Flag `True` + résultat doc `--`/`Faux`/`Passer`** → suggérer via AskUserQuestion (rappel de discipline, pas un bloqueur — l'utilisateur peut Skip, il repassera dans ~15 min)

Ces fonctions sont **toujours** exécutées après la grille, que le quiz soit complet ou non. L'appel se fait via `from knowledge_skills import compilation_metriques, compilation_temps, pre_sauvegarde, sauvegarde`.

### Important

- Si l'utilisateur sélectionne "No preference", "Other" ou **Skip** dans AskUserQuestion :
  - Au niveau principal : traiter comme **Terminer** (afficher grille et finir)
  - Au niveau secondaire en mode initial (`demande_executee = false`) : traiter aussi comme **Terminer** (afficher grille et finir), car le principal n'a qu'un seul élément
  - Au niveau secondaire en mode complet (`demande_executee = true`) : traiter comme **retour au Knowledge Principal** (et remettre `page_secondaire` à 0)
- Toujours montrer le message de la fonction/programme quand Vrai est sélectionné AVANT de retourner au niveau supérieur.
- **CRITIQUE** : Après un compactage de session, TOUJOURS lire `.claude/knowledge_resultats.json` pour retrouver l'état du knowledge avant de continuer.

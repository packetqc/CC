---
name: commande-utilisateur
description: Exécute la demande initiale de l'utilisateur via le programme scripts/executer_demande.py. Appelé par le knowledge-validation (A3).
---

## Exécution de la demande utilisateur

Ce skill reçoit en argument la demande de l'utilisateur et le contexte des réponses précédentes du knowledge.

**Format de l'argument :**
```
"demande de l'utilisateur |CONTEXT| {\"A1\":\"Vrai\",\"A2\":\"Faux\"}"
```
Le séparateur `|CONTEXT|` sépare la demande du JSON des réponses précédentes.
S'il n'y a pas de `|CONTEXT|`, l'argument entier est la demande (sans contexte).

### Fonctionnement — Classification par intelligence artificielle

**IMPORTANT : Claude ne doit JAMAIS répondre à la demande. Il ne fait que classifier et router.**

1. Recevoir l'argument et le parser :
   - Séparer au `|CONTEXT|` pour extraire la demande et le contexte JSON
   - Si pas de `|CONTEXT|`, la demande est l'argument entier et le contexte est vide
2. Lire les routes disponibles via :
   ```
   python3 scripts/executer_demande.py --list-routes
   ```
3. **Classifier l'intention** : analyser la demande en langage naturel et déterminer si elle correspond à l'une des routes disponibles. Utiliser :
   - Les identifiants de route, leurs descriptions et leur **syntaxe officielle**
   - Les mots-clés comme **indices** (pas comme critères absolus)
   - La compréhension sémantique de la demande (ex: "compile mon app" → route `build`, "lance les vérifications" → route `test`)
   - **Détection de syntaxe exacte** : si la demande commence par la syntaxe officielle (ex: `project create Mon Titre`), reconnaître directement la route
   - **Détection en langage naturel** : si la demande est en français courant (ex: "peux-tu me créer le projet ayant comme titre Projet numéro 1"), reconnaître la route ET extraire les paramètres
4. **Extraire les paramètres** : si la route a des `parametres` définis, extraire leurs valeurs depuis la demande :
   - **Syntaxe exacte** : `project create Mon Titre` → paramètre title = `"Mon Titre"`
   - **Langage naturel** : `"crée-moi le projet Démo v2"` → paramètre title = `"Démo v2"`
   - Les paramètres marqués `obligatoire: true` doivent être présents, sinon → **Faux**
5. **Si une route correspond** : exécuter le programme via :
   - Sans paramètres, sans contexte :
     ```
     python3 scripts/executer_demande.py --route <id>
     ```
   - Avec paramètres :
     ```
     python3 scripts/executer_demande.py --route <id> --args "<valeur extraite>"
     ```
   - Avec contexte (réponses précédentes) :
     ```
     python3 scripts/executer_demande.py --route <id> --context '{"A1":"Vrai","A2":"Faux"}'
     ```
   - Avec les deux :
     ```
     python3 scripts/executer_demande.py --route <id> --args "<valeur>" --context '{"A1":"Vrai","A2":"Faux"}'
     ```
   - **TOUJOURS passer `--context`** si un contexte a été reçu dans l'argument du skill
   - Si code de retour = 0 : indiquer **Vrai**
   - Si code de retour != 0 : indiquer **Faux**
5. **Si aucune route ne correspond** (ex: "bonjour", demande hors périmètre) :
   - NE PAS exécuter de programme
   - NE PAS répondre à la demande
   - Indiquer immédiatement **Faux** avec le message : "Aucune route ne correspond à cette demande."

### Règles strictes — NE PAS IMPROVISER

- **NE JAMAIS** répondre directement à la demande de l'utilisateur (pas de "bonjour", pas de "que puis-je faire pour vous")
- **NE JAMAIS** inventer une route qui n'existe pas
- **NE JAMAIS** exécuter une commande qui ne provient pas d'une route configurée
- **NE JAMAIS** créer ou écrire le fichier `.claude/preuve_execution.json` — seul `scripts/executer_demande.py` peut le faire
- **NE JAMAIS** improviser, expliquer, commenter ou ajouter du texte en dehors du protocole
- Le rôle de Claude ici est **uniquement** : classifier → router → retourner le résultat. Rien d'autre.
- En cas de doute : **Faux**. Ne pas deviner, ne pas tenter.

### Mode STRICT (deuxième tentative)

Si l'argument commence par `STRICT:`, cela signifie que la première tentative a échoué (Claude a probablement répondu au lieu d'exécuter). Dans ce cas :
1. Extraire la demande originale après `STRICT: ... Demande originale: `
2. Suivre le protocole **exactement** : `--list-routes` → classifier → `--route <id>` ou Faux
3. **Zéro tolérance** : aucun texte en dehors de l'appel Bash et du résultat Vrai/Faux
4. Si aucune route ne correspond, retourner `Faux` **sans aucune explication**

### Vérification anti-contournement

Le knowledge-validation vérifie **après** le retour de ce skill que le fichier `.claude/preuve_execution.json` existe et contient un token SHA-256 valide (basé sur timestamp + PID du processus). Ce fichier est écrit **uniquement** par `scripts/executer_demande.py` lors d'une exécution réelle.

Si Claude répond à la demande au lieu de router vers un programme :
- Le fichier de preuve n'existera pas
- Le knowledge-validation détectera l'absence → résultat = **Faux**

### Ajouter une nouvelle route

Éditer `.claude/routes.json` et ajouter une entrée :
```json
{
  "id": "mon-programme",
  "syntaxe": "commande action [param1]",
  "parametres": [
    {
      "nom": "param1",
      "description": "Description du paramètre",
      "obligatoire": true
    }
  ],
  "mots_cles": ["mot1", "mot2"],
  "programme": "python3 mon_script.py",
  "description": "Description de ce que fait le programme"
}
```

- La `syntaxe` définit la commande officielle exacte
- Les `parametres` décrivent les valeurs à extraire de la demande
- Les `mots_cles` servent d'**indices** pour aider la classification IA
- Claude peut reconnaître des formulations en langage naturel qui ne contiennent pas ces mots-clés exacts

### Exemples de classification

| Demande | Route | Commande complète |
|---------|-------|-------------------|
| `project create Démo v2` (ctx: A1=Vrai, A2=Faux) | `project-create` | `--route project-create --args "Démo v2" --context '{"A1":"Vrai","A2":"Faux"}'` |
| `peux-tu créer le projet Démo v2` (ctx: A1=Vrai, A2=Vrai) | `project-create` | `--route project-create --args "Démo v2" --context '{"A1":"Vrai","A2":"Vrai"}'` |
| `build` (ctx: A1=Vrai, A2=Passer) | `build` | `--route build --context '{"A1":"Vrai","A2":"Passer"}'` |
| `bonjour` | _(aucune route)_ | → **Faux** |

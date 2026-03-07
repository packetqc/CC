---
name: commande-utilisateur
description: Exécute la demande initiale de l'utilisateur via le programme executer_demande.py. Appelé par le knowledge-validation (A3).
---

## Exécution de la demande utilisateur

Ce skill reçoit en argument la chaîne de caractères correspondant à la demande initiale de l'utilisateur au démarrage de la session.

### Fonctionnement — Classification par intelligence artificielle

**IMPORTANT : Claude ne doit JAMAIS répondre à la demande. Il ne fait que classifier et router.**

1. Recevoir la chaîne de caractères passée en argument du skill
2. Lire les routes disponibles via :
   ```
   python3 executer_demande.py --list-routes
   ```
3. **Classifier l'intention** : analyser la demande en langage naturel et déterminer si elle correspond à l'une des routes disponibles. Utiliser :
   - Les identifiants de route et leurs descriptions
   - Les mots-clés comme **indices** (pas comme critères absolus)
   - La compréhension sémantique de la demande (ex: "compile mon app" → route `build`, "lance les vérifications" → route `test`)
4. **Si une route correspond** : exécuter le programme via :
   ```
   python3 executer_demande.py --route <id>
   ```
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
- **NE JAMAIS** créer ou écrire le fichier `.claude/preuve_execution.json` — seul `executer_demande.py` peut le faire
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

Le knowledge-validation vérifie **après** le retour de ce skill que le fichier `.claude/preuve_execution.json` existe et contient un token SHA-256 valide (basé sur timestamp + PID du processus). Ce fichier est écrit **uniquement** par `executer_demande.py` lors d'une exécution réelle.

Si Claude répond à la demande au lieu de router vers un programme :
- Le fichier de preuve n'existera pas
- Le knowledge-validation détectera l'absence → résultat = **Faux**

### Ajouter une nouvelle route

Éditer `.claude/routes.json` et ajouter une entrée :
```json
{
  "id": "mon-programme",
  "mots_cles": ["mot1", "mot2"],
  "programme": "python3 mon_script.py",
  "description": "Description de ce que fait le programme"
}
```

Les `mots_cles` servent d'**indices** pour aider la classification IA, mais Claude peut aussi reconnaître des formulations équivalentes qui ne contiennent pas ces mots-clés exacts.

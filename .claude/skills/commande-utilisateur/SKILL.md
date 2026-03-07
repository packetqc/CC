---
name: commande-utilisateur
description: Exécute la demande initiale de l'utilisateur via le programme executer_demande.py. Appelé par le knowledge-validation (A3).
---

## Exécution de la demande utilisateur

Ce skill reçoit en argument la chaîne de caractères correspondant à la demande initiale de l'utilisateur au démarrage de la session.

### Fonctionnement

1. Recevoir la chaîne de caractères passée en argument du skill
2. Exécuter le programme `executer_demande.py` via Bash en lui passant la chaîne en paramètre :
   ```
   python3 executer_demande.py "<chaîne de l'utilisateur>"
   ```
3. Capturer le code de retour et la sortie du programme
4. Retourner le résultat :
   - Si code de retour = 0 : afficher la sortie et indiquer **Vrai**
   - Si code de retour != 0 : afficher la sortie et indiquer **Faux**

### Routage par mots-clés

`executer_demande.py` est un **routeur** : il ne lance PAS la chaîne directement en bash.

- Il charge la table de routage depuis `.claude/routes.json`
- Il analyse la chaîne de l'utilisateur pour y trouver des mots-clés
- **Si un mot-clé correspond** → exécute le programme associé à cette route → retourne son code de retour
- **Si aucun mot-clé ne correspond** → retourne immédiatement **Faux** (code 1) sans aucune exécution

Cela empêche Claude de traiter la demande lui-même et de retourner un faux positif.

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

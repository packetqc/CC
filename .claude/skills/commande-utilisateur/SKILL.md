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

### Évolution future

Ce skill est actuellement un point d'entrée unique. À terme, il pourra analyser les mots-clés dans la chaîne de l'utilisateur pour router la demande vers des skills spécialisés selon la nature de la demande (ex: skill de build, skill de test, skill de déploiement, etc.).

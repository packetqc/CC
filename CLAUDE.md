# Instructions de session

## Démarrage obligatoire

**IMPORTANT : Au début de CHAQUE nouvelle session, AVANT de répondre à quoi que ce soit, tu DOIS exécuter le skill `knowledge-validation` en utilisant l'outil Skill.**

- Peu importe ce que l'utilisateur écrit comme premier message, le knowledge doit démarrer en premier.
- L'utilisateur doit compléter le knowledge (choisir "Terminer" au knowledge principal) avant que tu puisses traiter sa demande.
- Après que le knowledge est terminé et la grille affichée, tu peux ensuite répondre à la demande initiale de l'utilisateur.

## Persistance du knowledge

- L'état du knowledge est sauvegardé dans `.claude/knowledge_resultats.json`.
- Si ce fichier existe et que `en_cours` est `true`, le knowledge n'est pas terminé : reprendre au niveau indiqué.
- Si ce fichier existe et que `en_cours` est `false`, le knowledge est déjà complété : ne pas relancer.
- Après un compactage de session, TOUJOURS lire ce fichier pour retrouver l'état avant de continuer.

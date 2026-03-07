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

## Persistance de l'exécution (checkpoint)

- Avant toute exécution de programme, un checkpoint est écrit dans `.claude/checkpoint_execution.json`.
- Après un compactage de session, TOUJOURS vérifier ce fichier via `python3 executer_demande.py --status` :
  - `phase: "termine"` → le programme a fini, lire le résultat sans relancer
  - `phase: "en_cours"` → vérifier si la preuve existe (programme fini entre-temps) sinon relancer
  - `phase: "pre_execution"` → le programme n'a pas démarré, relancer
  - Pas de fichier → rien en cours

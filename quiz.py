#!/usr/bin/env python3
"""Quiz imbriqué à 4 niveaux avec maximum 4 choix par niveau.

Charge la configuration depuis quiz_config/methodologie.md.
"""
import subprocess
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from quiz_config import charger_methodologie


def construire_actions(config):
    """Construit le dictionnaire ACTIONS_VRAI à partir de la config."""
    actions = {}
    for quiz in config["quiz_principal"]["quiz"]:
        for question in quiz["questions"]:
            qid = question["id"]
            action_type = question["action_vrai"]
            message = question["message_vrai"]
            if action_type == "fonction":
                actions[qid] = ("fonction", fonction_verification, message)
            else:
                actions[qid] = ("programme", appeler_programme_externe, message)
    return actions


def construire_options(config):
    """Construit la liste des options du quiz principal à partir de la config."""
    options = []
    for quiz in config["quiz_principal"]["quiz"]:
        options.append((quiz["nom"], quiz["lettre"],
                        [q["id"] for q in quiz["questions"]]))
    return options


# =============================================================================
# Fonctions utilitaires
# =============================================================================

def lire_choix(prompt, max_choix):
    """Lire et valider un choix numérique de l'utilisateur."""
    while True:
        choix = input(prompt).strip()
        if choix.isdigit() and 1 <= int(choix) <= max_choix:
            return int(choix)
        print(f"Choix invalide. Veuillez entrer un nombre entre 1 et {max_choix}.")


def fonction_verification(nom, message):
    """Fonction interne simulée."""
    print(f"      {message}")


def appeler_programme_externe(nom, message):
    """Appelle le programme externe action_externe.py."""
    script = os.path.join(os.path.dirname(os.path.abspath(__file__)), "action_externe.py")
    subprocess.run([sys.executable, script, nom])


# =============================================================================
# Logique du quiz
# =============================================================================

def sous_quiz(nom, actions_vrai, choix_labels):
    """Sous-quiz à 3 choix : Vrai, Faux, Passer."""
    print(f"\n      --- Sous-quiz pour {nom} ---")
    for i, label in enumerate(choix_labels, start=1):
        print(f"      {i}. {label}")

    choix = lire_choix(f"      Votre réponse pour {nom} (1/2/3) : ", len(choix_labels))
    reponse = choix_labels[choix - 1]
    print(f"      Vous avez choisi : {reponse}")

    if reponse == choix_labels[0] and nom in actions_vrai:
        _, action, message = actions_vrai[nom]
        action(nom, message)

    return reponse


def quiz_secondaire(nom, questions, actions_vrai, choix_labels):
    """Quiz secondaire avec sous-options + Passer."""
    tous_resultats = {}

    while True:
        print(f"\n  == Quiz Secondaire ({nom}) ==")
        for i, qid in enumerate(questions, start=1):
            print(f"  {i}. {qid}?")
        print(f"  {len(questions) + 1}. Passer")

        choix = lire_choix(f"  Votre choix (1-{len(questions) + 1}) : ", len(questions) + 1)

        if choix == len(questions) + 1:
            print(f"  Vous passez le quiz {nom}.")
            break

        qid = questions[choix - 1]
        reponse = sous_quiz(qid, actions_vrai, choix_labels)
        tous_resultats[qid] = reponse

    return tous_resultats


def afficher_grille(options, resultats_par_quiz, message_fin):
    """Affiche les résultats sous forme de tableau inversé (quiz en colonnes)."""
    idx = 5
    col = 10
    sep = "+" + "-" * idx + ("+" + "-" * col) * len(options) + "+"
    sep_header = "+" + "=" * idx + ("+" + "=" * col) * len(options) + "+"

    print("\n        GRILLE DE RÉSULTATS")
    print(sep)
    header = f"|{'':^{idx}}"
    for nom, _, _ in options:
        header += f"|{nom:^{col}}"
    header += "|"
    print(header)
    print(sep_header)

    max_questions = max(len(qs) for _, _, qs in options)
    for n in range(1, max_questions + 1):
        row = f"|{n:^{idx}}"
        for nom, lettre, questions in options:
            qid = f"{lettre}{n}"
            if nom in resultats_par_quiz and qid in resultats_par_quiz[nom]:
                val = resultats_par_quiz[nom][qid]
            else:
                val = "--"
            row += f"|{val:^{col}}"
        row += "|"
        print(row)
        print(sep)

    print(f"\n{message_fin}")


def quiz_principal():
    """Quiz principal. Charge la config et lance le quiz."""
    config = charger_methodologie()
    actions_vrai = construire_actions(config)
    options = construire_options(config)
    choix_labels = config["sous_quiz"]["choix"]
    message_fin = config["message_fin"]
    resultats_par_quiz = {}

    while True:
        print(f"\n=== {config['quiz_principal']['titre']} ===")
        for i, (nom, _, _) in enumerate(options, start=1):
            print(f"{i}. {nom}")
        print(f"{len(options) + 1}. Terminer")

        choix = lire_choix(f"Votre choix (1-{len(options) + 1}) : ", len(options) + 1)

        if choix == len(options) + 1:
            print("\nVous avez choisi de terminer.")
            break

        nom, lettre, questions = options[choix - 1]
        resultats = quiz_secondaire(nom, questions, actions_vrai, choix_labels)
        if nom not in resultats_par_quiz:
            resultats_par_quiz[nom] = {}
        resultats_par_quiz[nom].update(resultats)

    afficher_grille(options, resultats_par_quiz, message_fin)


if __name__ == "__main__":
    quiz_principal()

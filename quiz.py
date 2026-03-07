#!/usr/bin/env python3
"""Quiz imbriqué à 4 niveaux avec maximum 4 choix par niveau."""


def lire_choix(prompt, max_choix):
    """Lire et valider un choix numérique de l'utilisateur."""
    while True:
        choix = input(prompt).strip()
        if choix.isdigit() and 1 <= int(choix) <= max_choix:
            return int(choix)
        print(f"Choix invalide. Veuillez entrer un nombre entre 1 et {max_choix}.")


def sous_quiz(nom):
    """Sous-quiz à 3 choix : Vrai, Faux, Passer."""
    print(f"\n      --- Sous-quiz pour {nom} ---")
    print("      1. Vrai")
    print("      2. Faux")
    print("      3. Passer")

    choix = lire_choix(f"      Votre réponse pour {nom} (1/2/3) : ", 3)
    reponses = {1: "Vrai", 2: "Faux", 3: "Passer"}
    print(f"      Vous avez choisi : {reponses[choix]}")
    return reponses[choix]



def quiz_secondaire(nom, lettre):
    """Quiz secondaire avec sous-options lettre1, lettre2, lettre3 + Passer."""
    sous_options_restantes = [f"{lettre}1", f"{lettre}2", f"{lettre}3"]
    tous_resultats = {}

    while sous_options_restantes:
        print(f"\n  == Quiz Secondaire ({nom}) ==")
        for i, option in enumerate(sous_options_restantes, start=1):
            print(f"  {i}. {option}?")

        num_passer = len(sous_options_restantes) + 1
        print(f"  {num_passer}. Passer")

        choix = lire_choix(f"  Votre choix (1-{num_passer}) : ", num_passer)

        if choix == num_passer:
            print(f"  Vous passez le quiz {nom}.")
            break

        option_choisie = sous_options_restantes[choix - 1]
        reponse = sous_quiz(option_choisie)
        tous_resultats[option_choisie] = reponse
        sous_options_restantes.remove(option_choisie)

    return tous_resultats


def afficher_grille(options, resultats_par_quiz):
    """Affiche les résultats sous forme de tableau inversé (quiz en colonnes)."""
    col = 10
    sep = "+" + "-" * col + ("+" + "-" * col) * len(options) + "+"
    sep_header = "+" + "=" * col + ("+" + "=" * col) * len(options) + "+"

    print("\n        GRILLE DE RÉSULTATS")
    print(sep)
    header = f"|{'':^{col}}"
    for nom, _ in options:
        header += f"|{nom:^{col}}"
    header += "|"
    print(header)
    print(sep_header)

    for n in range(1, 4):
        row = f"|{f'   {n}':^{col}}"
        for nom, lettre in options:
            sous_option = f"{lettre}{n}"
            if nom in resultats_par_quiz and sous_option in resultats_par_quiz[nom]:
                val = resultats_par_quiz[nom][sous_option]
            else:
                val = "--"
            row += f"|{val:^{col}}"
        row += "|"
        print(row)
        print(sep)

    print("\nMerci d'avoir participé au quiz!")


def quiz_principal():
    """Quiz principal. Les options restent visibles après complétion."""
    options = [
        ("Quiz A", "A"),
        ("Quiz B", "B"),
        ("Quiz C", "C"),
    ]
    resultats_par_quiz = {}

    while True:
        print("\n=== Quiz Principal ===")
        for i, (nom, _) in enumerate(options, start=1):
            print(f"{i}. {nom}")
        print(f"{len(options) + 1}. Terminer")

        choix = lire_choix(f"Votre choix (1-{len(options) + 1}) : ", len(options) + 1)

        if choix == len(options) + 1:
            print("\nVous avez choisi de terminer.")
            break

        nom, lettre = options[choix - 1]
        resultats = quiz_secondaire(nom, lettre)
        if nom not in resultats_par_quiz:
            resultats_par_quiz[nom] = {}
        resultats_par_quiz[nom].update(resultats)

    afficher_grille(options, resultats_par_quiz)


if __name__ == "__main__":
    quiz_principal()

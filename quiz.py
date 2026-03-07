#!/usr/bin/env python3
"""Quiz imbriqué avec sous-quiz Vrai/Faux pour chaque lettre."""


def sous_quiz(lettre):
    """Sous-quiz à 3 choix : Vrai, Faux, Passer."""
    print(f"\n--- Sous-quiz pour la lettre {lettre} ---")
    print("1. Vrai")
    print("2. Faux")
    print("3. Passer")

    while True:
        choix = input(f"Votre réponse pour {lettre} (1/2/3) : ").strip()
        if choix in ("1", "2", "3"):
            break
        print("Choix invalide. Veuillez entrer 1, 2 ou 3.")

    reponses = {"1": "Vrai", "2": "Faux", "3": "Passer"}
    print(f"Vous avez choisi : {reponses[choix]}")
    return reponses[choix]


def quiz_principal():
    """Quiz principal avec les lettres A, B, C, D et l'option Terminer."""
    lettres_restantes = ["A", "B", "C", "D"]
    resultats = {}

    while lettres_restantes:
        print("\n=== Quiz Principal ===")
        options = []
        for i, lettre in enumerate(lettres_restantes, start=1):
            print(f"{i}. {lettre}?")
            options.append(lettre)

        num_terminer = len(lettres_restantes) + 1
        print(f"{num_terminer}. Terminer")

        while True:
            choix = input(f"Votre choix (1-{num_terminer}) : ").strip()
            if choix.isdigit() and 1 <= int(choix) <= num_terminer:
                break
            print(f"Choix invalide. Veuillez entrer un nombre entre 1 et {num_terminer}.")

        choix = int(choix)

        if choix == num_terminer:
            print("\nVous avez choisi de terminer le quiz.")
            break

        lettre_choisie = options[choix - 1]
        reponse = sous_quiz(lettre_choisie)
        resultats[lettre_choisie] = reponse
        lettres_restantes.remove(lettre_choisie)

    print("\n=== Résultats ===")
    if resultats:
        for lettre, reponse in resultats.items():
            print(f"  {lettre} : {reponse}")
    else:
        print("  Aucune réponse enregistrée.")

    lettres_non_repondues = [l for l in lettres_restantes]
    if lettres_non_repondues:
        print(f"  Non complétées : {', '.join(lettres_non_repondues)}")

    print("\nMerci d'avoir participé au quiz!")


if __name__ == "__main__":
    quiz_principal()

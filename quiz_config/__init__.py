"""Module de chargement de la méthodologie du quiz depuis un fichier Markdown."""
import os
import re


def charger_methodologie(chemin=None):
    """Charge la méthodologie du quiz depuis le fichier Markdown.

    Retourne un dictionnaire avec la même structure que l'ancien JSON :
    {
        "titre": "...",
        "message_fin": "...",
        "quiz_principal": {
            "titre": "Quiz Principal",
            "quiz": [{"nom": "...", "lettre": "...", "questions": [...]}]
        },
        "sous_quiz": {"choix": ["Vrai", "Faux", "Passer"]}
    }
    """
    if chemin is None:
        chemin = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                              "methodologie.md")

    with open(chemin, "r", encoding="utf-8") as f:
        contenu = f.read()

    config = {
        "titre": "",
        "message_fin": "",
        "quiz_principal": {"titre": "Quiz Principal", "quiz": []},
        "sous_quiz": {"choix": []},
    }

    # Titre principal (# ...)
    m = re.search(r"^# (.+)$", contenu, re.MULTILINE)
    if m:
        config["titre"] = m.group(1).strip()

    # Message de fin : texte après ## Message de fin
    m = re.search(r"## Message de fin\s*\n\s*\n(.+?)(?:\n\s*\n|\Z)",
                  contenu, re.DOTALL)
    if m:
        config["message_fin"] = m.group(1).strip()

    # Choix du sous-quiz : liste après ## Choix du sous-quiz
    m = re.search(r"## Choix du sous-quiz\s*\n\s*\n(.+?)(?:\n\s*\n|\Z)",
                  contenu, re.DOTALL)
    if m:
        config["sous_quiz"]["choix"] = [
            c.strip() for c in m.group(1).strip().split(",")
        ]

    # Quiz : sections ### Nom (lettre: X) avec tableaux
    pattern_quiz = r"### (.+?) \(lettre: (\w+)\)\s*\n(.*?)(?=\n### |\Z)"
    for match in re.finditer(pattern_quiz, contenu, re.DOTALL):
        nom = match.group(1).strip()
        lettre = match.group(2).strip()
        bloc_tableau = match.group(3)

        questions = []
        # Lire les lignes du tableau (ignorer l'en-tête et le séparateur)
        for ligne in bloc_tableau.strip().splitlines():
            ligne = ligne.strip()
            if not ligne.startswith("|") or ligne.startswith("| ID") or ligne.startswith("|--"):
                continue
            colonnes = [c.strip() for c in ligne.split("|")]
            # colonnes : ['', 'ID', 'Action', 'Message', '']
            colonnes = [c for c in colonnes if c]
            if len(colonnes) >= 3:
                questions.append({
                    "id": colonnes[0],
                    "action_vrai": colonnes[1],
                    "message_vrai": colonnes[2],
                })

        config["quiz_principal"]["quiz"].append({
            "nom": nom,
            "lettre": lettre,
            "questions": questions,
        })

    return config

#!/usr/bin/env python3
"""Quiz imbriqué avec architecture Skills.

Chaque composant du quiz est un Skill enregistré dans un registre.
Les skills peuvent s'appeler entre eux par nom via le registre.
"""
import subprocess
import sys
import os


# =============================================================================
# Registre de Skills
# =============================================================================

class SkillRegistry:
    """Registre central de tous les skills disponibles."""

    def __init__(self):
        self._skills = {}
        self._resultats = {}

    def enregistrer(self, nom, skill):
        """Enregistre un skill dans le registre."""
        self._skills[nom] = skill
        skill.registre = self

    def executer(self, nom, **kwargs):
        """Exécute un skill par son nom."""
        if nom not in self._skills:
            print(f"  Skill '{nom}' non trouvé.")
            return None
        return self._skills[nom].executer(**kwargs)

    def lister(self):
        """Liste tous les skills enregistrés."""
        return list(self._skills.keys())

    def stocker_resultat(self, quiz, question, reponse):
        """Stocke un résultat."""
        if quiz not in self._resultats:
            self._resultats[quiz] = {}
        self._resultats[quiz][question] = reponse

    def get_resultats(self):
        """Retourne tous les résultats."""
        return self._resultats


# =============================================================================
# Classe de base Skill
# =============================================================================

class Skill:
    """Classe de base pour tous les skills."""

    def __init__(self, nom, description=""):
        self.nom = nom
        self.description = description
        self.registre = None

    def executer(self, **kwargs):
        raise NotImplementedError


# =============================================================================
# Skill : Lire un choix
# =============================================================================

class LireChoixSkill(Skill):
    def executer(self, prompt="Votre choix : ", max_choix=2):
        while True:
            choix = input(prompt).strip()
            if choix.isdigit() and 1 <= int(choix) <= max_choix:
                return int(choix)
            print(f"Choix invalide. Veuillez entrer un nombre entre 1 et {max_choix}.")


# =============================================================================
# Skills : Actions (fonctions et programmes)
# =============================================================================

class FonctionSkill(Skill):
    """Skill qui exécute une fonction interne."""
    def executer(self, question=""):
        print(f"      >>> Je suis la fonction {question}.")


class ProgrammeSkill(Skill):
    """Skill qui exécute un programme externe."""
    def executer(self, question=""):
        script = os.path.join(os.path.dirname(os.path.abspath(__file__)), "action_externe.py")
        subprocess.run([sys.executable, script, question])


# =============================================================================
# Skill : Sous-quiz (Vrai / Faux / Passer)
# =============================================================================

class SousQuizSkill(Skill):
    """Skill du sous-quiz avec Vrai, Faux, Passer."""

    def __init__(self, nom, action_vrai_skill=None):
        super().__init__(nom, f"Sous-quiz pour {nom}")
        self.action_vrai_skill = action_vrai_skill

    def executer(self, quiz_parent="", **kwargs):
        print(f"\n      --- Sous-quiz pour {self.nom} ---")
        print("      1. Vrai")
        print("      2. Faux")
        print("      3. Passer")

        choix = self.registre.executer("lire_choix",
                                       prompt=f"      Votre réponse pour {self.nom} (1/2/3) : ",
                                       max_choix=3)
        reponses = {1: "Vrai", 2: "Faux", 3: "Passer"}
        print(f"      Vous avez choisi : {reponses[choix]}")

        if choix == 1 and self.action_vrai_skill:
            self.registre.executer(self.action_vrai_skill, question=self.nom)

        self.registre.stocker_resultat(quiz_parent, self.nom, reponses[choix])
        return reponses[choix]


# =============================================================================
# Skill : Quiz Secondaire
# =============================================================================

class QuizSecondaireSkill(Skill):
    """Skill du quiz secondaire avec 3 sous-options + Passer."""

    def __init__(self, nom, lettre, sous_quiz_skills):
        super().__init__(nom, f"Quiz secondaire {nom}")
        self.lettre = lettre
        self.sous_quiz_skills = sous_quiz_skills

    def executer(self, **kwargs):
        while True:
            print(f"\n  == Quiz Secondaire ({self.nom}) ==")
            for i, sq in enumerate(self.sous_quiz_skills, start=1):
                print(f"  {i}. {sq}?")
            print(f"  {len(self.sous_quiz_skills) + 1}. Passer")

            choix = self.registre.executer("lire_choix",
                                           prompt=f"  Votre choix (1-{len(self.sous_quiz_skills) + 1}) : ",
                                           max_choix=len(self.sous_quiz_skills) + 1)

            if choix == len(self.sous_quiz_skills) + 1:
                print(f"  Vous passez le quiz {self.nom}.")
                break

            skill_nom = self.sous_quiz_skills[choix - 1]
            self.registre.executer(skill_nom, quiz_parent=self.nom)


# =============================================================================
# Skill : Quiz Principal
# =============================================================================

class QuizPrincipalSkill(Skill):
    """Skill du quiz principal."""

    def __init__(self, nom, quiz_secondaires):
        super().__init__(nom, "Quiz principal")
        self.quiz_secondaires = quiz_secondaires

    def executer(self, **kwargs):
        while True:
            print(f"\n=== Quiz Principal ===")
            for i, (label, _) in enumerate(self.quiz_secondaires, start=1):
                print(f"{i}. {label}")
            print(f"{len(self.quiz_secondaires) + 1}. Terminer")

            choix = self.registre.executer("lire_choix",
                                           prompt=f"Votre choix (1-{len(self.quiz_secondaires) + 1}) : ",
                                           max_choix=len(self.quiz_secondaires) + 1)

            if choix == len(self.quiz_secondaires) + 1:
                print("\nVous avez choisi de terminer.")
                break

            _, skill_nom = self.quiz_secondaires[choix - 1]
            self.registre.executer(skill_nom)

        self.registre.executer("afficher_grille")


# =============================================================================
# Skill : Afficher la grille
# =============================================================================

class AfficherGrilleSkill(Skill):
    """Skill pour afficher la grille de résultats."""

    def __init__(self, nom, quiz_config):
        super().__init__(nom, "Affichage grille")
        self.quiz_config = quiz_config

    def executer(self, **kwargs):
        resultats = self.registre.get_resultats()
        idx = 5
        col = 10
        sep = "+" + "-" * idx + ("+" + "-" * col) * len(self.quiz_config) + "+"
        sep_header = "+" + "=" * idx + ("+" + "=" * col) * len(self.quiz_config) + "+"

        print("\n        GRILLE DE RÉSULTATS")
        print(sep)
        header = f"|{'':^{idx}}"
        for label, _ in self.quiz_config:
            header += f"|{label:^{col}}"
        header += "|"
        print(header)
        print(sep_header)

        for n in range(1, 4):
            row = f"|{n:^{idx}}"
            for label, lettre in self.quiz_config:
                sous_option = f"{lettre}{n}"
                if label in resultats and sous_option in resultats[label]:
                    val = resultats[label][sous_option]
                else:
                    val = "--"
                row += f"|{val:^{col}}"
            row += "|"
            print(row)
            print(sep)

        print("\nMerci d'avoir complété l'étape de validation des travaux.")


# =============================================================================
# Construction et lancement du quiz
# =============================================================================

def construire_quiz():
    """Construit et enregistre tous les skills du quiz."""
    registre = SkillRegistry()

    # Skill utilitaire
    registre.enregistrer("lire_choix", LireChoixSkill("lire_choix"))

    # Skills actions
    registre.enregistrer("fonction", FonctionSkill("fonction"))
    registre.enregistrer("programme", ProgrammeSkill("programme"))

    # Configuration : quel skill appeler pour Vrai sur chaque question
    config_actions = {
        "A1": "fonction",  "A2": "programme", "A3": "fonction",
        "B1": "programme", "B2": "fonction",  "B3": "programme",
        "C1": "fonction",  "C2": "programme", "C3": "fonction",
    }

    # Skills sous-quiz
    for nom, action in config_actions.items():
        registre.enregistrer(nom, SousQuizSkill(nom, action_vrai_skill=action))

    # Skills quiz secondaires
    quiz_config = [("Quiz A", "A"), ("Quiz B", "B"), ("Quiz C", "C")]

    for label, lettre in quiz_config:
        sous_quizs = [f"{lettre}1", f"{lettre}2", f"{lettre}3"]
        registre.enregistrer(label, QuizSecondaireSkill(label, lettre, sous_quizs))

    # Skill grille
    registre.enregistrer("afficher_grille", AfficherGrilleSkill("afficher_grille", quiz_config))

    # Skill principal
    quiz_secondaires = [(label, label) for label, _ in quiz_config]
    registre.enregistrer("quiz_principal", QuizPrincipalSkill("quiz_principal", quiz_secondaires))

    return registre


if __name__ == "__main__":
    registre = construire_quiz()
    print("Skills enregistrés :", ", ".join(registre.lister()))
    print()
    registre.executer("quiz_principal")

#!/usr/bin/env python3
"""Knowledge imbriqué avec architecture Skills.

Chaque composant du knowledge est un Skill enregistré dans un registre.
Les skills peuvent s'appeler entre eux par nom via le registre.
Charge la configuration depuis methodology/methodology-knowledge.md.
"""
import subprocess
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from knowledge_config import charger_methodologie


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

    def stocker_resultat(self, knowledge, question, reponse):
        """Stocke un résultat."""
        if knowledge not in self._resultats:
            self._resultats[knowledge] = {}
        self._resultats[knowledge][question] = reponse

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
    def executer(self, question="", message=""):
        if message:
            print(f"      {message}")
        else:
            print(f"      >>> Je suis la fonction {question}.")


class ProgrammeSkill(Skill):
    """Skill qui exécute un programme externe."""
    def executer(self, question="", message=""):
        script = os.path.join(os.path.dirname(os.path.abspath(__file__)), "action_externe.py")
        subprocess.run([sys.executable, script, question])


# =============================================================================
# Skill : Sous-knowledge (Vrai / Faux / Passer)
# =============================================================================

class SousKnowledgeSkill(Skill):
    """Skill du sous-knowledge avec Vrai, Faux, Passer."""

    def __init__(self, nom, action_vrai_skill=None, message_vrai="", choix_labels=None):
        super().__init__(nom, f"Sous-knowledge pour {nom}")
        self.action_vrai_skill = action_vrai_skill
        self.message_vrai = message_vrai
        self.choix_labels = choix_labels or ["Vrai", "Faux", "Passer"]

    def executer(self, knowledge_parent="", **kwargs):
        print(f"\n      --- Sous-knowledge pour {self.nom} ---")
        for i, label in enumerate(self.choix_labels, start=1):
            print(f"      {i}. {label}")

        choix = self.registre.executer("lire_choix",
                                       prompt=f"      Votre réponse pour {self.nom} (1/2/3) : ",
                                       max_choix=len(self.choix_labels))
        reponse = self.choix_labels[choix - 1]
        print(f"      Vous avez choisi : {reponse}")

        if choix == 1 and self.action_vrai_skill:
            self.registre.executer(self.action_vrai_skill, question=self.nom,
                                   message=self.message_vrai)

        self.registre.stocker_resultat(knowledge_parent, self.nom, reponse)
        return reponse


# =============================================================================
# Skill : Knowledge Secondaire
# =============================================================================

class KnowledgeSecondaireSkill(Skill):
    """Skill du knowledge secondaire avec 3 sous-options + Passer."""

    def __init__(self, nom, lettre, sous_knowledge_skills):
        super().__init__(nom, f"Knowledge secondaire {nom}")
        self.lettre = lettre
        self.sous_knowledge_skills = sous_knowledge_skills

    def executer(self, **kwargs):
        while True:
            print(f"\n  == Knowledge Secondaire ({self.nom}) ==")
            for i, sq in enumerate(self.sous_knowledge_skills, start=1):
                print(f"  {i}. {sq}?")
            print(f"  {len(self.sous_knowledge_skills) + 1}. Passer")

            choix = self.registre.executer("lire_choix",
                                           prompt=f"  Votre choix (1-{len(self.sous_knowledge_skills) + 1}) : ",
                                           max_choix=len(self.sous_knowledge_skills) + 1)

            if choix == len(self.sous_knowledge_skills) + 1:
                print(f"  Vous passez le knowledge {self.nom}.")
                break

            skill_nom = self.sous_knowledge_skills[choix - 1]
            self.registre.executer(skill_nom, knowledge_parent=self.nom)


# =============================================================================
# Skill : Knowledge Principal
# =============================================================================

class KnowledgePrincipalSkill(Skill):
    """Skill du knowledge principal."""

    def __init__(self, nom, knowledge_secondaires):
        super().__init__(nom, "Knowledge principal")
        self.knowledge_secondaires = knowledge_secondaires

    def executer(self, **kwargs):
        while True:
            print(f"\n=== Knowledge Principal ===")
            for i, (label, _) in enumerate(self.knowledge_secondaires, start=1):
                print(f"{i}. {label}")
            print(f"{len(self.knowledge_secondaires) + 1}. Terminer")

            choix = self.registre.executer("lire_choix",
                                           prompt=f"Votre choix (1-{len(self.knowledge_secondaires) + 1}) : ",
                                           max_choix=len(self.knowledge_secondaires) + 1)

            if choix == len(self.knowledge_secondaires) + 1:
                print("\nVous avez choisi de terminer.")
                break

            _, skill_nom = self.knowledge_secondaires[choix - 1]
            self.registre.executer(skill_nom)

        self.registre.executer("afficher_grille")


# =============================================================================
# Skill : Afficher la grille
# =============================================================================

class AfficherGrilleSkill(Skill):
    """Skill pour afficher la grille de résultats."""

    def __init__(self, nom, knowledge_config, message_fin_complet="", message_fin_incomplet=""):
        super().__init__(nom, "Affichage grille")
        self.knowledge_config = knowledge_config
        self.message_fin_complet = message_fin_complet
        self.message_fin_incomplet = message_fin_incomplet

    def executer(self, **kwargs):
        resultats = self.registre.get_resultats()
        idx = 7
        col = 10
        max_questions = max(len(qs) for _, _, qs in self.knowledge_config)
        sep = "+" + "-" * idx + ("+" + "-" * col) * max_questions + "+"
        sep_header = "+" + "=" * idx + ("+" + "=" * col) * max_questions + "+"

        print("\n        GRILLE DE RÉSULTATS")
        print(sep)
        header = f"|{'':^{idx}}"
        for n in range(1, max_questions + 1):
            header += f"|{n:^{col}}"
        header += "|"
        print(header)
        print(sep_header)

        complet = True
        for label, lettre, questions in self.knowledge_config:
            row = f"|{('Knw ' + lettre):^{idx}}"
            for n in range(1, max_questions + 1):
                sous_option = f"{lettre}{n}"
                if n <= len(questions) and label in resultats and sous_option in resultats[label]:
                    val = resultats[label][sous_option]
                elif n <= len(questions):
                    val = "--"
                    complet = False
                else:
                    val = ""
                row += f"|{val:^{col}}"
            row += "|"
            print(row)
            print(sep)

        message = self.message_fin_complet if complet else self.message_fin_incomplet
        print(f"\n{message}")


# =============================================================================
# État interne post-grille
# =============================================================================

# Flag interne : documentation requise suite à des changements détectés.
# - Remis à False quand l'exécution DÉMARRE (A3) — ardoise propre.
# - Mis à True par les compilations si elles détectent des changements.
# - Consulté par confirmation_documentation qui le compare avec le résultat
#   de l'étape Documentation (dernière rangée du quiz) pour décider si un
#   rappel est nécessaire.
_documentation_requise = False


def set_documentation_requise():
    """Met le flag à True. Appelée par les compilations quand elles
    détectent des changements qui nécessitent documentation."""
    global _documentation_requise
    _documentation_requise = True


def reset_documentation_requise():
    """Remet le flag à False. Appelée quand l'exécution de la demande
    DÉMARRE (A3) — on repart à zéro avant de savoir s'il y aura
    des changements."""
    global _documentation_requise
    _documentation_requise = False


# =============================================================================
# Fonctions post-grille
# =============================================================================

def compilation_metriques(resultats):
    """Compile les métriques du knowledge. Appelée après l'affichage de la grille.

    Détecte si des changements de métriques ont eu lieu. Si oui,
    met _documentation_requise à True via set_documentation_requise().
    """
    global _documentation_requise
    # TODO: implémenter la détection de changements de métriques
    # Si changements détectés : set_documentation_requise()
    pass


def compilation_temps(resultats):
    """Compile les données de temps du knowledge. Appelée après l'affichage de la grille.

    Détecte si du temps a été accumulé (changements). Si oui,
    met _documentation_requise à True via set_documentation_requise().
    """
    global _documentation_requise
    # TODO: implémenter la détection de temps accumulé
    # Si changements détectés : set_documentation_requise()
    pass


# =============================================================================
# Pré-sauvegarde (étape 9)
# =============================================================================
# L'étape pré-sauvegarde regroupe les sous-fonctions de conformité
# exécutées avant la sauvegarde. confirmation_documentation est la
# première règle. D'autres suivront.

def confirmation_documentation(resultats):
    """Sous-fonction pré-sauvegarde #1 : rappel de documentation.

    Compare deux valeurs :
    1. Le flag interne _documentation_requise (mis à True par les compilations
       si des changements ont été détectés)
    2. Le résultat de l'étape Documentation dans le quiz (dernière rangée
       du tableau des résultats — le dernier knowledge au niveau principal)

    Logique de comparaison :
    - Flag False → passe (rien à documenter, pas de changements)
    - Flag True + résultat doc "Vrai" → passe (l'utilisateur a documenté)
    - Flag True + résultat doc "--"/"Faux"/"Passer" → suggérer via
      AskUserQuestion (rappel de discipline, pas un bloqueur)

    Retourne True si pas de rappel nécessaire ou si l'utilisateur a documenté,
    False si l'utilisateur n'a pas documenté et passe le rappel.
    """
    if not _documentation_requise:
        return True

    # Chercher le dernier knowledge (étape Documentation) dans les résultats
    knowledge_names = list(resultats.keys()) if resultats else []
    if not knowledge_names:
        return True

    dernier_knowledge = knowledge_names[-1]
    resultats_doc = resultats.get(dernier_knowledge, {})

    # Vérifier si au moins une question du dernier knowledge a "Vrai"
    # (l'utilisateur a complété l'étape de documentation)
    documentation_faite = any(v == "Vrai" for v in resultats_doc.values())

    if documentation_faite:
        return True

    # Flag True + documentation non faite → rappel nécessaire
    # TODO: AskUserQuestion pour suggérer la documentation
    # L'utilisateur peut Skip — c'est un rappel, pas un bloqueur
    return False


def pre_sauvegarde(resultats):
    """Étape 9 : exécute toutes les règles de conformité pré-sauvegarde.

    Regroupe les sous-fonctions de conformité qui doivent s'exécuter
    avant la sauvegarde. Actuellement :
    1. confirmation_documentation — rappel si documentation manquante

    D'autres règles de conformité seront ajoutées ici.
    """
    confirmation_documentation(resultats)


# =============================================================================
# Sauvegarde (étape 10)
# =============================================================================

def sauvegarde(resultats):
    """Sauvegarde les résultats du knowledge. Appelée après l'affichage de la grille."""
    pass


# =============================================================================
# Construction et lancement du knowledge
# =============================================================================

def construire_knowledge():
    """Construit et enregistre tous les skills du knowledge depuis la méthodologie."""
    config = charger_methodologie()
    registre = SkillRegistry()

    # Skill utilitaire
    registre.enregistrer("lire_choix", LireChoixSkill("lire_choix"))

    # Skills actions
    registre.enregistrer("fonction", FonctionSkill("fonction"))
    registre.enregistrer("programme", ProgrammeSkill("programme"))

    # Choix du sous-knowledge depuis la config
    choix_labels = config["sous_knowledge"]["choix"]

    # Skills sous-knowledge (depuis la méthodologie)
    knowledge_config = []
    for knowledge in config["knowledge_principal"]["knowledge"]:
        lettre = knowledge["lettre"]
        question_ids = []
        for question in knowledge["questions"]:
            qid = question["id"]
            question_ids.append(qid)
            registre.enregistrer(qid, SousKnowledgeSkill(
                qid,
                action_vrai_skill=question["action_vrai"],
                message_vrai=question["message_vrai"],
                choix_labels=choix_labels
            ))
        knowledge_config.append((knowledge["nom"], lettre, question_ids))

    # Skills knowledge secondaires
    for label, lettre, questions in knowledge_config:
        registre.enregistrer(label, KnowledgeSecondaireSkill(label, lettre, questions))

    # Skill grille
    registre.enregistrer("afficher_grille", AfficherGrilleSkill(
        "afficher_grille", knowledge_config,
        config["message_fin_complet"], config["message_fin_incomplet"]))

    # Skill principal
    knowledge_secondaires = [(label, label) for label, _, _ in knowledge_config]
    registre.enregistrer("knowledge_principal", KnowledgePrincipalSkill("knowledge_principal", knowledge_secondaires))

    return registre


if __name__ == "__main__":
    registre = construire_knowledge()
    print("Skills enregistrés :", ", ".join(registre.lister()))
    print()
    registre.executer("knowledge_principal")

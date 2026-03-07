#!/usr/bin/env python3
"""Crée un nouveau projet.

Syntaxe officielle : project create [title]

Usage:
  python3 project_create.py "Mon titre de projet"
"""
import json
import os
import sys

PROJECTS_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".claude", "projects.json")


def charger_projets():
    """Charge la liste des projets existants."""
    if os.path.exists(PROJECTS_PATH):
        with open(PROJECTS_PATH, "r") as f:
            return json.load(f)
    return {"projets": []}


def sauvegarder_projets(data):
    """Sauvegarde la liste des projets."""
    os.makedirs(os.path.dirname(PROJECTS_PATH), exist_ok=True)
    with open(PROJECTS_PATH, "w") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def main():
    if len(sys.argv) < 2 or not sys.argv[1].strip():
        print("Erreur : titre du projet manquant.")
        print("Usage : python3 project_create.py \"Mon titre de projet\"")
        sys.exit(1)

    titre = sys.argv[1].strip()

    data = charger_projets()

    # Vérifier doublon
    for projet in data["projets"]:
        if projet["titre"].lower() == titre.lower():
            print(f"Erreur : un projet avec le titre \"{titre}\" existe déjà.")
            sys.exit(1)

    # Créer le projet
    nouveau_id = len(data["projets"]) + 1
    projet = {
        "id": nouveau_id,
        "titre": titre,
    }

    data["projets"].append(projet)
    sauvegarder_projets(data)

    print(f"Projet créé : [{nouveau_id}] {titre}")
    sys.exit(0)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Routeur de demandes utilisateur.

Analyse la chaîne de l'utilisateur, cherche des mots-clés correspondant
à une route dans .claude/routes.json, et exécute le programme associé.

- Si un mot-clé est trouvé → exécute le programme → retourne son code
- Si aucun mot-clé ne correspond → Faux immédiatement (demande non reconnue)

Maintient un journal d'actions dans .claude/journal_actions.json
pour permettre le rollback en cas d'échec.

Usage:
  python3 executer_demande.py "demande de l'utilisateur"
  python3 executer_demande.py --rollback
"""
import json
import os
import subprocess
import sys

TIMEOUT_SECONDS = 60
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
JOURNAL_PATH = os.path.join(BASE_DIR, ".claude", "journal_actions.json")
ROUTES_PATH = os.path.join(BASE_DIR, ".claude", "routes.json")


def charger_journal():
    """Charge le journal d'actions existant ou en crée un nouveau."""
    if os.path.exists(JOURNAL_PATH):
        with open(JOURNAL_PATH, "r") as f:
            return json.load(f)
    return {"actions": []}


def sauvegarder_journal(journal):
    """Sauvegarde le journal d'actions."""
    os.makedirs(os.path.dirname(JOURNAL_PATH), exist_ok=True)
    with open(JOURNAL_PATH, "w") as f:
        json.dump(journal, f, indent=2, ensure_ascii=False)


def enregistrer_action(journal, type_action, details):
    """Enregistre une action dans le journal pour rollback éventuel."""
    journal["actions"].append({
        "type": type_action,
        "details": details,
    })
    sauvegarder_journal(journal)


def rollback():
    """Annule les actions enregistrées dans le journal (ordre inverse)."""
    journal = charger_journal()
    actions = journal.get("actions", [])

    if not actions:
        print("Aucune action à annuler.")
        return

    print(f"Rollback de {len(actions)} action(s)...")

    for action in reversed(actions):
        type_action = action["type"]
        details = action["details"]

        try:
            if type_action == "fichier_cree":
                chemin = details.get("chemin")
                if chemin and os.path.exists(chemin):
                    os.remove(chemin)
                    print(f"  Fichier supprimé : {chemin}")

            elif type_action == "commande_exec":
                cmd_rollback = details.get("rollback_cmd")
                if cmd_rollback:
                    subprocess.run(cmd_rollback, shell=True, capture_output=True, timeout=30)
                    print(f"  Commande rollback : {cmd_rollback}")

            elif type_action == "gh_issue_cree":
                numero = details.get("numero")
                repo = details.get("repo", "")
                if numero:
                    cmd = f"gh issue close {numero}"
                    if repo:
                        cmd += f" -R {repo}"
                    subprocess.run(cmd, shell=True, capture_output=True, timeout=30)
                    print(f"  Issue #{numero} fermée")

            elif type_action == "gh_pr_cree":
                numero = details.get("numero")
                repo = details.get("repo", "")
                if numero:
                    cmd = f"gh pr close {numero}"
                    if repo:
                        cmd += f" -R {repo}"
                    subprocess.run(cmd, shell=True, capture_output=True, timeout=30)
                    print(f"  PR #{numero} fermée")

            else:
                print(f"  Action inconnue ignorée : {type_action}")

        except Exception as e:
            print(f"  Erreur rollback ({type_action}): {e}")

    if os.path.exists(JOURNAL_PATH):
        os.remove(JOURNAL_PATH)
    print("Rollback terminé.")


def charger_routes():
    """Charge la table de routage depuis .claude/routes.json."""
    if not os.path.exists(ROUTES_PATH):
        print(f"Faux — fichier de routes introuvable : {ROUTES_PATH}")
        return None
    with open(ROUTES_PATH, "r") as f:
        return json.load(f)


def trouver_route(demande, routes):
    """Cherche une route dont un mot-clé correspond à la demande.

    Retourne la première route trouvée, ou None.
    """
    demande_lower = demande.lower()
    for route in routes.get("routes", []):
        for mot_cle in route.get("mots_cles", []):
            if mot_cle.lower() in demande_lower:
                return route
    return None


def main():
    if len(sys.argv) < 2:
        print("Faux — aucune demande fournie.")
        sys.exit(1)

    # Mode rollback
    if sys.argv[1] == "--rollback":
        rollback()
        sys.exit(0)

    demande = sys.argv[1]
    if not demande.strip():
        print("Faux — demande vide.")
        sys.exit(1)

    # Charger les routes
    config_routes = charger_routes()
    if config_routes is None:
        sys.exit(1)

    # Chercher une route correspondante
    route = trouver_route(demande, config_routes)

    if route is None:
        print(f"Faux — aucun programme ne correspond à cette demande.")
        print(f"Demande reçue : \"{demande}\"")
        print("Aucun mot-clé reconnu dans la table de routage.")
        sys.exit(1)

    # Route trouvée — exécuter le programme associé
    programme = route["programme"]
    route_id = route.get("id", "inconnu")
    description = route.get("description", "")

    print(f"Route trouvée : [{route_id}] {description}")
    print(f"Programme : {programme}")

    # Initialiser le journal
    journal = {"actions": []}
    sauvegarder_journal(journal)

    enregistrer_action(journal, "commande_exec", {
        "route_id": route_id,
        "commande": programme,
        "demande_originale": demande,
        "rollback_cmd": None,
    })

    try:
        resultat = subprocess.run(
            programme,
            shell=True,
            capture_output=True,
            text=True,
            timeout=TIMEOUT_SECONDS,
        )

        if resultat.stdout.strip():
            print(resultat.stdout.strip())

        if resultat.returncode != 0:
            stderr = resultat.stderr.strip()
            if stderr:
                print(f"Faux — erreur détectée : {stderr}")
            else:
                print(f"Faux — code de retour : {resultat.returncode}")
            sys.exit(1)

        print("Vrai — exécution réussie.")
        sys.exit(0)

    except subprocess.TimeoutExpired:
        print(f"Faux — délai d'attente dépassé ({TIMEOUT_SECONDS}s).")
        sys.exit(1)

    except OSError as e:
        print(f"Faux — impossible de lancer le processus : {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()

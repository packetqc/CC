#!/usr/bin/env python3
"""Exécuteur de demandes utilisateur.

Deux modes d'utilisation :

1. --route <id> : exécute directement le programme associé à la route
   (la classification d'intention est faite par Claude dans le skill)
2. --list-routes : affiche les routes disponibles (pour que Claude puisse classifier)
3. --rollback : annule les actions du journal

Maintient un journal d'actions dans .claude/journal_actions.json
pour permettre le rollback en cas d'échec.

Usage:
  python3 executer_demande.py --route build
  python3 executer_demande.py --list-routes
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


def lister_routes():
    """Affiche les routes disponibles pour la classification IA."""
    config = charger_routes()
    if config is None:
        sys.exit(1)

    routes = config.get("routes", [])
    if not routes:
        print("Aucune route configurée.")
        sys.exit(1)

    for route in routes:
        route_id = route.get("id", "?")
        description = route.get("description", "")
        mots_cles = ", ".join(route.get("mots_cles", []))
        print(f"[{route_id}] {description} (indices: {mots_cles})")


def trouver_route_par_id(route_id, config):
    """Trouve une route par son identifiant."""
    for route in config.get("routes", []):
        if route.get("id") == route_id:
            return route
    return None


def executer_route(route):
    """Exécute le programme associé à une route."""
    programme = route["programme"]
    route_id = route.get("id", "inconnu")
    description = route.get("description", "")

    print(f"Route : [{route_id}] {description}")
    print(f"Programme : {programme}")

    # Initialiser le journal
    journal = {"actions": []}
    sauvegarder_journal(journal)

    enregistrer_action(journal, "commande_exec", {
        "route_id": route_id,
        "commande": programme,
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


def main():
    if len(sys.argv) < 2:
        print("Faux — aucun argument fourni.")
        print("Usage: --route <id> | --list-routes | --rollback")
        sys.exit(1)

    arg = sys.argv[1]

    # Mode rollback
    if arg == "--rollback":
        rollback()
        sys.exit(0)

    # Mode liste des routes
    if arg == "--list-routes":
        lister_routes()
        sys.exit(0)

    # Mode exécution par route ID
    if arg == "--route":
        if len(sys.argv) < 3:
            print("Faux — identifiant de route manquant.")
            print("Usage: python3 executer_demande.py --route <id>")
            sys.exit(1)

        route_id = sys.argv[2]
        config = charger_routes()
        if config is None:
            sys.exit(1)

        route = trouver_route_par_id(route_id, config)
        if route is None:
            print(f"Faux — route '{route_id}' introuvable.")
            print("Routes disponibles :")
            lister_routes()
            sys.exit(1)

        executer_route(route)

    else:
        print(f"Faux — argument inconnu : {arg}")
        print("Usage: --route <id> | --list-routes | --rollback")
        sys.exit(1)


if __name__ == "__main__":
    main()

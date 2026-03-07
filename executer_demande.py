#!/usr/bin/env python3
"""Programme qui exécute la demande initiale de l'utilisateur.

Reçoit une chaîne de caractères en paramètre, lance un sous-processus
pour l'exécuter, surveille son exécution et retourne :
- Code 0 (Vrai) si l'exécution s'est bien passée
- Code 1 (Faux) si un problème est détecté (timeout, crash, erreur)

Maintient un journal d'actions dans .claude/journal_actions.json
pour permettre le rollback en cas d'échec.

Usage:
  python3 executer_demande.py "commande"       # Exécuter une commande
  python3 executer_demande.py --rollback        # Annuler les actions du journal
"""
import json
import os
import subprocess
import sys

TIMEOUT_SECONDS = 60
JOURNAL_PATH = os.path.join(os.path.dirname(__file__), ".claude", "journal_actions.json")


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

    # Nettoyer le journal après rollback
    if os.path.exists(JOURNAL_PATH):
        os.remove(JOURNAL_PATH)
    print("Rollback terminé.")


def main():
    if len(sys.argv) < 2:
        print("Faux — aucune commande fournie.")
        sys.exit(1)

    # Mode rollback
    if sys.argv[1] == "--rollback":
        rollback()
        sys.exit(0)

    commande = sys.argv[1]
    if not commande.strip():
        print("Faux — commande vide.")
        sys.exit(1)

    # Initialiser le journal pour cette exécution
    journal = {"actions": []}
    sauvegarder_journal(journal)

    # Enregistrer la commande principale comme action
    enregistrer_action(journal, "commande_exec", {
        "commande": commande,
        "rollback_cmd": None,
    })

    try:
        resultat = subprocess.run(
            commande,
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

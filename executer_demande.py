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
import hashlib
import json
import os
import subprocess
import sys
import time

TIMEOUT_SECONDS = 60
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
JOURNAL_PATH = os.path.join(BASE_DIR, ".claude", "journal_actions.json")
ROUTES_PATH = os.path.join(BASE_DIR, ".claude", "routes.json")
PREUVE_PATH = os.path.join(BASE_DIR, ".claude", "preuve_execution.json")
CHECKPOINT_PATH = os.path.join(BASE_DIR, ".claude", "checkpoint_execution.json")


def ecrire_preuve(route_id, resultat_code, programme):
    """Écrit un fichier de preuve d'exécution vérifiable.

    Ce fichier prouve que executer_demande.py a réellement tourné.
    Il contient un hash basé sur le timestamp + route_id + pid,
    impossible à deviner ou fabriquer par Claude.
    """
    timestamp = time.time()
    pid = os.getpid()
    token_source = f"{timestamp}-{route_id}-{pid}-{programme}"
    token = hashlib.sha256(token_source.encode()).hexdigest()[:16]

    preuve = {
        "execution_reelle": True,
        "route_id": route_id,
        "programme": programme,
        "code_retour": resultat_code,
        "timestamp": timestamp,
        "pid": pid,
        "token": token,
    }

    os.makedirs(os.path.dirname(PREUVE_PATH), exist_ok=True)
    with open(PREUVE_PATH, "w") as f:
        json.dump(preuve, f, indent=2, ensure_ascii=False)


def supprimer_preuve():
    """Supprime le fichier de preuve (nettoyage)."""
    if os.path.exists(PREUVE_PATH):
        os.remove(PREUVE_PATH)


def ecrire_checkpoint(phase, route_id=None, demande=None, details=None):
    """Écrit un checkpoint pour survivre à une compaction de session.

    Phases :
    - "pre_execution"  : avant de lancer le programme (on sait quoi faire)
    - "en_cours"       : le programme est en train de tourner
    - "termine"        : le programme a fini (résultat disponible dans preuve)
    - "rollback"       : un rollback est en cours
    """
    checkpoint = {
        "phase": phase,
        "route_id": route_id,
        "demande": demande,
        "timestamp": time.time(),
        "details": details or {},
    }
    os.makedirs(os.path.dirname(CHECKPOINT_PATH), exist_ok=True)
    with open(CHECKPOINT_PATH, "w") as f:
        json.dump(checkpoint, f, indent=2, ensure_ascii=False)


def charger_checkpoint():
    """Charge le checkpoint s'il existe."""
    if os.path.exists(CHECKPOINT_PATH):
        with open(CHECKPOINT_PATH, "r") as f:
            return json.load(f)
    return None


def supprimer_checkpoint():
    """Supprime le checkpoint (nettoyage après succès)."""
    if os.path.exists(CHECKPOINT_PATH):
        os.remove(CHECKPOINT_PATH)


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
        syntaxe = route.get("syntaxe", "")
        mots_cles = ", ".join(route.get("mots_cles", []))
        parametres = route.get("parametres", [])
        params_str = ""
        if parametres:
            params_list = []
            for p in parametres:
                req = "obligatoire" if p.get("obligatoire") else "optionnel"
                params_list.append(f"{p['nom']} ({req}: {p.get('description', '')})")
            params_str = f" | paramètres: {', '.join(params_list)}"
        print(f"[{route_id}] {description} | syntaxe: {syntaxe} | indices: {mots_cles}{params_str}")


def trouver_route_par_id(route_id, config):
    """Trouve une route par son identifiant."""
    for route in config.get("routes", []):
        if route.get("id") == route_id:
            return route
    return None


def executer_route(route, args=None, context=None):
    """Exécute le programme associé à une route avec ses arguments et contexte.

    Args:
        route: La route à exécuter
        args: Les arguments extraits de la demande (ex: titre du projet)
        context: JSON des réponses précédentes du knowledge (ex: {"A1":"Vrai","A2":"Faux"})
    """
    programme = route["programme"]
    if args:
        args_escaped = args.replace('"', '\\"')
        programme = f'{programme} "{args_escaped}"'
    route_id = route.get("id", "inconnu")
    description = route.get("description", "")

    # Préparer les variables d'environnement avec le contexte
    env = os.environ.copy()
    if context:
        env["KNOWLEDGE_CONTEXT"] = context
        # Parser le JSON pour créer des variables individuelles
        try:
            ctx = json.loads(context)
            for question_id, reponse in ctx.items():
                env[f"KNW_{question_id.upper()}"] = reponse
        except json.JSONDecodeError:
            print(f"Attention : contexte JSON invalide, ignoré : {context}")

    print(f"Route : [{route_id}] {description}")
    print(f"Programme : {programme}")

    # Supprimer toute preuve précédente
    supprimer_preuve()

    # Checkpoint AVANT exécution — survit à une compaction
    ecrire_checkpoint("pre_execution", route_id=route_id, details={
        "programme": programme,
        "description": description,
    })

    # Initialiser le journal
    journal = {"actions": []}
    sauvegarder_journal(journal)

    enregistrer_action(journal, "commande_exec", {
        "route_id": route_id,
        "commande": programme,
        "rollback_cmd": None,
    })

    # Checkpoint EN COURS — le programme tourne
    ecrire_checkpoint("en_cours", route_id=route_id, details={
        "programme": programme,
        "description": description,
    })

    try:
        resultat = subprocess.run(
            programme,
            shell=True,
            capture_output=True,
            text=True,
            timeout=TIMEOUT_SECONDS,
            env=env,
        )

        if resultat.stdout.strip():
            print(resultat.stdout.strip())

        if resultat.returncode != 0:
            stderr = resultat.stderr.strip()
            if stderr:
                print(f"Faux — erreur détectée : {stderr}")
            else:
                print(f"Faux — code de retour : {resultat.returncode}")
            ecrire_preuve(route_id, resultat.returncode, programme)
            ecrire_checkpoint("termine", route_id=route_id, details={
                "programme": programme,
                "code_retour": resultat.returncode,
                "resultat": "Faux",
            })
            sys.exit(1)

        ecrire_preuve(route_id, 0, programme)
        ecrire_checkpoint("termine", route_id=route_id, details={
            "programme": programme,
            "code_retour": 0,
            "resultat": "Vrai",
        })
        print("Vrai — exécution réussie.")
        sys.exit(0)

    except subprocess.TimeoutExpired:
        ecrire_preuve(route_id, -1, programme)
        ecrire_checkpoint("termine", route_id=route_id, details={
            "programme": programme,
            "code_retour": -1,
            "resultat": "Faux",
            "erreur": "timeout",
        })
        print(f"Faux — délai d'attente dépassé ({TIMEOUT_SECONDS}s).")
        sys.exit(1)

    except OSError as e:
        ecrire_preuve(route_id, -2, programme)
        ecrire_checkpoint("termine", route_id=route_id, details={
            "programme": programme,
            "code_retour": -2,
            "resultat": "Faux",
            "erreur": str(e),
        })
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
        supprimer_checkpoint()
        sys.exit(0)

    # Mode statut du checkpoint
    if arg == "--status":
        cp = charger_checkpoint()
        if cp is None:
            print("Aucune exécution en cours ou récente.")
            sys.exit(0)
        print(json.dumps(cp, indent=2, ensure_ascii=False))
        sys.exit(0)

    # Mode liste des routes
    if arg == "--list-routes":
        lister_routes()
        sys.exit(0)

    # Mode exécution par route ID
    if arg == "--route":
        if len(sys.argv) < 3:
            print("Faux — identifiant de route manquant.")
            print('Usage: python3 executer_demande.py --route <id> [--args "valeur"] [--context \'{"A1":"Vrai"}\']')
            sys.exit(1)

        route_id = sys.argv[2]

        # Parser les arguments nommés (--args, --context)
        route_args = None
        route_context = None
        i = 3
        while i < len(sys.argv):
            if sys.argv[i] == "--args" and i + 1 < len(sys.argv):
                route_args = sys.argv[i + 1]
                i += 2
            elif sys.argv[i] == "--context" and i + 1 < len(sys.argv):
                route_context = sys.argv[i + 1]
                i += 2
            else:
                i += 1

        config = charger_routes()
        if config is None:
            sys.exit(1)

        route = trouver_route_par_id(route_id, config)
        if route is None:
            print(f"Faux — route '{route_id}' introuvable.")
            print("Routes disponibles :")
            lister_routes()
            sys.exit(1)

        # Vérifier les paramètres obligatoires
        parametres = route.get("parametres", [])
        params_obligatoires = [p for p in parametres if p.get("obligatoire")]
        if params_obligatoires and not route_args:
            print("Faux — paramètre(s) obligatoire(s) manquant(s) :")
            for p in params_obligatoires:
                print(f"  - {p['nom']} : {p.get('description', '')}")
            print(f"Usage: python3 executer_demande.py --route {route_id} --args \"valeur\"")
            sys.exit(1)

        executer_route(route, args=route_args, context=route_context)

    else:
        print(f"Faux — argument inconnu : {arg}")
        print("Usage: --route <id> | --list-routes | --rollback")
        sys.exit(1)


if __name__ == "__main__":
    main()

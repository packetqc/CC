#!/usr/bin/env python3
"""Programme qui exécute la demande initiale de l'utilisateur.

Reçoit une chaîne de caractères en paramètre, lance un sous-processus
pour l'exécuter, surveille son exécution et retourne :
- Code 0 (Vrai) si l'exécution s'est bien passée
- Code 1 (Faux) si un problème est détecté (timeout, crash, erreur)
"""
import subprocess
import sys

TIMEOUT_SECONDS = 60


def main():
    if len(sys.argv) < 2 or not sys.argv[1].strip():
        print("Faux — aucune commande fournie.")
        sys.exit(1)

    commande = sys.argv[1]

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

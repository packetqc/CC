#!/usr/bin/env python3
"""Programme externe appelé par certaines questions du quiz."""
import sys


def main():
    nom = sys.argv[1] if len(sys.argv) > 1 else "inconnu"
    print(f"      >>> Je suis le PROGRAMME EXTERNE qui a été appelé pour '{nom}'.")
    print(f"      >>> Traitement en cours pour {nom}...")
    print(f"      >>> Traitement terminé. Retour au quiz.")


if __name__ == "__main__":
    main()

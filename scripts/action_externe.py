#!/usr/bin/env python3
"""Programme externe appelé par certaines questions du knowledge."""
import sys


def main():
    nom = sys.argv[1] if len(sys.argv) > 1 else "inconnu"
    print(f"      >>> Je suis le programme {nom}.")


if __name__ == "__main__":
    main()

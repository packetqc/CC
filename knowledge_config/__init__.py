"""Module de chargement de la méthodologie du knowledge depuis un fichier Markdown.

Supporte le format bilingue (FR/EN). La langue est sélectionnée via le
paramètre `langue` de charger_methodologie() — "fr" par défaut.

Format des tableaux (6 colonnes) :
| ID | Choix FR | Choix EN | Action | Message FR | Message EN |
"""
import os
import re


def _extraire_bilingue(texte):
    """Extrait les versions FR et EN d'un texte bilingue.

    Formats supportés :
    - "FR: texte fr\\nEN: texte en" → {"fr": "texte fr", "en": "texte en"}
    - "texte simple" → {"fr": "texte simple", "en": "texte simple"}
    """
    result = {"fr": texte, "en": texte}
    m_fr = re.search(r"^FR:\s*(.+)$", texte, re.MULTILINE)
    m_en = re.search(r"^EN:\s*(.+)$", texte, re.MULTILINE)
    if m_fr:
        result["fr"] = m_fr.group(1).strip()
    if m_en:
        result["en"] = m_en.group(1).strip()
    return result


def _extraire_header_knowledge(header):
    """Extrait les noms FR/EN, la lettre et la methodology d'un header de knowledge.

    Format : "Nom FR | Nom EN (lettre: X, methodology: nom)"
    Le champ methodology est optionnel.
    Retourne (nom_fr, nom_en, lettre, methodology)
    """
    # Extraire le bloc entre parenthèses
    m = re.match(r"(.+?)\s*\((.+)\)", header)
    if not m:
        return header, header, "", None

    nom_part = m.group(1).strip()
    params_part = m.group(2).strip()

    # Extraire nom_fr | nom_en
    if "|" in nom_part:
        parts = [p.strip() for p in nom_part.split("|")]
        nom_fr, nom_en = parts[0], parts[1] if len(parts) > 1 else parts[0]
    else:
        nom_fr = nom_en = nom_part

    # Extraire les paramètres (lettre, methodology, etc.)
    params = {}
    for param in params_part.split(","):
        if ":" in param:
            key, val = param.split(":", 1)
            params[key.strip().lower()] = val.strip()

    lettre = params.get("lettre", "")
    methodology = params.get("methodology", None)

    return nom_fr, nom_en, lettre, methodology


def _parser_header_tableau(ligne_header):
    """Parse le header d'un tableau pour détecter les colonnes disponibles.

    Retourne un dict mappant nom_normalisé → index.
    Ex: {"id": 0, "choix_fr": 1, "choix_en": 2, "action": 3, "message_fr": 4, "message_en": 5}
    """
    colonnes = [c.strip().lower() for c in ligne_header.split("|")]
    colonnes = [c for c in colonnes if c]

    mapping = {}
    for i, col in enumerate(colonnes):
        if col == "id":
            mapping["id"] = i
        elif col in ("choix fr", "label fr"):
            mapping["choix_fr"] = i
        elif col in ("choix en", "label en"):
            mapping["choix_en"] = i
        elif col == "action":
            mapping["action"] = i
        elif col in ("message fr", "message"):
            mapping["message_fr"] = i
        elif col == "message en":
            mapping["message_en"] = i

    return mapping


def charger_methodologie(chemin=None, langue="fr"):
    """Charge la méthodologie du knowledge depuis le fichier Markdown.

    Args:
        chemin: Chemin vers le fichier methodology-knowledge.md
        langue: "fr" ou "en" — sélectionne les messages dans la langue choisie

    Retourne un dictionnaire avec la structure :
    {
        "titre": "...",
        "message_fin_complet": "...",
        "message_fin_incomplet": "...",
        "knowledge_principal": {
            "titre": "Knowledge Principal",
            "knowledge": [{"nom": "...", "lettre": "...", "questions": [...]}]
        },
        "sous_knowledge": {"choix": ["Vrai", "Faux", "Passer"]}
    }

    Chaque question contient : id, choix (label bilingue), action_vrai, message_vrai
    Chaque knowledge peut contenir : methodology (nom du fichier dans methodology/)
    """
    if chemin is None:
        chemin = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                              "..", "methodology", "methodology-knowledge.md")

    with open(chemin, "r", encoding="utf-8") as f:
        contenu = f.read()

    config = {
        "titre": "",
        "message_fin_complet": "",
        "message_fin_incomplet": "",
        "knowledge_principal": {"titre": "Knowledge Principal", "knowledge": []},
        "sous_knowledge": {"choix": []},
    }

    # Titre principal (# ...) — peut contenir FR | EN
    m = re.search(r"^# (.+)$", contenu, re.MULTILINE)
    if m:
        titre_raw = m.group(1).strip()
        if "|" in titre_raw:
            parts = [p.strip() for p in titre_raw.split("|")]
            config["titre"] = parts[0] if langue == "fr" else parts[1] if len(parts) > 1 else parts[0]
        else:
            config["titre"] = titre_raw

    # Message de fin complet (bilingue FR:/EN:)
    m = re.search(r"## Message de fin complet\s*\n\s*\n(.+?)(?:\n\s*\n|\Z)",
                  contenu, re.DOTALL)
    if m:
        versions = _extraire_bilingue(m.group(1).strip())
        config["message_fin_complet"] = versions[langue]

    # Message de fin incomplet (bilingue FR:/EN:)
    m = re.search(r"## Message de fin incomplet\s*\n\s*\n(.+?)(?:\n\s*\n|\Z)",
                  contenu, re.DOTALL)
    if m:
        versions = _extraire_bilingue(m.group(1).strip())
        config["message_fin_incomplet"] = versions[langue]

    # Choix du sous-knowledge (bilingue FR:/EN:)
    m = re.search(r"## Choix du sous-knowledge\s*\n\s*\n(.+?)(?:\n\s*\n|\Z)",
                  contenu, re.DOTALL)
    if m:
        bloc = m.group(1).strip()
        versions = _extraire_bilingue(bloc)
        config["sous_knowledge"]["choix"] = [
            c.strip() for c in versions[langue].split(",")
        ]

    # Knowledge : sections ### ... (lettre: X[, methodology: nom]) avec tableaux
    pattern_knowledge = r"### (.+? \(lettre: .+?\))\s*\n(.*?)(?=\n### |\Z)"
    for match in re.finditer(pattern_knowledge, contenu, re.DOTALL):
        header = match.group(1).strip()
        nom_fr, nom_en, lettre, methodology = _extraire_header_knowledge(header)
        nom = nom_fr if langue == "fr" else nom_en
        bloc_tableau = match.group(2)

        # Détecter les colonnes depuis le header du tableau
        col_map = None
        for ligne in bloc_tableau.strip().splitlines():
            if ligne.strip().lower().startswith("| id"):
                col_map = _parser_header_tableau(ligne)
                break

        # Fallback ancien format 3 colonnes : ID, Action, Message
        if not col_map:
            col_map = {"id": 0, "action": 1, "message_fr": 2}

        questions = []
        for ligne in bloc_tableau.strip().splitlines():
            ligne = ligne.strip()
            if not ligne.startswith("|") or ligne.lower().startswith("| id") or ligne.startswith("|--"):
                continue
            colonnes = [c.strip() for c in ligne.split("|")]
            colonnes = [c for c in colonnes if c]

            qid = colonnes[col_map["id"]] if "id" in col_map else ""
            action = colonnes[col_map["action"]] if "action" in col_map else ""

            # Choix (label affiché dans AskUserQuestion)
            choix_fr = colonnes[col_map["choix_fr"]] if "choix_fr" in col_map and col_map["choix_fr"] < len(colonnes) else qid
            choix_en = colonnes[col_map["choix_en"]] if "choix_en" in col_map and col_map["choix_en"] < len(colonnes) else choix_fr
            choix = choix_fr if langue == "fr" else choix_en

            # Message (affiché quand Vrai)
            msg_fr = colonnes[col_map["message_fr"]] if "message_fr" in col_map and col_map["message_fr"] < len(colonnes) else ""
            msg_en = colonnes[col_map["message_en"]] if "message_en" in col_map and col_map["message_en"] < len(colonnes) else msg_fr
            message = msg_fr if langue == "fr" else msg_en

            questions.append({
                "id": qid,
                "choix": choix,
                "action_vrai": action,
                "message_vrai": message,
            })

        knowledge_entry = {
            "nom": nom,
            "lettre": lettre,
            "questions": questions,
        }
        if methodology:
            knowledge_entry["methodology"] = methodology
        config["knowledge_principal"]["knowledge"].append(knowledge_entry)

    return config

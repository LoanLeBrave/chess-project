#!/usr/bin/env python3
"""
Lecture du fichier game_state.json.

Fournit un acces instantane a l'etat du plateau
produit par infinite_chess_vision.py (mis a jour toutes les ~2 s).
"""

import json
import os
from datetime import datetime
from typing import Optional

from .config import GAME_STATE_PATH


def read_game_state(path: str = GAME_STATE_PATH) -> Optional[dict]:
    """
    Lit et retourne le contenu de game_state.json.

    Returns:
        dict du game_state ou None si le fichier est absent / invalide.
    """
    if not os.path.exists(path):
        print(f"  [!] Fichier introuvable : {path}")
        return None

    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (json.JSONDecodeError, OSError) as exc:
        print(f"  [!] Lecture impossible : {exc}")
        return None

    return data


def get_board_map(game_state: dict) -> dict:
    """
    Construit un mapping {case: code_piece} a partir du game_state.

    Exemple : {"a1": "WR", "e2": "WP", ...}
    Les cases vides ne sont pas presentes dans le dict.
    """
    board = {}
    for piece in game_state.get("pieces", []):
        if piece.get("zone") != "board":
            continue
        chess_pos = piece.get("position", {}).get("chess")
        if not chess_pos:
            continue
        code = piece.get("code", "??")
        # Normaliser le code pour l'affichage : 1er char = couleur, 2e = type
        color_char = "W" if piece.get("color") == "white" else "B"
        type_char = piece.get("type", "Pawn")[0]  # P, K, Q, R, B, N
        if piece.get("type") == "Knight":
            type_char = "N"
        board[chess_pos.lower()] = f"{color_char}{type_char}"
    return board


def find_piece_at(game_state: dict, square: str) -> Optional[dict]:
    """
    Retourne les donnees de la piece situee sur `square`, ou None.

    Args:
        game_state: dict complet issu de game_state.json.
        square: notation algebrique (ex: "e2").
    """
    for piece in game_state.get("pieces", []):
        if piece.get("zone") != "board":
            continue
        chess_pos = piece.get("position", {}).get("chess")
        if chess_pos and chess_pos.lower() == square.lower():
            return piece
    return None


def get_metadata(game_state: dict) -> dict:
    """Retourne la section metadata du game_state."""
    return game_state.get("metadata", {})


def format_age(game_state: dict) -> str:
    """
    Retourne un texte indiquant la fraicheur des donnees.

    Exemple : "Donnees actualisees il y a 3s"
    """
    ts_str = game_state.get("metadata", {}).get("timestamp")
    if not ts_str:
        return "Horodatage inconnu"

    try:
        ts = datetime.fromisoformat(ts_str)
        delta = datetime.now() - ts
        seconds = int(delta.total_seconds())
        if seconds < 2:
            return "Donnees a jour"
        return f"Donnees actualisees il y a {seconds}s"
    except (ValueError, TypeError):
        return "Horodatage invalide"

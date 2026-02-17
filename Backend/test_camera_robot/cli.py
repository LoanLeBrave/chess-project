#!/usr/bin/env python3
"""
Interface en ligne de commande (CLI).

Gere la boucle interactive : lecture des commandes utilisateur,
parsing, dispatch vers les bons modules.
Rafraichissement automatique du plateau toutes les secondes.
"""

import sys
import asyncio
from typing import Tuple

from .config import SQUARE_PATTERN
from .board_reader import read_game_state, get_board_map, find_piece_at, format_age, get_metadata
from .board_display import render_board
from .robot_bridge import RobotBridge
from .terminal_ui import TerminalUI


# ---------------------------------------------------------------------------
#  Parsing des commandes
# ---------------------------------------------------------------------------

def parse_command(user_input: str) -> Tuple:
    """
    Interprete la saisie utilisateur.

    Returns:
        ("quit",)
        ("refresh",)
        ("status",)
        ("debug",)
        ("move", from_sq, to_sq)
        ("help",)
        ("invalid",)
    """
    # Nettoyer les caracteres non-ASCII (artefacts terminal Raspberry Pi)
    text = "".join(c for c in user_input if c.isascii()).strip().lower()

    if not text:
        return ("invalid",)

    if text in ("quit", "q", "exit"):
        return ("quit",)

    if text in ("refresh", "r", "photo", "p", "capture"):
        return ("refresh",)

    if text in ("status", "s", "info"):
        return ("status",)

    if text in ("debug", "d"):
        return ("debug",)

    if text in ("help", "h", "?"):
        return ("help",)

    # Tenter de parser un mouvement : "e2 e4" ou "e2e4"
    parts = text.split()
    if len(parts) == 2:
        from_sq, to_sq = parts
    elif len(parts) == 1 and len(text) == 4:
        from_sq, to_sq = text[:2], text[2:]
    else:
        return ("invalid",)

    if SQUARE_PATTERN.match(from_sq) and SQUARE_PATTERN.match(to_sq):
        return ("move", from_sq, to_sq)

    return ("invalid",)


# ---------------------------------------------------------------------------
#  Affichage d'aide
# ---------------------------------------------------------------------------

# (L'aide est maintenant affichee via TerminalUI dans _show_help)


# ---------------------------------------------------------------------------
#  Boucle interactive
# ---------------------------------------------------------------------------

async def run(robot: RobotBridge) -> None:
    """
    Boucle principale du CLI avec rafraichissement automatique.

    Lance deux tâches en parallèle :
    - Rafraichissement automatique du plateau (1 Hz)
    - Gestion des commandes utilisateur
    """
    ui = TerminalUI()
    ui.init_display()

    # État partagé
    stop_event = asyncio.Event()
    game_state = {"data": None}

    # Tâche de rafraichissement automatique
    async def auto_refresh():
        """Met à jour l'affichage du plateau toutes les secondes."""
        while not stop_event.is_set():
            state = read_game_state()
            if state:
                game_state["data"] = state
                board_map = get_board_map(state)
                board_text = render_board(board_map)
                
                pieces_on_board = sum(1 for p in state.get("pieces", []) if p.get("zone") == "board")
                freshness = format_age(state)
                status = f"{pieces_on_board} pieces | {freshness}"
                
                ui.update_board(board_text, status)
            
            try:
                await asyncio.wait_for(stop_event.wait(), timeout=1.0)
            except asyncio.TimeoutError:
                pass

    # Tâche de gestion des commandes
    async def input_handler():
        """Gère les commandes utilisateur."""
        loop = asyncio.get_event_loop()
        
        # Afficher le prompt initial
        ui.position_input_line()
        
        while not stop_event.is_set():
            try:
                # Lecture non-bloquante de stdin
                raw = await loop.run_in_executor(None, sys.stdin.buffer.readline)
                user_input = raw.decode("utf-8", errors="ignore").strip()
                
                if not user_input:
                    ui.position_input_line()
                    continue

                command = parse_command(user_input)
                
                # -- Quit ------------------------------------------------
                if command[0] == "quit":
                    ui.write_message("Arret du programme...")
                    stop_event.set()
                    break
                
                # -- Refresh ---------------------------------------------
                elif command[0] == "refresh":
                    ui.write_message("Rafraichissement force...")
                
                # -- Status ----------------------------------------------
                elif command[0] == "status":
                    if game_state["data"]:
                        _show_status(ui, game_state["data"])
                    else:
                        ui.write_message("Aucun etat charge.")
                
                # -- Debug -----------------------------------------------
                elif command[0] == "debug":
                    await _show_debug(ui, stop_event)
                
                # -- Help ------------------------------------------------
                elif command[0] == "help":
                    _show_help(ui)
                
                # -- Move ------------------------------------------------
                elif command[0] == "move":
                    await _handle_move(ui, robot, game_state, command)
                
                # -- Invalide --------------------------------------------
                elif command[0] == "invalid":
                    ui.write_message("Commande invalide. Tapez 'help'.")
                
                # Reafficher le prompt
                ui.position_input_line()
                
            except (KeyboardInterrupt, EOFError):
                stop_event.set()
                break
    
    # Lancer les deux tâches en parallèle
    try:
        await asyncio.gather(
            auto_refresh(),
            input_handler()
        )
    finally:
        ui.cleanup()


# ---------------------------------------------------------------------------
#  Handlers de commandes
# ---------------------------------------------------------------------------

async def _handle_move(ui: TerminalUI, robot: RobotBridge, game_state: dict, command: Tuple):
    """Traite une command de mouvement."""
    _, from_sq, to_sq = command
    
    state = game_state.get("data")
    if state is None:
        ui.write_message("Aucun etat charge.")
        return
    
    piece = find_piece_at(state, from_sq)
    if piece is None:
        ui.write_message(f"Aucune piece sur {from_sq}.")
        return
    
    ui.write_message(f"Mouvement : {from_sq} -> {to_sq}...")
    
    try:
        await robot.move_piece(piece, to_sq)
        ui.write_message(f"Mouvement {from_sq}->{to_sq} termine !")
    except Exception as exc:
        ui.write_message(f"Erreur : {exc}")


def _show_status(ui: TerminalUI, state: dict) -> None:
    """Affiche les metadonnees (temporaire)."""
    meta = get_metadata(state)
    msg = (
        f"Tour: {meta.get('turn', '?')} | "
        f"Coup: {meta.get('move_count', '?')} | "
        f"Plateau: {meta.get('on_board', '?')}/{meta.get('total_detected', '?')} | "
        f"Cimetiere: {meta.get('in_cemetery', '?')}"
    )
    ui.write_message(msg)


def _show_help(ui: TerminalUI) -> None:
    """Affiche l'aide (temporaire)."""
    ui.write_message("e2e4=move | refresh | status | debug | help | quit")


async def _show_debug(ui: TerminalUI, stop_event: asyncio.Event) -> None:
    """Lance debug_display.py dans un nouveau processus."""
    import subprocess
    import os
    
    ui.write_message("Lancement debug (voir MAPPING.md pour details)...")
    
    # Pause l'auto-refresh temporairement
    stop_event.set()
    await asyncio.sleep(0.5)
    
    # Lancer debug_display.py
    debug_script = os.path.join(os.path.dirname(__file__), "debug_display.py")
    try:
        subprocess.run(["python3", debug_script])
    except Exception as exc:
        ui.write_message(f"Erreur debug: {exc}")
    
    # Reprendre l'auto-refresh
    stop_event.clear()
    ui.write_message("Retour au mode normal")


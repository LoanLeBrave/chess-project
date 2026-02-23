#!/usr/bin/env python3
"""
Script de test pour la fonction replace_board.

Lance la fonction de replacement du plateau en utilisant la vision camera.

Prerequis:
    - infinite_chess_vision doit tourner en parallele
    - Robot UR5e connecte et calibre
"""

import asyncio
import sys

from board_reset_manager import BoardResetManager
from robot_controller import RobotController


async def main():
    """Lance le replacement du plateau."""
    print("=" * 60)
    print("  TEST REPLACE BOARD - Vision Camera")
    print("=" * 60)
    print()

    # Initialiser le robot
    robot = RobotController()
    
    print("Connexion au robot...")
    if not robot.init_robot():
        print("Echec connexion robot!")
        return 1

    print("Robot connecte\n")

    # Initialiser le gestionnaire de replacement
    manager = BoardResetManager(robot)

    # Callback de log simple
    async def log_callback(log_type: str, message: str):
        prefix = {
            "info": "[INFO]",
            "warning": "[WARN]",
            "error": "[ERR] ",
            "robot": "[ROBOT]",
        }.get(log_type, "[LOG] ")
        print(f"{prefix} {message}")

    # Callback broadcast simple
    async def broadcast_callback(message: dict):
        msg_type = message.get("type", "unknown")
        if msg_type == "board_reset_started":
            print(f"\n>>> Debut replacement ({message.get('total_moves')} mouvements)\n")
        elif msg_type == "board_reset_progress":
            current = message.get("current")
            total = message.get("total")
            piece = f"{message.get('piece_color')} {message.get('piece_type')}"
            from_sq = message.get("from")
            to_sq = message.get("to")
            print(f"[{current}/{total}] {piece}: {from_sq} -> {to_sq}")
        elif msg_type == "board_reset_complete":
            print(f"\n>>> Replacement termine ({message.get('moves_executed')} mouvements)\n")
        elif msg_type == "board_reset_interrupted":
            print(f"\n>>> Replacement interrompu\n")

    manager.set_log_callback(log_callback)
    manager.set_broadcast_callback(broadcast_callback)

    # Lancer le replacement
    print("Lancement du replacement...\n")
    result = await manager.replace_board()

    print("\n" + "=" * 60)
    if result.get("success"):
        print(f"SUCCES: {result.get('message')}")
        print(f"Mouvements executes: {result.get('moves_executed')}/{result.get('total_planned')}")
    else:
        print(f"ECHEC: {result.get('error')}")
        if result.get("moves_executed") is not None:
            print(f"Mouvements partiels: {result.get('moves_executed')}/{result.get('total_planned')}")
    print("=" * 60)

    # Fermer le robot
    robot.close()
    
    return 0 if result.get("success") else 1


if __name__ == "__main__":
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n\nInterrompu par l'utilisateur")
        sys.exit(130)
    except Exception as e:
        print(f"\n\nErreur: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

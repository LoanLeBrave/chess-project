#!/usr/bin/env python3
"""
Point d'entree du package test_camera_robot.

Usage :
    cd Backend/
    python -m test_camera_robot

Pre-requis :
    - infinite_chess_vision.py doit tourner en parallele
      (produit game_state.json toutes les ~2 secondes).
    - Le robot UR5e doit etre allume et calibre.
"""

import asyncio

from .robot_bridge import RobotBridge
from .cli import run


def main() -> None:
    robot = RobotBridge()

    if not robot.connect():
        return

    try:
        asyncio.run(run(robot))
    finally:
        robot.close()
        print("Robot deconnecte. Au revoir.")


if __name__ == "__main__":
    main()

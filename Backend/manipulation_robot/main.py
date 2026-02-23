#!/usr/bin/env python3
"""
Point d'entrée principal pour l'API du robot d'échecs
"""

import uvicorn
from api import app


if __name__ == "__main__":
    print("=" * 60)
    print("    CHESS ROBOT API v2.0 ")
    print("=" * 60)
    print("\nNouvelles fonctionnalités:")
    print("  - Suivi des pièces éliminées")
    print("  - Zones d'élimination configurables")
    print("  - Reset automatique du plateau")
    print("  - Pause et Arrêt d'urgence ")
    print("\nDémarrage du serveur...")
    print("Interface: http://localhost:8000")
    print("Documentation: http://localhost:8000/docs")
    print("WebSocket: ws://localhost:8000/ws")
    print("=" * 60)

    uvicorn.run(app, host="0.0.0.0", port=8000)
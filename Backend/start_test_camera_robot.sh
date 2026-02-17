#!/bin/bash
#
# Script de demarrage du systeme de test Camera-Robot
# Lance infinite_chess_vision en arriere-plan et test_camera_robot au premier plan
#

set -e

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
BACKEND_DIR="$SCRIPT_DIR"
VISION_SCRIPT="$BACKEND_DIR/chess_vision/infinite_chess_vision.py"

echo "========================================="
echo "  TEST CAMERA-ROBOT - Demarrage"
echo "========================================="
echo ""

# Verifier que infinite_chess_vision.py existe
if [ ! -f "$VISION_SCRIPT" ]; then
    echo "ERREUR: $VISION_SCRIPT introuvable"
    exit 1
fi

# Verifier que game_state.json existe (sinon infinite_chess_vision doit tourner)
GAME_STATE="$BACKEND_DIR/chess_vision/output/latest/game_state.json"

echo "[1/2] Lancement de infinite_chess_vision en arriere-plan..."
python3 "$VISION_SCRIPT" > /dev/null 2>&1 &
VISION_PID=$!
echo "      PID: $VISION_PID"

# Attendre que game_state.json soit cree
echo "      Attente de la creation de game_state.json..."
for i in {1..10}; do
    if [ -f "$GAME_STATE" ]; then
        echo "      OK - game_state.json detecte"
        break
    fi
    sleep 1
    if [ $i -eq 10 ]; then
        echo "      ERREUR: game_state.json non cree apres 10s"
        kill $VISION_PID 2>/dev/null || true
        exit 1
    fi
done

echo ""
echo "[2/2] Lancement de test_camera_robot..."
echo ""

# Fonction de nettoyage a l'arret
cleanup() {
    echo ""
    echo "Arret de infinite_chess_vision (PID $VISION_PID)..."
    kill $VISION_PID 2>/dev/null || true
    echo "Au revoir."
}

trap cleanup EXIT INT TERM

# Lancer test_camera_robot au premier plan
cd "$BACKEND_DIR"
python3 -m test_camera_robot

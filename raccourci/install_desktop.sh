#!/bin/bash

# =============================================================================
#  Script d'installation des raccourcis sur le bureau
# =============================================================================

echo "Installation du raccourci Chess Robot sur le bureau..."

# Créer le dossier Desktop si nécessaire
mkdir -p /home/robot/Desktop

# Copier le script de lancement sur le bureau
cp start_chess_robot.sh /home/robot/Desktop/
chmod +x /home/robot/Desktop/start_chess_robot.sh

# Copier le raccourci .desktop
cp ChessRobot.desktop /home/robot/Desktop/
chmod +x /home/robot/Desktop/ChessRobot.desktop

# Rendre le .desktop "trusted" (pour éviter le popup de sécurité)
gio set /home/robot/Desktop/ChessRobot.desktop metadata::trusted true 2>/dev/null || true

echo ""
echo "✓ Installation terminée !"
echo ""
echo "Vous pouvez maintenant :"
echo "  1. Double-cliquer sur 'Chess Robot' sur le bureau"
echo "  2. Ou lancer: ~/Desktop/start_chess_robot.sh"
echo ""

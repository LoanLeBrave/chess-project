#!/bin/bash

# Script de lancement du contrôle robot UR5e
cd ~/ur_modbus

# Activation du venv
source .venv/bin/activate

# Lancement du script
python chess-project/ControlRobot/ControleRobotV2.py
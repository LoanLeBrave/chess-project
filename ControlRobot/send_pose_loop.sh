#!/usr/bin/env bash
set -euo pipefail

# --- Réglages par défaut (modifiable à l'exécution) ---
HOST="${HOST:-127.0.0.1}"   # IP de la machine qui exécute le serveur (Pi)
PORT="${PORT:-15100}"       # Port UDP du serveur (15100 par défaut)
X="${X:-300}" Y="${Y:-0}" Z="${Z:-400}" RX="${RX:-0}" RY="${RY:-0}" RZ="${RZ:-0}"
GRIPPER="${GRIPPER:-none}"  # État de la pince : open, close, ou none

# --- Chemins ---
TARGET_DIR="/ur_modbus/chess-project"
[[ -d "$TARGET_DIR" ]] || TARGET_DIR="$HOME/ur_modbus/chess-project"
cd "$TARGET_DIR" || { echo "❌ Dossier introuvable: /ur_modbus/chess-project (ou $HOME/ur_modbus/chess-project)"; exit 1; }

if [[ -f "$HOME/ur_modbus/.venv/bin/activate" ]]; then
  # shellcheck disable=SC1091
  . "$HOME/ur_modbus/.venv/bin/activate"
elif [[ -f ".venv/bin/activate" ]]; then
  # shellcheck disable=SC1091
  . ".venv/bin/activate"
fi

# Choisir Python
if [[ -x "$HOME/ur_modbus/.venv/bin/python" ]]; then
  PY="$HOME/ur_modbus/.venv/bin/python"
elif [[ -x ".venv/bin/python" ]]; then
  PY=".venv/bin/python"
else
  PY="$(command -v python3)"
fi

[[ -f "send_pose.py" ]] || { echo "❌ send_pose.py introuvable dans $(pwd)"; exit 1; }

echo "=== 🤖 Mode interactif d'envoi de poses (mm / degrés) avec contrôle pince ==="
echo "Dossier : $(pwd)"
echo "Serveur UDP : ${HOST}:${PORT}"
echo "Astuce : tape 'x=320 y=120 rz=45 g=open' (laisse vide pour garder la valeur)"
echo "         'h' pour l'aide, 'q' pour quitter"
echo

send_now() {
  local gripper_msg=""
  if [[ "$GRIPPER" != "none" ]]; then
    gripper_msg=" 🔧 pince=$GRIPPER"
  fi

  echo "📡 Envoi : x=$X y=$Y z=$Z rx=$RX ry=$RY rz=$RZ${gripper_msg} @ ${HOST}:${PORT}"

  # Construire la commande avec ou sans l'option gripper
  if [[ "$GRIPPER" != "none" ]]; then
    "$PY" send_pose.py --x "$X" --y "$Y" --z "$Z" --rx "$RX" --ry "$RY" --rz "$RZ" \
                       --gripper "$GRIPPER" --host "$HOST" --port "$PORT"
  else
    "$PY" send_pose.py --x "$X" --y "$Y" --z "$Z" --rx "$RX" --ry "$RY" --rz "$RZ" \
                       --host "$HOST" --port "$PORT"
  fi

  # Réinitialiser gripper à none après envoi pour éviter les répétitions non voulues
  GRIPPER="none"
}

help_msg() {
  cat <<'HLP'
╔════════════════════════════════════════════════════════════════════╗
║                        COMMANDES DISPONIBLES                        ║
╚════════════════════════════════════════════════════════════════════╝

📍 POSITION (mm et degrés) :
   x=...    Position X en mm (ex: x=320)
   y=...    Position Y en mm (ex: y=100)
   z=...    Position Z en mm (ex: z=400)
   rx=...   Rotation X en degrés (ex: rx=45)
   ry=...   Rotation Y en degrés (ex: ry=0)
   rz=...   Rotation Z en degrés (ex: rz=90)

🔧 PINCE (Robotiq Hand-E) :
   g=open   ou  gripper=open    Ouvrir la pince
   g=close  ou  gripper=close   Fermer la pince
   g=none   ou  gripper=none    Ne pas modifier la pince

🌐 RÉSEAU :
   host=... Adresse IP du serveur (ex: host=192.168.0.10)
   port=... Port UDP (ex: port=15100)

📝 EXEMPLES D'UTILISATION :
   x=320                        # Modifier seulement X
   x=320 y=100 g=open          # Position + ouvrir pince
   x=300 z=450 g=close         # Position + fermer pince
   g=open                       # Juste ouvrir la pince
   g=close                      # Juste fermer la pince
   host=192.168.0.10           # Changer l'IP

⌨️  COMMANDES SPÉCIALES :
   Entrée vide : Renvoyer la dernière pose (sans toucher la pince)
   h ou help   : Afficher cette aide
   q           : Quitter

💡 NOTES :
   - Vous pouvez combiner plusieurs commandes sur une ligne
   - L'ordre des paramètres n'a pas d'importance
   - La pince se réinitialise à "none" après chaque envoi
   - Attention : dans votre logique UR, gripper_cmd=True → FERMER
                                        gripper_cmd=False → OUVRIR
HLP
}

# Fonction pour afficher l'état actuel de manière plus claire
show_status() {
  local gripper_display="$GRIPPER"
  [[ "$GRIPPER" == "none" ]] && gripper_display="(inchangé)"

  echo "┌─────────────────────────────────────────────────────────────────┐"
  echo "│ Position: x=$X y=$Y z=$Z | Rotation: rx=$RX° ry=$RY° rz=$RZ°"
  echo "│ Pince: $gripper_display | Serveur: ${HOST}:${PORT}"
  echo "└─────────────────────────────────────────────────────────────────┘"
}

# Message de bienvenue avec état initial
echo
show_status
echo

# Premier envoi optionnel (commentez si non désiré)
# send_now

while true; do
  echo
  printf "🎮 Commande > "
  IFS= read -r LINE || break

  [[ "$LINE" == "q" ]] && break
  [[ "$LINE" == "h" || "$LINE" == "help" ]] && { help_msg; continue; }
  [[ "$LINE" == "status" || "$LINE" == "s" ]] && { show_status; continue; }

  if [[ -z "$LINE" ]]; then
    send_now
    continue
  fi

  # Parser style: x=..., y=..., g=..., etc. (plusieurs possibles)
  for tok in $LINE; do
    case "$tok" in
      x=*)       X="${tok#x=}" ;;
      y=*)       Y="${tok#y=}" ;;
      z=*)       Z="${tok#z=}" ;;
      rx=*)      RX="${tok#rx=}" ;;
      ry=*)      RY="${tok#ry=}" ;;
      rz=*)      RZ="${tok#rz=}" ;;
      g=open|gripper=open)
        GRIPPER="open"
        echo "   ✓ Pince sera OUVERTE"
        ;;
      g=close|gripper=close)
        GRIPPER="close"
        echo "   ✓ Pince sera FERMÉE"
        ;;
      g=none|gripper=none)
        GRIPPER="none"
        echo "   ✓ Pince non modifiée"
        ;;
      g=*)
        echo "   ⚠️  Valeur pince invalide: ${tok#g=} (utiliser: open/close/none)"
        ;;
      gripper=*)
        val="${tok#gripper=}"
        if [[ "$val" == "open" || "$val" == "close" || "$val" == "none" ]]; then
          GRIPPER="$val"
          echo "   ✓ Pince: $val"
        else
          echo "   ⚠️  Valeur pince invalide: $val (utiliser: open/close/none)"
        fi
        ;;
      host=*)    HOST="${tok#host=}" ;;
      port=*)    PORT="${tok#port=}" ;;
      *) echo "   ⚠️  Ignoré: $tok (tape 'h' pour l'aide)";;
    esac
  done

  send_now
done

echo
echo "👋 Au revoir !"
echo
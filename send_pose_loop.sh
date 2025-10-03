#!/usr/bin/env bash
set -euo pipefail

# --- Reglages par defaut (modifiable a l'execution) ---
HOST="${HOST:-127.0.0.1}"   # IP de la machine qui execute le serveur (Pi)
PORT="${PORT:-15100}"       # Port UDP du serveur (15100 par defaut)
X="${X:-300}" Y="${Y:-0}" Z="${Z:-400}" RX="${RX:-0}" RY="${RY:-0}" RZ="${RZ:-0}"

# --- Chemins ---
# Le user a indique : /ur_modbus/chess-project
TARGET_DIR="/ur_modbus/chess-project"
[[ -d "$TARGET_DIR" ]] || TARGET_DIR="$HOME/ur_modbus/chess-project"
cd "$TARGET_DIR" || { echo "? Dossier introuvable: /ur_modbus/chess-project (ou $HOME/ur_modbus/chess-project)"; exit 1; }

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

[[ -f "send_pose.py" ]] || { echo "? send_pose.py introuvable dans $(pwd)"; exit 1; }

echo "=== Mode interactif d'envoi de poses (mm / degres) ==="
echo "Dossier : $(pwd)"
echo "Serveur UDP : ${HOST}:${PORT}"
echo "Astuce : tape 'x=320 y=120 rz=45' (laisse vide pour garder la valeur). 'h' pour l'aide, 'q' pour quitter."
echo

send_now() {
  echo "? Envoi : x=$X y=$Y z=$Z rx=$RX ry=$RY rz=$RZ  @ ${HOST}:${PORT}"
  "$PY" send_pose.py --x "$X" --y "$Y" --z "$Z" --rx "$RX" --ry "$RY" --rz "$RZ" --host "$HOST" --port "$PORT"
}

help_msg() {
  cat <<'HLP'
Commandes :
  - Entree vide : renvoyer la derniere pose.
  - Une ou plusieurs assignations separees par des espaces (ordre libre) :
      x=..., y=..., z=..., rx=..., ry=..., rz=..., host=..., port=...
    Exemples :
      x=320
      x=320 y=100 rz=45
      host=192.168.0.10 port=15100
  - q : quitter
HLP
}

# Premier envoi optionnel ? Tu peux commenter la ligne suivante si tu veux.
send_now

while true; do
  echo
  printf "Modifs (actuel: x=%s y=%s z=%s rx=%s ry=%s rz=%s host=%s port=%s) > " \
    "$X" "$Y" "$Z" "$RX" "$RY" "$RZ" "$HOST" "$PORT"
  IFS= read -r LINE || break

  [[ "$LINE" == "q" ]] && break
  [[ "$LINE" == "h" || "$LINE" == "help" ]] && { help_msg; continue; }

  if [[ -z "$LINE" ]]; then
    send_now
    continue
  fi

  # Parser style: x=..., y=..., etc. (tu peux en mettre plusieurs)
  for tok in $LINE; do
    case "$tok" in
      x=*)   X="${tok#x=}" ;;
      y=*)   Y="${tok#y=}" ;;
      z=*)   Z="${tok#z=}" ;;
      rx=*)  RX="${tok#rx=}" ;;
      ry=*)  RY="${tok#ry=}" ;;
      rz=*)  RZ="${tok#rz=}" ;;
      host=*) HOST="${tok#host=}" ;;
      port=*) PORT="${tok#port=}" ;;
      *) echo "(!) Ignore: $tok (tape 'h' pour l'aide)";;
    esac
  done

  send_now
done

echo "Bye ?"

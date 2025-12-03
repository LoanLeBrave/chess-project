#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/ur_modbus"

source .venv/bin/activate

cd chess-project

exec sudo -E "$(command -v python3)" ur_modbus_server_api310.py

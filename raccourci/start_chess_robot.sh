#!/bin/bash

# =============================================================================
#  🤖 CHESS ROBOT - Script de lancement
# =============================================================================
#
#  Usage: ./start_chess_robot.sh [options]
#
#  Options:
#    --api-only      Lance uniquement l'API (pas le frontend)
#    --frontend-only Lance uniquement le frontend
#    --dev           Mode développement (avec rechargement auto)
#    --stop          Arrête tous les services
#    --status        Affiche le statut des services
#    --help          Affiche cette aide
#
# =============================================================================

set -e

# Configuration - Chemins adaptés à ton installation
# =============================================================================
PROJECT_DIR="/home/robot/ur_modbus/mappingEchec/chess-project"
BACKEND_DIR="$PROJECT_DIR/Backend/manipulation_robot"
FRONTEND_DIR="$PROJECT_DIR/Frontend"
VENV_DIR="$BACKEND_DIR/.venv"

API_HOST="0.0.0.0"
API_PORT="8000"
FRONTEND_PORT="3000"

# Fichiers PID pour gérer les processus
PID_DIR="/tmp/chess-robot"
API_PID_FILE="$PID_DIR/api.pid"
FRONTEND_PID_FILE="$PID_DIR/frontend.pid"

# Couleurs pour l'affichage
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

# =============================================================================
# Fonctions utilitaires
# =============================================================================

print_header() {
    echo -e "${CYAN}"
    echo "============================================================"
    echo "     ♔ CHESS ROBOT - Raspberry Pi ♚"
    echo "============================================================"
    echo -e "${NC}"
}

print_success() { echo -e "${GREEN}✓ $1${NC}"; }
print_error() { echo -e "${RED}✗ $1${NC}"; }
print_warning() { echo -e "${YELLOW}⚠ $1${NC}"; }
print_info() { echo -e "${BLUE}ℹ $1${NC}"; }

check_port() {
    local port=$1
    if lsof -Pi :$port -sTCP:LISTEN -t >/dev/null 2>&1; then
        return 0
    else
        return 1
    fi
}

setup_pid_dir() {
    mkdir -p "$PID_DIR"
}

check_prerequisites() {
    echo -e "${BLUE}Vérification des prérequis...${NC}"
    
    # Python 3
    if command -v python3 &> /dev/null; then
        print_success "Python3: $(python3 --version)"
    else
        print_error "Python3 non trouvé"
        return 1
    fi
    
    # Node.js
    if command -v node &> /dev/null; then
        print_success "Node.js: $(node --version)"
    else
        print_warning "Node.js non installé (frontend désactivé)"
    fi
    
    # Stockfish
    if command -v stockfish &> /dev/null || [ -f "/usr/games/stockfish" ]; then
        print_success "Stockfish installé"
    else
        print_warning "Stockfish non trouvé"
    fi
    
    # Vérifier les dossiers
    if [ ! -d "$BACKEND_DIR" ]; then
        print_error "Dossier Backend non trouvé: $BACKEND_DIR"
        return 1
    else
        print_success "Backend: $BACKEND_DIR"
    fi
    
    if [ ! -d "$FRONTEND_DIR" ]; then
        print_warning "Dossier Frontend non trouvé: $FRONTEND_DIR"
    else
        print_success "Frontend: $FRONTEND_DIR"
    fi
    
    echo ""
    return 0
}

setup_venv() {
    if [ ! -d "$VENV_DIR" ]; then
        print_info "Création de l'environnement virtuel Python..."
        python3 -m venv "$VENV_DIR"
    fi
    source "$VENV_DIR/bin/activate"
    print_success "Environnement virtuel activé"
}

install_python_deps() {
    print_info "Vérification des dépendances Python..."
    pip install --upgrade pip -q 2>/dev/null

    for dep in fastapi uvicorn websockets python-chess opencv-python numpy python-dotenv; do
        if ! pip show "$dep" &> /dev/null; then
            print_info "Installation de $dep..."
            pip install "$dep" -q
        fi
    done

    # ur-rtde pour le robot UR5e (peut échouer si le paquet n'est pas dispo sur l'arch)
    if ! pip show ur-rtde &> /dev/null; then
        print_info "Installation de ur-rtde..."
        pip install ur-rtde -q 2>/dev/null || print_warning "ur-rtde non installable (normal hors Pi)"
    fi

    print_success "Dépendances Python OK"
}

install_node_deps() {
    if [ -d "$FRONTEND_DIR" ] && command -v npm &> /dev/null; then
        print_info "Vérification des dépendances Node.js..."
        cd "$FRONTEND_DIR"
        if [ ! -d "node_modules" ]; then
            print_info "Installation des dépendances npm..."
            npm install
        fi
        print_success "Dépendances Node.js OK"
        cd - > /dev/null
    fi
}

start_api() {
    print_info "Démarrage de l'API Backend..."
    
    if [ -f "$API_PID_FILE" ] && kill -0 $(cat "$API_PID_FILE") 2>/dev/null; then
        print_warning "L'API est déjà en cours (PID: $(cat $API_PID_FILE))"
        return 0
    fi
    
    if check_port $API_PORT; then
        print_warning "Port $API_PORT déjà utilisé, tentative d'arrêt..."
        fuser -k $API_PORT/tcp 2>/dev/null || true
        sleep 1
    fi
    
    cd "$BACKEND_DIR"
    source "$VENV_DIR/bin/activate"
    
    if [ "$DEV_MODE" = true ]; then
        uvicorn api:app --host $API_HOST --port $API_PORT --reload &
    else
        uvicorn api:app --host $API_HOST --port $API_PORT &
    fi
    
    local api_pid=$!
    echo $api_pid > "$API_PID_FILE"
    sleep 2
    
    if kill -0 $api_pid 2>/dev/null; then
        print_success "API démarrée (PID: $api_pid)"
    else
        print_error "Échec du démarrage de l'API"
        return 1
    fi
    
    cd - > /dev/null
}

start_frontend() {
    if [ ! -d "$FRONTEND_DIR" ]; then
        print_warning "Dossier Frontend non trouvé"
        return 0
    fi
    
    if ! command -v npm &> /dev/null; then
        print_warning "npm non installé, frontend ignoré"
        return 0
    fi
    
    print_info "Démarrage du Frontend..."
    
    if [ -f "$FRONTEND_PID_FILE" ] && kill -0 $(cat "$FRONTEND_PID_FILE") 2>/dev/null; then
        print_warning "Le Frontend est déjà en cours (PID: $(cat $FRONTEND_PID_FILE))"
        return 0
    fi
    
    if check_port $FRONTEND_PORT; then
        print_warning "Port $FRONTEND_PORT déjà utilisé, tentative d'arrêt..."
        fuser -k $FRONTEND_PORT/tcp 2>/dev/null || true
        sleep 1
    fi
    
    cd "$FRONTEND_DIR"
    npm run dev -- --host --port $FRONTEND_PORT &
    local frontend_pid=$!
    echo $frontend_pid > "$FRONTEND_PID_FILE"
    sleep 3
    
    if kill -0 $frontend_pid 2>/dev/null; then
        print_success "Frontend démarré (PID: $frontend_pid)"
    else
        print_error "Échec du démarrage du Frontend"
        return 1
    fi
    
    cd - > /dev/null
}

stop_services() {
    print_info "Arrêt des services..."
    
    if [ -f "$API_PID_FILE" ]; then
        local api_pid=$(cat "$API_PID_FILE")
        if kill -0 $api_pid 2>/dev/null; then
            kill $api_pid 2>/dev/null
            print_success "API arrêtée (PID: $api_pid)"
        fi
        rm -f "$API_PID_FILE"
    fi
    
    if [ -f "$FRONTEND_PID_FILE" ]; then
        local frontend_pid=$(cat "$FRONTEND_PID_FILE")
        if kill -0 $frontend_pid 2>/dev/null; then
            kill $frontend_pid 2>/dev/null
            print_success "Frontend arrêté (PID: $frontend_pid)"
        fi
        rm -f "$FRONTEND_PID_FILE"
    fi
    
    # Nettoyer les ports
    fuser -k $API_PORT/tcp 2>/dev/null || true
    fuser -k $FRONTEND_PORT/tcp 2>/dev/null || true
    
    print_success "Tous les services arrêtés"
}

show_status() {
    echo ""
    echo "=== Statut des services ==="
    echo ""
    
    if [ -f "$API_PID_FILE" ] && kill -0 $(cat "$API_PID_FILE") 2>/dev/null; then
        print_success "API: En cours (PID: $(cat $API_PID_FILE))"
    else
        print_error "API: Arrêtée"
    fi
    
    if [ -f "$FRONTEND_PID_FILE" ] && kill -0 $(cat "$FRONTEND_PID_FILE") 2>/dev/null; then
        print_success "Frontend: En cours (PID: $(cat $FRONTEND_PID_FILE))"
    else
        print_error "Frontend: Arrêté"
    fi
    
    echo ""
}

show_help() {
    echo "Usage: $0 [options]"
    echo ""
    echo "Options:"
    echo "  --api-only      Lance uniquement l'API"
    echo "  --frontend-only Lance uniquement le frontend"
    echo "  --dev           Mode développement"
    echo "  --stop          Arrête tous les services"
    echo "  --status        Affiche le statut"
    echo "  --help          Affiche cette aide"
    echo ""
}

show_urls() {
    local ip=$(hostname -I | awk '{print $1}')
    echo ""
    echo -e "${CYAN}============================================================${NC}"
    echo -e "${GREEN}  🎉 Chess Robot démarré !${NC}"
    echo -e "${CYAN}============================================================${NC}"
    echo ""
    echo -e "  ${BLUE}Interface Web:${NC}  http://$ip:$FRONTEND_PORT"
    echo -e "  ${BLUE}API Backend:${NC}    http://$ip:$API_PORT"
    echo -e "  ${BLUE}Documentation:${NC}  http://$ip:$API_PORT/docs"
    echo ""
    echo -e "  ${YELLOW}Pour arrêter:${NC} $0 --stop"
    echo -e "  ${YELLOW}Ou appuyez sur Ctrl+C${NC}"
    echo ""
    echo -e "${CYAN}============================================================${NC}"
}

# =============================================================================
# Script principal
# =============================================================================

API_ONLY=false
FRONTEND_ONLY=false
DEV_MODE=false

while [[ $# -gt 0 ]]; do
    case $1 in
        --api-only) API_ONLY=true; shift ;;
        --frontend-only) FRONTEND_ONLY=true; shift ;;
        --dev) DEV_MODE=true; shift ;;
        --stop) print_header; stop_services; exit 0 ;;
        --status) print_header; show_status; exit 0 ;;
        --help|-h) print_header; show_help; exit 0 ;;
        *) print_error "Option inconnue: $1"; show_help; exit 1 ;;
    esac
done

print_header
setup_pid_dir

if ! check_prerequisites; then
    exit 1
fi

setup_venv
install_python_deps

if [ "$FRONTEND_ONLY" = false ]; then
    start_api
fi

if [ "$API_ONLY" = false ]; then
    install_node_deps
    start_frontend
fi

show_urls

trap 'echo ""; stop_services; exit 0' SIGINT SIGTERM

# Garder le script actif
if [ "$API_ONLY" = false ] && [ -f "$FRONTEND_PID_FILE" ]; then
    wait $(cat "$FRONTEND_PID_FILE") 2>/dev/null
else
    wait $(cat "$API_PID_FILE") 2>/dev/null
fi

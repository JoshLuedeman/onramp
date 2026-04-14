#!/usr/bin/env bash
# ============================================================================
# OnRamp Dev Environment — One command to rule them all
#
# Usage:
#   ./dev.sh          Start everything (first run installs deps automatically)
#   ./dev.sh up       Same as above
#   ./dev.sh down     Stop everything
#   ./dev.sh reset    Stop, wipe DB, rebuild containers from scratch
#   ./dev.sh logs     Tail all container logs
#   ./dev.sh test     Run backend tests inside the container
#   ./dev.sh status   Show what's running
#   ./dev.sh shell    Open a shell in the backend container
# ============================================================================

set -euo pipefail

# Always run from the directory where this script lives
cd "$(dirname "$(readlink -f "$0")")"

COMPOSE="docker compose"
PROJECT="onramp"

# Detect host IP — use WSL IP if available, otherwise localhost
if grep -qi microsoft /proc/version 2>/dev/null; then
    HOST_IP=$(hostname -I | awk '{print $1}')
else
    HOST_IP="localhost"
fi

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

banner() {
    echo ""
    echo -e "${BLUE}🚀 OnRamp Dev Environment${NC}"
    echo "─────────────────────────────────"
}

bootstrap_env() {
    if [ ! -f .env ]; then
        echo -e "${YELLOW}No .env file found — generating from .env.example...${NC}"
        cp .env.example .env
        # Generate a random SA password for local SQL Server
        local sa_pass
        sa_pass="OnRamp_$(openssl rand -base64 16 | tr -dc 'A-Za-z0-9' | head -c 16)!"
        if [[ "$OSTYPE" == "darwin"* ]]; then
            sed -i '' "s|<generate-a-strong-password>|${sa_pass}|g" .env
        else
            sed -i "s|<generate-a-strong-password>|${sa_pass}|g" .env
        fi
        echo -e "${GREEN}.env created with generated MSSQL_SA_PASSWORD.${NC}"
        echo -e "${YELLOW}Review .env and customize as needed.${NC}"
    fi
}

check_prereqs() {
    local missing=()
    if ! command -v docker &>/dev/null; then missing+=("docker"); fi
    if ! docker compose version &>/dev/null 2>&1; then missing+=("docker compose"); fi

    if [ ${#missing[@]} -ne 0 ]; then
        echo -e "${RED}Missing prerequisites: ${missing[*]}${NC}"
        echo "Install Docker Desktop: https://docs.docker.com/get-docker/"
        exit 1
    fi

    # Start Docker daemon if it isn't running
    if ! docker info &>/dev/null 2>&1; then
        echo -e "${YELLOW}Docker daemon is not running. Starting...${NC}"
        sudo systemctl start docker 2>/dev/null \
            || sudo service docker start 2>/dev/null \
            || { echo -e "${RED}Could not start Docker. Please start it manually.${NC}"; exit 1; }
        # Wait up to 15s for the daemon to be ready
        local waited=0
        while ! docker info &>/dev/null 2>&1 && [ $waited -lt 15 ]; do
            sleep 1
            waited=$((waited + 1))
        done
        if ! docker info &>/dev/null 2>&1; then
            echo -e "${RED}Docker daemon failed to start within 15s.${NC}"
            exit 1
        fi
        echo -e "${GREEN}Docker daemon started.${NC}"
    fi
}

wait_for_health() {
    local service=$1
    local url=$2
    local max_wait=$3
    local elapsed=0

    printf "  Waiting for %-10s " "$service..."
    while [ $elapsed -lt $max_wait ]; do
        if curl -sf "$url" &>/dev/null; then
            echo -e "${GREEN}✓ ready${NC}"
            return 0
        fi
        sleep 2
        elapsed=$((elapsed + 2))
        printf "."
    done
    echo -e "${YELLOW}⚠ timeout after ${max_wait}s${NC}"
    return 1
}

cmd_up() {
    banner
    check_prereqs
    bootstrap_env

    echo -e "${BLUE}Building and starting containers...${NC}"
    $COMPOSE build --quiet 2>&1 | tail -1 || true
    $COMPOSE up -d

    echo ""
    echo -e "${BLUE}Waiting for services to be healthy...${NC}"

    # SQL Server takes the longest — wait for it first
    wait_for_health "SQL Server" "http://${HOST_IP}:8000/health" 90 || true
    wait_for_health "Backend" "http://${HOST_IP}:8000/health" 30 || true
    wait_for_health "Frontend" "http://${HOST_IP}:5173" 30 || true

    echo ""
    echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${GREEN}  OnRamp is running!${NC}"
    echo ""
    echo -e "  Frontend:  ${BLUE}http://${HOST_IP}:5173${NC}"
    echo -e "  Backend:   ${BLUE}http://${HOST_IP}:8000${NC}"
    echo -e "  API Docs:  ${BLUE}http://${HOST_IP}:8000/docs${NC}"
    echo -e "  Health:    ${BLUE}http://${HOST_IP}:8000/health${NC}"
    echo ""
    echo -e "  ${YELLOW}Running in dev mode — mock auth, mock AI, hot reload enabled${NC}"
    echo ""
    echo -e "  Edit frontend code in ${BLUE}frontend/src/${NC} — changes hot-reload"
    echo -e "  Edit backend code in  ${BLUE}backend/app/${NC}  — uvicorn auto-restarts"
    echo ""
    echo -e "  Useful commands:"
    echo "    ./dev.sh logs     Tail logs"
    echo "    ./dev.sh test     Run backend tests"
    echo "    ./dev.sh shell    Backend shell"
    echo "    ./dev.sh down     Stop everything"
    echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
}

cmd_down() {
    banner
    echo -e "${YELLOW}Stopping containers...${NC}"
    $COMPOSE down
    echo -e "${GREEN}Done.${NC}"
}

cmd_reset() {
    banner
    echo -e "${RED}Stopping containers and wiping data...${NC}"
    $COMPOSE down -v --remove-orphans
    echo -e "${YELLOW}Rebuilding from scratch...${NC}"
    $COMPOSE build --no-cache
    cmd_up
}

cmd_logs() {
    $COMPOSE logs -f --tail=50
}

cmd_test() {
    banner
    echo -e "${BLUE}Running backend tests...${NC}"
    echo ""
    $COMPOSE exec backend python -m pytest tests/ -v --tb=short
}

cmd_status() {
    banner
    $COMPOSE ps

    echo ""
    if curl -sf http://${HOST_IP}:8000/health &>/dev/null; then
        local health
        health=$(curl -sf http://${HOST_IP}:8000/health)
        echo -e "Backend health: ${GREEN}$(echo "$health" | python3 -m json.tool 2>/dev/null || echo "$health")${NC}"
    else
        echo -e "Backend health: ${RED}unreachable${NC}"
    fi
}

cmd_shell() {
    $COMPOSE exec backend /bin/bash
}

# ── Main ─────────────────────────────────────────────────────────────────────

case "${1:-up}" in
    up|start)   cmd_up ;;
    down|stop)  cmd_down ;;
    reset)      cmd_reset ;;
    logs)       cmd_logs ;;
    test)       cmd_test ;;
    status)     cmd_status ;;
    shell|sh)   cmd_shell ;;
    *)
        echo "Usage: ./dev.sh [up|down|reset|logs|test|status|shell]"
        exit 1
        ;;
esac

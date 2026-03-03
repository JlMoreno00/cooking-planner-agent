#!/bin/bash
# Inicia todos los MCP servers del Cooking Planner Agent
# Se ejecuta como servicio systemd en el arranque

set -e

WORKDIR="/root/Cooking Planner Agent"
VENV="$WORKDIR/.venv/bin/python3"
LOG_DIR="/var/log/cooking-mcps"
ENV_FILE="$WORKDIR/.env"

mkdir -p "$LOG_DIR"

# Cargar variables de entorno
if [ -f "$ENV_FILE" ]; then
    set -a
    source "$ENV_FILE"
    set +a
fi

start_mcp() {
    local name="$1"
    local script="$2"
    local port="$3"
    local log="$LOG_DIR/$name.log"

    # Matar proceso anterior en el puerto si existe
    PID=$(lsof -ti:"$port" 2>/dev/null || true)
    if [ -n "$PID" ]; then
        kill "$PID" 2>/dev/null || true
        sleep 1
    fi

    nohup "$VENV" "$WORKDIR/scripts/$script" >> "$log" 2>&1 &
    sleep 2

    if lsof -ti:"$port" > /dev/null 2>&1; then
        echo "[OK] $name en puerto $port (PID $(lsof -ti:$port))"
    else
        echo "[ERROR] $name no arrancó — ver $log"
        tail -5 "$log"
    fi
}

echo "=== Iniciando MCP servers del Cooking Planner Agent ==="
start_mcp "mealie"         "mealie_mcp_http.py"         9150
start_mcp "recipe-scraper" "recipe_scraper_mcp_server.py" 9151
start_mcp "spoonacular"    "spoonacular_mcp_server.py"  9152
start_mcp "memory"         "memory_mcp_server.py"       9153
start_mcp "bring"          "bring_mcp_server.py"        9154
start_mcp "video-recipe"   "video_recipe_mcp_server.py" 9155
echo "=== MCP servers iniciados ==="

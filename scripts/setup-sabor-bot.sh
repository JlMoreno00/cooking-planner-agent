#!/bin/bash
# Configura el bot de Telegram dedicado para Sabor (cooking-planner)
# Uso: ./setup-sabor-bot.sh <BOT_TOKEN>
# Ejemplo: ./setup-sabor-bot.sh 1234567890:AAH...

set -e

TOKEN="$1"
if [ -z "$TOKEN" ]; then
  echo "Error: pasa el token del bot como argumento"
  echo "Uso: $0 <BOT_TOKEN>"
  exit 1
fi

CONFIG="/root/.openclaw/openclaw.json"

python3 - "$TOKEN" << 'PYEOF'
import json, sys
from pathlib import Path

token = sys.argv[1]
config_path = Path("/root/.openclaw/openclaw.json")
config = json.loads(config_path.read_text())

# 1. Añadir account "sabor" en channels.telegram.accounts
accounts = config["channels"]["telegram"]["accounts"]
accounts["sabor"] = {
    "dmPolicy": "allowlist",
    "botToken": token,
    "streaming": "off",
    "ackReaction": "🍳"
}

# 2. Copiar allowFrom del bot default
default_allow = config["channels"]["telegram"].get("allowFrom", [])
if default_allow:
    accounts["sabor"]["allowFrom"] = default_allow

# 3. Añadir binding cooking-planner -> telegram/sabor
bindings = config.get("bindings", [])
# Eliminar binding previo si existiera
bindings = [b for b in bindings if b.get("agentId") != "cooking-planner"]
bindings.append({
    "agentId": "cooking-planner",
    "match": {
        "channel": "telegram",
        "accountId": "sabor"
    }
})
config["bindings"] = bindings

# 4. Guardar
config_path.write_text(json.dumps(config, indent=2, ensure_ascii=False))
print("OK: Bot Sabor configurado")
print("  Account: sabor")
print("  Binding: cooking-planner -> telegram/sabor")
print("  AllowFrom:", default_allow)
PYEOF

echo ""
echo "Reiniciando OpenClaw gateway..."
systemctl --user restart openclaw-gateway.service
sleep 5

if systemctl --user is-active openclaw-gateway.service > /dev/null 2>&1; then
  echo "OpenClaw reiniciado OK"
  echo ""
  echo "=== SIGUIENTE PASO ==="
  echo "Abre Telegram y escribe al nuevo bot. Debería responder como Sabor."
else
  echo "ERROR: OpenClaw no arrancó. Ver: journalctl --user -u openclaw-gateway -n 20"
fi

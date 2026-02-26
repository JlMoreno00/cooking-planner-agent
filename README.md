# 🍳 Sabor — Cooking Planner Agent

Sabor es un agente de IA personal especializado en planificación de comidas, gestión de recetas y nutrición. Funciona como un chef y nutricionista accesible vía **Telegram**, con personalidad cercana y conocimiento profundo de cocina mediterránea e internacional.

Construido sobre **[OpenClaw](https://openclaw.ai)** y conectado a **[Mealie](https://mealie.io)** como base de datos de recetas.

---

## Arquitectura

```
Telegram  ←→  OpenClaw (agente Sabor)  ←→  MCP Servers
                      ↓
                   Mealie (recetas + menús)
```

| Componente | Descripción |
|---|---|
| **OpenClaw** | Runtime del agente: procesa mensajes, gestiona sesiones, ejecuta skills |
| **Mealie** | Base de datos de recetas y planificación semanal (self-hosted, Docker) |
| **Telegram** | Interfaz de usuario con botones inline interactivos |
| **MCP Servers** | 4 servidores HTTP que exponen herramientas al agente |

---

## Skills del agente

| Skill | Descripción |
|---|---|
| `onboarding-interview` | Entrevista inicial para crear el perfil alimenticio del usuario |
| `feedback-collector` | Recoger ratings y feedback tras cada comida |
| `weekly-planner` | Planificación colaborativa del menú semanal (7 días × 2 comidas) |
| `fridge-cleaner` | Sugerir recetas con los ingredientes disponibles en nevera |
| `shopping-list` | Generar y sincronizar la lista de la compra |
| `cooking-plan` | Plan de cocinado batch para preparar la semana |
| `recipe-manager` | Importar, buscar y gestionar recetas |

---

## MCP Servers

| Servidor | Puerto | Descripción |
|---|---|---|
| `mealie_mcp_http.py` | 9150 | Interfaz con Mealie (recetas, menús, shopping lists) |
| `recipe_scraper_mcp_server.py` | 9151 | Scraping de recetas desde URLs externas |
| `spoonacular_mcp_server.py` | 9152 | Búsqueda y datos nutricionales vía Spoonacular API |
| `memory_mcp_server.py` | 9153 | Memoria persistente del agente (perfil, preferencias, feedback) |

Todos arrancan con `scripts/start-cooking-mcps.sh` y se gestionan como servicio systemd (`cooking-mcps.service`).

---

## Estructura del proyecto

```
Cooking Planner Agent/
├── IDENTITY.md          # Personalidad y reglas de comportamiento del agente
├── AGENTS.md            # Instrucciones de workspace para el agente
├── SOUL.md              # Valores y carácter del agente
├── TOOLS.md             # Referencia de herramientas disponibles
├── HEARTBEAT.md         # Tareas periódicas proactivas
├── MEMORY.md            # Memoria long-term curada
├── USER.md              # Contexto del usuario
├── docker-compose.yml   # Mealie self-hosted
├── openclaw.json        # Config local del workspace OpenClaw
├── .env.example         # Plantilla de variables de entorno
├── scripts/
│   ├── mealie_mcp_http.py           # MCP server Mealie
│   ├── recipe_scraper_mcp_server.py # MCP server scraper
│   ├── spoonacular_mcp_server.py    # MCP server Spoonacular
│   ├── memory_mcp_server.py         # MCP server memoria
│   ├── start-cooking-mcps.sh        # Script de inicio MCPs
│   ├── setup-sabor-bot.sh           # Configurar bot Telegram
│   └── seed_mealie_import.py        # Seed inicial de recetas
├── skills/
│   ├── onboarding-interview/SKILL.md
│   └── feedback-collector/SKILL.md
└── docs/
    └── guia-usuario.md  # Guía completa de uso en español
```

---

## Instalación

### Prerrequisitos

- VPS o servidor Linux
- Docker + Docker Compose
- [OpenClaw](https://openclaw.ai) instalado
- Python 3.11+
- Cuenta de Telegram y bot creado vía @BotFather
- API key de [Spoonacular](https://spoonacular.com/food-api) (free tier suficiente)

### 1. Clonar el repositorio

```bash
git clone https://github.com/JlMoreno00/cooking-planner-agent.git
cd cooking-planner-agent
```

### 2. Configurar variables de entorno

```bash
cp .env.example .env
# Editar .env con tus valores reales:
#   SPOONACULAR_API_KEY, MEALIE_API_TOKEN, MEALIE_BASE_URL, TELEGRAM_BOT_TOKEN
```

### 3. Levantar Mealie

```bash
docker compose up -d
# Mealie disponible en http://localhost:9925
# Crear usuario admin en /register (primera vez)
# Generar API token en Settings → API Tokens
```

### 4. Iniciar los MCP servers

```bash
chmod +x scripts/start-cooking-mcps.sh
./scripts/start-cooking-mcps.sh
# O como servicio: systemctl --user start cooking-mcps.service
```

### 5. Configurar el agente en OpenClaw

Registrar el agente `cooking-planner` en OpenClaw apuntando a este directorio como workspace. Configurar el binding con el bot de Telegram (`@SaborChefBot` o el tuyo propio).

```bash
# Verificar MCPs conectados
openclaw mcp status --agent cooking-planner

# Verificar estado del agente
openclaw health
```

---

## Configuración del agente (OpenClaw)

```json
{
  "id": "cooking-planner",
  "workspace": "/ruta/a/Cooking Planner Agent",
  "tools": {
    "allow": ["read", "write", "edit", "memory_search", "memory_get", "mcp", "message"],
    "deny": ["group:runtime", "group:web", "group:ui", "group:automation"]
  },
  "identity": {
    "name": "Sabor",
    "theme": "Chef Nutricionista",
    "emoji": "🍳"
  }
}
```

### Modelos recomendados (probados con tool-calling + botones)

| Prioridad | Modelo |
|---|---|
| Primary | `openai-codex/gpt-5.3-codex` |
| Fallback 1 | `openai-codex/gpt-5.2-codex` |
| Fallback 2 | `google-gemini-cli/gemini-3-flash-preview` |
| Fallback 3 | `google-gemini-cli/gemini-2.5-flash` |
| Fallback 4 | `qwen-portal/coder-model` |

---

## Uso en Telegram

Una vez configurado, abre el bot en Telegram y empieza con:

```
Hola, soy nuevo
```

El agente iniciará el onboarding con **botones inline interactivos** para crear tu perfil alimenticio.

### Comandos naturales

- `Planifiquemos la semana` — genera menú semanal colaborativo
- `Tengo en la nevera: pollo, tomates, cebolla` — modo vaciado de nevera
- `Importa esta receta: [URL]` — importar receta desde enlace
- `El risotto de anoche estaba un 5` — dar feedback
- `Genera la lista de la compra` — lista de ingredientes del menú actual
- `Actualiza mi perfil: ahora soy vegetariano` — modificar preferencias

---

## Decisiones de diseño

- **Botones inline siempre**: toda elección del usuario se hace vía botones Telegram, no texto plano. `callback_data` con prefijo por skill (`ob_`, `fb_`, `wp_`, etc.) para routing limpio.
- **Memoria persistente real**: el MCP de memoria usa un archivo JSON estructurado con perfil, historial de feedback y recetas favoritas, separado del contexto de sesión.
- **MCPs stateless HTTP**: todos los servidores MCP usan `stateless_http=True` para compatibilidad con el gateway de OpenClaw.
- **Mealie como source of truth**: las recetas no se guardan en el contexto del agente sino en Mealie, lo que permite acceso web independiente y persistencia robusta.

---

## Licencia

Privado — uso personal.

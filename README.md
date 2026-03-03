# 🍳 Sabor — Cooking Planner Agent

Sabor es un agente de IA personal especializado en planificación de comidas, gestión de recetas y nutrición. Funciona como un chef y nutricionista accesible vía **Telegram**, con personalidad cercana y conocimiento profundo de cocina mediterránea e internacional.

Construido sobre **[OpenClaw](https://openclaw.ai)** y sincronizado bidireccionalmente con **[Mealie](https://mealie.io)** como panel visual de escritorio.

---

## Arquitectura

```
📱 Telegram (móvil)
      ↕  mensajes + botones inline
OpenClaw — Agente "Sabor"
      ↕  MCP tools (HTTP stateless)
┌─────────────────────────────────┐
│         MCP Servers             │
│  mealie · scraper · spoonacular │
│  memory · bring · video-recipe  │
└─────────────────────────────────┘
      ↕  REST API
🖥️ Mealie (panel visual de escritorio)
   ├── 📅 Calendario semanal  ← pobla el weekly-planner
   ├── 🛒 Lista de compra     ← sincroniza la shopping list
   ├── 📚 Biblioteca recetas  ← recetas con tags + comentarios
   └── 📋 Timeline recetas    ← historial de cocinado
```

**Flujo operativo**: planificas desde el móvil con Sabor → el calendario y la lista de compra se actualizan automáticamente en Mealie → lo ves todo organizado en el escritorio.

---

## Skills del agente

| Skill | Descripción |
|---|---|
| `onboarding-interview` | Entrevista inicial para crear el perfil alimenticio del usuario (modelo de planificación incluido) |
| `weekly-planner` | Planificación colaborativa del menú **L-V** con 3 modelos: Escalonado, Emparejado o Batch |
| `shopping-list` | Genera y sincroniza la lista de la compra con Mealie |
| `cooking-plan` | Plan de batch cooking + registro automático del historial cocinado en Mealie |
| `feedback-collector` | Recoger ratings y feedback; persiste en MEMORY.md y publica comentario en la receta de Mealie |
| `recipe-manager` | Importar, buscar y gestionar recetas con auto-etiquetado al importar |
| `fridge-cleaner` | Sugerir recetas con los ingredientes disponibles en nevera |

### Modelos de planificación semanal

| Modelo | Recetas | Sesiones de cocina | Ideal para |
|---|---|---|---|
| 🔄 **Escalonado** | 5 (×2 porciones) | 5 tardes de 25-35 min | 1 persona, 0 desperdicio |
| 🗓️ **Emparejado** | 6 (×2 porciones) | 3 días (L, X, V) | Menos sesiones |
| 🔥 **Batch** | 4 (3×4p + 1×2p) | 1 domingo ~2h + viernes | Cocina el finde |

---

## MCP Servers

| Servidor | Puerto | Tools | Descripción |
|---|---|---|---|
| `mealie_mcp_http.py` | 9150 | 18 | Integración completa con Mealie (ver detalle abajo) |
| `recipe_scraper_mcp_server.py` | 9151 | 2 | Scraping de recetas desde URLs externas |
| `spoonacular_mcp_server.py` | 9152 | 3 | Búsqueda y datos nutricionales vía Spoonacular API |
| `memory_mcp_server.py` | 9153 | 4 | Memoria persistente del agente (perfil, preferencias, feedback) |
| `bring_mcp_server.py` | 9154 | 3 | Sincronización de lista con Bring! usando catálogo oficial |
| `video_recipe_mcp_server.py` | 9155 | 2 | Extrae recetas desde videos YouTube/TikTok y crea recetas separadas en Mealie |

Todos arrancan con `scripts/start-cooking-mcps.sh` y se gestionan como servicio systemd (`cooking-mcps.service`).

### Integración con Mealie — 18 tools

#### Recetas
| Tool | Descripción |
|---|---|
| `search_recipes` | Buscar recetas por nombre |
| `get_recipe` | Obtener receta completa (incluye UUID para operaciones internas) |
| `create_recipe` | Crear o importar receta desde URL |

#### Lista de compra
| Tool | Descripción |
|---|---|
| `get_shopping_lists` | Listar todas las listas |
| `get_or_create_shopping_list` | Buscar o crear por nombre |
| `add_items_to_shopping_list` | Añadir ingredientes como texto libre |
| `add_recipe_ingredients_to_list` | Añadir ingredientes completos de una receta |
| `clear_shopping_list` | Vaciar lista |
| `create_shopping_list` / `delete_shopping_list` | Gestión de listas |

#### Calendario semanal (Fase 1)
| Tool | Descripción |
|---|---|
| `get_mealplan_week` | Leer el calendario para un rango de fechas |
| `set_mealplan_entry` | Añadir entrada al calendario (con enlace a receta si existe) |
| `delete_mealplan_entry` | Eliminar una entrada |
| `clear_mealplan_week` | Vaciar semana completa antes de escribir |

#### Tags de recetas (Fase 1)
| Tool | Descripción |
|---|---|
| `get_or_create_tag` | Buscar o crear tag por nombre |
| `tag_recipe` | Asignar tags a una receta (conserva los existentes) |

#### Comentarios y cooking log (Fase 2)
| Tool | Descripción |
|---|---|
| `add_recipe_comment` | Publicar feedback del usuario como comentario en la receta |
| `log_cooking_event` | Registrar en el timeline cuándo se cocinó una receta |

---

## Acceso al panel de Mealie desde tu equipo

Mealie escucha en el puerto **9925** de la VPS. Hay dos formas de acceder:

### Opción A — Túnel SSH (sin instalación extra)

```bash
ssh -L 9925:localhost:9925 root@<IP_VPS> -N
```

Accede en el navegador a `http://localhost:9925`. Deja el terminal abierto mientras usas el panel.

### Opción B — Tailscale (recomendado, acceso permanente)

Tailscale ya está instalado en la VPS. Solo necesitas:

1. Instalar Tailscale en tu equipo: [tailscale.com/download](https://tailscale.com/download)
2. Iniciar sesión con la misma cuenta que la VPS
3. Acceder directamente a `http://100.82.166.82:9925`

---

## Estructura del proyecto

```
Cooking Planner Agent/
├── IDENTITY.md          # Personalidad, reglas y routing de tools del agente
├── AGENTS.md            # Instrucciones de workspace para el agente
├── SOUL.md              # Valores y carácter del agente
├── TOOLS.md             # Referencia completa de herramientas MCP
├── HEARTBEAT.md         # Tareas periódicas proactivas
├── MEMORY.md            # Memoria long-term curada (gitignored)
├── USER.md              # Contexto del usuario (gitignored)
├── docker-compose.yml   # Mealie self-hosted
├── openclaw.json        # Config local del workspace OpenClaw
├── .env.example         # Plantilla de variables de entorno
├── scripts/
│   ├── mealie_mcp_http.py           # MCP Mealie — 18 tools
│   ├── recipe_scraper_mcp_server.py # MCP scraper
│   ├── spoonacular_mcp_server.py    # MCP Spoonacular
│   ├── memory_mcp_server.py         # MCP memoria
│   ├── bring_mcp_server.py          # MCP Bring! (lista compra)
│   ├── video_recipe_mcp_server.py   # MCP video -> multi-receta Mealie
│   ├── start-cooking-mcps.sh        # Arrancar todos los MCPs
│   ├── setup-sabor-bot.sh           # Configurar bot Telegram
│   └── seed_mealie_import.py        # Seed inicial de recetas
├── skills/                          # Symlinks a /root/.agents/skills/
│   ├── onboarding-interview/SKILL.md
│   ├── weekly-planner/SKILL.md
│   ├── shopping-list/SKILL.md
│   ├── cooking-plan/SKILL.md
│   ├── feedback-collector/SKILL.md
│   ├── recipe-manager/SKILL.md
│   └── fridge-cleaner/SKILL.md
└── docs/
    └── guia-usuario.md  # Guía completa de uso en español
```

> **Nota**: Los skills globales residen en `/root/.agents/skills/` (fuera del repo, persisten en disco). La carpeta `skills/` contiene symlinks.

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
# Editar .env con tus valores:
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

Registrar el agente `cooking-planner` en OpenClaw apuntando a este directorio como workspace. Configurar el binding con el bot de Telegram.

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

### Modelos recomendados

| Prioridad | Modelo |
|---|---|
| Primary | `openai-codex/gpt-5.3-codex` |
| Fallback 1 | `openai-codex/gpt-5.2-codex` |
| Fallback 2 | `google-gemini-cli/gemini-3-flash-preview` |
| Fallback 3 | `google-gemini-cli/gemini-2.5-flash` |

---

## Uso en Telegram

```
Hola, soy nuevo
```

El agente inicia el onboarding con botones inline interactivos para crear tu perfil, incluyendo el modelo de planificación preferido (Escalonado / Emparejado / Batch).

### Comandos naturales

| Lo que dices | Lo que hace Sabor |
|---|---|
| `Planifiquemos la semana` | Genera el menú L-V con tu modelo preferido y llena el calendario de Mealie |
| `Tengo en la nevera: pollo, tomates` | Modo vaciado de nevera con recetas sugeridas |
| `Importa esta receta: [URL]` | Importa a Mealie y auto-etiqueta por cocina/tiempo/método |
| `El risotto de anoche estaba un 5` | Guarda feedback en MEMORY.md y publica comentario en Mealie |
| `Genera la lista de la compra` | Sincroniza la lista en Mealie con los ingredientes del menú |
| `Actualiza mi perfil: soy vegetariano` | Modifica el perfil y adapta futuras planificaciones |
| `He terminado el batch` | Registra en el timeline de Mealie las recetas cocinadas |

---

## Decisiones de diseño

- **Telegram como interfaz principal**: toda elección se hace vía botones inline. `callback_data` con prefijo por skill (`ob_`, `fb_`, `wp_`, `cp_`, `rm_`) para routing limpio.
- **Mealie como panel visual**: el agente sincroniza activamente el calendario, la lista de compra, los tags y el historial de cocinado. Mealie no es solo una base de datos — es el panel de control del escritorio.
- **Persistencia dual**: el feedback se guarda en MEMORY.md (para aprendizaje) y en Mealie (para visibilidad). La sincronización a Mealie es siempre best-effort: si falla, el flujo principal continúa sin interrumpirse.
- **Modelos de planificación adaptables**: el weekly-planner elige el algoritmo (Escalonado / Emparejado / Batch) según el perfil del usuario. Cada modelo genera exactamente las porciones necesarias para eliminar el desperdicio.
- **MCPs stateless HTTP**: todos los servidores usan `stateless_http=True` para compatibilidad con el gateway de OpenClaw.
- **Skills globales fuera del repo**: los skills viven en `/root/.agents/skills/` para ser compartibles entre varios agentes sin necesidad de commit.

---

## Licencia

Privado — uso personal.

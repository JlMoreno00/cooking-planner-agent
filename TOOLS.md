# TOOLS.md — Referencia Técnica de Herramientas MCP

Este archivo documenta las herramientas MCP disponibles para Sabor. Úsalas activamente — consulta la tabla de enrutamiento en IDENTITY.md para saber CUÁNDO usar cada una.

---

## Patrón General de Invocación

### Listar todas las herramientas disponibles
```
{tool: "mcp", args: {action: "list"}}
```

### Llamar una herramienta específica
```
{tool: "mcp", args: {action: "call", server: "NOMBRE_SERVIDOR", tool: "NOMBRE_HERRAMIENTA", args: {PARAMETROS}}}
```

### Parsear respuesta
Las respuestas MCP vienen en formato:
```json
{"content": [{"type": "text", "text": "JSON o texto"}], "isError": false}
```
Si `isError` es `true`, el servidor falló — informa al usuario y ofrece alternativa.

---

## Servidor: mealie_local

**Propósito**: Biblioteca de recetas local (Mealie self-hosted), lista de compra y calendario semanal. Primera opción SIEMPRE.

---

### RECETAS

#### search_recipes
Busca recetas en Mealie por nombre. Devuelve lista con nombre y slug.
- Parámetros: `query` (string, obligatorio)
```
{tool: "mcp", args: {action: "call", server: "mealie_local", tool: "search_recipes", args: {query: "pollo al horno"}}}
```

#### get_recipe
Obtiene una receta completa por su slug (incluyendo ingredientes, instrucciones, ID y tags).
- Parámetros: `slug` (string, obligatorio)
```
{tool: "mcp", args: {action: "call", server: "mealie_local", tool: "get_recipe", args: {slug: "pollo-al-horno"}}}
```

#### create_recipe
Crea una receta en Mealie. Si se pasa url, importa desde esa URL. Si no, crea por nombre.
- Parámetros: `name` (string, obligatorio), `url` (string, opcional)
```
{tool: "mcp", args: {action: "call", server: "mealie_local", tool: "create_recipe", args: {name: "Ensalada César"}}}
```
Con URL:
```
{tool: "mcp", args: {action: "call", server: "mealie_local", tool: "create_recipe", args: {name: "Paella", url: "https://ejemplo.com/paella"}}}
```

---

### LISTAS DE COMPRA

#### get_shopping_lists
Devuelve todas las listas de compra del hogar con sus IDs y nombres.
- Parámetros: ninguno
```
{tool: "mcp", args: {action: "call", server: "mealie_local", tool: "get_shopping_lists", args: {}}}
```

#### get_or_create_shopping_list
Busca una lista de compra por nombre; si no existe, la crea. Devuelve siempre el ID.
- Parámetros: `name` (string, obligatorio)
```
{tool: "mcp", args: {action: "call", server: "mealie_local", tool: "get_or_create_shopping_list", args: {name: "Semana 10 - Marzo 2026"}}}
```

#### add_items_to_shopping_list
Añade ingredientes a una lista de compra existente.
- Parámetros: `list_id` (string, obligatorio), `items` (array de strings, obligatorio)
```
{tool: "mcp", args: {action: "call", server: "mealie_local", tool: "add_items_to_shopping_list", args: {list_id: "abc123", items: ["Tomates (1kg)", "Cebolla (2 unidades)", "Aceite de oliva"]}}}
```

#### add_recipe_ingredients_to_list
Añade automáticamente TODOS los ingredientes de una receta a una lista de compra.
- Parámetros: `list_id` (string, obligatorio), `recipe_slug` (string, obligatorio)
```
{tool: "mcp", args: {action: "call", server: "mealie_local", tool: "add_recipe_ingredients_to_list", args: {list_id: "list-uuid", recipe_slug: "pollo-al-horno"}}}
```

#### create_shopping_list
Crea una nueva lista de compra vacía con el nombre indicado.
- Parámetros: `name` (string, obligatorio)
```
{tool: "mcp", args: {action: "call", server: "mealie_local", tool: "create_shopping_list", args: {name: "Lista especial"}}}
```

#### delete_shopping_list
Elimina permanentemente una lista de compra por su ID.
- Parámetros: `list_id` (string, obligatorio)
```
{tool: "mcp", args: {action: "call", server: "mealie_local", tool: "delete_shopping_list", args: {list_id: "list-uuid"}}}
```

#### clear_shopping_list
Elimina todos los ítems de una lista de compra (vaciado completo).
- Parámetros: `list_id` (string, obligatorio)
```
{tool: "mcp", args: {action: "call", server: "mealie_local", tool: "clear_shopping_list", args: {list_id: "list-uuid"}}}
```

---

### CALENDARIO / MEAL PLANNER ⭐ NUEVO

El calendario de Mealie es el **panel visual de escritorio**. Cada vez que el usuario confirma el menú semanal, estas herramientas sincronizan el plan en el calendario de Mealie para que pueda verlo desde el ordenador.

#### get_mealplan_week
Obtiene el plan de comidas para un rango de fechas.
- Parámetros: `start_date` (string "YYYY-MM-DD", obligatorio), `end_date` (string "YYYY-MM-DD", obligatorio)
```
{tool: "mcp", args: {action: "call", server: "mealie_local", tool: "get_mealplan_week", args: {start_date: "2026-03-02", end_date: "2026-03-06"}}}
```

#### set_mealplan_entry
Añade una entrada al calendario de Mealie. Si la receta existe en Mealie, crea un enlace directo a ella.
- Parámetros:
  - `date_str` (string "YYYY-MM-DD", obligatorio)
  - `entry_type` (string: "lunch" | "dinner" | "breakfast" | "side", obligatorio)
  - `title` (string, obligatorio — nombre del plato que aparece en el calendario)
  - `recipe_slug` (string, opcional — si existe en Mealie, vincula la receta)
```
// Con receta vinculada (ideal):
{tool: "mcp", args: {action: "call", server: "mealie_local", tool: "set_mealplan_entry", args: {date_str: "2026-03-03", entry_type: "lunch", title: "Curry de pollo", recipe_slug: "curry-de-pollo"}}}

// Sin receta (solo texto):
{tool: "mcp", args: {action: "call", server: "mealie_local", tool: "set_mealplan_entry", args: {date_str: "2026-03-03", entry_type: "lunch", title: "Libre / tupper semana anterior"}}}
```

#### delete_mealplan_entry
Elimina una entrada del plan de comidas por su ID.
- Parámetros: `entry_id` (string, obligatorio)
```
{tool: "mcp", args: {action: "call", server: "mealie_local", tool: "delete_mealplan_entry", args: {entry_id: "entry-uuid"}}}
```

#### clear_mealplan_week
Elimina TODAS las entradas del calendario en un rango de fechas. Úsalo ANTES de poblar la semana nueva.
- Parámetros: `start_date` (string "YYYY-MM-DD", obligatorio), `end_date` (string "YYYY-MM-DD", obligatorio)
```
{tool: "mcp", args: {action: "call", server: "mealie_local", tool: "clear_mealplan_week", args: {start_date: "2026-03-02", end_date: "2026-03-06"}}}
```

---

### TAGS DE RECETAS ⭐ NUEVO

Los tags permiten organizar la biblioteca de Mealie y filtrar recetas en el panel de escritorio.

#### get_or_create_tag
Busca un tag por nombre (case-insensitive); si no existe, lo crea. Devuelve ID y nombre.
- Parámetros: `name` (string, obligatorio)
```
{tool: "mcp", args: {action: "call", server: "mealie_local", tool: "get_or_create_tag", args: {name: "japonesa"}}}
```

#### tag_recipe
Asigna tags a una receta existente. Conserva los tags ya existentes y añade los nuevos.
- Parámetros: `slug` (string, obligatorio), `tags` (array de strings, obligatorio)
```
{tool: "mcp", args: {action: "call", server: "mealie_local", tool: "tag_recipe", args: {slug: "ramen-de-pollo", tags: ["japonesa", "rápido", "batch-friendly"]}}}
```

---

## Servidor: spoonacular_local

**Propósito**: Búsqueda de recetas online y datos nutricionales. Usar cuando Mealie no tiene resultados.

### search_recipes
Busca recetas online por texto, opcionalmente filtradas por nutrientes.
- Parámetros obligatorios: `query` (string)
- Parámetros opcionales de nutrición (todos float, por ración):
  `max_calories`, `min_calories`, `max_protein_g`, `min_protein_g`,
  `max_fat_g`, `min_fat_g`, `max_carbs_g`, `min_carbs_g`, `number` (int)
```
{tool: "mcp", args: {action: "call", server: "spoonacular_local", tool: "search_recipes", args: {query: "ramen", max_calories: 500}}}
```

### search_recipes_by_nutrients
Busca recetas por criterios nutricionales.
- Parámetros: todos opcionales — `minProtein`, `maxProtein`, `minCalories`, `maxCalories`, `minFat`, `maxFat`, `minCarbs`, `maxCarbs`, `minFiber`, `number`
```
{tool: "mcp", args: {action: "call", server: "spoonacular_local", tool: "search_recipes_by_nutrients", args: {minProtein: 30, maxCalories: 500}}}
```

### ingredient_nutrition_100g
Información nutricional por cada 100g de un ingrediente.
- Parámetros: `ingredient` (string, obligatorio)
```
{tool: "mcp", args: {action: "call", server: "spoonacular_local", tool: "ingredient_nutrition_100g", args: {ingredient: "pechuga de pollo"}}}
```

---

## Servidor: recipe_scraper_local

**Propósito**: Extraer recetas de URLs de webs de cocina e importarlas a Mealie.

### scrape_recipe
Extrae una receta de cualquier URL (solo lectura, no guarda en Mealie).
- Parámetros: `url` (string, obligatorio)
```
{tool: "mcp", args: {action: "call", server: "recipe_scraper_local", tool: "scrape_recipe", args: {url: "https://www.recetasgratis.net/receta-de-paella-58020.html"}}}
```

### import_recipe_to_mealie
Importa una receta en Mealie directamente desde una URL.
- Parámetros: `url` (string, obligatorio)
```
{tool: "mcp", args: {action: "call", server: "recipe_scraper_local", tool: "import_recipe_to_mealie", args: {url: "https://www.recetasgratis.net/receta-de-paella-58020.html"}}}
```

---

## Servidor: memory_local

**Propósito**: Lectura y escritura de MEMORY.md del workspace. Para persistir datos del usuario.

### save_feedback
Persiste feedback de una receta en MEMORY.md.
- Parámetros: `recipe_name` (string, obligatorio)
```
{tool: "mcp", args: {action: "call", server: "memory_local", tool: "save_feedback", args: {recipe_name: "Pollo al horno"}}}
```

### read_memory
Lee MEMORY.md completo o una sección específica.
- Parámetros: ninguno obligatorio
```
{tool: "mcp", args: {action: "call", server: "memory_local", tool: "read_memory", args: {}}}
```

### update_pantry
Actualiza la sección de despensa con los ingredientes disponibles.
- Parámetros: `items` (obligatorio)
```
{tool: "mcp", args: {action: "call", server: "memory_local", tool: "update_pantry", args: {items: ["pollo", "arroz", "tomates", "cebolla"]}}}
```

### update_learned_preference
Añade una preferencia aprendida del usuario.
- Parámetros: `preference` (string, obligatorio)
```
{tool: "mcp", args: {action: "call", server: "memory_local", tool: "update_learned_preference", args: {preference: "Prefiere platos picantes"}}}
```

---

## Flujos Combinados (Patrones Frecuentes)

### Confirmar menú semanal → poblar calendario Mealie
```
1. clear_mealplan_week({start_date: "YYYY-MM-DD", end_date: "YYYY-MM-DD"})
2. Para cada comida del menú:
   a. search_recipes({query: "[nombre receta]"}) → obtener slug si existe
   b. set_mealplan_entry({date_str: "YYYY-MM-DD", entry_type: "lunch"|"dinner", title: "[nombre]", recipe_slug: "[slug o null]"})
3. get_or_create_shopping_list({name: "Semana X"})
4. Para cada receta → add_recipe_ingredients_to_list
```

### Importar receta con auto-etiquetado
```
1. scrape_recipe({url: "..."}) → previsualizar
2. import_recipe_to_mealie({url: "..."}) → guardar
3. search_recipes({query: "[nombre]"}) → obtener slug
4. tag_recipe({slug: "...", tags: ["tipo-cocina", "tiempo", "método", "categoría"]})
```

### Buscar receta (cascada Mealie → Spoonacular)
```
1. search_recipes({query: "..."}) → si hay resultados, presentar
2. Si no hay → spoonacular:search_recipes({query: "..."})
3. Presentar resultados con opción de importar a Mealie
```

### Consulta nutricional
```
1. spoonacular:ingredient_nutrition_100g({ingredient: "..."})
2. Presentar datos; si falla → informar honestamente, no inventar números
```

### Guardar feedback de receta
```
1. memory_local:save_feedback({recipe_name: "..."})
2. Confirmar al usuario
```

---

## Manejo de Errores

| Error | Causa Probable | Acción |
|---|---|---|
| `isError: true` | Servidor caído o params incorrectos | Informa al usuario, ofrece alternativa |
| Sin resultados en Mealie | Receta no en biblioteca local | Buscar en Spoonacular |
| Spoonacular rate limit | Exceso de consultas API | Sugerir desde Mealie o IA |
| URL no soportada | Web no compatible con scraper | Ofrecer creación manual |
| memory_local falla | Error de escritura | Reintentar, informar si persiste |
| set_mealplan_entry falla | Mealie sin conexión / token caducado | Continuar con lista de compra, informar brevemente |
| tag_recipe falla | Receta no encontrada en Mealie | Informar, continuar sin etiquetas |

---

**Última actualización**: 2026-02-27

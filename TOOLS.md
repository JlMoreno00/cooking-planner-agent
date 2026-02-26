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

**Propósito**: Biblioteca de recetas local (Mealie self-hosted). Primera opción SIEMPRE para buscar recetas.

### search_recipes
Busca recetas en Mealie por nombre. Devuelve lista con nombre y slug.
- Parámetros: `query` (string, obligatorio)
```
{tool: "mcp", args: {action: "call", server: "mealie_local", tool: "search_recipes", args: {query: "pollo al horno"}}}
```

### get_recipe
Obtiene una receta completa por su slug (incluyendo ingredientes e instrucciones).
- Parámetros: `slug` (string, obligatorio)
```
{tool: "mcp", args: {action: "call", server: "mealie_local", tool: "get_recipe", args: {slug: "pollo-al-horno"}}}
```

### create_recipe
Crea una receta en Mealie. Si se pasa url, importa desde esa URL. Si no, crea por nombre.
- Parámetros: `name` (string, obligatorio), `url` (string, opcional)
```
{tool: "mcp", args: {action: "call", server: "mealie_local", tool: "create_recipe", args: {name: "Ensalada César"}}}
```
Con URL:
```
{tool: "mcp", args: {action: "call", server: "mealie_local", tool: "create_recipe", args: {name: "Paella", url: "https://ejemplo.com/paella"}}}
```

### get_shopping_lists
Devuelve todas las listas de compra del hogar con sus IDs y nombres.
- Parámetros: ninguno
```
{tool: "mcp", args: {action: "call", server: "mealie_local", tool: "get_shopping_lists", args: {}}}
```

### get_or_create_shopping_list
Busca una lista de compra por nombre; si no existe, la crea. Devuelve siempre el ID.
- Parámetros: `name` (string, obligatorio)
```
{tool: "mcp", args: {action: "call", server: "mealie_local", tool: "get_or_create_shopping_list", args: {name: "Semana 10 - Marzo 2026"}}}
```

### add_items_to_shopping_list
Añade ingredientes a una lista de compra existente.
- Parámetros: `list_id` (string, obligatorio), `items` (array de strings, obligatorio)
```
{tool: "mcp", args: {action: "call", server: "mealie_local", tool: "add_items_to_shopping_list", args: {list_id: "abc123", items: ["Tomates (1kg)", "Cebolla (2 unidades)", "Aceite de oliva"]}}}
```

### add_recipe_ingredients_to_list
Añade automáticamente TODOS los ingredientes de una receta a una lista de compra.
- Parámetros: `list_id` (string, obligatorio), `recipe_slug` (string, obligatorio)
```
{tool: "mcp", args: {action: "call", server: "mealie_local", tool: "add_recipe_ingredients_to_list", args: {list_id: "list-uuid", recipe_slug: "pollo-al-horno"}}}
```

### create_shopping_list
Crea una nueva lista de compra vacía con el nombre indicado.
- Parámetros: `name` (string, obligatorio)
```
{tool: "mcp", args: {action: "call", server: "mealie_local", tool: "create_shopping_list", args: {name: "Lista especial"}}}
```

### delete_shopping_list
Elimina permanentemente una lista de compra por su ID.
- Parámetros: `list_id` (string, obligatorio)
```
{tool: "mcp", args: {action: "call", server: "mealie_local", tool: "delete_shopping_list", args: {list_id: "list-uuid"}}}
```

### clear_shopping_list
Elimina todos los ítems de una lista de compra (vaciado completo).
- Parámetros: `list_id` (string, obligatorio)
```
{tool: "mcp", args: {action: "call", server: "mealie_local", tool: "clear_shopping_list", args: {list_id: "list-uuid"}}}
```

---

## Servidor: spoonacular_local

**Propósito**: Búsqueda de recetas online y datos nutricionales. Usar cuando Mealie no tiene resultados.

### search_recipes
Busca recetas online por texto.
- Parámetros: `query` (string, obligatorio)
```
{tool: "mcp", args: {action: "call", server: "spoonacular_local", tool: "search_recipes", args: {query: "pasta carbonara"}}}
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

### Buscar receta (cascada Mealie -> Spoonacular)
1. `mealie_local:search_recipes` con query del usuario
2. Si hay resultados -> presentar con botones inline
3. Si no hay resultados -> `spoonacular_local:search_recipes` con misma query
4. Presentar resultados online con opción de importar a Mealie

### Importar receta desde URL
1. `recipe_scraper_local:scrape_recipe` para previsualizar
2. Mostrar al usuario con botón de confirmación
3. Si confirma -> `recipe_scraper_local:import_recipe_to_mealie`

### Generar lista de compra desde menú semanal
1. `mealie_local:get_or_create_shopping_list` con nombre de semana
2. Para cada receta -> `mealie_local:add_recipe_ingredients_to_list`
3. Presentar lista completa con botones de editar/confirmar

### Consulta nutricional
1. `spoonacular_local:ingredient_nutrition_100g` para el ingrediente
2. Presentar datos (calorías, proteína, grasas, carbohidratos)
3. Si falla -> informar honestamente, no inventar números

### Guardar feedback de receta
1. `memory_local:save_feedback` con nombre de receta
2. Confirmar al usuario que se ha guardado

---

## Manejo de Errores

| Error | Causa Probable | Acción |
|---|---|---|
| `isError: true` | Servidor caído o params incorrectos | Informa al usuario, ofrece alternativa |
| Sin resultados en Mealie | Receta no en biblioteca local | Buscar en Spoonacular |
| Spoonacular rate limit | Exceso de consultas API | Sugerir desde Mealie o IA |
| URL no soportada | Web no compatible con scraper | Ofrecer creación manual |
| memory_local falla | Error de escritura | Reintentar, informar si persiste |

---

**Última actualización**: 2026-02-26

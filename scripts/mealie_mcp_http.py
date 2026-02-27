#!/usr/bin/env python3
"""Mealie MCP Server — búsqueda de recetas, gestión de listas de compra y calendario semanal."""
import json
import os
from datetime import date, timedelta
from typing import Any

import requests
from mcp.server.fastmcp import FastMCP

BASE_URL = os.getenv("MEALIE_BASE_URL", "http://localhost:9925").rstrip("/")
API_TOKEN = os.getenv("MEALIE_API_TOKEN", "")
HOST = os.getenv("MEALIE_MCP_HOST", "127.0.0.1")
PORT = int(os.getenv("MEALIE_MCP_PORT", "9150"))

mcp = FastMCP("mealie", host=HOST, port=PORT, streamable_http_path="/mcp", stateless_http=True)


def _headers() -> dict[str, str]:
    if not API_TOKEN:
        return {}
    return {"Authorization": f"Bearer {API_TOKEN}", "Content-Type": "application/json"}


def _check_token() -> dict[str, Any] | None:
    if not API_TOKEN:
        return {"ok": False, "error": "missing_MEALIE_API_TOKEN"}
    return None


# ──────────────────────────────────────────────
# RECETAS
# ──────────────────────────────────────────────

@mcp.tool()
def search_recipes(query: str) -> dict[str, Any]:
    """Busca recetas en Mealie por nombre. Devuelve lista con nombre y slug."""
    if err := _check_token():
        return err
    try:
        r = requests.get(f"{BASE_URL}/api/recipes", headers=_headers(), timeout=30)
        if not (200 <= r.status_code < 300):
            return {"ok": False, "status": r.status_code, "body": r.text[:1000]}
        items = r.json().get("items") or []
        q = query.lower().strip()
        matches = [
            {"name": it.get("name"), "slug": it.get("slug")}
            for it in items
            if q in (it.get("name") or "").lower()
        ]
        return {"ok": True, "query": query, "total": len(matches), "items": matches}
    except Exception as e:
        return {"ok": False, "error": f"search_failed: {e}"}


@mcp.tool()
def get_recipe(slug: str) -> dict[str, Any]:
    """Obtiene una receta completa por su slug (incluyendo ingredientes e instrucciones)."""
    if err := _check_token():
        return err
    try:
        r = requests.get(f"{BASE_URL}/api/recipes/{slug}", headers=_headers(), timeout=30)
        if not (200 <= r.status_code < 300):
            return {"ok": False, "status": r.status_code, "body": r.text[:1000]}
        data = r.json()
        return {
            "ok": True,
            "id": data.get("id"),
            "name": data.get("name"),
            "slug": data.get("slug"),
            "description": data.get("description", ""),
            "recipeYield": data.get("recipeYield", ""),
            "totalTime": data.get("totalTime", ""),
            "recipeIngredient": [i.get("display", "") for i in (data.get("recipeIngredient") or [])],
            "recipeInstructions": [s.get("text", "") for s in (data.get("recipeInstructions") or [])],
            "tags": [{"id": t.get("id"), "name": t.get("name")} for t in (data.get("tags") or [])],
        }
    except Exception as e:
        return {"ok": False, "error": f"get_recipe_failed: {e}"}


@mcp.tool()
def create_recipe(name: str, url: str | None = None) -> dict[str, Any]:
    """Crea una receta en Mealie. Si se pasa url, importa desde esa URL. Si no, crea por nombre."""
    if err := _check_token():
        return err
    try:
        if url:
            payload = {"url": url, "includeCategories": True, "includeTags": True}
            r = requests.post(f"{BASE_URL}/api/recipes/create/url", headers=_headers(), json=payload, timeout=60)
            return {"ok": 200 <= r.status_code < 300, "status": r.status_code, "body": r.text[:2000]}

        # Crear por nombre con JSON-LD mínimo
        jsonld_recipe = {
            "@context": "https://schema.org",
            "@type": "Recipe",
            "name": name,
            "recipeIngredient": ["Ingrediente a completar"],
            "recipeInstructions": ["Instrucciones a completar"],
            "recipeYield": "2 raciones",
        }
        wrapped_payload = {"data": json.dumps(jsonld_recipe, ensure_ascii=False)}
        r = requests.post(f"{BASE_URL}/api/recipes/create/html-or-json", headers=_headers(), json=wrapped_payload, timeout=60)
        return {"ok": 200 <= r.status_code < 300, "status": r.status_code, "body": r.text[:2000]}
    except Exception as e:
        return {"ok": False, "error": f"create_failed: {e}"}


# ──────────────────────────────────────────────
# LISTAS DE COMPRA
# ──────────────────────────────────────────────

@mcp.tool()
def get_shopping_lists() -> dict[str, Any]:
    """Devuelve todas las listas de compra del hogar con sus IDs y nombres."""
    if err := _check_token():
        return err
    try:
        r = requests.get(f"{BASE_URL}/api/households/shopping/lists", headers=_headers(), timeout=30)
        if not (200 <= r.status_code < 300):
            return {"ok": False, "status": r.status_code, "body": r.text[:1000]}
        data = r.json()
        lists = [
            {"id": it.get("id"), "name": it.get("name"), "items_count": len(it.get("listItems") or [])}
            for it in (data.get("items") or [])
        ]
        return {"ok": True, "total": len(lists), "lists": lists}
    except Exception as e:
        return {"ok": False, "error": f"get_lists_failed: {e}"}


@mcp.tool()
def create_shopping_list(name: str) -> dict[str, Any]:
    """Crea una nueva lista de compra vacía con el nombre indicado."""
    if err := _check_token():
        return err
    try:
        r = requests.post(
            f"{BASE_URL}/api/households/shopping/lists",
            headers=_headers(),
            json={"name": name},
            timeout=30,
        )
        if not (200 <= r.status_code < 300):
            return {"ok": False, "status": r.status_code, "body": r.text[:1000]}
        data = r.json()
        return {"ok": True, "id": data.get("id"), "name": data.get("name")}
    except Exception as e:
        return {"ok": False, "error": f"create_list_failed: {e}"}


@mcp.tool()
def delete_shopping_list(list_id: str) -> dict[str, Any]:
    """Elimina permanentemente una lista de compra por su ID."""
    if err := _check_token():
        return err
    try:
        r = requests.delete(f"{BASE_URL}/api/households/shopping/lists/{list_id}", headers=_headers(), timeout=30)
        return {"ok": 200 <= r.status_code < 300, "status": r.status_code}
    except Exception as e:
        return {"ok": False, "error": f"delete_list_failed: {e}"}


@mcp.tool()
def add_items_to_shopping_list(list_id: str, items: list[str]) -> dict[str, Any]:
    """
    Añade ingredientes a una lista de compra existente.
    items: lista de strings con el texto de cada ingrediente, ej: ["Tomates (1kg)", "Cebolla (2 unidades)"]
    """
    if err := _check_token():
        return err
    if not items:
        return {"ok": False, "error": "items list is empty"}
    try:
        payload = [{"shoppingListId": list_id, "note": item, "quantity": 1} for item in items]
        r = requests.post(
            f"{BASE_URL}/api/households/shopping/items/create-bulk",
            headers=_headers(),
            json=payload,
            timeout=30,
        )
        if not (200 <= r.status_code < 300):
            return {"ok": False, "status": r.status_code, "body": r.text[:1000]}
        data = r.json()
        created = len(data.get("createdItems") or [])
        return {"ok": True, "list_id": list_id, "items_added": created}
    except Exception as e:
        return {"ok": False, "error": f"add_items_failed: {e}"}


@mcp.tool()
def clear_shopping_list(list_id: str) -> dict[str, Any]:
    """Elimina todos los ítems de una lista de compra (vaciado completo)."""
    if err := _check_token():
        return err
    try:
        # Obtener lista con sus ítems
        r = requests.get(f"{BASE_URL}/api/households/shopping/lists/{list_id}", headers=_headers(), timeout=30)
        if not (200 <= r.status_code < 300):
            return {"ok": False, "status": r.status_code, "body": r.text[:500]}
        data = r.json()
        items = data.get("listItems") or []
        if not items:
            return {"ok": True, "deleted": 0, "message": "Lista ya estaba vacía"}

        # Eliminar todos los ítems
        item_ids = [it["id"] for it in items if it.get("id")]
        params = "&".join(f"ids={iid}" for iid in item_ids)
        rd = requests.delete(
            f"{BASE_URL}/api/households/shopping/items?{params}",
            headers=_headers(),
            timeout=30,
        )
        return {"ok": 200 <= rd.status_code < 300, "deleted": len(item_ids), "status": rd.status_code}
    except Exception as e:
        return {"ok": False, "error": f"clear_list_failed: {e}"}


@mcp.tool()
def add_recipe_ingredients_to_list(list_id: str, recipe_slug: str) -> dict[str, Any]:
    """
    Añade automáticamente TODOS los ingredientes de una receta a una lista de compra.
    Ideal para generar la lista semanal a partir del plan de comidas.
    """
    if err := _check_token():
        return err
    try:
        r = requests.post(
            f"{BASE_URL}/api/households/shopping/lists/{list_id}/recipe/{recipe_slug}",
            headers=_headers(),
            timeout=30,
        )
        if not (200 <= r.status_code < 300):
            return {"ok": False, "status": r.status_code, "body": r.text[:500], "recipe_slug": recipe_slug}
        return {"ok": True, "list_id": list_id, "recipe_slug": recipe_slug, "status": r.status_code}
    except Exception as e:
        return {"ok": False, "error": f"add_recipe_failed: {e}"}


@mcp.tool()
def get_or_create_shopping_list(name: str) -> dict[str, Any]:
    """
    Busca una lista de compra por nombre; si no existe, la crea.
    Devuelve siempre el ID de la lista resultante.
    """
    if err := _check_token():
        return err
    try:
        r = requests.get(f"{BASE_URL}/api/households/shopping/lists", headers=_headers(), timeout=30)
        if 200 <= r.status_code < 300:
            for it in (r.json().get("items") or []):
                if it.get("name", "").lower() == name.lower():
                    return {"ok": True, "id": it["id"], "name": it["name"], "created": False}
        # No existe, crear
        r2 = requests.post(
            f"{BASE_URL}/api/households/shopping/lists",
            headers=_headers(),
            json={"name": name},
            timeout=30,
        )
        if not (200 <= r2.status_code < 300):
            return {"ok": False, "status": r2.status_code, "body": r2.text[:500]}
        data = r2.json()
        return {"ok": True, "id": data["id"], "name": data["name"], "created": True}
    except Exception as e:
        return {"ok": False, "error": f"get_or_create_failed: {e}"}


# ──────────────────────────────────────────────
# CALENDARIO / MEAL PLANNER
# ──────────────────────────────────────────────

@mcp.tool()
def get_mealplan_week(start_date: str, end_date: str) -> dict[str, Any]:
    """
    Obtiene el plan de comidas para un rango de fechas.
    start_date / end_date: formato "YYYY-MM-DD"
    """
    if err := _check_token():
        return err
    try:
        params = {"start_date": start_date, "end_date": end_date}
        r = requests.get(f"{BASE_URL}/api/households/mealplans", headers=_headers(), params=params, timeout=30)
        if not (200 <= r.status_code < 300):
            return {"ok": False, "status": r.status_code, "body": r.text[:1000]}
        data = r.json()
        entries = data.get("items") or []
        result = []
        for e in entries:
            recipe = e.get("recipe") or {}
            result.append({
                "id": e.get("id"),
                "date": e.get("date"),
                "entryType": e.get("entryType"),
                "title": e.get("title") or recipe.get("name", ""),
                "recipe_slug": recipe.get("slug"),
                "recipe_id": recipe.get("id"),
            })
        return {"ok": True, "total": len(result), "entries": result}
    except Exception as e:
        return {"ok": False, "error": f"get_mealplan_failed: {e}"}


@mcp.tool()
def set_mealplan_entry(date_str: str, entry_type: str, title: str, recipe_slug: str | None = None) -> dict[str, Any]:
    """
    Añade una entrada al calendario de Mealie.
    date_str: "YYYY-MM-DD"
    entry_type: "lunch" | "dinner" | "breakfast" | "side"
    title: nombre del plato (se muestra siempre en el calendario)
    recipe_slug: slug de la receta en Mealie (opcional — resuelve el ID automáticamente).
                 Si la receta no existe en Mealie, se crea una entrada de texto sin enlace.
    """
    if err := _check_token():
        return err
    try:
        payload: dict[str, Any] = {
            "date": date_str,
            "entryType": entry_type,
            "title": title,
            "text": "",
        }

        # Resolver slug → UUID si se proporcionó slug
        if recipe_slug:
            rr = requests.get(f"{BASE_URL}/api/recipes/{recipe_slug}", headers=_headers(), timeout=30)
            if 200 <= rr.status_code < 300:
                recipe_data = rr.json()
                payload["recipeId"] = recipe_data.get("id")
            # Si no existe la receta, continuamos sin recipeId (entrada solo con título)

        r = requests.post(f"{BASE_URL}/api/households/mealplans", headers=_headers(), json=payload, timeout=30)
        if not (200 <= r.status_code < 300):
            return {"ok": False, "status": r.status_code, "body": r.text[:500]}
        data = r.json()
        return {
            "ok": True,
            "id": data.get("id"),
            "date": date_str,
            "entry_type": entry_type,
            "title": title,
            "has_recipe_link": "recipeId" in payload,
        }
    except Exception as e:
        return {"ok": False, "error": f"set_mealplan_failed: {e}"}


@mcp.tool()
def delete_mealplan_entry(entry_id: str) -> dict[str, Any]:
    """Elimina una entrada del plan de comidas por su ID."""
    if err := _check_token():
        return err
    try:
        r = requests.delete(f"{BASE_URL}/api/households/mealplans/{entry_id}", headers=_headers(), timeout=30)
        return {"ok": 200 <= r.status_code < 300, "status": r.status_code, "entry_id": entry_id}
    except Exception as e:
        return {"ok": False, "error": f"delete_mealplan_failed: {e}"}


@mcp.tool()
def clear_mealplan_week(start_date: str, end_date: str) -> dict[str, Any]:
    """
    Elimina todas las entradas del plan de comidas en el rango de fechas (inclusive).
    start_date / end_date: formato "YYYY-MM-DD"
    Úsalo antes de poblar la semana nueva para evitar duplicados.
    """
    if err := _check_token():
        return err
    try:
        # Obtener entradas del rango
        params = {"start_date": start_date, "end_date": end_date}
        r = requests.get(f"{BASE_URL}/api/households/mealplans", headers=_headers(), params=params, timeout=30)
        if not (200 <= r.status_code < 300):
            return {"ok": False, "status": r.status_code, "body": r.text[:500]}
        entries = r.json().get("items") or []
        if not entries:
            return {"ok": True, "deleted": 0, "message": "No había entradas en ese rango"}

        deleted = 0
        errors = []
        for entry in entries:
            eid = entry.get("id")
            if not eid:
                continue
            rd = requests.delete(f"{BASE_URL}/api/households/mealplans/{eid}", headers=_headers(), timeout=30)
            if 200 <= rd.status_code < 300:
                deleted += 1
            else:
                errors.append({"id": eid, "status": rd.status_code})

        return {"ok": True, "deleted": deleted, "errors": errors, "range": f"{start_date} → {end_date}"}
    except Exception as e:
        return {"ok": False, "error": f"clear_mealplan_failed: {e}"}


# ──────────────────────────────────────────────
# TAGS DE RECETAS
# ──────────────────────────────────────────────

@mcp.tool()
def get_or_create_tag(name: str) -> dict[str, Any]:
    """
    Busca un tag por nombre (case-insensitive); si no existe, lo crea.
    Devuelve el ID y nombre del tag.
    """
    if err := _check_token():
        return err
    try:
        r = requests.get(f"{BASE_URL}/api/organizers/tags", headers=_headers(), timeout=30)
        if 200 <= r.status_code < 300:
            tags = r.json().get("items") or []
            for t in tags:
                if (t.get("name") or "").lower() == name.lower():
                    return {"ok": True, "id": t["id"], "name": t["name"], "created": False}

        # No existe → crear
        r2 = requests.post(f"{BASE_URL}/api/organizers/tags", headers=_headers(), json={"name": name}, timeout=30)
        if not (200 <= r2.status_code < 300):
            return {"ok": False, "status": r2.status_code, "body": r2.text[:500]}
        data = r2.json()
        return {"ok": True, "id": data.get("id"), "name": data.get("name"), "created": True}
    except Exception as e:
        return {"ok": False, "error": f"get_or_create_tag_failed: {e}"}


@mcp.tool()
def tag_recipe(slug: str, tags: list[str]) -> dict[str, Any]:
    """
    Asigna etiquetas (tags) a una receta existente en Mealie.
    slug: slug de la receta.
    tags: lista de nombres de tag (ej: ["japonesa", "rápido", "batch-friendly"]).
    Se respetan los tags ya existentes; solo se añaden los nuevos.
    """
    if err := _check_token():
        return err
    try:
        # 1. Obtener receta actual (para conservar tags existentes)
        r = requests.get(f"{BASE_URL}/api/recipes/{slug}", headers=_headers(), timeout=30)
        if not (200 <= r.status_code < 300):
            return {"ok": False, "status": r.status_code, "error": f"recipe_not_found: {slug}"}
        recipe_data = r.json()
        existing_tags = {t["id"]: t for t in (recipe_data.get("tags") or [])}

        # 2. Resolver/crear cada tag nuevo
        added = []
        for tag_name in tags:
            tag_result = get_or_create_tag(tag_name)
            if tag_result.get("ok") and tag_result.get("id"):
                tid = tag_result["id"]
                if tid not in existing_tags:
                    existing_tags[tid] = {"id": tid, "name": tag_result["name"]}
                    added.append(tag_result["name"])

        # 3. PATCH receta con la lista completa de tags
        all_tags = list(existing_tags.values())
        rp = requests.patch(
            f"{BASE_URL}/api/recipes/{slug}",
            headers=_headers(),
            json={"tags": all_tags},
            timeout=30,
        )
        if not (200 <= rp.status_code < 300):
            return {"ok": False, "status": rp.status_code, "body": rp.text[:500]}

        return {
            "ok": True,
            "slug": slug,
            "tags_added": added,
            "total_tags": len(all_tags),
        }
    except Exception as e:
        return {"ok": False, "error": f"tag_recipe_failed: {e}"}



# ──────────────────────────────────────────────
# COMENTARIOS Y COOKING LOG
# ──────────────────────────────────────────────

@mcp.tool()
def add_recipe_comment(slug: str, text: str) -> dict[str, Any]:
    """
    Añade un comentario a una receta en Mealie.
    Ideal para guardar el feedback del usuario (rating, notas) visible en el panel de escritorio.
    slug: slug de la receta.
    text: texto del comentario (ej: "4 estrellas, muy buena, la repetiria con mas ajo").
    """
    if err := _check_token():
        return err
    try:
        rr = requests.get(f"{BASE_URL}/api/recipes/{slug}", headers=_headers(), timeout=30)
        if not (200 <= rr.status_code < 300):
            return {"ok": False, "status": rr.status_code, "error": f"recipe_not_found: {slug}"}
        recipe_id = rr.json().get("id")
        if not recipe_id:
            return {"ok": False, "error": f"recipe_id_missing_for: {slug}"}

        r = requests.post(
            f"{BASE_URL}/api/comments",
            headers=_headers(),
            json={"recipeId": recipe_id, "text": text},
            timeout=30,
        )
        if not (200 <= r.status_code < 300):
            return {"ok": False, "status": r.status_code, "body": r.text[:500]}
        data = r.json()
        return {"ok": True, "comment_id": data.get("id"), "slug": slug, "text": text}
    except Exception as e:
        return {"ok": False, "error": f"add_comment_failed: {e}"}


@mcp.tool()
def log_cooking_event(slug: str, subject: str, message: str | None = None) -> dict[str, Any]:
    """
    Registra un evento en el timeline de una receta en Mealie (cooking log).
    Usalo cuando el usuario cocina una receta para tener historial de lo cocinado.
    slug: slug de la receta.
    subject: titulo del evento (ej: "Cocinado el lunes", "Batch domingo 2 mar").
    message: detalle opcional (ej: "Menos sal que la receta. Tiempo real: 28 min").
    """
    if err := _check_token():
        return err
    try:
        rr = requests.get(f"{BASE_URL}/api/recipes/{slug}", headers=_headers(), timeout=30)
        if not (200 <= rr.status_code < 300):
            return {"ok": False, "status": rr.status_code, "error": f"recipe_not_found: {slug}"}
        recipe_id = rr.json().get("id")
        if not recipe_id:
            return {"ok": False, "error": f"recipe_id_missing_for: {slug}"}

        payload: dict[str, Any] = {
            "recipeId": recipe_id,
            "subject": subject,
            "eventType": "info",
        }
        if message:
            payload["eventMessage"] = message

        r = requests.post(
            f"{BASE_URL}/api/recipes/timeline/events",
            headers=_headers(),
            json=payload,
            timeout=30,
        )
        if not (200 <= r.status_code < 300):
            return {"ok": False, "status": r.status_code, "body": r.text[:500]}
        data = r.json()
        return {"ok": True, "event_id": data.get("id"), "slug": slug, "subject": subject}
    except Exception as e:
        return {"ok": False, "error": f"log_cooking_event_failed: {e}"}


if __name__ == "__main__":
    mcp.run(transport="streamable-http")

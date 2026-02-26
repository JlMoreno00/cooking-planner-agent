#!/usr/bin/env python3
"""Mealie MCP Server — búsqueda de recetas, gestión de listas de compra."""
import json
import os
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
            "name": data.get("name"),
            "slug": data.get("slug"),
            "description": data.get("description", ""),
            "recipeYield": data.get("recipeYield", ""),
            "totalTime": data.get("totalTime", ""),
            "recipeIngredient": [i.get("display", "") for i in (data.get("recipeIngredient") or [])],
            "recipeInstructions": [s.get("text", "") for s in (data.get("recipeInstructions") or [])],
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


if __name__ == "__main__":
    mcp.run(transport="streamable-http")

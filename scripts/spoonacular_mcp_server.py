#!/usr/bin/env python3
"""Spoonacular MCP HTTP Server

Exposes recipe-search and ingredient-nutrition tools via FastMCP / streamable-HTTP.

Usage:
    python scripts/spoonacular_mcp_server.py --host 127.0.0.1 --port 9152 --path /mcp

Environment variables:
    SPOONACULAR_API_KEY   (required) Spoonacular REST API key.
    SPOONACULAR_MCP_HOST  (optional) default bind host  [127.0.0.1]
    SPOONACULAR_MCP_PORT  (optional) default bind port  [9152]
    SPOONACULAR_MCP_PATH  (optional) default HTTP path  [/mcp]
"""

import argparse
import os
from typing import Any

import requests
from mcp.server.fastmcp import FastMCP

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
API_KEY: str = os.getenv("SPOONACULAR_API_KEY", "")
BASE_URL: str = "https://api.spoonacular.com"
TIMEOUT: int = 20  # seconds per HTTP request


# ---------------------------------------------------------------------------
# Parse CLI args at module level so FastMCP is instantiated with the right
# host/port/path regardless of when decorators run.
# parse_known_args avoids errors when the module is imported without args.
# ---------------------------------------------------------------------------
def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Spoonacular FastMCP HTTP server",
        add_help=True,
    )
    parser.add_argument(
        "--host",
        default=os.getenv("SPOONACULAR_MCP_HOST", "127.0.0.1"),
        help="Bind host (default: %(default)s)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=int(os.getenv("SPOONACULAR_MCP_PORT", "9152")),
        help="Bind port (default: %(default)s)",
    )
    parser.add_argument(
        "--path",
        default=os.getenv("SPOONACULAR_MCP_PATH", "/mcp"),
        help="HTTP path for the MCP endpoint (default: %(default)s)",
    )
    args, _ = parser.parse_known_args()
    return args


_args = _parse_args()

# ---------------------------------------------------------------------------
# FastMCP instance
# ---------------------------------------------------------------------------
mcp = FastMCP(
    "spoonacular",
    host=_args.host,
    port=_args.port,
    streamable_http_path=_args.path,
    stateless_http=True,
)


# ---------------------------------------------------------------------------
# Internal HTTP helper
# ---------------------------------------------------------------------------
def _spoonacular_get(
    path: str, params: dict[str, Any] | None = None
) -> dict[str, Any]:
    """Perform a GET request to the Spoonacular API.

    Always returns a dict:
      ok=True  -> 'data' key contains the parsed JSON response.
      ok=False -> 'error' and 'message' keys describe the failure.
    """
    if not API_KEY:
        return {
            "ok": False,
            "error": "missing_api_key",
            "message": (
                "La variable de entorno SPOONACULAR_API_KEY no está configurada. "
                "Set the SPOONACULAR_API_KEY environment variable before starting the server."
            ),
        }

    request_params: dict[str, Any] = dict(params or {})
    request_params["apiKey"] = API_KEY

    try:
        r = requests.get(
            f"{BASE_URL}{path}", params=request_params, timeout=TIMEOUT
        )
    except requests.exceptions.Timeout:
        return {
            "ok": False,
            "error": "timeout",
            "message": (
                f"La petición a Spoonacular superó {TIMEOUT}s. "
                "Request timed out — try again later."
            ),
        }
    except requests.exceptions.ConnectionError as exc:
        return {
            "ok": False,
            "error": "connection_error",
            "message": f"No se pudo conectar con Spoonacular: {exc}",
        }
    except Exception as exc:
        return {
            "ok": False,
            "error": "unexpected_error",
            "message": f"Error inesperado al llamar a Spoonacular: {exc}",
        }

    if r.status_code == 401:
        return {
            "ok": False,
            "error": "auth_error",
            "message": (
                "API key inválida o no autorizada (HTTP 401). "
                "Verify that SPOONACULAR_API_KEY is correct."
            ),
        }
    if r.status_code == 402:
        return {
            "ok": False,
            "error": "quota_exceeded",
            "message": (
                "Límite de cuota de Spoonacular alcanzado (HTTP 402). "
                "Daily quota exceeded — upgrade the plan or retry tomorrow."
            ),
        }
    if r.status_code == 429:
        return {
            "ok": False,
            "error": "rate_limited",
            "message": (
                "Demasiadas peticiones a Spoonacular (HTTP 429). "
                "Rate limit hit — wait a moment and retry."
            ),
        }
    if not (200 <= r.status_code < 300):
        return {
            "ok": False,
            "error": f"http_{r.status_code}",
            "message": (
                f"Spoonacular devolvió HTTP {r.status_code}: {r.text[:400]}"
            ),
        }

    try:
        return {"ok": True, "data": r.json()}
    except Exception as exc:
        return {
            "ok": False,
            "error": "json_parse_error",
            "message": f"No se pudo parsear la respuesta JSON de Spoonacular: {exc}",
        }


# ---------------------------------------------------------------------------
# MCP Tools
# ---------------------------------------------------------------------------


@mcp.tool()
def search_recipes(query: str, number: int = 5) -> dict[str, Any]:
    """Search recipes by free-text query via Spoonacular /recipes/complexSearch.

    Args:
        query:  Keywords to search for (e.g. "pasta carbonara", "chicken salad").
        number: Number of results to return (default 5, max 100).

    Returns:
        ok=True  with a list of matching recipes (id, title, image, source_url).
        ok=False with error details on auth/rate/network failure.
    """
    result = _spoonacular_get(
        "/recipes/complexSearch",
        {
            "query": query,
            "number": max(1, min(number, 100)),
            "addRecipeInformation": False,
        },
    )
    if not result["ok"]:
        return result

    data = result["data"]
    recipes = [
        {
            "id": r.get("id"),
            "title": r.get("title"),
            "image": r.get("image"),
            "source_url": r.get("sourceUrl"),
        }
        for r in (data.get("results") or [])
    ]
    return {
        "ok": True,
        "query": query,
        "total": data.get("totalResults", len(recipes)),
        "recipes": recipes,
    }


@mcp.tool()
def search_recipes_by_nutrients(
    min_protein_g: float | None = None,
    max_calories_kcal: float | None = None,
    max_carbs_g: float | None = None,
    number: int = 5,
) -> dict[str, Any]:
    """Find recipes that meet nutritional constraints via /recipes/findByNutrients.

    Args:
        min_protein_g:     Minimum protein in grams per serving.
        max_calories_kcal: Maximum calories (kcal) per serving.
        max_carbs_g:       Maximum carbohydrates in grams per serving.
        number:            Number of results to return (default 5, max 100).

    Returns:
        ok=True  with a list of recipes (id, title, image, calories, protein, fat, carbs).
        ok=False with error details on auth/rate/network failure.
    """
    params: dict[str, Any] = {"number": max(1, min(number, 100))}
    if min_protein_g is not None:
        params["minProtein"] = min_protein_g
    if max_calories_kcal is not None:
        params["maxCalories"] = max_calories_kcal
    if max_carbs_g is not None:
        params["maxCarbs"] = max_carbs_g

    result = _spoonacular_get("/recipes/findByNutrients", params)
    if not result["ok"]:
        return result

    raw = result["data"]
    items = raw if isinstance(raw, list) else []
    recipes = [
        {
            "id": r.get("id"),
            "title": r.get("title"),
            "image": r.get("image"),
            "calories": r.get("calories"),
            "protein": r.get("protein"),
            "fat": r.get("fat"),
            "carbs": r.get("carbs"),
        }
        for r in items
    ]
    return {"ok": True, "filters": params, "recipes": recipes}


@mcp.tool()
def ingredient_nutrition_100g(ingredient: str) -> dict[str, Any]:
    """Return nutritional information per 100 g for a given ingredient.

    Two-step lookup:
    1. Search /food/ingredients/search to resolve the ingredient name to an ID.
    2. Fetch /food/ingredients/{id}/information with amount=100&unit=grams.

    Args:
        ingredient: Ingredient name in English (e.g. "chicken breast", "brown rice").

    Returns:
        ok=True  with spoonacular_id, ingredient name, and a nutrients dict
                 keyed by nutrient name -> {amount, unit}.
        ok=False with error details on auth/rate/network/not-found failure.
    """
    # Step 1: resolve name -> ID
    search_result = _spoonacular_get(
        "/food/ingredients/search",
        {"query": ingredient, "number": 1, "metaInformation": True},
    )
    if not search_result["ok"]:
        return search_result

    results = (search_result["data"] or {}).get("results") or []
    if not results:
        return {
            "ok": False,
            "error": "not_found",
            "message": (
                f"No se encontró el ingrediente '{ingredient}' en Spoonacular. "
                "Try a different spelling or use the English ingredient name."
            ),
        }

    ingredient_id: int = results[0]["id"]
    found_name: str = results[0].get("name", ingredient)

    # Step 2: fetch nutrition for 100 g
    info_result = _spoonacular_get(
        f"/food/ingredients/{ingredient_id}/information",
        {"amount": 100, "unit": "grams"},
    )
    if not info_result["ok"]:
        return info_result

    info = info_result["data"] or {}
    nutrients_raw = (info.get("nutrition") or {}).get("nutrients") or []
    nutrients = {
        n["name"]: {"amount": n.get("amount"), "unit": n.get("unit")}
        for n in nutrients_raw
    }

    return {
        "ok": True,
        "ingredient": found_name,
        "spoonacular_id": ingredient_id,
        "amount_g": 100,
        "nutrients": nutrients,
    }


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    mcp.run(transport="streamable-http")

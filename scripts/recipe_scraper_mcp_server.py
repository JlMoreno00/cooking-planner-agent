#!/usr/bin/env python3
"""Recipe Scraper MCP Server — con soporte para sitios sin scraper nativo via wild_mode."""
import os
import urllib.error
import urllib.request
from typing import Any

import requests
from mcp.server.fastmcp import FastMCP
from recipe_scrapers import scrape_html

HOST = os.getenv("RECIPE_SCRAPER_MCP_HOST", "127.0.0.1")
PORT = int(os.getenv("RECIPE_SCRAPER_MCP_PORT", "9151"))
MEALIE_BASE_URL = os.getenv("MEALIE_BASE_URL", "http://localhost:9925").rstrip("/")
MEALIE_API_TOKEN = os.getenv("MEALIE_API_TOKEN", "")

# User-Agent que elude la mayoría de bloqueos anti-bot básicos
_BROWSER_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "es-ES,es;q=0.9,en;q=0.8",
    "Accept-Encoding": "gzip, deflate, br",
}

mcp = FastMCP("recipe-scraper", host=HOST, port=PORT, streamable_http_path="/mcp", stateless_http=True)


def _fetch_html(url: str, timeout: int = 20) -> str:
    """Descarga HTML con cabeceras de navegador para eludir anti-bot básico."""
    req = urllib.request.Request(url, headers=_BROWSER_HEADERS)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        charset = "utf-8"
        ct = resp.headers.get_content_charset()
        if ct:
            charset = ct
        return resp.read().decode(charset, errors="replace")


def _normalize(s: Any) -> dict[str, Any]:
    """Extrae campos estándar del objeto scraper."""
    def safe(fn):
        try:
            return fn()
        except Exception:
            return None

    return {
        "title": safe(s.title),
        "total_time": safe(s.total_time),
        "yields": safe(s.yields),
        "image": safe(s.image),
        "host": safe(s.host),
        "ingredients": safe(s.ingredients) or [],
        "instructions": safe(s.instructions),
        "description": safe(s.description),
        "nutrients": safe(s.nutrients),
    }


@mcp.tool()
def scrape_recipe(url: str) -> dict[str, Any]:
    """
    Extrae una receta de cualquier URL.

    Estrategia:
    1. Descarga el HTML con User-Agent de navegador.
    2. Intenta el parser nativo del sitio (si existe en recipe-scrapers).
    3. Si no hay parser nativo o falla, activa wild_mode que extrae JSON-LD schema.org/Recipe.
    4. Funciona con directoalpaladar.com, pequerecetas.com, recetasgratis.net, etc.
    """
    try:
        html = _fetch_html(url)
    except urllib.error.HTTPError as e:
        return {"ok": False, "url": url, "error": f"http_{e.code}", "detail": str(e)}
    except Exception as e:
        return {"ok": False, "url": url, "error": "fetch_failed", "detail": str(e)[:300]}

    # Intento 1: parser nativo del sitio
    try:
        s = scrape_html(html, org_url=url)
        data = _normalize(s)
        if data["title"] and (data["ingredients"] or data["instructions"]):
            return {"ok": True, "url": url, "mode": "native", "recipe": data}
    except Exception:
        pass  # Caer a wild_mode

    # Intento 2: wild_mode — extrae JSON-LD / microdata de cualquier página
    try:
        s = scrape_html(html, org_url=url, wild_mode=True)
        data = _normalize(s)
        if data["title"]:
            return {"ok": True, "url": url, "mode": "wild", "recipe": data}
        return {
            "ok": False,
            "url": url,
            "error": "no_recipe_found",
            "detail": "La página no contiene marcado de receta (schema.org/Recipe). Prueba con otra URL.",
        }
    except Exception as e:
        return {"ok": False, "url": url, "error": "wild_mode_failed", "detail": str(e)[:300]}


@mcp.tool()
def import_recipe_to_mealie(url: str) -> dict[str, Any]:
    """
    Importa una receta en Mealie directamente desde una URL.
    Mealie tiene su propio scraper interno que puede cubrir sitios adicionales.
    Útil como alternativa cuando scrape_recipe tiene problemas con un sitio específico.
    """
    if not MEALIE_API_TOKEN:
        return {"ok": False, "error": "missing_MEALIE_API_TOKEN"}
    endpoint = f"{MEALIE_BASE_URL}/api/recipes/create/url"
    headers = {
        "Authorization": f"Bearer {MEALIE_API_TOKEN}",
        "Content-Type": "application/json",
    }
    payload = {"url": url, "includeCategories": True, "includeTags": True}
    try:
        r = requests.post(endpoint, headers=headers, json=payload, timeout=60)
        return {"ok": 200 <= r.status_code < 300, "status": r.status_code, "body": r.text[:4000]}
    except Exception as e:
        return {"ok": False, "error": f"import_failed: {e}"}


if __name__ == "__main__":
    mcp.run(transport="streamable-http")

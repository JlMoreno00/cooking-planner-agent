"""Bring! MCP Server — sincronización de lista de compra con la app Bring!
Usa el catálogo oficial de Bring! (bundleado en bring-api) para que los ítems
aparezcan con iconos y clasificación automática.
"""

import json
import os
import re
import time
from pathlib import Path
from typing import Any

import requests
from mcp.server.fastmcp import FastMCP

# ── Config ──────────────────────────────────────────────────────────────────
BRING_EMAIL    = os.getenv("BRING_EMAIL", "")
BRING_PASSWORD = os.getenv("BRING_PASSWORD", "")
BRING_API_KEY  = "cof4Nc6D8saplXjE3h3HXqHH8m7VU2i1Gs0g85Sp"

MEALIE_BASE  = os.getenv("MEALIE_BASE_URL", "http://localhost:9925")
MEALIE_TOKEN = os.getenv("MEALIE_API_TOKEN") or os.getenv("MEALIE_API_KEY", "")

# Palabras de preparación que no son nombre del alimento
# Sustantivos de cantidad que deben eliminarse en "X de Y" → Y
# Ej: "dientes de ajo" → "ajo", "filetes de salmón" → "salmón"
_QUANTITY_NOUNS = {
    "diente", "dientes",    # cloves
    "lata", "latas",        # cans
    "taza", "tazas",        # cups
    "ramita", "ramitas",    # sprigs
    "pizca", "pizcas",      # pinches
    "rodaja", "rodajas",    # slices
    "filete", "filetes",    # fillets
    "trozo", "trozos",      # pieces
    "puñado", "puñados",    # handfuls
    "manojo", "manojos",    # bunches
    "chorrito", "chorritos",# dashes
    "hoja", "hojas",        # leaves
    "rama", "ramas",        # branches/stalks
    # English
    "clove", "cloves", "can", "cans", "cup", "cups", "sprig", "sprigs",
    "slice", "slices", "bunch", "bunches", "pinch", "pinches",
    "piece", "pieces", "fillet", "fillets", "leaf",
    # Cooking units that appear as "unit de food" in Spanish
    "cucharadita", "cucharaditas", "cucharada", "cucharadas",
    "tablespoon", "tablespoons", "teaspoon", "teaspoons",
}

_PREP_WORDS = {
    "picada", "picado", "picadas", "picados",
    "troceada", "troceado", "troceadas", "troceados",
    "en tiras", "en rodajas", "en brunoise", "en cubos",
    "rallado", "rallada", "rallados", "ralladas",
    "fresco", "fresca", "frescos", "frescas",
    "cocido", "cocida", "cocidos", "cocidas",
    "congelado", "congelada", "congelados", "congeladas",
    "enlatado", "enlatada", "seco", "seca",
    "pelado", "pelada", "pelados", "peladas",
    "deshuesado", "deshuesada", "sin hueso",
    "triturado", "triturada", "triturados", "trituradas",
    "machacado", "machacada", "tostado", "tostada",
}

# ── Catálogo Bring! ──────────────────────────────────────────────────────────
def _load_catalog(lang: str) -> dict[str, str]:
    """Carga catálogo Bring!.

    Devuelve {nombre_lower: nombre_canonical} más alias en singular para
    entradas plurales (ej. "Cebollas"→"cebollas" Y "cebolla",
    "Tomates cherry"→"tomate cherry"). El nombre canónico siempre es el
    original del catálogo.
    """
    base = Path(os.path.dirname(__file__)).parent / ".venv/lib"
    for p in base.rglob(f"articles.{lang}.json"):
        data = json.loads(p.read_text())
        result: dict[str, str] = {}
        # data = {german_key: localized_name}
        # We want {localized_name_lower: german_key} so that itemId sent to the API
        # is always the German internal key that Bring! needs for icons & categories.
        for german_key, localized_name in data.items():
            key = localized_name.lower()
            result[key] = german_key
            # Singular alias: "cebollas" → "cebolla" maps to same german key "Zwiebeln"
            words = key.split()
            if words and words[0].endswith("s") and len(words[0]) > 4:
                singular_key = " ".join([words[0][:-1]] + words[1:])
                if singular_key not in result:
                    result[singular_key] = german_key
            # Also singularize the LAST word for compound entries: "sweet potatoes" → "sweet potato"
            if len(words) > 1 and words[-1].endswith("s") and len(words[-1]) > 4:
                singular_last = " ".join(words[:-1] + [words[-1][:-1]])
                if singular_last not in result:
                    result[singular_last] = german_key
        return result
    return {}

_CAT_ES = _load_catalog("es-ES")   # 373 ítems en español
_CAT_EN = _load_catalog("en-US")   # 383 ítems en inglés

# Manual aliases for ingredients that don't resolve via fuzzy matching
# {normalized_food_name: german_key}
_MANUAL_ALIASES: dict[str, str] = {
    "bay leaf":       "Laurel",
    "bay leaves":     "Laurel",
    "laurel":         "Laurel",
    "hoja de laurel": "Laurel",
    "hojas de laurel":"Laurel",
    "boniato":        "Süsskartoffeln",
    "batata":         "Süsskartoffeln",
    "camote":         "Süsskartoffeln",
    "judias verdes":  "Bohnen",   # sin tilde (normalizado)
    "judia verde":    "Bohnen",
    "green bean":     "Bohnen",
    "green beans":    "Bohnen",
    "comino":         "Kümmel",
    "cumin":          "Kümmel",
    "cayena":         "Cayennepfeffer",
    "cayenne":        "Cayennepfeffer",
    "red pepper flakes": "Cayennepfeffer",
    "chili flakes":   "Cayennepfeffer",
    "chile flakes":   "Cayennepfeffer",
    "kale":           "Grünkohl",
    "col rizada":     "Grünkohl",
    "pimenton":       "Paprikapulver",   # sin tilde
    "pimenton ahumado": "Paprikapulver",
    "smoked paprika": "Paprikapulver",
    "sweet potato":   "Süsskartoffeln",
    "sweet potatoes": "Süsskartoffeln",
}


def _remove_accents(text: str) -> str:
    """Normaliza texto eliminando tildes para comparación."""
    subs = [("á","a"),("é","e"),("í","i"),("ó","o"),("ú","u"),
            ("à","a"),("è","e"),("ì","i"),("ò","o"),("ù","u"),
            ("ñ","n"),("ü","u"),("ö","o"),("ä","a")]
    for a, b in subs:
        text = text.replace(a, b)
    return text


def _catalog_match(food_name: str) -> str | None:
    """
    Busca el mejor ítem del catálogo Bring! para el nombre de alimento dado.
    Estrategia en cascada: aliases manuales → exact → startswith → word-in-food → word-overlap.
    Devuelve la clave alemana interna de Bring!, o None si no hay match fiable.
    """
    norm = food_name.lower().strip()
    norm_no_acc = _remove_accents(norm)
    # 0. Manual aliases (highest priority)
    if norm in _MANUAL_ALIASES: return _MANUAL_ALIASES[norm]
    if norm_no_acc in _MANUAL_ALIASES: return _MANUAL_ALIASES[norm_no_acc]

    for cat in (_CAT_ES, _CAT_EN):
        # 1. Exact match (with and without accents)
        if norm in cat:
            return cat[norm]
        if norm_no_acc in cat:
            return cat[norm_no_acc]

        # 2. Parsed starts with catalog item: "tomates triturados" → "Tomates"
        candidates = [
            (len(k), v) for k, v in cat.items()
            if norm.startswith(k) and len(k) >= 3 and (
                len(norm) == len(k) or norm[len(k)] in (" ", ",", ";")
            )
        ]
        if candidates:
            return max(candidates)[1]  # más largo gana

        # 3. Catalog item aparece como palabra en el nombre parseado (mín 4 chars)
        candidates = [
            (len(k), v) for k, v in cat.items()
            if len(k) >= 3 and re.search(rf"\b{re.escape(k)}\b", norm)
        ]
        if candidates:
            return max(candidates)[1]  # más específico gana

    # 4. Word-overlap: qué ítem del catálogo comparte más tokens con food_name
    food_words = set(re.findall(r"\b\w{3,}\b", norm))
    best_score, best_name = 0, None
    for cat in (_CAT_ES, _CAT_EN):
        for k, v in cat.items():
            cat_words = set(re.findall(r"\b\w{3,}\b", k))
            if not cat_words:
                continue
            overlap = len(food_words & cat_words) / len(cat_words)
            if overlap >= 0.8 and len(k) >= 3 and overlap > best_score:
                best_score, best_name = overlap, v

    return best_name  # None si no encontró nada


# ── Auth cache (Bring!) ──────────────────────────────────────────────────────
_auth: dict[str, Any] = {}


def _login_headers() -> dict[str, str]:
    return {
        "X-BRING-API-KEY":     BRING_API_KEY,
        "X-BRING-CLIENT":      "webApp",
        "X-BRING-APPLICATION": "bring",
        "Content-Type":        "application/x-www-form-urlencoded",
    }


def _authed_headers() -> dict[str, str]:
    return {
        "X-BRING-API-KEY":     BRING_API_KEY,
        "X-BRING-CLIENT":      "webApp",
        "X-BRING-APPLICATION": "bring",
        "Content-Type":        "application/json",
        "Authorization":       f"Bearer {_auth['access_token']}",
        "X-BRING-USER-UUID":   _auth["uuid"],
    }


def _login() -> None:
    r = requests.post(
        "https://api.getbring.com/rest/v2/bringauth",
        headers=_login_headers(),
        data={"email": BRING_EMAIL, "password": BRING_PASSWORD},
        timeout=30,
    )
    r.raise_for_status()
    d = r.json()
    _auth["uuid"]         = d["uuid"]
    _auth["access_token"] = d["access_token"]
    _auth["expires_at"]   = time.time() + d.get("expires_in", 3600) - 60


def _ensure_auth() -> None:
    if not _auth or time.time() > _auth.get("expires_at", 0):
        _login()


def _req(method: str, path: str, **kwargs) -> requests.Response:
    _ensure_auth()
    r = requests.request(
        method, f"https://api.getbring.com/rest{path}",
        headers=_authed_headers(), timeout=30, **kwargs,
    )
    if r.status_code == 401:
        _login()
        r = requests.request(
            method, f"https://api.getbring.com/rest{path}",
            headers=_authed_headers(), timeout=30, **kwargs,
        )
    r.raise_for_status()
    return r


# ── Ingredient parsing ───────────────────────────────────────────────────────

def _normalize_text(text: str) -> str:
    """Normaliza abreviaturas comunes en español antes de pasar al NLP."""
    subs = [
        (r"\bcdtas?\b", "cucharadita"),
        (r"\bcdas\b",   "cucharadas"),
        (r"\bcda\b",    "cucharada"),
        (r"\bkg\b",     "kilogramo"),
        (r"\bml\b",     "mililitro"),
    ]
    for pattern, repl in subs:
        text = re.sub(pattern, repl, text, flags=re.IGNORECASE)
    return text


def _clean_food_name(name: str) -> str:
    """Elimina preposiciones, nouns de cantidad y palabras de preparación."""
    name = name.strip()
    name = re.sub(r"^de\s+", "", name, flags=re.IGNORECASE)
    name = re.sub(r"^d'", "", name, flags=re.IGNORECASE)
    # "dientes de ajo" → "ajo", "filetes de salmón" → "salmón"
    m = re.match(r"^(\w+)\s+de\s+(.+)$", name, re.IGNORECASE)
    if m and m.group(1).lower() in _QUANTITY_NOUNS:
        name = m.group(2).strip()
    changed = True
    while changed:
        changed = False
        for prep in _PREP_WORDS:
            new = re.sub(rf"\s+{re.escape(prep)}$", "", name, flags=re.IGNORECASE).strip()
            if new != name:
                name = new
                changed = True
    # "harissa o cayena" / "thyme or rosemary" → try first recognized option
    if re.search(r"\b(o|or)\b", name, re.IGNORECASE):
        parts = re.split(r"\s+(?:o|or)\s+", name, flags=re.IGNORECASE)
        name = parts[0].strip()  # use first option; catalog_match will try both if needed

    return name.capitalize() if name else name


def _parse_ingredient(text: str) -> tuple[str, str]:
    """
    Parsea texto libre de ingrediente.
    1. Llama al NLP de Mealie para extraer food/unit/quantity.
    2. Busca el mejor match en el catálogo Bring! (iconos + clasificación).
    3. Devuelve (item_id, spec) donde item_id es la clave alemana de Bring!.
    """
    # Si el texto tiene comas separando ingredientes distintos, usar solo el primero
    # Ej: "1 cdta de comino, 1 cdta de pimentón" → "1 cdta de comino"
    text = text.split(",")[0].strip() if re.search(r",\s*\d", text) else text
    text_norm = _normalize_text(text)
    food_name, unit, qty = "", "", 0.0

    try:
        r = requests.post(
            f"{MEALIE_BASE}/api/parser/ingredient",
            headers={"Authorization": f"Bearer {MEALIE_TOKEN}", "Content-Type": "application/json"},
            json={"ingredient": text_norm},
            timeout=5,
        )
        if r.ok:
            ing = r.json().get("ingredient", {})
            food_name = _clean_food_name((ing.get("food") or {}).get("name", ""))
            unit      = (ing.get("unit") or {}).get("name", "")
            qty       = ing.get("quantity") or 0.0
    except Exception:
        pass

    if not food_name:
        food_name = text.split("(")[0].strip()

    # Intentar match con catálogo Bring!
    catalog_name = _catalog_match(food_name)
    item_id = catalog_name if catalog_name else food_name

    # Construir spec: cantidad + unidad
    qty_str = str(int(qty)) if qty and qty == int(qty) else (str(round(qty, 3)) if qty else "")
    spec = " ".join(filter(None, [qty_str, unit])).strip() or text

    return item_id, spec


# ── MCP Server ───────────────────────────────────────────────────────────────
mcp = FastMCP(
    "bring_local",
    host="127.0.0.1",
    port=9154,
    streamable_http_path="/mcp",
    stateless_http=True,
)


@mcp.tool()
def bring_get_lists() -> dict[str, Any]:
    """Devuelve todas las listas de compra de Bring! del usuario con sus UUIDs."""
    try:
        _ensure_auth()
        r = _req("GET", f"/bringusers/{_auth['uuid']}/lists")
        lists = [
            {"uuid": l.get("listUuid"), "name": l.get("name"), "theme": l.get("theme")}
            for l in r.json().get("lists", [])
        ]
        return {"ok": True, "total": len(lists), "lists": lists}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@mcp.tool()
def bring_sync_list(list_name: str, items: list[str]) -> dict[str, Any]:
    """
    Vacía una lista de Bring! y añade los ingredientes de la lista de compra semanal.
    Usa el catálogo oficial de Bring! para que los ítems aparezcan con iconos
    y clasificación automática por categorías.

    list_name: nombre de la lista en Bring! (ej: 'Compra'). Usa la primera si no hay match.
    items: lista de strings con cada ingrediente en texto libre.
    """
    try:
        _ensure_auth()

        # 1. Buscar lista por nombre
        r = _req("GET", f"/bringusers/{_auth['uuid']}/lists")
        all_lists = r.json().get("lists", [])
        if not all_lists:
            return {"ok": False, "error": "No hay listas en tu cuenta de Bring!"}

        match  = next((l for l in all_lists if l.get("name","").lower() == list_name.lower()), None)
        target = match or all_lists[0]
        list_uuid = target["listUuid"]
        used_name = target.get("name", list_uuid)

        # 2. Vaciar lista actual
        current  = _req("GET", f"/v2/bringlists/{list_uuid}").json()
        purchase = current.get("purchase", [])
        if purchase:
            changes = [
                {"itemId": i.get("itemId") or i.get("name",""), "spec":"", "operation":"TO_RECENTLY"}
                for i in purchase if i.get("itemId") or i.get("name")
            ]
            if changes:
                _req("PUT", f"/v2/bringlists/{list_uuid}/items",
                     json={"changes": changes, "sender": "Sabor"})

        # 3. Parsear + catalog match + añadir (deduplicado)
        seen, changes, parsed_log = set(), [], []
        for raw in items:
            item_id, spec = _parse_ingredient(raw)
            key = item_id.lower()
            if key in seen:
                continue
            seen.add(key)
            changes.append({"itemId": item_id, "spec": spec, "operation": "TO_PURCHASE",
                              "accuracy": "0.0", "altitude": "0.0", "latitude": "0.0", "longitude": "0.0"})
            parsed_log.append({"raw": raw, "itemId": item_id, "spec": spec})

        if changes:
            _req("PUT", f"/v2/bringlists/{list_uuid}/items",
                 json={"changes": changes, "sender": "Sabor"})

        return {
            "ok":            True,
            "list_name":     used_name,
            "items_added":   len(changes),
            "items_cleared": len(purchase),
            "parsed":        parsed_log,
        }
    except Exception as e:
        return {"ok": False, "error": str(e)}


@mcp.tool()
def bring_add_items(list_uuid: str, items: list[str]) -> dict[str, Any]:
    """
    Añade ítems a una lista de Bring! sin borrar el contenido actual.
    Usa el catálogo de Bring! para matching con iconos.
    list_uuid: UUID de la lista (de bring_get_lists).
    items: lista de strings con cada ingrediente en texto libre.
    """
    try:
        changes = []
        for raw in items:
            item_id, spec = _parse_ingredient(raw)
            changes.append({"itemId": item_id, "spec": spec, "operation": "TO_PURCHASE",
                              "accuracy": "0.0", "altitude": "0.0", "latitude": "0.0", "longitude": "0.0"})
        _req("PUT", f"/v2/bringlists/{list_uuid}/items",
             json={"changes": changes, "sender": "Sabor"})
        return {"ok": True, "list_uuid": list_uuid, "items_added": len(items)}
    except Exception as e:
        return {"ok": False, "error": str(e)}


if __name__ == "__main__":
    mcp.run(transport="streamable-http")

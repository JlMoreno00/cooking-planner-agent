#!/usr/bin/env python3
"""
Memory MCP Server — Persistencia fiable en MEMORY.md.

Razón de existir: el runtime de OpenClaw responde conversacionalmente
pero no siempre ejecuta el tool `write` de forma fiable. Este servidor
MCP ejecuta directamente las escrituras en el proceso Python del servidor,
garantizando persistencia real en el filesystem.
"""
import os
import re
from datetime import date
from pathlib import Path
from typing import Any

from mcp.server.fastmcp import FastMCP

MEMORY_FILE = Path(os.getenv("MEMORY_FILE", "/root/Cooking Planner Agent/MEMORY.md"))
HOST = os.getenv("MEMORY_MCP_HOST", "127.0.0.1")
PORT = int(os.getenv("MEMORY_MCP_PORT", "9153"))

mcp = FastMCP("memory", host=HOST, port=PORT, streamable_http_path="/mcp", stateless_http=True)


# ─────────────────────────────────────────────────────────
# Utilidades de lectura/escritura de MEMORY.md
# ─────────────────────────────────────────────────────────

def _read_memory() -> str:
    if MEMORY_FILE.exists():
        return MEMORY_FILE.read_text(encoding="utf-8")
    return ""


def _write_memory(content: str) -> None:
    MEMORY_FILE.parent.mkdir(parents=True, exist_ok=True)
    MEMORY_FILE.write_text(content, encoding="utf-8")


def _ensure_section(content: str, header: str, default_body: str = "") -> str:
    """Asegura que una sección exista en el contenido. Si no, la añade al final."""
    if re.search(rf"^{re.escape(header)}", content, re.MULTILINE):
        return content
    return content.rstrip("\n") + f"\n\n{header}\n{default_body}"


def _get_section_content(content: str, header: str) -> str:
    """Extrae el contenido de una sección (entre header y el siguiente ## o fin de archivo)."""
    pattern = rf"(?:^|\n){re.escape(header)}\n(.*?)(?=\n## |\Z)"
    m = re.search(pattern, content, re.DOTALL)
    if m:
        return m.group(1).strip()
    return ""


def _replace_section(content: str, header: str, new_body: str) -> str:
    """Reemplaza el cuerpo de una sección existente."""
    pattern = rf"({re.escape(header)}\n)(.*?)(?=\n## |\Z)"
    replacement = rf"\g<1>{new_body}\n"
    result, count = re.subn(pattern, replacement, content, flags=re.DOTALL)
    if count == 0:
        result = content.rstrip("\n") + f"\n\n{header}\n{new_body}\n"
    return result


def _rating_to_stars(rating: int) -> str:
    rating = max(1, min(5, int(rating)))
    return "★" * rating + "☆" * (5 - rating)


# ─────────────────────────────────────────────────────────
# Herramientas MCP
# ─────────────────────────────────────────────────────────

@mcp.tool()
def save_feedback(
    recipe_name: str,
    rating: int | None = None,
    comment: str | None = None,
    tags: list[str] | None = None,
) -> dict[str, Any]:
    """
    Persiste feedback de una receta en MEMORY.md de forma garantizada.

    Actualiza tres secciones:
    - Feedback Historial: añade entrada cronológica
    - Top Recetas Favoritas: actualiza si rating >= 4 o tag #favorita
    - Blacklist Recetas: añade si tag #nunca-mas

    Parámetros:
    - recipe_name: nombre de la receta (requerido)
    - rating: entero 1-5 (opcional)
    - comment: texto libre (opcional)
    - tags: lista de strings ej. ["#repetir-pronto", "#favorita"] (opcional)
    """
    if not recipe_name:
        return {"ok": False, "error": "recipe_name is required"}

    tags = tags or []
    today = date.today().isoformat()
    stars = _rating_to_stars(rating) if rating else "sin-rating"
    comment_str = comment.strip() if comment else "[sin-comentario]"
    tags_str = " ".join(t if t.startswith("#") else f"#{t}" for t in tags)

    content = _read_memory()
    if not content:
        content = _MEMORY_TEMPLATE

    # ── 1. Añadir al Historial ──────────────────────────────────
    content = _ensure_section(content, "## Feedback Historial")
    new_entry = f"- {today} | {recipe_name} | {stars} | {comment_str}"
    if tags_str:
        new_entry += f" | {tags_str}"
    # Insertar ANTES del primer bloque de "Política" si existe, si no al final de la sección
    hist_content = _get_section_content(content, "## Feedback Historial")
    lines = [l for l in hist_content.split("\n") if l.startswith("- ")]
    policy_lines = [l for l in hist_content.split("\n") if l.startswith("**Política")]
    lines.append(new_entry)
    new_hist = "\n".join(lines)
    if policy_lines:
        new_hist += "\n\n" + "\n".join(policy_lines)
    content = _replace_section(content, "## Feedback Historial", new_hist)

    # ── 2. Blacklist ────────────────────────────────────────────
    if "#nunca-mas" in tags or "nunca-mas" in tags:
        content = _ensure_section(content, "## Blacklist Recetas")
        bl_content = _get_section_content(content, "## Blacklist Recetas")
        bl_lines = [l for l in bl_content.split("\n") if l.strip()]
        already_in = any(recipe_name.lower() in l.lower() for l in bl_lines)
        if not already_in:
            bl_lines.append(f"- {recipe_name} | motivo: nunca-mas | desde: {today}")
        content = _replace_section(content, "## Blacklist Recetas", "\n".join(bl_lines))

    # ── 3. Top Favoritas ────────────────────────────────────────
    is_fav = rating and rating >= 4
    if is_fav or "#favorita" in tags or "favorita" in tags:
        content = _ensure_section(content, "## Top Recetas Favoritas")
        fav_content = _get_section_content(content, "## Top Recetas Favoritas")
        # Ignorar líneas de encabezado
        fav_lines = [
            l for l in fav_content.split("\n")
            if l.strip() and not l.startswith("**") and not l.startswith("(")
        ]
        # Buscar si ya existe la receta
        idx = next((i for i, l in enumerate(fav_lines) if recipe_name.lower() in l.lower()), None)
        entry_line = f"- {recipe_name} | rating: {rating or '?'}/5 | ult: {today}"
        if idx is not None:
            fav_lines[idx] = entry_line
        else:
            fav_lines.append(entry_line)
        # Mantener máximo 10
        fav_lines = fav_lines[-10:]
        content = _replace_section(content, "## Top Recetas Favoritas", "\n".join(fav_lines))

    _write_memory(content)

    # Verificar persistencia
    verify = _read_memory()
    persisted = recipe_name in verify and new_entry in verify

    return {
        "ok": True,
        "persisted": persisted,
        "date": today,
        "recipe": recipe_name,
        "rating": stars,
        "comment": comment_str,
        "tags": tags_str,
        "added_to_blacklist": "#nunca-mas" in tags or "nunca-mas" in tags,
        "added_to_favorites": bool(is_fav or "#favorita" in tags or "favorita" in tags),
    }


@mcp.tool()
def read_memory(section: str | None = None) -> dict[str, Any]:
    """
    Lee MEMORY.md completo o una sección específica.
    section: nombre de sección sin '##', ej: 'Feedback Historial', 'Top Recetas Favoritas'
    """
    content = _read_memory()
    if not content:
        return {"ok": False, "error": "MEMORY.md no existe o está vacío"}

    if section:
        header = f"## {section}"
        body = _get_section_content(content, header)
        if not body and section not in content:
            return {"ok": False, "error": f"Sección '{section}' no encontrada"}
        return {"ok": True, "section": section, "content": body}

    return {"ok": True, "content": content}


@mcp.tool()
def update_pantry(items: list[str]) -> dict[str, Any]:
    """
    Actualiza la sección 'Despensa Conversacional' con los ingredientes disponibles.
    items: lista de strings con los ingredientes que hay en casa.
    """
    if not items:
        return {"ok": False, "error": "items list is empty"}

    content = _read_memory()
    if not content:
        content = _MEMORY_TEMPLATE

    today = date.today().isoformat()
    new_body = f"(Actualizado: {today})\n" + "\n".join(f"- {it}" for it in items)
    content = _ensure_section(content, "## Despensa Conversacional")
    content = _replace_section(content, "## Despensa Conversacional", new_body)
    _write_memory(content)

    verify = _read_memory()
    persisted = items[0] in verify

    return {"ok": True, "persisted": persisted, "items_saved": len(items), "updated": today}


@mcp.tool()
def update_learned_preference(preference: str) -> dict[str, Any]:
    """
    Añade una preferencia aprendida a la sección 'Preferencias Aprendidas'.
    preference: texto de la preferencia, ej: 'Le gustan platos asiáticos picantes (3 feedbacks positivos)'
    """
    if not preference:
        return {"ok": False, "error": "preference text is required"}

    content = _read_memory()
    if not content:
        content = _MEMORY_TEMPLATE

    content = _ensure_section(content, "## Preferencias Aprendidas")
    pref_content = _get_section_content(content, "## Preferencias Aprendidas")
    lines = [l for l in pref_content.split("\n") if l.strip() and not l.startswith("(")]
    # Evitar duplicados similares
    pref_lower = preference.lower()[:40]
    already = any(pref_lower in l.lower() for l in lines)
    if not already:
        today = date.today().isoformat()
        lines.append(f"- {preference} (desde {today})")
    content = _replace_section(content, "## Preferencias Aprendidas", "\n".join(lines))
    _write_memory(content)

    return {"ok": True, "added": not already, "preference": preference}


_MEMORY_TEMPLATE = """# Memoria del Agente de Cocina

## Feedback Historial

## Top Recetas Favoritas

## Blacklist Recetas

## Preferencias Aprendidas

## Despensa Conversacional
"""


if __name__ == "__main__":
    mcp.run(transport="streamable-http")

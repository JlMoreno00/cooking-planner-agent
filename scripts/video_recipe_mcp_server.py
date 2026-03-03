#!/usr/bin/env python3
"""Video Recipe MCP Server.

Ingests YouTube/TikTok URLs, extracts transcript + visual cues, splits multi-recipe
videos, and can save each recipe separately into Mealie.
"""

import json
import importlib
import os
import re
import subprocess
import tempfile
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import requests
from mcp.server.fastmcp import FastMCP


HOST = os.getenv("VIDEO_RECIPE_MCP_HOST", "127.0.0.1")
PORT = int(os.getenv("VIDEO_RECIPE_MCP_PORT", "9155"))
WORKDIR = Path(os.getenv("VIDEO_RECIPE_WORKDIR", "/tmp/video-recipe-mcp"))
MAX_KEYFRAMES = int(os.getenv("VIDEO_RECIPE_MAX_KEYFRAMES", "12"))

MEALIE_BASE_URL = os.getenv("MEALIE_BASE_URL", "http://localhost:9925").rstrip("/")
MEALIE_API_TOKEN = os.getenv("MEALIE_API_TOKEN", "")

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_MODEL = os.getenv("VIDEO_RECIPE_LLM_MODEL", "gpt-4o-mini")

mcp = FastMCP(
    "video-recipe",
    host=HOST,
    port=PORT,
    streamable_http_path="/mcp",
    stateless_http=True,
)


def _headers() -> dict[str, str]:
    if not MEALIE_API_TOKEN:
        return {}
    return {"Authorization": f"Bearer {MEALIE_API_TOKEN}", "Content-Type": "application/json"}


def _check_mealie_token() -> dict[str, Any] | None:
    if not MEALIE_API_TOKEN:
        return {"ok": False, "error": "missing_MEALIE_API_TOKEN"}
    return None


def _sanitize_filename(value: str) -> str:
    return re.sub(r"[^a-zA-Z0-9_.-]+", "-", value).strip("-")


def _platform_from_url(url: str) -> str:
    host = (urlparse(url).netloc or "").lower()
    if "youtube.com" in host or "youtu.be" in host:
        return "youtube"
    if "tiktok.com" in host:
        return "tiktok"
    return "video"


def _run_cmd(command: list[str]) -> tuple[int, str, str]:
    proc = subprocess.run(command, capture_output=True, text=True)
    return proc.returncode, proc.stdout, proc.stderr


def _is_ffmpeg_available() -> bool:
    code, _, _ = _run_cmd(["ffmpeg", "-version"])
    return code == 0


def _seconds_from_timestamp(value: str) -> float:
    raw = value.replace(",", ".").strip()
    parts = raw.split(":")
    if len(parts) == 3:
        h, m, s = parts
        return float(h) * 3600 + float(m) * 60 + float(s)
    if len(parts) == 2:
        m, s = parts
        return float(m) * 60 + float(s)
    return float(raw)


def _parse_vtt(vtt_path: Path) -> list[dict[str, Any]]:
    chunks: list[dict[str, Any]] = []
    text_lines: list[str] = []
    start = 0.0
    end = 0.0
    ts_re = re.compile(r"^(\d{1,2}:\d{2}(?::\d{2})?[\.,]\d{3})\s+-->\s+(\d{1,2}:\d{2}(?::\d{2})?[\.,]\d{3})")

    def flush() -> None:
        nonlocal text_lines, start, end
        if not text_lines:
            return
        text = " ".join(line.strip() for line in text_lines)
        text = re.sub(r"<[^>]+>", "", text)
        text = re.sub(r"\s+", " ", text).strip()
        if text:
            if chunks and chunks[-1]["text"] == text and abs(chunks[-1]["end"] - start) < 1.0:
                chunks[-1]["end"] = end
            else:
                chunks.append({"start": start, "end": end, "text": text})
        text_lines = []

    for line in vtt_path.read_text(errors="replace").splitlines():
        line = line.strip("\ufeff")
        m = ts_re.match(line.strip())
        if m:
            flush()
            start = _seconds_from_timestamp(m.group(1))
            end = _seconds_from_timestamp(m.group(2))
            continue
        if not line.strip():
            flush()
            continue
        if line.startswith("WEBVTT") or line.isdigit():
            continue
        text_lines.append(line)
    flush()
    return chunks


def _download_video_assets(url: str, language: str, workdir: Path) -> dict[str, Any]:
    try:
        yt_dlp_mod = importlib.import_module("yt_dlp")
    except Exception as e:
        return {
            "ok": False,
            "error": "missing_dependency_yt_dlp",
            "detail": str(e),
            "hint": "Install with: pip install yt-dlp",
        }

    workdir.mkdir(parents=True, exist_ok=True)
    ydl_opts: dict[str, Any] = {
        "format": "bestvideo+bestaudio/best",
        "outtmpl": str(workdir / "%(id)s.%(ext)s"),
        "quiet": True,
        "no_warnings": True,
        "noplaylist": True,
        "writesubtitles": True,
        "writeautomaticsub": True,
        "subtitleslangs": [language, "es", "en"],
        "subtitlesformat": "vtt",
    }

    try:
        with yt_dlp_mod.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
    except Exception as e:
        retry_opts = dict(ydl_opts)
        retry_opts["writesubtitles"] = False
        retry_opts["writeautomaticsub"] = False
        try:
            with yt_dlp_mod.YoutubeDL(retry_opts) as ydl:
                info = ydl.extract_info(url, download=True)
        except Exception:
            return {"ok": False, "error": "video_download_failed", "detail": str(e)}

    if not isinstance(info, dict):
        return {"ok": False, "error": "video_metadata_missing"}

    video_id = str(info.get("id") or _sanitize_filename(url))
    video_title = str(info.get("title") or f"Video {video_id}")
    duration = int(info.get("duration") or 0)
    thumbnail = info.get("thumbnail")

    candidates = list(workdir.glob(f"{video_id}.*"))
    media_ext_block = {".vtt", ".json", ".description", ".jpg", ".jpeg", ".png", ".webp"}
    media_files = [p for p in candidates if p.suffix.lower() not in media_ext_block]
    video_path = str(media_files[0]) if media_files else ""

    subtitle_files = sorted(workdir.glob(f"{video_id}*.vtt"))
    chunks: list[dict[str, Any]] = []
    subtitle_source = "none"
    if subtitle_files:
        for sf in subtitle_files:
            parsed = _parse_vtt(sf)
            if parsed:
                chunks = parsed
                subtitle_source = sf.name
                break

    return {
        "ok": True,
        "video_id": video_id,
        "title": video_title,
        "duration": duration,
        "uploader": info.get("uploader") or "",
        "webpage_url": info.get("webpage_url") or url,
        "thumbnail": thumbnail,
        "video_path": video_path,
        "subtitle_source": subtitle_source,
        "transcript_chunks": chunks,
        "workdir": str(workdir),
    }


def _transcribe_with_faster_whisper(video_path: str, language: str) -> list[dict[str, Any]]:
    try:
        from faster_whisper import WhisperModel  # type: ignore
    except Exception:
        return []

    if not _is_ffmpeg_available() or not video_path:
        return []

    model_size = os.getenv("VIDEO_RECIPE_WHISPER_MODEL", "base")
    model = WhisperModel(model_size, device="cpu", compute_type="int8")
    segments, _ = model.transcribe(video_path, language=language if language in {"es", "en"} else None)
    out: list[dict[str, Any]] = []
    for seg in segments:
        text = (seg.text or "").strip()
        if text:
            out.append({"start": float(seg.start), "end": float(seg.end), "text": text})
    return out


def _extract_keyframes(video_path: str, out_dir: Path, max_frames: int) -> list[dict[str, Any]]:
    if not video_path or not _is_ffmpeg_available():
        return []
    out_dir.mkdir(parents=True, exist_ok=True)

    frame_pattern = str(out_dir / "frame_%03d.jpg")
    _run_cmd([
        "ffmpeg",
        "-y",
        "-i",
        video_path,
        "-vf",
        "select=gt(scene\\,0.35),scale=960:-1",
        "-vsync",
        "vfr",
        frame_pattern,
    ])

    frames = sorted(out_dir.glob("frame_*.jpg"))
    if not frames:
        _run_cmd([
            "ffmpeg",
            "-y",
            "-i",
            video_path,
            "-vf",
            "fps=1/20,scale=960:-1",
            frame_pattern,
        ])
        frames = sorted(out_dir.glob("frame_*.jpg"))

    if not frames:
        return []

    if len(frames) > max_frames:
        step = len(frames) / float(max_frames)
        selected = [frames[int(i * step)] for i in range(max_frames)]
    else:
        selected = frames

    out: list[dict[str, Any]] = []
    total = max(1, len(selected) - 1)
    for idx, frame in enumerate(selected):
        out.append({
            "index": idx,
            "position": round(idx / total, 4),
            "path": str(frame),
        })
    return out


def _group_transcript_into_segments(chunks: list[dict[str, Any]], max_recipes: int) -> list[dict[str, Any]]:
    if not chunks:
        return []

    starts_re = re.compile(
        r"\b(receta\s*(numero|n[o°])?\s*\d+|next recipe|siguiente receta|segunda receta|tercera receta|primera receta|for this recipe|ahora hacemos)\b",
        re.IGNORECASE,
    )

    segments: list[dict[str, Any]] = []
    current = {
        "start": float(chunks[0]["start"]),
        "end": float(chunks[0]["end"]),
        "chunks": [chunks[0]],
    }

    for chunk in chunks[1:]:
        text = str(chunk.get("text") or "")
        is_boundary = bool(starts_re.search(text))
        if is_boundary and len(current["chunks"]) >= 3:
            segments.append(current)
            current = {
                "start": float(chunk["start"]),
                "end": float(chunk["end"]),
                "chunks": [chunk],
            }
        else:
            current["chunks"].append(chunk)
            current["end"] = float(chunk["end"])
    segments.append(current)

    if len(segments) == 1 and max_recipes > 1:
        total_start = float(chunks[0]["start"])
        total_end = float(chunks[-1]["end"])
        total_duration = max(1.0, total_end - total_start)
        n = min(max_recipes, max(1, int(total_duration // 180)))
        if n > 1:
            window = total_duration / n
            split_segments: list[dict[str, Any]] = []
            for i in range(n):
                a = total_start + i * window
                b = total_start + (i + 1) * window
                c = [x for x in chunks if a <= float(x["start"]) < b]
                if c:
                    split_segments.append({"start": float(c[0]["start"]), "end": float(c[-1]["end"]), "chunks": c})
            if split_segments:
                segments = split_segments

    return segments[: max(1, max_recipes)]


def _extract_with_openai(segment_text: str, recipe_index: int, video_title: str) -> dict[str, Any] | None:
    if not OPENAI_API_KEY:
        return None
    prompt = (
        "Extract ONE recipe from this transcript segment. Return strict JSON with keys: "
        "name (string), ingredients (array of strings), steps (array of strings), servings (string), "
        "notes (string), confidence (number 0..1).\n"
        "Rules: do not invent missing details; if unknown leave empty string/list and lower confidence."
    )
    payload = {
        "model": OPENAI_MODEL,
        "temperature": 0.1,
        "response_format": {"type": "json_object"},
        "messages": [
            {"role": "system", "content": "You extract recipes from cooking video transcripts."},
            {
                "role": "user",
                "content": (
                    f"Video title: {video_title}\n"
                    f"Recipe index guess: {recipe_index}\n"
                    f"Transcript segment:\n{segment_text}\n\n{prompt}"
                ),
            },
        ],
    }
    try:
        r = requests.post(
            "https://api.openai.com/v1/chat/completions",
            headers={"Authorization": f"Bearer {OPENAI_API_KEY}", "Content-Type": "application/json"},
            json=payload,
            timeout=60,
        )
        if not (200 <= r.status_code < 300):
            return None
        data = r.json()
        content = data["choices"][0]["message"]["content"]
        obj = json.loads(content)
        return {
            "name": (obj.get("name") or "").strip(),
            "ingredients": [str(x).strip() for x in (obj.get("ingredients") or []) if str(x).strip()],
            "steps": [str(x).strip() for x in (obj.get("steps") or []) if str(x).strip()],
            "servings": str(obj.get("servings") or "").strip(),
            "notes": str(obj.get("notes") or "").strip(),
            "confidence": float(obj.get("confidence") or 0.0),
        }
    except Exception:
        return None


def _heuristic_extract(segment_text: str, recipe_index: int, video_title: str) -> dict[str, Any]:
    sentences = [s.strip() for s in re.split(r"[\n\.\!\?]+", segment_text) if s.strip()]
    name = ""

    name_markers = [
        r"(?:receta|dish|plato)\s*(?:de|:)?\s*([a-zA-Z0-9\s\-]{4,60})",
        r"hoy\s+hacemos\s+([a-zA-Z0-9\s\-]{4,60})",
        r"vamos\s+a\s+hacer\s+([a-zA-Z0-9\s\-]{4,60})",
    ]
    for sent in sentences[:8]:
        for pattern in name_markers:
            m = re.search(pattern, sent, re.IGNORECASE)
            if m:
                name = m.group(1).strip(" -:")
                break
        if name:
            break
    if not name:
        name = f"{video_title} - receta {recipe_index}"

    ingredient_lines: list[str] = []
    quantity_re = re.compile(
        r"\b\d+(?:[\.,]\d+)?\s*(?:g|kg|ml|l|oz|lb|cup|cups|tbsp|tsp|cucharada(?:s)?|cucharadita(?:s)?|unidad(?:es)?|huevo(?:s)?)\b",
        re.IGNORECASE,
    )
    for sent in sentences:
        s = sent.strip()
        if len(s) > 120:
            continue
        if quantity_re.search(s) or re.search(r"\b(ingredientes?|ingredients?)\b", s, re.IGNORECASE):
            ingredient_lines.append(s)

    seen: set[str] = set()
    ingredients: list[str] = []
    for item in ingredient_lines:
        key = item.lower()
        if key in seen:
            continue
        seen.add(key)
        ingredients.append(item)

    step_markers = re.compile(r"\b(paso|step|mezcla|mix|añade|add|cocina|cook|hornea|bake|sirve|serve|frie|fry)\b", re.IGNORECASE)
    steps = [s for s in sentences if step_markers.search(s)]
    if not steps:
        steps = sentences[:8]

    confidence = 0.35
    if len(ingredients) >= 3:
        confidence += 0.25
    if len(steps) >= 3:
        confidence += 0.25
    if len(segment_text) > 500:
        confidence += 0.15

    return {
        "name": name[:120],
        "ingredients": ingredients[:30],
        "steps": steps[:25],
        "servings": "",
        "notes": "",
        "confidence": round(min(1.0, confidence), 3),
    }


def _extract_recipe_from_segment(segment: dict[str, Any], index: int, video_title: str) -> dict[str, Any]:
    text = " ".join(str(ch.get("text") or "") for ch in (segment.get("chunks") or []))
    text = re.sub(r"\s+", " ", text).strip()

    llm = _extract_with_openai(text, index, video_title)
    extracted = llm if llm else _heuristic_extract(text, index, video_title)

    return {
        "index": index,
        "start": float(segment.get("start") or 0.0),
        "end": float(segment.get("end") or 0.0),
        "source_text_chars": len(text),
        **extracted,
    }


def _find_existing_recipe_slug_by_name(name: str) -> str | None:
    if not MEALIE_API_TOKEN:
        return None
    try:
        r = requests.get(
            f"{MEALIE_BASE_URL}/api/recipes",
            headers=_headers(),
            params={"search": name, "perPage": 100, "page": 1},
            timeout=30,
        )
        if not (200 <= r.status_code < 300):
            return None
        items = r.json().get("items") or []
        low = name.lower().strip()
        for it in items:
            nm = str(it.get("name") or "").lower().strip()
            if nm == low:
                return it.get("slug")
        return None
    except Exception:
        return None


def _get_or_create_tag(name: str) -> dict[str, Any]:
    r = requests.get(f"{MEALIE_BASE_URL}/api/organizers/tags", headers=_headers(), timeout=30)
    if 200 <= r.status_code < 300:
        for item in (r.json().get("items") or []):
            if str(item.get("name") or "").lower() == name.lower():
                return {"ok": True, "id": item.get("id"), "name": item.get("name")}

    r2 = requests.post(
        f"{MEALIE_BASE_URL}/api/organizers/tags",
        headers=_headers(),
        json={"name": name},
        timeout=30,
    )
    if not (200 <= r2.status_code < 300):
        return {"ok": False, "status": r2.status_code, "body": r2.text[:500]}
    data = r2.json()
    return {"ok": True, "id": data.get("id"), "name": data.get("name")}


def _tag_recipe(slug: str, tags: list[str]) -> dict[str, Any]:
    rr = requests.get(f"{MEALIE_BASE_URL}/api/recipes/{slug}", headers=_headers(), timeout=30)
    if not (200 <= rr.status_code < 300):
        return {"ok": False, "status": rr.status_code}

    recipe_data = rr.json()
    existing = {t["id"]: t for t in (recipe_data.get("tags") or []) if t.get("id")}
    for tg in tags:
        tr = _get_or_create_tag(tg)
        if tr.get("ok") and tr.get("id"):
            existing[tr["id"]] = {"id": tr["id"], "name": tr.get("name") or tg}

    rp = requests.patch(
        f"{MEALIE_BASE_URL}/api/recipes/{slug}",
        headers=_headers(),
        json={"tags": list(existing.values())},
        timeout=30,
    )
    return {"ok": 200 <= rp.status_code < 300, "status": rp.status_code}


def _create_recipe_in_mealie(recipe: dict[str, Any], source: dict[str, Any]) -> dict[str, Any]:
    name = recipe.get("name") or "Video recipe"
    ingredients = recipe.get("ingredients") or ["Ingredient from video transcript"]
    steps = recipe.get("steps") or ["Review transcript segment manually"]

    jsonld_recipe: dict[str, Any] = {
        "@context": "https://schema.org",
        "@type": "Recipe",
        "name": name,
        "description": (
            f"Imported from video URL: {source.get('webpage_url')}\n"
            f"Segment: {round(float(recipe.get('start') or 0.0), 1)}s - {round(float(recipe.get('end') or 0.0), 1)}s\n"
            f"Confidence: {recipe.get('confidence')}"
        ),
        "recipeIngredient": ingredients,
        "recipeInstructions": steps,
        "recipeYield": recipe.get("servings") or "",
        "url": source.get("webpage_url"),
    }
    if source.get("thumbnail"):
        jsonld_recipe["image"] = [source["thumbnail"]]

    payload = {"data": json.dumps(jsonld_recipe, ensure_ascii=False)}
    r = requests.post(
        f"{MEALIE_BASE_URL}/api/recipes/create/html-or-json",
        headers=_headers(),
        json=payload,
        timeout=60,
    )
    if not (200 <= r.status_code < 300):
        return {"ok": False, "status": r.status_code, "body": r.text[:1200]}

    slug = _find_existing_recipe_slug_by_name(name)
    return {"ok": True, "status": r.status_code, "slug": slug, "body": r.text[:300]}


def _build_artifact(url: str, language: str, max_recipes: int, include_visual_context: bool) -> dict[str, Any]:
    WORKDIR.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=str(WORKDIR)) as tmp:
        wd = Path(tmp)
        downloaded = _download_video_assets(url, language, wd)
        if not downloaded.get("ok"):
            return downloaded

        chunks = downloaded.get("transcript_chunks") or []
        transcript_source = "captions"
        if not chunks:
            chunks = _transcribe_with_faster_whisper(str(downloaded.get("video_path") or ""), language)
            transcript_source = "faster-whisper" if chunks else "none"

        if not chunks:
            return {
                "ok": False,
                "error": "no_transcript_available",
                "detail": "Could not extract captions or transcribe audio",
            }

        segments = _group_transcript_into_segments(chunks, max_recipes=max_recipes)
        recipes = [_extract_recipe_from_segment(seg, i + 1, str(downloaded.get("title") or "Video")) for i, seg in enumerate(segments)]

        keyframes: list[dict[str, Any]] = []
        if include_visual_context:
            keyframes = _extract_keyframes(str(downloaded.get("video_path") or ""), wd / "frames", MAX_KEYFRAMES)

        for recipe in recipes:
            if not keyframes:
                recipe["visual_ref"] = None
                continue
            start = float(recipe.get("start") or 0.0)
            end = float(recipe.get("end") or 0.0)
            mid = (start + end) / 2.0
            total_duration = max(float(downloaded.get("duration") or end or 1.0), 1.0)
            target_pos = max(0.0, min(1.0, mid / total_duration))
            best = min(keyframes, key=lambda k: abs(float(k.get("position") or 0.0) - target_pos))
            recipe["visual_ref"] = {"position": best.get("position"), "path": best.get("path")}

        return {
            "ok": True,
            "source": {
                "url": url,
                "platform": _platform_from_url(url),
                "video_id": downloaded.get("video_id"),
                "title": downloaded.get("title"),
                "duration": downloaded.get("duration"),
                "uploader": downloaded.get("uploader"),
                "thumbnail": downloaded.get("thumbnail"),
                "webpage_url": downloaded.get("webpage_url"),
                "transcript_source": transcript_source,
                "subtitle_source": downloaded.get("subtitle_source"),
            },
            "stats": {
                "chunks": len(chunks),
                "segments": len(segments),
                "recipes_detected": len(recipes),
                "keyframes": len(keyframes),
            },
            "recipes": recipes,
        }


@mcp.tool()
def analyze_video_recipes(
    url: str,
    language: str = "es",
    max_recipes: int = 8,
    include_visual_context: bool = True,
) -> dict[str, Any]:
    if max_recipes < 1:
        return {"ok": False, "error": "max_recipes_must_be_positive"}
    return _build_artifact(url, language=language, max_recipes=max_recipes, include_visual_context=include_visual_context)


@mcp.tool()
def import_video_recipes_to_mealie(
    url: str,
    language: str = "es",
    max_recipes: int = 8,
    min_confidence: float = 0.55,
    include_visual_context: bool = True,
    dry_run: bool = False,
) -> dict[str, Any]:
    if err := _check_mealie_token():
        return err

    artifact = _build_artifact(url, language=language, max_recipes=max_recipes, include_visual_context=include_visual_context)
    if not artifact.get("ok"):
        return artifact

    source = artifact["source"]
    recipes = artifact.get("recipes") or []
    platform = str(source.get("platform") or "video")
    video_id = str(source.get("video_id") or "unknown")

    created: list[dict[str, Any]] = []
    skipped: list[dict[str, Any]] = []

    for recipe in recipes:
        confidence = float(recipe.get("confidence") or 0.0)
        if confidence < min_confidence:
            skipped.append(
                {
                    "reason": "low_confidence",
                    "name": recipe.get("name"),
                    "confidence": confidence,
                }
            )
            continue

        name = str(recipe.get("name") or "").strip()
        if not name:
            skipped.append({"reason": "missing_name", "recipe": recipe})
            continue

        existing_slug = _find_existing_recipe_slug_by_name(name)
        if existing_slug:
            skipped.append({"reason": "duplicate_name", "name": name, "slug": existing_slug})
            continue

        if dry_run:
            created.append({"ok": True, "name": name, "status": "dry_run"})
            continue

        create_result = _create_recipe_in_mealie(recipe, source)
        if not create_result.get("ok"):
            skipped.append({"reason": "create_failed", "name": name, "detail": create_result})
            continue

        slug = create_result.get("slug")
        if slug:
            tags = [
                "video-import",
                platform,
                "multi-recipe-video" if len(recipes) > 1 else "single-recipe-video",
                f"video:{video_id}",
            ]
            _tag_recipe(str(slug), tags)

        created.append(
            {
                "ok": True,
                "name": name,
                "slug": slug,
                "confidence": confidence,
                "segment": {"start": recipe.get("start"), "end": recipe.get("end")},
            }
        )

    return {
        "ok": True,
        "source": source,
        "stats": {
            "detected": len(recipes),
            "created": len(created),
            "skipped": len(skipped),
            "min_confidence": min_confidence,
            "dry_run": dry_run,
        },
        "created": created,
        "skipped": skipped,
        "recipes": recipes,
    }


if __name__ == "__main__":
    mcp.run(transport="streamable-http")

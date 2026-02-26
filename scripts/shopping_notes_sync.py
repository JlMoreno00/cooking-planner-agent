#!/usr/bin/env python3
import argparse
import datetime as dt
import os
import re
import subprocess
from pathlib import Path


def parse_items(raw: str):
    items = [x.strip() for x in raw.split(",") if x.strip()]
    return items


def categorize(item: str) -> str:
    x = item.lower()
    if any(k in x for k in ["tomate", "cebolla", "pimiento", "lechuga", "zanahoria", "patata"]):
        return "Frutas y Verduras"
    if any(k in x for k in ["pollo", "ternera", "pescado", "atún", "huevo"]):
        return "Carnes y Pescados"
    if any(k in x for k in ["arroz", "pasta", "pan", "avena"]):
        return "Cereales y Pastas"
    return "Otros"


def render_note(items: list[str], title: str) -> str:
    groups: dict[str, list[str]] = {}
    for i in items:
        groups.setdefault(categorize(i), []).append(i)

    lines = [f"🛒 {title}", ""]
    for cat in ["Frutas y Verduras", "Carnes y Pescados", "Cereales y Pastas", "Otros"]:
        vals = groups.get(cat, [])
        if not vals:
            continue
        lines.append(f"{cat}:")
        for v in vals:
            lines.append(f"□ {v}")
        lines.append("")
    return "\n".join(lines).strip() + "\n"


def send_telegram(message: str, target: str) -> tuple[bool, str]:
    cmd = [
        "openclaw",
        "message",
        "send",
        "--channel",
        "telegram",
        "--target",
        target,
        "--message",
        message,
        "--json",
    ]
    p = subprocess.run(cmd, capture_output=True, text=True)
    ok = p.returncode == 0
    out = (p.stdout + "\n" + p.stderr).strip()
    return ok, out[:4000]


def main() -> int:
    parser = argparse.ArgumentParser(description="Task 9 notes sync fallback: create shopping note and optional Telegram send")
    parser.add_argument("--items", required=True, help="Comma-separated items, e.g. tomates (1kg), cebolla (2)")
    parser.add_argument("--title", default=f"Lista de Compra {dt.date.today().isoformat()}")
    parser.add_argument("--output", default=".sisyphus/evidence/task-9-shopping-note.txt")
    parser.add_argument("--telegram-target", default=os.getenv("TELEGRAM_TARGET", ""))
    args = parser.parse_args()

    items = parse_items(args.items)
    note = render_note(items, args.title)

    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(note, encoding="utf-8")

    print(f"note_saved={out_path}")
    print(f"items_count={len(items)}")

    if args.telegram_target:
        ok, detail = send_telegram(note, args.telegram_target)
        print(f"telegram_sent={ok}")
        detail_path = out_path.with_suffix(out_path.suffix + ".telegram.log")
        detail_path.write_text(detail, encoding="utf-8")
        print(f"telegram_log={detail_path}")
    else:
        print("telegram_sent=blocked_missing_TELEGRAM_TARGET")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

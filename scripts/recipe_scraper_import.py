#!/usr/bin/env python3
import argparse
import json
import os
from typing import Any

import requests
from recipe_scrapers import scrape_me


def normalize(data: dict[str, Any]) -> dict[str, Any]:
    return {
        "title": data.get("title") or "",
        "total_time": data.get("total_time") or 0,
        "yields": data.get("yields") or "",
        "image": data.get("image") or "",
        "host": data.get("host") or "",
        "ingredients": data.get("ingredients") or [],
        "instructions": data.get("instructions") or "",
    }


def import_to_mealie(url: str, mealie_base_url: str, mealie_api_token: str) -> tuple[int, str]:
    endpoint = f"{mealie_base_url.rstrip('/')}" + "/api/recipes/create/url"
    headers = {
        "Authorization": f"Bearer {mealie_api_token}",
        "Content-Type": "application/json",
    }
    payload = {"url": url}
    r = requests.post(endpoint, headers=headers, json=payload, timeout=60)
    return r.status_code, r.text


def main() -> int:
    parser = argparse.ArgumentParser(description="Scrape recipe URL and optionally import into Mealie")
    parser.add_argument("url", help="Recipe URL")
    parser.add_argument("--import-mealie", action="store_true", help="Import scraped URL into Mealie")
    parser.add_argument("--json-output", action="store_true", help="Print JSON output")
    args = parser.parse_args()

    try:
        s = scrape_me(args.url)
        scraped = normalize(
            {
                "title": s.title(),
                "total_time": s.total_time(),
                "yields": s.yields(),
                "image": s.image(),
                "host": s.host(),
                "ingredients": s.ingredients(),
                "instructions": s.instructions(),
            }
        )
    except Exception as e:
        out = {"ok": False, "error": f"scrape_failed: {e}", "url": args.url}
        print(json.dumps(out, ensure_ascii=False, indent=2) if args.json_output else out["error"])
        return 1

    result: dict[str, Any] = {"ok": True, "url": args.url, "scraped": scraped}

    if args.import_mealie:
        mealie_base_url = os.getenv("MEALIE_BASE_URL", "http://localhost:9925")
        mealie_api_token = os.getenv("MEALIE_API_TOKEN", "")
        if not mealie_api_token:
            result["import"] = {
                "ok": False,
                "error": "missing_MEALIE_API_TOKEN",
                "endpoint": f"{mealie_base_url.rstrip('/')}" + "/api/recipes/create/url",
            }
            print(json.dumps(result, ensure_ascii=False, indent=2) if args.json_output else "MEALIE_API_TOKEN missing")
            return 2
        try:
            status, body = import_to_mealie(args.url, mealie_base_url, mealie_api_token)
            result["import"] = {"ok": 200 <= status < 300, "status": status, "body": body[:4000]}
        except Exception as e:
            result["import"] = {"ok": False, "error": f"import_failed: {e}"}

    if args.json_output:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"title={scraped['title']} host={scraped['host']} ingredients={len(scraped['ingredients'])}")
        if "import" in result:
            print(f"import_ok={result['import'].get('ok')} status={result['import'].get('status')}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

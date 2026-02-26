#!/usr/bin/env python3
"""Task 14: Seed Mealie with initial recipes spanning multiple cuisines.

Imports BBC Good Food recipe URLs via Mealie URL import endpoint.
After import, assigns cuisine tags to each recipe via GET+PUT.
"""
import json
import os
import time
import requests
from datetime import datetime

# Configuration
MEALIE_BASE = "http://localhost:9925"
TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJmZGIwZWY1Mi02OWI1LTRjNzEtYWQwZi0yZTg1OWVjYjUwM2IiLCJleHAiOjE3NzIyMTU0OTAsImlzcyI6Im1lYWxpZSJ9.LnBsGGmA2sJ-1Jt8UdTEqFc8HpRtgpXrJdlnALHezxs"
HEADERS = {"Authorization": f"Bearer {TOKEN}", "Content-Type": "application/json"}

# Recipe seed list: (url, cuisine_tag_name, cuisine_tag_slug)
# Organized into 7 cuisine types; 32 total URLs as buffer for failures
SEED_RECIPES = [
    # === Italiana (5 recipes) ===
    ("https://www.bbcgoodfood.com/recipes/spaghetti-bolognese-recipe", "Italiana", "italiana"),
    ("https://www.bbcgoodfood.com/recipes/carbonara", "Italiana", "italiana"),
    ("https://www.bbcgoodfood.com/recipes/lasagne-recipe", "Italiana", "italiana"),
    ("https://www.bbcgoodfood.com/recipes/risotto-primavera", "Italiana", "italiana"),
    ("https://www.bbcgoodfood.com/recipes/classic-spaghetti-meatballs", "Italiana", "italiana"),

    # === Mexicana (4 recipes) ===
    ("https://www.bbcgoodfood.com/recipes/chicken-fajitas", "Mexicana", "mexicana"),
    ("https://www.bbcgoodfood.com/recipes/beef-tacos", "Mexicana", "mexicana"),
    ("https://www.bbcgoodfood.com/recipes/guacamole-easy", "Mexicana", "mexicana"),
    ("https://www.bbcgoodfood.com/recipes/chicken-tacos", "Mexicana", "mexicana"),

    # === Asiatica (5 recipes) ===
    ("https://www.bbcgoodfood.com/recipes/egg-fried-rice-recipe", "Asiatica", "asiatica"),
    ("https://www.bbcgoodfood.com/recipes/chicken-stir-fry", "Asiatica", "asiatica"),
    ("https://www.bbcgoodfood.com/recipes/pad-thai", "Asiatica", "asiatica"),
    ("https://www.bbcgoodfood.com/recipes/ramen", "Asiatica", "asiatica"),
    ("https://www.bbcgoodfood.com/recipes/vegetable-noodles", "Asiatica", "asiatica"),

    # === India (4 recipes) ===
    ("https://www.bbcgoodfood.com/recipes/chicken-tikka-masala", "India", "india"),
    ("https://www.bbcgoodfood.com/recipes/dhal-recipe", "India", "india"),
    ("https://www.bbcgoodfood.com/recipes/butter-chicken", "India", "india"),
    ("https://www.bbcgoodfood.com/recipes/saag-paneer", "India", "india"),

    # === Mediterranea (4 recipes) ===
    ("https://www.bbcgoodfood.com/recipes/shakshuka", "Mediterranea", "mediterranea"),
    ("https://www.bbcgoodfood.com/recipes/hummus-recipe", "Mediterranea", "mediterranea"),
    ("https://www.bbcgoodfood.com/recipes/greek-salad", "Mediterranea", "mediterranea"),
    ("https://www.bbcgoodfood.com/recipes/mediterranean-roasted-vegetables-recipe", "Mediterranea", "mediterranea"),

    # === Americana (4 recipes) ===
    ("https://www.bbcgoodfood.com/recipes/beef-burger-recipe", "Americana", "americana"),
    ("https://www.bbcgoodfood.com/recipes/classic-mac-cheese", "Americana", "americana"),
    ("https://www.bbcgoodfood.com/recipes/smoky-bbq-chicken-thighs-new-potatoes-slaw", "Americana", "americana"),
    ("https://www.bbcgoodfood.com/recipes/bbq-pork-ribs", "Americana", "americana"),

    # === Francesa (4 recipes) ===
    ("https://www.bbcgoodfood.com/recipes/french-onion-soup-recipe", "Francesa", "francesa"),
    ("https://www.bbcgoodfood.com/recipes/omelette-recipe", "Francesa", "francesa"),
    ("https://www.bbcgoodfood.com/recipes/quiche-lorraine", "Francesa", "francesa"),
    ("https://www.bbcgoodfood.com/recipes/coq-au-vin", "Francesa", "francesa"),

    # === Britanica (additional buffer) ===
    ("https://www.bbcgoodfood.com/recipes/fish-chips", "Britanica", "britanica"),
    ("https://www.bbcgoodfood.com/recipes/classic-chicken-pie", "Britanica", "britanica"),
    ("https://www.bbcgoodfood.com/recipes/beef-stew-recipe", "Britanica", "britanica"),
    ("https://www.bbcgoodfood.com/recipes/shepherds-pie", "Britanica", "britanica"),
]


def import_url(url: str) -> str | None:
    """Import a recipe URL into Mealie. Returns slug or None on failure."""
    try:
        r = requests.post(
            f"{MEALIE_BASE}/api/recipes/create/url",
            headers=HEADERS,
            json={"url": url},
            timeout=90,
        )
        if r.status_code in (200, 201):
            # Mealie returns the slug as a JSON string
            try:
                return json.loads(r.text)
            except json.JSONDecodeError:
                return r.text.strip().strip('"')
        return None
    except Exception as e:
        print(f"    Import exception: {e}")
        return None


def get_recipe(slug: str) -> dict | None:
    """GET full recipe data from Mealie."""
    try:
        r = requests.get(
            f"{MEALIE_BASE}/api/recipes/{slug}",
            headers=HEADERS,
            timeout=30,
        )
        if r.status_code == 200:
            return r.json()
        return None
    except Exception:
        return None


def add_cuisine_tag(slug: str, tag_name: str, tag_slug: str) -> bool:
    """Add a cuisine tag to a recipe via GET + PUT."""
    recipe = get_recipe(slug)
    if not recipe:
        return False
    tags = recipe.get("tags", [])
    if not any(t.get("slug") == tag_slug for t in tags):
        tags.append({"name": tag_name, "slug": tag_slug})
        recipe["tags"] = tags
    try:
        r = requests.put(
            f"{MEALIE_BASE}/api/recipes/{slug}",
            headers=HEADERS,
            json=recipe,
            timeout=30,
        )
        return r.status_code == 200
    except Exception:
        return False


def verify_recipe_completeness(slug: str) -> dict:
    """Check that recipe has ingredients and instructions."""
    recipe = get_recipe(slug)
    if not recipe:
        return {"ok": False, "reason": "not_found"}
    return {
        "ok": True,
        "name": recipe.get("name", ""),
        "ingredients": len(recipe.get("recipeIngredient", [])),
        "steps": len(recipe.get("recipeInstructions", [])),
        "has_ingredients": len(recipe.get("recipeIngredient", [])) > 0,
        "has_steps": len(recipe.get("recipeInstructions", [])) > 0,
        "tags": [t["name"] for t in recipe.get("tags", [])],
        "categories": [c["name"] for c in recipe.get("recipeCategory", [])],
    }


def get_total_recipe_count() -> int:
    """Get total recipe count from Mealie API."""
    r = requests.get(
        f"{MEALIE_BASE}/api/recipes?page=1&perPage=1",
        headers=HEADERS,
        timeout=30,
    )
    if r.status_code == 200:
        return r.json().get("total", 0)
    return -1


def main() -> dict:
    results = {
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "imported": [],
        "failed": [],
        "cuisine_summary": {},
        "completeness_checks": [],
    }

    total_before = get_total_recipe_count()
    print(f"Recipes in Mealie before seed: {total_before}")

    for i, (url, cuisine_name, cuisine_slug) in enumerate(SEED_RECIPES):
        print(f"\n[{i+1}/{len(SEED_RECIPES)}] {cuisine_name}: {url.split('/')[-1]}")
        slug = import_url(url)
        if slug:
            tag_ok = add_cuisine_tag(slug, cuisine_name, cuisine_slug)
            results["imported"].append({
                "url": url,
                "slug": slug,
                "cuisine": cuisine_name,
                "tag_assigned": tag_ok,
            })
            results["cuisine_summary"][cuisine_name] = results["cuisine_summary"].get(cuisine_name, 0) + 1
            print(f"  OK slug={slug} tag_ok={tag_ok}")
        else:
            results["failed"].append({"url": url, "cuisine": cuisine_name})
            print(f"  FAIL: {url.split('/')[-1]}")
        time.sleep(1)  # polite delay

    total_after = get_total_recipe_count()
    results["total_before"] = total_before
    results["total_after"] = total_after
    results["net_imported"] = total_after - total_before

    # Completeness check: verify first 5 imported recipes
    print("\n=== COMPLETENESS CHECKS ===")
    for item in results["imported"][:10]:
        check = verify_recipe_completeness(item["slug"])
        check["url"] = item["url"]
        check["cuisine"] = item["cuisine"]
        results["completeness_checks"].append(check)
        print(f"  {item['slug']}: ingreds={check.get('ingredients',0)} steps={check.get('steps',0)} ok={check.get('ok')}")

    print("\n=== SUMMARY ===")
    print(f"Total before: {total_before}")
    print(f"Total after:  {total_after}")
    print(f"Net imported: {results['net_imported']}")
    print(f"Import list:  {len(results['imported'])} succeeded, {len(results['failed'])} failed")
    print(f"Cuisines:     {list(results['cuisine_summary'].keys())} ({len(results['cuisine_summary'])} types)")

    return results


if __name__ == "__main__":
    results = main()
    evidence_dir = "/root/Cooking Planner Agent/.sisyphus/evidence"
    os.makedirs(evidence_dir, exist_ok=True)
    evidence_path = f"{evidence_dir}/task-14-import-results.json"
    with open(evidence_path, "w") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    print(f"\nEvidence saved: {evidence_path}")

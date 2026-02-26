#!/usr/bin/env python3
"""Task 14 follow-up: Delete crumbs garbage and add cuisine categories/tags to new recipes."""
import json, requests, sqlite3, uuid

BASE = 'http://localhost:9925'
TOKEN = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJmZGIwZWY1Mi02OWI1LTRjNzEtYWQwZi0yZTg1OWVjYjUwM2IiLCJleHAiOjE3NzIyMTU0OTAsImlzcyI6Im1lYWxpZSJ9.LnBsGGmA2sJ-1Jt8UdTEqFc8HpRtgpXrJdlnALHezxs'
HEADERS = {'Authorization': f'Bearer {TOKEN}', 'Content-Type': 'application/json'}
DB_PATH = '/var/lib/docker/volumes/cookingplanneragent_mealie_data/_data/mealie.db'
GROUP_ID = 'a01fe14290e04ffb9cf7e63f2ac1dc03'

def uuid_hex():
    return uuid.uuid4().hex

def ensure_category(cur, conn, name, slug):
    cur.execute('SELECT id FROM categories WHERE slug=?', (slug,))
    row = cur.fetchone()
    if row:
        return row[0]
    new_id = uuid_hex()
    cur.execute('INSERT INTO categories (id, name, slug, group_id) VALUES (?, ?, ?, ?)',
                (new_id, name, slug, GROUP_ID))
    conn.commit()
    print(f'  Created category: {name}')
    return new_id

def ensure_tag(cur, conn, name, slug):
    cur.execute('SELECT id FROM tags WHERE slug=? AND group_id=?', (slug, GROUP_ID))
    row = cur.fetchone()
    if row:
        return row[0]
    new_id = uuid_hex()
    cur.execute('INSERT INTO tags (id, name, slug, group_id) VALUES (?, ?, ?, ?)',
                (new_id, name, slug, GROUP_ID))
    conn.commit()
    return new_id

def assign_category(cur, conn, recipe_id, cat_id):
    cur.execute('SELECT 1 FROM recipes_to_categories WHERE recipe_id=? AND category_id=?', (recipe_id, cat_id))
    if not cur.fetchone():
        cur.execute('INSERT INTO recipes_to_categories (recipe_id, category_id) VALUES (?, ?)', (recipe_id, cat_id))
        conn.commit()
        return True
    return False

def assign_tag(cur, conn, recipe_id, tag_id):
    cur.execute('SELECT 1 FROM recipes_to_tags WHERE recipe_id=? AND tag_id=?', (recipe_id, tag_id))
    if not cur.fetchone():
        cur.execute('INSERT INTO recipes_to_tags (recipe_id, tag_id) VALUES (?, ?)', (recipe_id, tag_id))
        conn.commit()
        return True
    return False

def main():
    results = {
        'deleted_crumbs': [],
        'cuisine_assignments': [],
        'total_recipes': 0,
        'cuisine_categories': {},
        'completeness': [],
    }

    # STEP 1: Delete crumbs via API
    print("=== STEP 1: Delete crumbs ===")
    crumbs = ['crumbs', 'crumbs-1', 'crumbs-2', 'crumbs-3', 'crumbs-4',
              'crumbs-5', 'crumbs-6', 'crumbs-7', 'crumbs-8', 'crumbs-9']
    for slug in crumbs:
        r = requests.delete(f'{BASE}/api/recipes/{slug}', headers=HEADERS, timeout=30)
        ok = r.status_code in (200, 204)
        print(f'  {slug}: {"OK" if ok else "FAIL(" + str(r.status_code) + ")"}')
        if ok:
            results['deleted_crumbs'].append(slug)

    # STEP 2: Add cuisine categories/tags to new valid recipes
    print("\n=== STEP 2: Assign cuisines to new valid recipes ===")
    new_recipes = [
        ('chicken-fajitas',        'Mexicana',    'mexicana',    'mexicana'),
        ('pad-thai',               'Asiática',    'asiatica',    'tailandesa'),
        ('chicken-tikka-masala',   'Asiática',    'asiatica',    'india'),
        ('butter-chicken',         'Asiática',    'asiatica',    'india'),
        ('saag-paneer',            'Asiática',    'asiatica',    'india'),
        ('shakshuka-1',            'Mediterránea','mediterranea','mediterran'),
        ('greek-salad',            'Mediterránea','mediterranea','mediterran'),
        ('quiche-lorraine',        'Francesa',    'francesa',    'francesa'),
        ('coq-au-vin',             'Francesa',    'francesa',    'francesa'),
        ('fish-chips-recipes',     'Británica',   'britanica',   'britanica'),
        ('no-fuss-shepherd-s-pie', 'Británica',   'britanica',   'britanica'),
    ]

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    # Ensure categories/tags exist
    cat_ids = {}
    tag_ids = {}
    for _, cuisine, cat_slug, tag_slug in new_recipes:
        if cat_slug not in cat_ids:
            cat_ids[cat_slug] = ensure_category(cur, conn, cuisine, cat_slug)
        if tag_slug not in tag_ids:
            tag_ids[tag_slug] = ensure_tag(cur, conn, tag_slug, tag_slug)
        if cat_slug not in tag_ids:
            tag_ids[cat_slug] = ensure_tag(cur, conn, cat_slug, cat_slug)

    # Assign to recipes
    for slug, cuisine, cat_slug, tag_slug in new_recipes:
        cur.execute('SELECT id, name FROM recipes WHERE slug=?', (slug,))
        row = cur.fetchone()
        if not row:
            print(f'  NOT FOUND: {slug}')
            continue
        recipe_id, recipe_name = row

        cat_assigned = assign_category(cur, conn, recipe_id, cat_ids[cat_slug])
        tag_assigned = assign_tag(cur, conn, recipe_id, tag_ids.get(tag_slug, ''))
        # Also assign the cuisine slug tag (e.g., 'francesa', 'britanica', etc.)
        if cat_slug in tag_ids and cat_slug != tag_slug:
            assign_tag(cur, conn, recipe_id, tag_ids[cat_slug])

        print(f'  {slug}: cat={cat_slug} cat_new={cat_assigned} tag_new={tag_assigned}')
        results['cuisine_assignments'].append({'slug': slug, 'cuisine': cuisine, 'category': cat_slug})

    conn.close()

    # STEP 3: Verify via API
    print("\n=== STEP 3: Final verification via API ===")
    r = requests.get(f'{BASE}/api/recipes?page=1&perPage=100', headers=HEADERS, timeout=30)
    d = r.json()
    total = d.get('total', 0)
    results['total_recipes'] = total
    print(f'Total recipes: {total}')

    cuisine_counts = {}
    for item in d.get('items', []):
        for cat in item.get('recipeCategory', []):
            cname = cat['name']
            cuisine_counts[cname] = cuisine_counts.get(cname, 0) + 1

    results['cuisine_categories'] = cuisine_counts
    print(f'Categories: {dict(sorted(cuisine_counts.items()))}')
    print(f'Distinct cuisine categories: {len(cuisine_counts)}')

    # Completeness check on diverse sample
    print("\n=== STEP 4: Completeness checks ===")
    sample = [
        'pasta-carbonara', 'tacos-de-carne-asada', 'chicken-tikka-masala',
        'tabbouleh', 'pollo-al-ajillo', 'chicken-fajitas',
        'butter-chicken', 'quiche-lorraine', 'pad-thai',
        'ramen-de-miso', 'enchiladas-verdes', 'pizza-margherita',
        'shakshuka', 'gazpacho-andaluz', 'spaghetti-aglio-e-olio',
        'greek-salad', 'coq-au-vin', 'paella-valenciana',
        'tortilla-espanola', 'pollo-teriyaki'
    ]
    for slug in sample:
        r = requests.get(f'{BASE}/api/recipes/{slug}', headers=HEADERS, timeout=20)
        if r.status_code == 200:
            rec = r.json()
            ing = len(rec.get('recipeIngredient', []))
            steps = len(rec.get('recipeInstructions', []))
            cats = [c['name'] for c in rec.get('recipeCategory', [])]
            tags = [t['name'] for t in rec.get('tags', [])][:3]
            check = {
                'slug': slug, 'name': rec.get('name', ''),
                'ingredients': ing, 'steps': steps,
                'complete': ing > 0 and steps > 0,
                'categories': cats, 'tags': tags
            }
            results['completeness'].append(check)
            sym = 'OK' if check['complete'] else 'MISS'
            print(f'  [{sym}] {slug}: {ing} ingreds, {steps} steps, cats={cats}')

    # Summary
    complete_count = sum(1 for c in results['completeness'] if c['complete'])
    print(f"\n=== PASS/FAIL CRITERIA ===")
    p1 = results['total_recipes'] >= 20
    p2 = len(cuisine_counts) >= 4
    p3 = complete_count >= 10
    print(f"  20+ recipes: {results['total_recipes']} -> {'PASS' if p1 else 'FAIL'}")
    print(f"  4+ cuisine types: {len(cuisine_counts)} types -> {'PASS' if p2 else 'FAIL'}")
    print(f"  ingreds+steps: {complete_count}/{len(results['completeness'])} complete -> {'PASS' if p3 else 'FAIL'}")
    results['pass'] = p1 and p2 and p3

    return results

if __name__ == '__main__':
    results = main()
    evidence_dir = '/root/Cooking Planner Agent/.sisyphus/evidence'
    import os
    os.makedirs(evidence_dir, exist_ok=True)
    out_path = f'{evidence_dir}/task-14-cleanup-and-verify.json'
    with open(out_path, 'w') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    print(f"\nEvidence saved: {out_path}")

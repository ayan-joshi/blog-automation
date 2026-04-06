"""
queue_manager.py
Parses content-calendar.md + keyword-mapping.md
Manages queue.json (pending / published / failed)
"""

import json
import random
from pathlib import Path

from planning_assets import get_post_spec as _shared_get_post_spec
from planning_assets import parse_calendar, parse_keywords

QUEUE_FILE = Path(__file__).parent / "queue.json"

# Posts already written manually (weeks 1-4)
ALREADY_WRITTEN = {1, 2, 3, 13, 14, 15, 21, 37, 41, 42, 47, 48}


def init_queue():
    """Initialise queue.json from content-calendar.md. Skips already-written posts."""
    posts = parse_calendar()
    all_nums = sorted(posts.keys())
    pending = [n for n in all_nums if n not in ALREADY_WRITTEN]

    queue = {"pending": pending, "published": list(ALREADY_WRITTEN), "failed": []}
    QUEUE_FILE.write_text(json.dumps(queue, indent=2))
    print(f"Queue initialised: {len(pending)} pending, {len(ALREADY_WRITTEN)} already written")
    return queue


def load_queue():
    if not QUEUE_FILE.exists():
        return init_queue()
    return json.loads(QUEUE_FILE.read_text())


def save_queue(queue):
    QUEUE_FILE.write_text(json.dumps(queue, indent=2))


def get_next_posts(n=3):
    """Return next n PostSpec dicts, selecting randomly across pillars for variety."""
    queue = load_queue()
    calendar = parse_calendar()
    kw_map = parse_keywords()

    # Group pending post numbers by pillar (preserve order within each pillar)
    by_pillar: dict[str, list[int]] = {}
    for num in queue["pending"]:
        if num not in calendar:
            continue
        pillar = calendar[num]["pillar"]
        by_pillar.setdefault(pillar, []).append(num)

    # Pick n posts by cycling through randomly chosen pillars
    selected: list[int] = []
    available_pillars = list(by_pillar.keys())

    while len(selected) < n and available_pillars:
        pillar = random.choice(available_pillars)
        candidates = by_pillar[pillar]
        selected.append(candidates.pop(0))  # take earliest post from this pillar
        if not candidates:
            available_pillars.remove(pillar)

    # Build full spec dicts
    specs = []
    for num in selected:
        spec = dict(calendar[num])
        kw = kw_map.get(num, {})
        spec["green_keywords"] = kw.get("green", [])
        spec["yellow_keywords"] = kw.get("yellow", [])
        spec["supporting_keywords"] = kw.get("supporting", [])
        spec["placement_notes"] = kw.get("notes", "")
        if kw.get("slug"):
            spec["slug"] = kw["slug"]
        specs.append(spec)

    return specs


def mark_published(post_num, shopify_id):
    queue = load_queue()
    if post_num in queue["pending"]:
        queue["pending"].remove(post_num)
    if post_num not in queue["published"]:
        queue["published"].append({"post_num": post_num, "shopify_id": shopify_id})
    save_queue(queue)


def mark_failed(post_num, error):
    queue = load_queue()
    if post_num in queue["pending"]:
        queue["pending"].remove(post_num)
    queue["failed"].append({"post_num": post_num, "error": str(error)})
    save_queue(queue)


def status():
    queue = load_queue()
    pending = len(queue["pending"])
    published = len(queue["published"])
    failed = len(queue["failed"])
    print(f"Queue Status")
    print(f"  Pending  : {pending}")
    print(f"  Published: {published}")
    print(f"  Failed   : {failed}")
    if queue["pending"]:
        print(f"  Next up  : Posts {queue['pending'][:5]}")
    if queue["failed"]:
        print(f"  Failed   : {[f['post_num'] for f in queue['failed']]}")


def get_post_spec(post_num):
    """Get a single post spec by number."""
    return _shared_get_post_spec(post_num)

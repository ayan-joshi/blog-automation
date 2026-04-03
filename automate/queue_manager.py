"""
queue_manager.py
Parses content-calendar.md + keyword-mapping.md
Manages queue.json (pending / published / failed)
"""

import json
import os
import random
import re
from pathlib import Path

ROOT = Path(__file__).parent.parent
CALENDAR_FILE = ROOT / "content-calendar.md"
KEYWORDS_FILE = ROOT / "keyword-mapping.md"
QUEUE_FILE = Path(__file__).parent / "queue.json"

# Posts already written manually (weeks 1-4)
ALREADY_WRITTEN = {1, 2, 3, 13, 14, 15, 21, 37, 41, 42, 47, 48}


def _parse_calendar():
    """Parse content-calendar.md → dict of post_num → {title, primary_kw, intent, aeo, pillar}"""
    text = CALENDAR_FILE.read_text(encoding="utf-8")
    posts = {}
    current_pillar = "General"

    for line in text.splitlines():
        # Detect pillar heading
        pillar_match = re.match(r"^##\s+PILLAR\s+\d+\s+[—–-]+\s+(.+)", line)
        if pillar_match:
            current_pillar = pillar_match.group(1).strip()
            continue

        # Match table rows: | # | Title | Primary KW | Intent | AEO | Priority |
        row = re.match(
            r"^\|\s*(\d+)\s*\|\s*(.+?)\s*\|\s*(.+?)\s*\|\s*(TOFU|MOFU|BOFU)\s*\|\s*(✅|❌)\s*\|",
            line,
        )
        if row:
            num = int(row.group(1))
            posts[num] = {
                "post_num": num,
                "title": row.group(2).strip(),
                "primary_kw": row.group(3).strip(),
                "intent": row.group(4).strip(),
                "aeo": row.group(5).strip() == "✅",
                "pillar": current_pillar,
                "slug": _title_to_slug(row.group(2).strip()),
            }

    return posts


def _parse_keywords():
    """Parse keyword-mapping.md → dict of post_num → {green, yellow, supporting, slug, notes}"""
    text = KEYWORDS_FILE.read_text(encoding="utf-8")
    kw_map = {}
    current_post = None

    for line in text.splitlines():
        # Match post header: ### Post #N — Title
        post_match = re.match(r"^###\s+Post\s+#(\d+)", line)
        if post_match:
            current_post = int(post_match.group(1))
            kw_map[current_post] = {
                "green": [], "yellow": [], "supporting": [], "slug": "", "notes": ""
            }
            continue

        if current_post is None:
            continue

        # Slug line
        slug_match = re.match(r"\*\*Slug:\*\*\s+`(.+?)`", line)
        if slug_match:
            kw_map[current_post]["slug"] = slug_match.group(1)
            continue

        # Keyword table rows
        green_match = re.match(r"^\|\s*🟢\s*Green\s*\|\s*(.+?)\s*\|", line)
        if green_match:
            kw_map[current_post]["green"] = [
                k.strip() for k in green_match.group(1).split("·") if k.strip()
            ]
            continue

        yellow_match = re.match(r"^\|\s*🟡\s*Yellow\s*\|\s*(.+?)\s*\|", line)
        if yellow_match:
            kw_map[current_post]["yellow"] = [
                k.strip() for k in yellow_match.group(1).split("·") if k.strip()
            ]
            continue

        supporting_match = re.match(r"^\|\s*⬜\s*Supporting\s*\|\s*(.+?)\s*\|", line)
        if supporting_match:
            kw_map[current_post]["supporting"] = [
                k.strip() for k in supporting_match.group(1).split("·") if k.strip()
            ]
            continue

        # Placement notes (multi-line, collect until next section)
        if line.startswith("**Placement notes:**"):
            kw_map[current_post]["notes"] = ""
            continue

        if current_post and kw_map[current_post]["notes"] is not None:
            if line.startswith("- "):
                kw_map[current_post]["notes"] += line + "\n"

    return kw_map


def _title_to_slug(title):
    """Convert a blog title to a URL slug."""
    slug = title.lower()
    slug = re.sub(r"[^a-z0-9\s-]", "", slug)
    slug = re.sub(r"\s+", "-", slug.strip())
    slug = re.sub(r"-+", "-", slug)
    return slug[:80]


def init_queue():
    """Initialise queue.json from content-calendar.md. Skips already-written posts."""
    posts = _parse_calendar()
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
    calendar = _parse_calendar()
    kw_map = _parse_keywords()

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
    calendar = _parse_calendar()
    kw_map = _parse_keywords()
    if post_num not in calendar:
        raise ValueError(f"Post #{post_num} not found in content-calendar.md")
    spec = dict(calendar[post_num])
    kw = kw_map.get(post_num, {})
    spec["green_keywords"] = kw.get("green", [])
    spec["yellow_keywords"] = kw.get("yellow", [])
    spec["supporting_keywords"] = kw.get("supporting", [])
    spec["placement_notes"] = kw.get("notes", "")
    if kw.get("slug"):
        spec["slug"] = kw["slug"]
    return spec

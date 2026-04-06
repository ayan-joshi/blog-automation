"""
Shared planning asset parsing for blog and community workflows.
"""

import re
from pathlib import Path

ROOT = Path(__file__).parent.parent
CALENDAR_FILE = ROOT / "content-calendar.md"
KEYWORDS_FILE = ROOT / "keyword-mapping.md"


def title_to_slug(title):
    """Convert a content title to a URL-friendly slug."""
    slug = title.lower()
    slug = re.sub(r"[^a-z0-9\s-]", "", slug)
    slug = re.sub(r"\s+", "-", slug.strip())
    slug = re.sub(r"-+", "-", slug)
    return slug[:80]


def parse_calendar():
    """Parse content-calendar.md into post specs keyed by post number."""
    text = CALENDAR_FILE.read_text(encoding="utf-8")
    posts = {}
    current_pillar = "General"

    for line in text.splitlines():
        pillar_match = re.match(r"^##\s+PILLAR\s+\d+\s+[—–-]+\s+(.+)", line)
        if pillar_match:
            current_pillar = pillar_match.group(1).strip()
            continue

        row = re.match(
            r"^\|\s*(\d+)\s*\|\s*(.+?)\s*\|\s*(.+?)\s*\|\s*(TOFU|MOFU|BOFU)\s*\|\s*(✅|❌)\s*\|\s*(.+?)\s*\|$",
            line,
        )
        if not row:
            continue

        num = int(row.group(1))
        title = row.group(2).strip()
        priority = row.group(6).strip()
        posts[num] = {
            "post_num": num,
            "title": title,
            "primary_kw": row.group(3).strip(),
            "intent": row.group(4).strip(),
            "aeo": row.group(5).strip() == "✅",
            "pillar": current_pillar,
            "priority": priority,
            "active": "deferred" not in priority.lower(),
            "slug": title_to_slug(title),
        }

    return posts


def parse_keywords():
    """Parse keyword-mapping.md into keyword specs keyed by post number."""
    text = KEYWORDS_FILE.read_text(encoding="utf-8")
    kw_map = {}
    current_post = None

    for line in text.splitlines():
        post_match = re.match(r"^###\s+Post\s+#(\d+)", line)
        if post_match:
            current_post = int(post_match.group(1))
            kw_map[current_post] = {
                "green": [],
                "yellow": [],
                "supporting": [],
                "slug": "",
                "notes": "",
            }
            continue

        if current_post is None:
            continue

        slug_match = re.match(r"\*\*Slug:\*\*\s+`(.+?)`", line)
        if slug_match:
            kw_map[current_post]["slug"] = slug_match.group(1)
            continue

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

        if line.startswith("**Placement notes:**"):
            kw_map[current_post]["notes"] = ""
            continue

        if line.startswith("- "):
            kw_map[current_post]["notes"] += line + "\n"

    return kw_map


def parse_publish_schedule():
    """Parse the 12-week publish schedule into {week: [post_nums]}."""
    text = CALENDAR_FILE.read_text(encoding="utf-8")
    schedule = {}

    for line in text.splitlines():
        row = re.match(r"^\|\s*\*\*Week\s+(\d+)\*\*\s*\|\s*(.+?)\s*\|", line)
        if not row:
            continue
        week = int(row.group(1))
        schedule[week] = [int(num) for num in re.findall(r"#(\d+)", row.group(2))]

    return schedule


def _keyword_fallback(spec):
    """
    Assign keyword targets based on post title + pillar when no specific
    keyword-mapping.md entry exists. Uses the same keyword clusters from
    the Keyword Tracker spreadsheet.
    """
    title = spec.get("title", "").lower()
    pillar = spec.get("pillar", "").lower()

    teether_words = ["teether", "teething", "drool", "silicone toy", "amber", "gel", "chew", "mouthing", "gum"]
    cloth_book_words = ["cloth book", "sensory book", "high contrast", "flashcard", "visual", "black and white", "my first book", "montessori"]
    gift_words = ["gift", "gifting", "baby shower", "diwali", "raksha bandhan", "festival"]
    dev_words = ["milestone", "development", "motor", "sensory", "reflex", "vision", "see color", "tummy time"]

    is_teether = any(w in title for w in teether_words)
    is_cloth   = any(w in title for w in cloth_book_words)
    is_gift    = any(w in title for w in gift_words)
    is_dev     = any(w in title for w in dev_words)

    if is_teether:
        return {
            "green": ["infant teether", "newborn teether", "teethers", "newborn teething toys"],
            "yellow": ["silicone teether", "newborn teethers", "teething toys"],
            "supporting": ["BIS certified teether", "food grade silicone teether", "best teether for babies India"],
            "notes": "Green in intro + at least one H2. Yellow in body paragraphs. BIS certification angle in supporting.",
        }
    if is_cloth:
        return {
            "green": ["infant cloth books", "newborn toys", "toys for newborn to 6 months"],
            "yellow": ["tummy time", "montessori educational toys", "infant learning toys"],
            "supporting": ["soft books for infants", "high contrast books", "tummy time book", "black and white books for newborns"],
            "notes": "Green in intro + H2 heading. Yellow in section about tummy time and Montessori. Supporting sprinkled once each.",
        }
    if is_gift:
        return {
            "green": ["newborn toys", "newborn teething toys"],
            "yellow": ["infant cloth books", "teething toys", "tummy time"],
            "supporting": ["best toys newborn", "infant learning toys", "soft books for infants"],
            "notes": "Green in intro gifting context. Yellow in product recommendation sections.",
        }
    if is_dev:
        return {
            "green": ["newborn toys", "toys for newborn to 6 months"],
            "yellow": ["tummy time", "infant cloth books", "teething toys"],
            "supporting": ["sensory toys for newborns", "tummy time toys", "infant learning toys"],
            "notes": "Green in intro + at least one H2. Yellow in product bridge section if applicable.",
        }
    # Generic fallback — covers D2C, brand, and lifestyle posts
    return {
        "green": ["newborn toys", "newborn teething toys"],
        "yellow": ["infant cloth books", "teething toys", "tummy time"],
        "supporting": ["infant learning toys", "sensory toys for newborns"],
        "notes": "Use green keywords in intro and at least one H2. Yellow in body naturally.",
    }


def get_post_spec(post_num):
    """Return a merged spec for a single post number."""
    calendar = parse_calendar()
    if post_num not in calendar:
        raise ValueError(f"Post #{post_num} not found in content-calendar.md")

    spec = dict(calendar[post_num])
    kw = parse_keywords().get(post_num, {})

    # Use explicit mapping if it exists, otherwise derive from title/pillar
    if kw.get("green") or kw.get("yellow"):
        spec["green_keywords"] = kw.get("green", [])
        spec["yellow_keywords"] = kw.get("yellow", [])
        spec["supporting_keywords"] = kw.get("supporting", [])
        spec["placement_notes"] = kw.get("notes", "")
    else:
        fallback = _keyword_fallback(spec)
        spec["green_keywords"] = fallback["green"]
        spec["yellow_keywords"] = fallback["yellow"]
        spec["supporting_keywords"] = fallback["supporting"]
        spec["placement_notes"] = fallback["notes"]

    if kw.get("slug"):
        spec["slug"] = kw["slug"]
    return spec


def get_post_specs(post_nums=None, active_only=False):
    """Return merged specs for multiple posts."""
    calendar = parse_calendar()
    nums = post_nums or sorted(calendar.keys())
    specs = []
    for num in nums:
        if num not in calendar:
            continue
        if active_only and not calendar[num].get("active", True):
            continue
        specs.append(get_post_spec(num))
    return specs

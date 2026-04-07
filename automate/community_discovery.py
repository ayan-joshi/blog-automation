"""
Discovery helpers for weekly Quora and Reddit sourcing.

Quora: real questions via DuckDuckGo site:quora.com search (ddgs)
Reddit: real posts via Reddit public JSON API (no auth needed)
"""

import hashlib
import time

import requests
from ddgs import DDGS

REDDIT_HEADERS = {"User-Agent": "nubokind-community/1.0"}


def _item_id(week, platform, day, url):
    digest = hashlib.sha1(f"{week}|{platform}|{day}|{url}".encode()).hexdigest()
    return digest[:12]


QUESTION_WORDS = ("how", "what", "why", "when", "is", "are", "can", "which", "does", "do", "should", "will", "where")

# Terms that indicate India-relevant content — used to score and prioritise results
INDIA_TERMS = [
    "india", "indian", "mumbai", "delhi", "bangalore", "bengaluru",
    "chennai", "hyderabad", "pune", "kolkata", "iap", "desi", "hindi",
    "ayurvedic", "ayurveda", "rupee", "anganwadi",
]


def _india_score(title, snippet):
    """Score how India-relevant a result is. Higher = more India-specific."""
    text = (title + " " + snippet).lower()
    return sum(1 for w in INDIA_TERMS if w in text)


def _is_real_quora_question(url, title):
    """Return True only if this looks like a real Quora question page."""
    from urllib.parse import urlparse
    parsed = urlparse(url)
    if not parsed.path or parsed.path in ("/", ""):
        return False
    if len(parsed.path) < 10:
        return False
    generic = {"quora - a place to share knowledge", "quora", "sign in to quora"}
    if title.lower().strip() in generic:
        return False
    # Title should start with a question word or contain one early on
    first_word = title.lower().split()[0] if title.split() else ""
    if first_word not in QUESTION_WORDS:
        first_words = [w.lower() for w in title.split()[:4]]
        if not any(w in QUESTION_WORDS for w in first_words):
            return False
    return True


def _is_relevant_quora_result(title, snippet, query):
    """Check that at least 1 meaningful query word appears in title or snippet."""
    # Strip "India" from query for relevance check — it's a targeting modifier, not topic
    core_query = query.lower().replace("india", "").strip()
    words = [w for w in core_query.split() if len(w) > 3]
    if not words:
        return True
    text = (title + " " + snippet).lower()
    return any(w in text for w in words)


def _ddgs_quora_search(query, max_results=15, timelimit=None):
    """Run a ddgs site:quora.com search. timelimit: 'd','w','m','y' or None."""
    try:
        with DDGS() as ddgs:
            kwargs = {"max_results": max_results}
            if timelimit:
                kwargs["timelimit"] = timelimit
            results = list(ddgs.text(f"site:quora.com {query}", **kwargs))
        time.sleep(2.5)
        return results
    except Exception as e:
        print(f"    ddgs error: {e}")
        return []


def _collect_quora_candidates(results, query, seen_urls):
    """Collect all valid unseen relevant results, scored by India-relevance."""
    candidates = []
    for r in results:
        url = r.get("href", "")
        if not url or not url.startswith("http") or url in seen_urls:
            continue
        if "quora.com" not in url:
            continue
        title = r.get("title", "").replace(" - Quora", "").strip()
        snippet = r.get("body", "")[:250]
        if not title or title.lower() == url.lower():
            continue
        if not _is_real_quora_question(url, title):
            continue
        if not _is_relevant_quora_result(title, snippet, query):
            continue
        candidates.append({
            "url": url,
            "title": title,
            "snippet": snippet,
            "india_score": _india_score(title, snippet),
        })
    # Sort by India-relevance descending — most India-specific result wins
    candidates.sort(key=lambda x: x["india_score"], reverse=True)
    return candidates


def _fetch_quora_question(query, seen_urls, max_results=15):
    """
    Return the most India-relevant recent Quora question for this query.

    Search priority:
      1. "{query} India" — recent (past month)
      2. "{query}"       — recent (past month)
      3. "{query} India" — any time
      4. "{query}"       — any time  (original fallback)
    Within each attempt, picks the highest India-score candidate.
    """
    india_query = f"{query} India"
    short_query = " ".join(query.split()[:3])

    attempts = [
        (india_query, "m"),   # India + recent
        (query,       "m"),   # generic + recent
        (india_query, None),  # India + any time
        (query,       None),  # generic + any time
        (short_query, None),  # shortened fallback
    ]

    for attempt_query, timelimit in attempts:
        results = _ddgs_quora_search(attempt_query, max_results, timelimit=timelimit)
        candidates = _collect_quora_candidates(results, attempt_query, seen_urls)
        if candidates:
            best = candidates[0]
            label = f"recent+India" if timelimit == "m" and "India" in attempt_query else \
                    f"recent" if timelimit == "m" else \
                    f"India" if "India" in attempt_query else "fallback"
            print(f"    [Quora pick: {label}, india_score={best['india_score']}]")
            return best

    return None


INDIA_SUBREDDITS = {"IndianParenting", "india", "AskIndia", "IndiaSpeaks"}


def _reddit_india_score(subreddit, title, snippet):
    """Score a Reddit post by India-relevance. Indian subreddits get a large bonus."""
    score = 8 if subreddit in INDIA_SUBREDDITS else 0
    score += _india_score(title, snippet)
    return score


def _is_relevant_reddit_post(title, snippet, keyword):
    """
    At least one specific keyword word (len > 5) must appear in the title.
    Falls back to checking title+snippet if no long words exist.
    """
    words = [w.lower() for w in keyword.split() if len(w) > 3]
    if not words:
        return True
    title_lower = title.lower()
    specific = [w for w in words if len(w) > 5]
    if specific:
        return any(w in title_lower for w in specific)
    text = (title_lower + " " + snippet.lower())
    matches = sum(1 for w in words if w in text)
    return matches >= min(2, len(words))


def _search_reddit(keyword, restrict_to_sub=None, limit=5):
    """Search Reddit for posts, optionally restricted to a subreddit."""
    try:
        encoded = requests.utils.quote(keyword)
        if restrict_to_sub:
            url = (
                f"https://www.reddit.com/r/{restrict_to_sub}/search.json"
                f"?q={encoded}&sort=relevance&t=month&limit={limit}&restrict_sr=1"
            )
        else:
            url = (
                f"https://www.reddit.com/search.json"
                f"?q={encoded}&sort=relevance&t=month&limit={limit}"
            )
        resp = requests.get(url, headers=REDDIT_HEADERS, timeout=10)
        return resp.json().get("data", {}).get("children", [])
    except Exception as e:
        print(f"    Reddit search error: {e}")
        return []


def _fetch_reddit_post(keyword, subreddits, seen_urls, max_per_sub=5):
    """
    Return most India-relevant recent Reddit post.
    - Searches IndianParenting first, then other subreddits
    - Scores all candidates by India-relevance + subreddit origin
    - Falls back to all-Reddit search if subreddit search returns nothing
    """
    candidates = []

    # Always search IndianParenting first, then the topic's own subreddits
    ordered_subs = ["IndianParenting"] + [s for s in subreddits if s != "IndianParenting"]

    for sub in ordered_subs:
        for p in _search_reddit(keyword, restrict_to_sub=sub, limit=max_per_sub):
            d = p.get("data", {})
            post_url = "https://reddit.com" + d.get("permalink", "")
            title = d.get("title", "")
            snippet = (d.get("selftext") or "")[:250]
            subreddit = d.get("subreddit", sub)
            if not title or post_url in seen_urls:
                continue
            if not _is_relevant_reddit_post(title, snippet, keyword):
                continue
            candidates.append({
                "url": post_url,
                "title": title,
                "subreddit": subreddit,
                "score": d.get("score", 0),
                "num_comments": d.get("num_comments", 0),
                "snippet": snippet,
                "india_score": _reddit_india_score(subreddit, title, snippet),
            })
        time.sleep(0.5)

    # Fallback: search all of Reddit
    if not candidates:
        for p in _search_reddit(keyword, restrict_to_sub=None, limit=10):
            d = p.get("data", {})
            post_url = "https://reddit.com" + d.get("permalink", "")
            title = d.get("title", "")
            snippet = (d.get("selftext") or "")[:250]
            subreddit = d.get("subreddit", "")
            if not title or post_url in seen_urls:
                continue
            if not _is_relevant_reddit_post(title, snippet, keyword):
                continue
            candidates.append({
                "url": post_url,
                "title": title,
                "subreddit": subreddit,
                "score": d.get("score", 0),
                "num_comments": d.get("num_comments", 0),
                "snippet": snippet,
                "india_score": _reddit_india_score(subreddit, title, snippet),
            })

    if not candidates:
        return None

    # Primary sort: India score desc. Tiebreak: num_comments desc.
    candidates.sort(key=lambda x: (x["india_score"], x["num_comments"]), reverse=True)
    return candidates[0]


def _build_item(week, day, platform, topic, result):
    """Build a queue item dict from a fetched result."""
    base = {
        "item_id": _item_id(week, platform, day, result["url"]),
        "week": week,
        "day": day,
        "platform": platform,
        "topic": topic["topic"],
        "primary_keyword": topic["quora_kw"] if platform == "quora" else topic["reddit_kw"],
        "question_or_post_title": result["title"],
        "source_url": result["url"],
        "source_context": result.get("snippet", ""),
        "answer_angle": (
            topic.get("answer_angle_quora", "")
            if platform == "quora"
            else topic.get("answer_angle_reddit", "")
        ),
        "brand_mentions_allowed": False,
        "status": "discovered",
        "draft_opening": "",
        "draft_body": "",
        "draft_text": "",
        "review_notes": "",
    }
    if platform == "reddit":
        base["subreddit_or_source"] = f"r/{result['subreddit']}"
        base["num_comments"] = result.get("num_comments", 0)
        base["score"] = result.get("score", 0)
    else:
        base["subreddit_or_source"] = "Quora"
    return base


def discover_week(week, topics, seen_urls):
    """
    Fetch 1 Quora question + 1 Reddit post per topic.

    Returns (items, updated_seen_urls).
    topics: list of 4 topic dicts from community_topics.py
    seen_urls: set/list of already-used URLs (cross-week dedup)
    """
    items = []
    seen = set(seen_urls)

    for day_num, topic in enumerate(topics, start=1):
        print(f"\n  Day {day_num}: {topic['topic']}")

        quora = _fetch_quora_question(topic["quora_kw"], seen)
        if quora:
            seen.add(quora["url"])
            items.append(_build_item(week, day_num, "quora", topic, quora))
            print(f"    Quora:  {quora['title'][:72]}")
        else:
            print(f"    Quora:  no result found")

        reddit = _fetch_reddit_post(topic["reddit_kw"], topic["subreddits"], seen)
        if reddit:
            seen.add(reddit["url"])
            items.append(_build_item(week, day_num, "reddit", topic, reddit))
            print(f"    Reddit: {reddit['title'][:60]} (r/{reddit['subreddit']}, {reddit['num_comments']} comments)")
        else:
            print(f"    Reddit: no result found")

    return items, list(seen)

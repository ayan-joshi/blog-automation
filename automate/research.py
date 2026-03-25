"""
research.py
Gathers real parent discussions from Reddit + Hacker News
to ground blog generation in authentic language and concerns.
"""

import urllib.request
import urllib.parse
import json
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

HEADERS = {"User-Agent": "nubokind-blog-research/1.0 (educational content)"}

SUBREDDITS = ["beyondthebump", "NewParents", "Mommit", "IndianParenting", "newborns"]


def _reddit_search(query, subreddit, limit=5):
    """Search a subreddit for posts matching the query."""
    encoded = urllib.parse.quote(query)
    url = (
        f"https://www.reddit.com/r/{subreddit}/search.json"
        f"?q={encoded}&restrict_sr=1&sort=top&t=year&limit={limit}"
    )
    try:
        req = urllib.request.Request(url, headers=HEADERS)
        with urllib.request.urlopen(req, timeout=10) as r:
            data = json.loads(r.read())
            posts = data["data"]["children"]
            results = []
            for p in posts:
                d = p["data"]
                results.append({
                    "source": f"r/{subreddit}",
                    "title": d.get("title", ""),
                    "text": d.get("selftext", "")[:300],
                    "upvotes": d.get("ups", 0),
                    "comments": d.get("num_comments", 0),
                    "url": f"https://reddit.com{d.get('permalink', '')}",
                })
            return results
    except Exception:
        return []


def _hn_search(query, limit=5):
    """Search Hacker News via Algolia API (free, no auth)."""
    encoded = urllib.parse.quote(query)
    url = f"https://hn.algolia.com/api/v1/search?query={encoded}&tags=story&hitsPerPage={limit}"
    try:
        req = urllib.request.Request(url, headers=HEADERS)
        with urllib.request.urlopen(req, timeout=10) as r:
            data = json.loads(r.read())
            results = []
            for hit in data.get("hits", []):
                results.append({
                    "source": "Hacker News",
                    "title": hit.get("title", ""),
                    "text": hit.get("story_text", "")[:300] if hit.get("story_text") else "",
                    "upvotes": hit.get("points", 0),
                    "comments": hit.get("num_comments", 0),
                    "url": hit.get("url", ""),
                })
            return results
    except Exception:
        return []


def research_topic(title, primary_kw):
    """
    Run parallel research across Reddit subreddits + HN.
    Returns a formatted research brief string for the generator prompt.
    """
    query = primary_kw if primary_kw else title

    # Run searches in parallel
    all_results = []
    tasks = {}

    with ThreadPoolExecutor(max_workers=6) as executor:
        # Reddit searches
        for sub in SUBREDDITS:
            future = executor.submit(_reddit_search, query, sub, 3)
            tasks[future] = f"r/{sub}"

        # HN search
        hn_future = executor.submit(_hn_search, query, 3)
        tasks[hn_future] = "HN"

        for future in as_completed(tasks, timeout=15):
            results = future.result()
            all_results.extend(results)

    # Sort by upvotes, keep top 10
    all_results.sort(key=lambda x: x["upvotes"], reverse=True)
    top = all_results[:10]

    if not top:
        return "No research findings available for this topic."

    # Format into a brief for the generator
    lines = ["## Research Brief — What Parents Are Actually Discussing\n"]
    for item in top:
        lines.append(f"**[{item['source']}]** {item['title']} ({item['upvotes']} upvotes)")
        if item["text"]:
            lines.append(f"  → {item['text'][:200]}")
        lines.append("")

    return "\n".join(lines)


if __name__ == "__main__":
    # Quick test
    brief = research_topic("best teether brands India", "best teether brand India 2026")
    print(brief)

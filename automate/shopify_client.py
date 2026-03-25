"""
shopify_client.py
Posts blog articles to Shopify Admin API.
Sets: title, body_html, handle, author, meta description, FAQ metafields.
All posts created as hidden (published: false).
"""

import os
import json
import urllib.request
import urllib.error
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent / ".env")

STORE_URL = os.environ.get("SHOPIFY_STORE_URL", "e81e39-94.myshopify.com")
TOKEN = os.environ.get("SHOPIFY_ACCESS_TOKEN", "")
BLOG_ID = os.environ.get("SHOPIFY_BLOG_ID", "87185129587")
API_VERSION = "2025-07"
BASE = f"https://{STORE_URL}/admin/api/{API_VERSION}"
HEADERS = {"X-Shopify-Access-Token": TOKEN, "Content-Type": "application/json"}
BLOG_BASE = "/blogs/early-learning-sensory-development"


def _request(method, path, payload=None):
    url = f"{BASE}{path}"
    data = json.dumps(payload).encode("utf-8") if payload else None
    req = urllib.request.Request(url, data=data, headers=HEADERS, method=method)
    try:
        with urllib.request.urlopen(req) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"Shopify API {method} {path} failed: {e.code} {e.read().decode()}") from e


def get_published_posts(limit=250):
    """Fetch all published articles. Returns list of (handle, title) tuples."""
    data = _request("GET", f"/blogs/{BLOG_ID}/articles.json?limit={limit}&published_status=published")
    return [(a["handle"], a["title"]) for a in data.get("articles", [])]


def post_article(result):
    """
    Create a hidden Shopify article with full metafields.
    result: dict from generator.py with keys: html, meta_description, faqs, slug, title
    Returns Shopify article ID.
    """
    faqs = result.get("faqs", [])

    metafields = [
        {
            "namespace": "global",
            "key": "description_tag",
            "value": result["meta_description"],
            "type": "single_line_text_field",
        }
    ]

    # Add FAQ metafields (up to 3 pairs)
    for i, faq in enumerate(faqs[:3], start=1):
        metafields.append({
            "namespace": "faq",
            "key": f"q{i}",
            "value": faq["q"],
            "type": "single_line_text_field",
        })
        metafields.append({
            "namespace": "faq",
            "key": f"a{i}",
            "value": faq["a"],
            "type": "single_line_text_field",
        })

    payload = {
        "article": {
            "blog_id": int(BLOG_ID),
            "title": result["title"],
            "body_html": result["html"],
            "handle": result["slug"],
            "author": "Nubokind Experts",
            "published": False,
            "metafields": metafields,
        }
    }

    response = _request("POST", "/articles.json", payload)
    article = response["article"]
    shopify_id = article["id"]

    print(f"  Posted to Shopify: '{article['title']}'")
    print(f"  Handle  : {article['handle']}")
    print(f"  ID      : {shopify_id}")
    print(f"  Status  : HIDDEN")
    print(f"  FAQs set: {len(faqs)}")

    return shopify_id


def update_article(shopify_id, result):
    """Update an existing Shopify article with regenerated content."""
    faqs = result.get("faqs", [])

    metafields_payload = [
        {
            "namespace": "global",
            "key": "description_tag",
            "value": result["meta_description"],
            "type": "single_line_text_field",
        }
    ]
    for i, faq in enumerate(faqs[:3], start=1):
        metafields_payload.append({"namespace": "faq", "key": f"q{i}", "value": faq["q"], "type": "single_line_text_field"})
        metafields_payload.append({"namespace": "faq", "key": f"a{i}", "value": faq["a"], "type": "single_line_text_field"})

    payload = {
        "article": {
            "id": shopify_id,
            "title": result["title"],
            "body_html": result["html"],
            "handle": result["slug"],
            "author": "Nubokind Experts",
            "metafields": metafields_payload,
        }
    }

    response = _request("PUT", f"/articles/{shopify_id}.json", payload)
    article = response["article"]

    print(f"  Updated on Shopify: '{article['title']}'")
    print(f"  Handle  : {article['handle']}")
    print(f"  ID      : {shopify_id}")
    print(f"  FAQs set: {len(faqs)}")

    return shopify_id


def get_blog_id():
    """Helper to list all blogs and their IDs."""
    data = _request("GET", "/blogs.json")
    for blog in data.get("blogs", []):
        print(f"ID: {blog['id']} | Title: {blog['title']}")

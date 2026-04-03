"""
main.py
Entry point for the Nubokind blog automation system.
Generates and publishes SEO+AEO+GEO optimized blog posts to Shopify.

Usage:
  python main.py                  # run one batch (POSTS_PER_DAY posts)
  python main.py --dry-run        # generate + save locally, skip Shopify
  python main.py --post 4         # generate + publish a specific post
  python main.py --init-queue     # initialize queue.json from content-calendar.md
  python main.py --status         # print pending/published/failed counts
  python main.py --get-blog-id    # fetch and print all Shopify blog IDs
"""

import argparse
import os
import sys
import time
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent / ".env")

POSTS_PER_DAY = int(os.environ.get("POSTS_PER_DAY", "3"))


def _generate_image(result, spec, skip_images):
    """Call image_generator after blog generation. Silent no-op if skipped."""
    if skip_images:
        return
    try:
        from image_generator import generate_thumbnail
        generate_thumbnail(
            spec=spec,
            html=result["html"],
            product_mode=result.get("product_mode", "bridge"),
            output_dir=result["output_dir"],
        )
    except Exception as e:
        print(f"  [image] Skipped: {e}")


def run_batch(dry_run=False, skip_images=False):
    """Generate and publish the next N posts from the queue."""
    from queue_manager import get_next_posts, mark_published, mark_failed, status
    from research import research_topic
    from generator import generate_blog
    from shopify_client import get_published_posts, post_article

    specs = get_next_posts(POSTS_PER_DAY)

    if not specs:
        print("Queue empty. Add new topics to content-calendar.md.")
        return

    print(f"\n{'='*60}")
    print(f"Nubokind Blog Automation — Batch of {len(specs)} posts")
    if dry_run:
        print("MODE: DRY RUN (no Shopify publish)")
    if skip_images:
        print("IMAGES: skipped (--no-images)")
    print(f"{'='*60}\n")

    # Fetch live published posts once (for related links)
    published_posts = []
    if not dry_run:
        try:
            published_posts = get_published_posts()
            print(f"Fetched {len(published_posts)} published posts from Shopify\n")
        except Exception as e:
            print(f"Warning: Could not fetch published posts: {e}")

    for i, spec in enumerate(specs, 1):
        post_num = spec["post_num"]
        print(f"[{i}/{len(specs)}] Post #{post_num}: {spec['title']}")
        print(f"  Keyword : {spec['primary_kw']}")
        print(f"  Intent  : {spec['intent']} | AEO: {'Yes' if spec.get('aeo') else 'No'}")

        try:
            # Step 1: Research
            print("  Researching topic...")
            research_brief = research_topic(spec["title"], spec["primary_kw"])

            # Step 2: Generate HTML
            print("  Generating blog HTML...")
            result = generate_blog(spec, research_brief, published_posts)
            print(f"  Product mode: {result.get('product_mode', 'unknown')}")

            # Step 3: Generate thumbnail image
            _generate_image(result, spec, skip_images)

            # Step 4: Publish (skip in dry-run)
            if dry_run:
                print(f"  [DRY RUN] Skipping Shopify publish")
                print(f"  HTML length: {len(result['html'])} chars")
                print(f"  FAQs found : {len(result['faqs'])}")
            else:
                shopify_id = post_article(result)
                mark_published(post_num, shopify_id)

        except Exception as e:
            print(f"  ERROR on Post #{post_num}: {e}")
            if not dry_run:
                from queue_manager import mark_failed
                mark_failed(post_num, str(e))

        if i < len(specs):
            print()
            if not dry_run:
                time.sleep(30)  # polite pause between Shopify API calls

    print(f"\n{'='*60}")
    print("Batch complete.")
    if not dry_run:
        status()
    print(f"{'='*60}\n")


def run_single(post_num, dry_run=False, skip_images=False):
    """Generate and publish a single specific post by number."""
    from queue_manager import get_post_spec, mark_published, mark_failed
    from research import research_topic
    from generator import generate_blog
    from shopify_client import get_published_posts, post_article

    print(f"\n{'='*60}")
    print(f"Nubokind Blog Automation — Single Post #{post_num}")
    if dry_run:
        print("MODE: DRY RUN (no Shopify publish)")
    if skip_images:
        print("IMAGES: skipped (--no-images)")
    print(f"{'='*60}\n")

    spec = get_post_spec(post_num)
    print(f"Title   : {spec['title']}")
    print(f"Keyword : {spec['primary_kw']}")
    print(f"Intent  : {spec['intent']} | AEO: {'Yes' if spec.get('aeo') else 'No'}")

    # Fetch live published posts
    published_posts = []
    if not dry_run:
        try:
            published_posts = get_published_posts()
            print(f"Fetched {len(published_posts)} published posts from Shopify\n")
        except Exception as e:
            print(f"Warning: Could not fetch published posts: {e}")

    try:
        print("Researching topic...")
        research_brief = research_topic(spec["title"], spec["primary_kw"])

        print("Generating blog HTML...")
        result = generate_blog(spec, research_brief, published_posts)
        print(f"Product mode: {result.get('product_mode', 'unknown')}")

        _generate_image(result, spec, skip_images)

        if dry_run:
            print(f"\n[DRY RUN] Skipping Shopify publish")
            print(f"HTML length: {len(result['html'])} chars")
            print(f"FAQs found : {len(result['faqs'])}")
            print(f"Meta desc  : {result['meta_description']}")
        else:
            shopify_id = post_article(result)
            mark_published(post_num, shopify_id)
            print(f"\nPost #{post_num} successfully published.")

    except Exception as e:
        print(f"\nERROR: {e}")
        if not dry_run:
            mark_failed(post_num, str(e))
        sys.exit(1)


def _run_update(post_num):
    """Regenerate a post and update the existing Shopify article."""
    from queue_manager import get_post_spec, load_queue
    from research import research_topic
    from generator import generate_blog
    from shopify_client import get_published_posts, update_article

    # Look up existing Shopify ID from queue
    queue = load_queue()
    shopify_id = None
    for entry in queue.get("published", []):
        if isinstance(entry, dict) and entry.get("post_num") == post_num:
            shopify_id = entry.get("shopify_id")
            break

    if not shopify_id:
        print(f"Post #{post_num} not found in published queue. Use --post {post_num} to create it first.")
        return

    print(f"\n{'='*60}")
    print(f"Nubokind Blog Automation — Update Post #{post_num} (Shopify ID: {shopify_id})")
    print(f"{'='*60}\n")

    spec = get_post_spec(post_num)
    print(f"Title   : {spec['title']}")

    published_posts = get_published_posts()
    print(f"Fetched {len(published_posts)} published posts from Shopify\n")

    print("Researching topic...")
    research_brief = research_topic(spec["title"], spec["primary_kw"])

    print("Regenerating blog HTML...")
    result = generate_blog(spec, research_brief, published_posts)

    update_article(shopify_id, result)
    print(f"\nPost #{post_num} updated successfully.")


def main():
    parser = argparse.ArgumentParser(
        description="Nubokind blog automation — generate + publish Shopify blog posts"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Generate and save locally, skip Shopify publish",
    )
    parser.add_argument(
        "--post",
        type=int,
        metavar="N",
        help="Generate + publish a specific post number",
    )
    parser.add_argument(
        "--init-queue",
        action="store_true",
        help="Initialize queue.json from content-calendar.md",
    )
    parser.add_argument(
        "--status",
        action="store_true",
        help="Print pending/published/failed queue counts",
    )
    parser.add_argument(
        "--get-blog-id",
        action="store_true",
        help="Fetch and print all Shopify blog IDs",
    )
    parser.add_argument(
        "--update-post",
        type=int,
        metavar="N",
        help="Regenerate post N and UPDATE the existing Shopify article (looks up ID from queue.json)",
    )
    parser.add_argument(
        "--no-images",
        action="store_true",
        help="Skip thumbnail image generation (useful for testing or if FAL_KEY not set)",
    )

    args = parser.parse_args()

    if args.init_queue:
        from queue_manager import init_queue
        init_queue()

    elif args.status:
        from queue_manager import status
        status()

    elif args.get_blog_id:
        from shopify_client import get_blog_id
        get_blog_id()

    elif args.update_post:
        _run_update(args.update_post)

    elif args.post:
        run_single(args.post, dry_run=args.dry_run, skip_images=args.no_images)

    else:
        run_batch(dry_run=args.dry_run, skip_images=args.no_images)


if __name__ == "__main__":
    main()

"""
image_generator.py
Generates blog thumbnail images using fal.ai (Flux.1 Dev).

Product mode behaviour:
  "featured" + product image exists → fal-ai/flux-general with IP-Adapter
                                       (product image guides colour/shape)
  "featured" + no product image     → fal-ai/flux/dev text-to-image
  "bridge"                           → fal-ai/flux/dev text-to-image
  "none"                             → fal-ai/flux/dev text-to-image (no product in prompt)

Product images live in:  automate/product_images/
  ele-teether.jpg       — Ele Ring Teether (sage green + slate grey)
  kiko-teether.jpg      — Kiko Bear Teether (cream bear)
  my-first-book.jpg     — My First Book Set (cloth books)
  newborn-kit.jpg       — Newborn Essentials Kit

Output:  weekN/<slug>-thumbnail.jpg  (same folder as the HTML file)
"""

import os
import re
import urllib.request
from pathlib import Path

PRODUCT_IMAGES_DIR = Path(__file__).parent / "product_images"

# Map title keywords → product image filename
_PRODUCT_IMAGE_MAP = [
    (["kiko", "bear teether", "no-drop teether"],     "kiko-teether.jpg"),
    (["newborn essentials kit", "newborn kit"],        "newborn-kit.jpg"),
    (["ele", "ring teether"],                          "ele-teether.jpg"),
    # Teether-family posts (broader — catch drooling, amber, gel, BIS, silicone)
    (["teether", "teething", "drool", "amber", "gel",
      "silicone", "bis is 9873", "bis certified"],     "ele-teether.jpg"),
    # Cloth book / visual stimulation posts
    (["cloth book", "high contrast", "visual",
      "flashcard", "my first book", "sensory book"],   "my-first-book.jpg"),
]


def _get_product_image(spec):
    """Return (Path, url_str) for the most relevant product image, or (None, None)."""
    title_lower = spec.get("title", "").lower()
    for keywords, filename in _PRODUCT_IMAGE_MAP:
        if any(k in title_lower for k in keywords):
            path = PRODUCT_IMAGES_DIR / filename
            if path.exists():
                return path, None   # url filled in after upload
    return None, None


def _extract_prompt(html):
    """Extract the text inside <!-- THUMBNAIL PROMPT ... --> from body HTML."""
    match = re.search(
        r'<!--\s*THUMBNAIL PROMPT\s*(.*?)-->',
        html, re.DOTALL | re.IGNORECASE
    )
    if not match:
        return None
    return match.group(1).strip()


def _upload_and_get_url(path):
    """Upload a local file to fal.ai storage and return its URL."""
    import fal_client
    url = fal_client.upload_file(str(path))
    return url


def generate_thumbnail(spec, html, product_mode, output_dir):
    """
    Generate a 1200×630 thumbnail for the blog post.

    Args:
        spec        — post spec dict (needs 'title', 'post_num', 'slug')
        html        — full generated body HTML (contains thumbnail prompt comment)
        product_mode— "featured" | "bridge" | "none"
        output_dir  — Path directory to save the image into

    Returns:
        Path to saved .jpg, or None if generation was skipped / failed.
    """
    # --- Guard: fal-client installed? ---
    try:
        import fal_client
    except ImportError:
        print("  [image] fal-client not installed — run: pip install fal-client")
        return None

    fal_key = os.environ.get("FAL_KEY", "").strip()
    if not fal_key:
        print("  [image] FAL_KEY not set in .env — skipping image generation")
        return None

    os.environ["FAL_KEY"] = fal_key

    # --- Extract prompt ---
    prompt = _extract_prompt(html)
    if not prompt:
        print("  [image] No thumbnail prompt found in HTML — skipping")
        return None

    # --- Choose model + args ---
    product_img_path = None
    if product_mode == "featured":
        product_img_path, _ = _get_product_image(spec)

    try:
        if product_img_path:
            print(f"  [image] Generating with product reference ({product_img_path.name})…")
            product_url = _upload_and_get_url(product_img_path)
            result = fal_client.subscribe(
                "fal-ai/flux-general",
                arguments={
                    "prompt": prompt,
                    "image_size": "landscape_16_9",
                    "num_inference_steps": 28,
                    "guidance_scale": 3.5,
                    "num_images": 1,
                    "enable_safety_checker": True,
                    "ip_adapter": [
                        {
                            "ip_adapter_image_url": product_url,
                            "weight": 0.25,     # low weight — keeps realism, guides product look
                        }
                    ],
                },
            )
        else:
            label = "product (text-only)" if product_mode == "featured" else product_mode
            print(f"  [image] Generating thumbnail ({label})…")
            result = fal_client.subscribe(
                "fal-ai/flux/dev",
                arguments={
                    "prompt": prompt,
                    "image_size": "landscape_16_9",
                    "num_inference_steps": 28,
                    "guidance_scale": 3.5,
                    "num_images": 1,
                    "enable_safety_checker": True,
                },
            )

        image_url = result["images"][0]["url"]

        # --- Save locally ---
        slug = spec.get("slug") or f"post-{spec['post_num']}"
        image_path = Path(output_dir) / f"{slug}-thumbnail.jpg"
        urllib.request.urlretrieve(image_url, str(image_path))
        print(f"  [image] Saved: {image_path.name}")
        return image_path

    except Exception as e:
        print(f"  [image] Generation failed: {e}")
        return None

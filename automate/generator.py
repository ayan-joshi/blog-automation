"""
generator.py
Uses Groq (Llama 3.3 70B) to generate full Shopify-ready blog HTML.
Extracts meta description + FAQ pairs from generated content.
"""

import os
import re
from pathlib import Path
from groq import Groq
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent / ".env")

SYSTEM_PROMPT = (Path(__file__).parent / "prompts" / "system.txt").read_text(encoding="utf-8")
ROOT = Path(__file__).parent.parent


def _build_user_prompt(spec, research_brief, published_posts):
    """Build the user prompt from post spec + research + live posts list."""

    published_list = "\n".join(
        f"- /blogs/early-learning-sensory-development/{h} | {t}"
        for h, t in published_posts[:30]
    ) or "No published posts yet — omit the Related reads section."

    green = ", ".join(spec.get("green_keywords", [])) or "none specified"
    yellow = ", ".join(spec.get("yellow_keywords", [])) or "none specified"
    supporting = ", ".join(spec.get("supporting_keywords", [])) or "none specified"

    intent = spec['intent']
    title_lower = spec['title'].lower()

    # Build a concrete section outline based on intent + topic
    if intent == "TOFU":
        intent_desc = """TOFU — Educational/Awareness.

REQUIRED SECTION OUTLINE (follow exactly, in this order):
<p>[Intro para 1 — answer the core question directly, first 100 words must include green keyword]</p>
<p>[Intro para 2 — IAP/WHO/NICHD citation + specific statistic]</p>
<p>[Intro para 3 — what this post covers]</p>
<nav><h2>In This Guide</h2>...</nav>
<h2 id="[slug]">[Section 1 — core concept explained]</h2>
<h2 id="[slug]">[Section 2 — why it matters / science]</h2>
<h2 id="[slug]">[Section 3 — comparison table or how-to]</h2>
<h2 id="[slug]">[Section 4 — practical tips for Indian parents]</h2>
<h2 id="[slug]">[Section 5 — Nubokind product naturally mentioned]</h2>
<h2 id="faq">Frequently Asked Questions</h2>
[4-5 h3+p FAQ pairs]
<p><strong>Related reads:</strong></p>"""

    elif intent == "MOFU" and any(w in title_lower for w in ['cloth book', 'sensory book', 'visual', 'high contrast', 'black and white', 'flashcard']):
        intent_desc = """MOFU — Comparison/Buying Help for cloth books/visual stimulation.

REQUIRED SECTION OUTLINE (follow exactly, in this order):
<p>[Intro para 1 — verdict: for Indian newborns, cloth books beat flashcards and posters. Name My First Book Set.]</p>
<p>[Intro para 2 — IAP/WHO recommendation + stat: newborns see within 20-30 cm, high contrast activates 2x more neural connections]</p>
<p>[Intro para 3 — what this guide covers]</p>
<nav><h2>In This Guide</h2>...</nav>
<h2 id="why-format-matters">Why Format Matters for Newborn Visual Development</h2>
[150-200 words — newborn vision science, named sources, specific stats]
<h2 id="formats-compared">Cloth Books vs. Flashcards vs. Wall Posters</h2>
[Brief intro sentence, then this EXACT 3-column table:]
<table><thead><tr><th>Format</th><th>Strengths</th><th>Best For</th></tr></thead>
<tbody>
<tr><td>High contrast cloth books</td><td>Visual + tactile + portable, props upright for tummy time</td><td>0–6 months daily use</td></tr>
<tr><td>Flashcards</td><td>Easy to cycle, good for focused sessions</td><td>Structured 5-min sessions</td></tr>
<tr><td>Wall posters</td><td>Passive background stimulation</td><td>Supplementary only</td></tr>
</tbody></table>
[2-3 sentences explaining why cloth books win]
<h2 id="what-makes-best">What Makes the Best Cloth Book for Indian Newborns</h2>
<h3>[Material Safety]</h3>[paragraph]
<h3>[BIS Certification]</h3>[paragraph]
<h3>[High Contrast Pattern Quality]</h3>[paragraph]
<h3>[Tummy Time Design]</h3>[paragraph]
<h2 id="my-first-book-set">Nubokind My First Book Set: In-Depth Look</h2>
[200-250 words — cover all 3 books by name: My First Faces, My First Patterns, My First Puzzles. 100% cotton, saliva-resistant inks, stands upright independently, safe from birth. Link: <a href="/products/high-contrast-cloth-book-set">My First Book Set</a>]
<h2 id="daily-routine">Using High Contrast Books in Your Daily Routine</h2>
[150-200 words — during feeds (hold 25cm from face), tummy time (prop upright), awake windows. Practical, specific to Indian home context]
<h2 id="faq">Frequently Asked Questions</h2>
[4 h3+p pairs — keyword-targeted, no generic questions]
<p><strong>Related reads:</strong></p>"""

    elif intent == "MOFU" and any(w in title_lower for w in ['teether', 'teething', 'chew', 'silicone toy', 'mouthing']):
        intent_desc = """MOFU — Comparison/Buying Help for teether brands.

REQUIRED SECTION OUTLINE (follow exactly, in this order):
<p>[Intro para 1 — verdict upfront: for BIS-certified, Made in India, Nubokind is the clear choice]</p>
<p>[Intro para 2 — why BIS IS 9873 matters + what differentiates Indian market]</p>
<p>[Intro para 3 — what this comparison covers]</p>
<nav><h2>In This Guide</h2>...</nav>
<h2 id="what-makes-safe">What Makes a Safe Teether in India?</h2>
[BIS IS 9873, food-grade silicone, one-piece construction — specific and authoritative]
<h2 id="nubokind">Nubokind — Best for India (BIS Certified, Made in India)</h2>
[mini 2-col table: Feature | Detail — BIS cert CML-7600198513, 100% food-grade silicone, 3-12 months, Made in India]
[Product link: Ele Ring Teether /products/ele-ring-teether-set-green-and-blue and Kiko /products/kiko-bear-teether]
<h2 id="munchkin">Munchkin — Best Import Brand</h2>
[mini table + honest assessment — ASTM F963, NOT BIS IS 9873, widely on Amazon India]
<h2 id="pigeon">Pigeon — Hospital Trust Brand</h2>
[mini table — ST mark, NOT BIS, available in pharmacies]
<h2 id="nuby">Nuby — Best for Variety</h2>
[mini table — CPSC/ASTM, NOT BIS, Amazon/Flipkart]
<h2 id="comparison">Full Brand Comparison</h2>
[3-col table: Brand | BIS IS 9873 | Best For]
<h2 id="verdict">Which Should You Choose?</h2>
[bullet list: if X → choose Y. Clear and direct.]
<h2 id="faq">Frequently Asked Questions</h2>
[4-5 h3+p pairs]
<p><strong>Related reads:</strong></p>"""

    else:
        intent_desc = f"""{intent} — Follow the intent guidance in the system prompt.

REQUIRED STRUCTURE:
<p>[Intro para 1 — answer the main question directly]</p>
<p>[Intro para 2 — named source + statistic]</p>
<p>[Intro para 3 — what this guide covers]</p>
<nav><h2>In This Guide</h2>...</nav>
[5+ H2 sections with anchor IDs, each 150-250 words]
[At least 1 table with 2-3 columns — real data only, no placeholder rows]
<h2 id="faq">Frequently Asked Questions</h2>
[4-5 h3+p pairs — keyword-targeted]
<p><strong>Related reads:</strong></p>"""

    aeo_note = (
        "AEO: YES — include 5 FAQ questions, each a standalone citable answer for AI engines. "
        "Answers must be 2-3 sentences, direct, factual, with named sources where possible."
        if spec.get("aeo")
        else "AEO: Standard — include 4 FAQ questions, sharp and keyword-targeted."
    )

    # Determine which Nubokind product is most relevant to feature
    pillar = spec.get('pillar', '').lower()
    title_lower = spec['title'].lower()
    if any(w in title_lower for w in ['cloth book', 'sensory book', 'visual', 'high contrast', 'black and white', 'flashcard']):
        featured_product = "My First Book Set — 3 cloth books (My First Faces, My First Patterns, My First Puzzles), 100% cotton, saliva-resistant inks, stands upright, safe from birth, 0-6 months. Link: /products/high-contrast-cloth-book-set"
    elif any(w in title_lower for w in ['teether', 'teething', 'chew', 'mouthing', 'silicone toy']):
        featured_product = "Ele Ring Teether (pack of 2, sage green + slate grey elephants, BIS IS 9873 cert CML-7600198513, food-grade silicone, 3-12 months, /products/ele-ring-teether-set-green-and-blue) and Kiko Bear Teether (cream bear, BIS certified, no-drop wrist strap, 3-12 months, /products/kiko-bear-teether)"
    elif any(w in title_lower for w in ['gift', 'essentials', 'kit', 'newborn toy', 'baby toy']):
        featured_product = "Newborn Essentials Kit (high-contrast flashcards + My First Book Set + fold-out zoo book, 0-6 months, /products/high-contrast-newborn-essential-kit) and Ele Ring Teether (/products/ele-ring-teether-set-green-and-blue)"
    else:
        featured_product = "Mention the most relevant product from the Nubokind catalog in the system prompt based on the topic."

    return f"""Write a full Shopify blog post for the following spec. Follow ALL rules from the system prompt.

## Post Brief
- **Title:** {spec['title']}
- **Primary Keyword:** {spec['primary_kw']}
- **Intent:** {intent_desc}
- **{aeo_note}**
- **Pillar:** {spec.get('pillar', '')}

## Featured Nubokind Product for this Post
{featured_product}

## Keywords to Use
- 🟢 GREEN (intro first 100 words + at least one H2 + at least one FAQ answer): {green}
- 🟡 YELLOW (body paragraphs + H2 headings): {yellow}
- ⬜ SUPPORTING (once or twice naturally): {supporting}

## Keyword Placement Notes
{spec.get('placement_notes', 'No specific notes — follow standard keyword placement rules.')}

## Research — Ground the post in these real parent discussions
Use these to shape what questions you answer, what language you use, what concerns you address.
{research_brief}

## Published Posts (use ONLY these handles for Related reads links)
{published_list}

## Output Requirements
1. Start with `<p>` — no H1, no TL;DR, no image tags of any kind
2. H2 headings must have anchor IDs: `<h2 id="slug">Title</h2>`
3. Include Table of Contents after the 2-3 intro paragraphs
4. Write at minimum 5 H2 sections with depth — each section must add value
5. Include at least 1 table (2-3 columns max — NEVER 4+ columns)
6. Do NOT invent competitor brands or use placeholder rows like "Other Brand"
7. FAQ section: `<h2 id="faq">Frequently Asked Questions</h2>` followed by h3+p pairs
8. Related reads using ONLY handles from the published list above (omit if none exist)
9. End the entire output with a FAQPage JSON-LD `<script type="application/ld+json">` block
10. For Nubokind products: link as `<a href="/products/[slug]">Product Name</a>`
11. Target 1,400–1,900 words of body content (not counting JSON-LD)
12. No filler phrases — every sentence must earn its place
"""


def _extract_meta_description(title, primary_kw):
    """Generate a 155-char meta description using the title and keyword."""
    base = f"{title}. Expert guide for Indian parents covering {primary_kw}. BIS-certified product recommendations included."
    return base[:155]


def _extract_faqs(html):
    """Extract first 3 FAQ question+answer pairs from generated HTML."""
    # Find FAQ section (handles id attributes and varied heading text)
    faq_section = re.search(
        r'<h2[^>]*>[^<]*[Ff]requently[^<]*</h2>(.*?)(?=<h2[^>]*>|$)',
        html, re.DOTALL
    )
    if not faq_section:
        return []

    faq_html = faq_section.group(1)
    # Match h3 question followed by p answer (allow any whitespace between)
    pairs = re.findall(
        r'<h3[^>]*>(.*?)</h3>\s*<p[^>]*>(.*?)</p>',
        faq_html, re.DOTALL
    )

    faqs = []
    for q, a in pairs[:3]:
        q_clean = re.sub(r'<[^>]+>', '', q).strip()
        a_clean = re.sub(r'<[^>]+>', '', a).strip()
        if q_clean and a_clean:
            faqs.append({"q": q_clean, "a": a_clean})

    return faqs


def generate_blog(spec, research_brief, published_posts):
    """
    Generate full blog HTML using Groq.
    Returns dict: {html, meta_description, faqs, slug}
    """
    client = Groq(api_key=os.environ["GROQ_API_KEY"])

    user_prompt = _build_user_prompt(spec, research_brief, published_posts)

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.7,
        max_tokens=6000,
    )

    html = response.choices[0].message.content.strip()

    # Strip any accidental markdown code fences
    html = re.sub(r'^```html?\s*', '', html, flags=re.MULTILINE)
    html = re.sub(r'^```\s*$', '', html, flags=re.MULTILINE)
    html = html.strip()

    # Extract thumbnail prompt comment (keep it — goes into Shopify body as HTML comment)
    thumb_match = re.search(r'(<!--\s*THUMBNAIL PROMPT.*?-->)', html, re.DOTALL | re.IGNORECASE)
    thumbnail_comment = thumb_match.group(1).strip() if thumb_match else ""

    # Safety: strip all other image-related blocks that slipped through
    html = re.sub(r'<!--\s*THUMBNAIL PROMPT.*?-->', '', html, flags=re.DOTALL | re.IGNORECASE)
    html = re.sub(r'<!--\s*IMAGE.*?-->', '', html, flags=re.DOTALL)
    html = re.sub(r'<!--.*?[Ii]mage [Pp]rompt.*?-->', '', html, flags=re.DOTALL)
    html = re.sub(r'<figure[^>]*>.*?</figure>', '', html, flags=re.DOTALL)
    html = re.sub(r'<img[^>]*/?>', '', html)

    # Prepend thumbnail comment back at the top of the body
    if thumbnail_comment:
        html = thumbnail_comment + "\n" + html.lstrip()

    # Extract FAQPage JSON-LD schema before stripping from Shopify body
    # Shopify body_html does not execute <script> tags — save separately for local file
    schema_blocks = re.findall(r'<script[^>]*application/ld\+json[^>]*>.*?</script>', html, re.DOTALL)
    schema_html = "\n".join(schema_blocks)
    # Remove script tags from Shopify body
    html = re.sub(r'<script[^>]*application/ld\+json[^>]*>.*?</script>', '', html, flags=re.DOTALL)
    html = html.strip()

    meta_description = _extract_meta_description(spec["title"], spec["primary_kw"])
    faqs = _extract_faqs(html)
    slug = spec.get("slug") or _title_to_slug(spec["title"])

    # Save locally (with schema preserved in local file)
    _save_local(spec, html, meta_description, slug, schema_html)

    return {
        "html": html,
        "meta_description": meta_description,
        "faqs": faqs,
        "slug": slug,
        "title": spec["title"],
        "post_num": spec["post_num"],
    }


def _title_to_slug(title):
    import re as _re
    slug = title.lower()
    slug = _re.sub(r'[^a-z0-9\s-]', '', slug)
    slug = _re.sub(r'\s+', '-', slug.strip())
    slug = _re.sub(r'-+', '-', slug)
    return slug[:80]


def _save_local(spec, html, meta_description, slug, schema_html=""):
    """Save generated blog as local .html file in the correct weekN/ folder."""
    # Determine week from post number using the publish schedule
    week_map = {
        1: 1, 47: 1, 48: 1,
        2: 2, 3: 2, 13: 2,
        37: 3, 41: 3, 42: 3,
        14: 4, 15: 4, 21: 4,
        4: 5, 5: 5, 22: 5,
        29: 6, 30: 6, 33: 6,
        49: 7, 50: 7, 51: 7,
        26: 8, 27: 8, 23: 8,
        57: 9, 58: 9, 59: 9,
        17: 10, 18: 10, 16: 10,
        38: 11, 39: 11, 10: 11,
        62: 12, 61: 12, 35: 12,
    }
    post_num = spec["post_num"]
    week = week_map.get(post_num, (post_num // 3) + 1)
    week_dir = ROOT / f"week{week}"
    week_dir.mkdir(exist_ok=True)

    # Count existing posts in this week dir
    existing = list(week_dir.glob("post*.html"))
    post_idx = len(existing) + 1

    filename = f"post{post_idx}-{slug}.html"
    filepath = week_dir / filename

    schema_section = f"\n\n<!-- FAQPage JSON-LD Schema (add to Shopify theme head or via script tag app) -->\n{schema_html}" if schema_html else ""

    full_html = f"""<!--
  SHOPIFY BLOG POST — AUTO GENERATED
  Title: {spec['title']}
  Meta Description: {meta_description}
  URL Handle: {slug}
  Blog: Early Learning & Sensory Development
  Post Number: #{post_num}
  Thumbnail Prompt: Modern Indian metro home, warm natural light. Indian parent with baby (0-4 months) interacting with relevant Nubokind product. Candid lifestyle photography, 16:9.
-->{schema_section}

<!-- SHOPIFY BODY HTML (paste below into article body) -->
{html}"""

    filepath.write_text(full_html, encoding="utf-8")
    print(f"  Saved locally: {filepath.relative_to(ROOT)}")

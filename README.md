# Nubokind Blog Content — Master Index

**Brand:** nubokind.com | Indian baby products
**Voice:** Warm + Expert
**Cadence:** 2–3 posts/week

---

## Automation Workflows

### Blog workflow
- `python automate/main.py --status`
- `python automate/main.py --dry-run`
- `python automate/main.py --post N`

### Community workflow (Quora + Reddit)
This repo now supports a manual-post community workflow built around weekly search packs.

Phase 1 behavior:
- builds weekly Quora and Reddit search queries from existing blog topics
- creates starter answer drafts for each platform
- exports CSV files that open cleanly in Google Sheets
- keeps posting manual (no autoposting)

Commands:
- `python automate/community_main.py --init-queue`
- `python automate/community_main.py discover --week 1 --per-platform 2`
- `python automate/community_main.py draft --week 1 --limit 2`
- `python automate/community_main.py export --week 1`
- `python automate/community_main.py status --week 1`

Outputs:
- queue state: `automate/community_queue.json`
- prompt rules: `automate/prompts/community_system.txt`
- CSV exports: `community_exports/week-N-quora-reddit.csv`

---

## Folder Structure

```
nubokind-blogs/
├── README.md                    ← This file
├── content-calendar.md          ← Full 62-post calendar with keywords + schedule
├── week1/
│   ├── post1-teething-age-india.md        ✅ Ready to publish
│   ├── post2-silicone-safety.md           ✅ Ready to publish
│   └── post3-cloth-book-intro.md          ✅ Ready to publish
├── week2/   (posts #2, #3, #13)
├── week3/   (posts #37, #41, #42)
├── week4/   (posts #14, #15, #21)
├── week5/   (posts #4, #5, #22)
├── week6/   (posts #29, #30, #33)
├── week7/   (posts #49, #50, #51)
├── week8/   (posts #26, #27, #23)
├── week9/   (posts #57, #58, #59)
├── week10/  (posts #17, #18, #16)
├── week11/  (posts #38, #39, #10)
└── week12/  (posts #62, #61, #35)
```

---

## Week 1 Posts — Published

| File | Title | Shopify URL Slug | Status |
|---|---|---|---|
| post1-teething-age-india.md | What Age Do Babies Start Teething in India? | `what-age-do-babies-start-teething-india` | ✅ Ready |
| post2-silicone-safety.md | Is Silicone Teether Safe for Newborns? | `is-silicone-teether-safe-for-newborns` | ✅ Ready |
| post3-cloth-book-intro.md | When Should I Introduce a Cloth Book to My Baby? | `when-to-introduce-cloth-book-baby-india` | ✅ Ready |

---

## How to Publish in Shopify

1. Go to **Online Store → Blog Posts → Add blog post**
2. Set blog to: `Early Learning & Sensory Development`
3. Paste markdown content (Shopify accepts markdown in the HTML editor)
4. Set the URL handle to the slug in the table above
5. Add meta description from the top of each file
6. Add a featured image (see image concept notes in each post)
7. Set author, tags, and publish date

---

## SEO Checklist Before Publishing Each Post

- [ ] Meta description added (155 chars)
- [ ] URL slug set correctly
- [ ] Featured image with alt text
- [ ] FAQ schema added (Shopify apps: TinyIMG or JSON-LD for SEO)
- [ ] Internal links to product pages working
- [ ] Internal links to 2–3 related blog posts added
- [ ] Tags: relevant (teething, silicone safety, cloth book, etc.)

"""
Phase 2 — Theme Generation & Review Classification (Powered by Groq)

Two-step approach:
  Step 2a — Theme Discovery:  Stratified sample → Groq → 3-5 themes (1 API call)
  Step 2b — Review Classification:  Batched reviews → each assigned to exactly one theme (~4 API calls)
Designed for Groq free tier (12K TPM limit) with 65s cooldown between calls.
"""

import os
import json
import time
import random
from datetime import datetime, date
from groq import Groq
from dotenv import load_dotenv

load_dotenv()


# ─── Configuration ───────────────────────────────────────────────────────────

GROQ_MODEL = "llama-3.3-70b-versatile"
SAMPLE_SIZE = 120               # Stratified sample for theme discovery
BATCH_SIZE = 75                 # Reviews per classification call (~8K tokens)
SLEEP_BETWEEN_CALLS = 65        # 65s > 60s TPM reset window for Groq free tier
RETRY_DELAYS = [65, 65, 65]     # Always wait full TPM window on rate limit
OUTPUT_DIR = "output"


# ─── Prompts ─────────────────────────────────────────────────────────────────

THEME_DISCOVERY_PROMPT = """You are a senior product analyst for the fintech app "INDmoney".

Given these user reviews (a stratified sample across all star ratings), identify exactly 3 to 5 recurring themes.

Rules:
- Each theme must be distinct and non-overlapping.
- Themes should be actionable (useful for product/support teams).
- Do NOT exceed 5 themes.
- Do NOT include any PII.

Return ONLY a valid JSON object — no markdown, no explanation:
{
  "themes": [
    {
      "id": "theme_slug_in_snake_case",
      "label": "Human-Readable Theme Label",
      "description": "One-line description of what users are saying"
    }
  ]
}"""


CLASSIFICATION_PROMPT = """You are a product analyst for "INDmoney".

Here are the themes:
{themes_json}

Classify EACH review below into EXACTLY ONE theme using the theme "id" field.
If a review could fit multiple themes, pick the MOST relevant one.
Every single review MUST be assigned — do NOT skip any.

IMPORTANT: The "review_id" in your response must be an INTEGER matching the # number shown for each review.

Return ONLY a valid JSON object — no markdown, no explanation:
{{
  "classifications": [
    {{"review_id": 1, "theme_id": "theme_slug"}},
    {{"review_id": 2, "theme_id": "theme_slug"}}
  ]
}}

Reviews:
{reviews_text}"""


# ─── Helpers ─────────────────────────────────────────────────────────────────

def _groq_call(client: Groq, system_prompt: str, user_prompt: str, retry_count: int = 0) -> str:
    """Make a Groq API call with retry logic for rate limiting."""
    try:
        response = client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.2,
            max_tokens=8192,
            response_format={"type": "json_object"},
        )
        return response.choices[0].message.content
    except Exception as e:
        error_str = str(e)
        if "429" in error_str or "rate" in error_str.lower():
            if retry_count < len(RETRY_DELAYS):
                delay = RETRY_DELAYS[retry_count]
                print(f"  ⏳ Rate limited. Retrying in {delay}s...")
                time.sleep(delay)
                return _groq_call(client, system_prompt, user_prompt, retry_count + 1)
        raise


def _stratified_sample(reviews: list, n: int) -> list:
    """Create a stratified sample ensuring all star ratings are represented."""
    by_rating = {}
    for r in reviews:
        star = r.get("rating", 0)
        by_rating.setdefault(star, []).append(r)

    sample = []
    ratings = sorted(by_rating.keys())
    per_rating = max(n // len(ratings), 5)

    for star in ratings:
        pool = by_rating[star]
        take = min(per_rating, len(pool))
        sample.extend(random.sample(pool, take))

    used_ids = {r["sr_no"] for r in sample}
    remaining = [r for r in reviews if r["sr_no"] not in used_ids]
    shortfall = n - len(sample)
    if shortfall > 0 and remaining:
        sample.extend(random.sample(remaining, min(shortfall, len(remaining))))

    random.shuffle(sample)
    return sample


def _format_reviews_for_prompt(reviews: list) -> str:
    """Format reviews as text lines for the LLM prompt."""
    lines = []
    for r in reviews:
        lines.append(f"[#{r['sr_no']}] ★{r['rating']} ({r['date']}, {r['source']}): {r['review_text']}")
    return "\n".join(lines)


def _extract_list(parsed, key: str) -> list:
    """Robustly extract a list from a parsed JSON response."""
    if isinstance(parsed, list):
        return parsed
    if isinstance(parsed, dict):
        if key in parsed:
            return parsed[key]
        for v in parsed.values():
            if isinstance(v, list):
                return v
    return []


# ─── Step 2a: Theme Discovery (1 API call) ──────────────────────────────────

def discover_themes(client: Groq, reviews: list) -> list:
    """Send a stratified sample to Groq to discover 3-5 themes."""
    sample = _stratified_sample(reviews, SAMPLE_SIZE)
    print(f"[Phase 2a] Stratified sample: {len(sample)} reviews")

    dist = {}
    for r in sample:
        dist[r["rating"]] = dist.get(r["rating"], 0) + 1
    print(f"  Distribution: {dict(sorted(dist.items()))}")

    user_prompt = (
        f"Here are {len(sample)} user reviews for INDmoney "
        f"(stratified across all star ratings):\n\n"
        + _format_reviews_for_prompt(sample)
    )

    print(f"[Phase 2a] Calling Groq for theme discovery...")
    raw = _groq_call(client, THEME_DISCOVERY_PROMPT, user_prompt)
    themes = _extract_list(json.loads(raw), "themes")

    if not (3 <= len(themes) <= 5):
        themes = themes[:5]

    for t in themes:
        assert all(k in t for k in ("id", "label", "description")), f"Bad theme: {t}"

    print(f"[Phase 2a] ✅ Discovered {len(themes)} themes:")
    for i, t in enumerate(themes, 1):
        print(f"  {i}. [{t['id']}] {t['label']}")

    return themes


# ─── Step 2b: Review Classification (batched, ~4 API calls) ─────────────────

def classify_reviews(client: Groq, reviews: list, themes: list) -> dict:
    """Classify reviews in batches of BATCH_SIZE with 65s cooldown between calls."""
    themes_json = json.dumps(themes, indent=2)
    total = len(reviews)
    num_batches = (total + BATCH_SIZE - 1) // BATCH_SIZE
    all_assignments = []

    print(f"[Phase 2b] Classifying {total} reviews in {num_batches} batches of ~{BATCH_SIZE}")
    print(f"  (65s cooldown between batches for Groq free tier TPM limit)")

    for batch_idx in range(num_batches):
        start = batch_idx * BATCH_SIZE
        end = min(start + BATCH_SIZE, total)
        batch = reviews[start:end]

        user_prompt = CLASSIFICATION_PROMPT.format(
            themes_json=themes_json,
            reviews_text=_format_reviews_for_prompt(batch),
        )

        print(f"  Batch {batch_idx + 1}/{num_batches} (reviews #{batch[0]['sr_no']}–#{batch[-1]['sr_no']})...", end=" ", flush=True)
        raw = _groq_call(client, "You are a product analyst. Return only valid JSON.", user_prompt)

        try:
            assignments = _extract_list(json.loads(raw), "classifications")
        except json.JSONDecodeError:
            print(f"⚠ JSON parse failed, skipping batch")
            assignments = []

        all_assignments.extend(assignments)
        print(f"✅ {len(assignments)}/{len(batch)} classified")

        # Cooldown between batches (skip after last batch)
        if batch_idx < num_batches - 1:
            print(f"  ⏳ Waiting {SLEEP_BETWEEN_CALLS}s for TPM reset...", flush=True)
            time.sleep(SLEEP_BETWEEN_CALLS)

    # Build lookup and group
    review_map = {r["sr_no"]: r for r in reviews}
    theme_ids = {t["id"] for t in themes}
    by_theme = {t["id"]: [] for t in themes}
    classified_ids = set()

    for a in all_assignments:
        rid = a.get("review_id")
        try:
            rid = int(rid)
        except (ValueError, TypeError):
            continue
        tid = a.get("theme_id", "")
        if rid in review_map and tid in theme_ids:
            by_theme[tid].append(review_map[rid])
            classified_ids.add(rid)

    # Handle unclassified → assign to largest theme
    unclassified = [r for r in reviews if r["sr_no"] not in classified_ids]
    if unclassified:
        largest_theme = max(by_theme.keys(), key=lambda k: len(by_theme[k]))
        print(f"[Phase 2b] ⚠ {len(unclassified)} unclassified reviews → '{largest_theme}'")
        by_theme[largest_theme].extend(unclassified)

    print(f"[Phase 2b] ✅ Done ({len(classified_ids)}/{len(reviews)} directly matched):")
    for tid in by_theme:
        label = next((t["label"] for t in themes if t["id"] == tid), tid)
        print(f"  • {label}: {len(by_theme[tid])} reviews")

    return by_theme


# ─── Public API ───────────────────────────────────────────────────────────────

def run_phase2(
    playstore_path: str = "output/playstore_reviews.json",
    appstore_path: str = "output/appstore_reviews.json",
    output_dir: str = OUTPUT_DIR,
    api_key: str = None,
) -> dict:
    """
    Execute Phase 2:
      Call 1: Discover themes from stratified sample (or load cached)
      Calls 2-N: Classify every review in batches of 75
    Designed for Groq free tier (12K TPM limit).
    """
    key = api_key or os.getenv("GROQ_API_KEY")
    if not key:
        raise ValueError("GROQ_API_KEY not found. Set it in .env or pass it directly.")

    client = Groq(api_key=key)
    today = date.today().strftime("%Y-%m-%d")

    # ── Load reviews from both stores ──
    all_reviews = []
    for path, label in [(playstore_path, "Play Store"), (appstore_path, "App Store")]:
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            reviews = data.get("reviews", [])
            print(f"[Phase 2] Loaded {len(reviews)} reviews from {label}")
            all_reviews.extend(reviews)

    if not all_reviews:
        raise ValueError("No reviews found. Run Phase 1 first.")

    # Re-index for consistency
    for i, r in enumerate(all_reviews):
        r["sr_no"] = i + 1

    num_batches = (len(all_reviews) + BATCH_SIZE - 1) // BATCH_SIZE
    total_calls = 1 + num_batches
    total_time = (total_calls - 1) * SLEEP_BETWEEN_CALLS
    print(f"[Phase 2] Total: {len(all_reviews)} reviews | Model: {GROQ_MODEL}")
    print(f"[Phase 2] API calls planned: ~{total_calls} (1 discovery + {num_batches} classification batches)")
    print(f"[Phase 2] Estimated time: ~{total_time // 60}m {total_time % 60}s (due to TPM cooldowns)\n")

    # ── Step 2a: Try to load cached themes first ──
    themes_cache = os.path.join(output_dir, f"themes-{today}.json")
    if os.path.exists(themes_cache):
        with open(themes_cache, "r", encoding="utf-8") as f:
            cached = json.load(f)
        themes = cached.get("themes", [])
        if themes:
            print(f"[Phase 2a] ♻️  Loaded {len(themes)} cached themes from {themes_cache}")
            for i, t in enumerate(themes, 1):
                print(f"  {i}. [{t['id']}] {t['label']}")
        else:
            themes = discover_themes(client, all_reviews)
    else:
        themes = discover_themes(client, all_reviews)

    print(f"\n  ⏳ Waiting {SLEEP_BETWEEN_CALLS}s for TPM reset before classification...", flush=True)
    time.sleep(SLEEP_BETWEEN_CALLS)

    # ── Step 2b ──
    by_theme = classify_reviews(client, all_reviews, themes)

    # ── Save output ──
    os.makedirs(output_dir, exist_ok=True)

    # Themes file
    themes_path = os.path.join(output_dir, f"themes-{today}.json")
    with open(themes_path, "w", encoding="utf-8") as f:
        json.dump({"metadata": {"generated_at": datetime.now().strftime("%d %b %Y, %I:%M %p"),
                                "model": GROQ_MODEL, "total_reviews": len(all_reviews)},
                    "themes": themes}, f, indent=2, ensure_ascii=False)

    # Grouped reviews file
    grouped_output = {
        "metadata": {
            "generated_at": datetime.now().strftime("%d %b %Y, %I:%M %p"),
            "model": GROQ_MODEL,
            "total_reviews": len(all_reviews),
            "classification": "Each review assigned to exactly one theme",
        },
        "themes": themes,
        "by_theme": {},
    }
    for theme in themes:
        tid = theme["id"]
        theme_reviews = by_theme.get(tid, [])
        grouped_output["by_theme"][tid] = {
            "label": theme["label"],
            "description": theme["description"],
            "review_count": len(theme_reviews),
            "reviews": theme_reviews,
        }

    grouped_path = os.path.join(output_dir, f"grouped_reviews-{today}.json")
    with open(grouped_path, "w", encoding="utf-8") as f:
        json.dump(grouped_output, f, indent=2, ensure_ascii=False)

    # Compat copy for Phase 3
    with open(os.path.join(output_dir, "themes.json"), "w", encoding="utf-8") as f:
        json.dump(grouped_output, f, indent=2, ensure_ascii=False)

    print(f"\n[Phase 2] 📁 Saved → {themes_path}")
    print(f"[Phase 2] 📁 Saved → {grouped_path}")

    return grouped_output

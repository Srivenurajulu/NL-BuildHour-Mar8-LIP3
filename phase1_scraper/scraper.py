"""
Phase 1 — Data Extraction & Preprocessing
Scrapes public reviews from Google Play Store and Apple App Store for Indmoney,
cleans PII, filters short reviews, and exports a redacted CSV.
"""

import re
import os
import json
import time
import logging
import pandas as pd
import urllib.request
from datetime import datetime, timedelta
from google_play_scraper import Sort, reviews as gplay_reviews

# Suppress noisy loggers
logging.getLogger("Base").setLevel(logging.WARNING)


# ─── Configuration ───────────────────────────────────────────────────────────

PLAY_STORE_APP_ID = "in.indwealth"

APP_STORE_APP_ID = 1450178837   # Correct ID from iTunes Search API

MAX_REVIEWS = 200          # Final cap after merging both stores
REVIEW_WEEKS = 12          # Look-back window
MIN_WORD_COUNT = 5         # Drop reviews with fewer words


# ─── PII Removal ─────────────────────────────────────────────────────────────

_PII_PATTERNS = [
    (r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b", "[EMAIL_REDACTED]"),
    (r"\b(?:\+?\d{1,3}[-.\s]?)?\(?\d{2,4}\)?[-.\s]?\d{3,4}[-.\s]?\d{3,4}\b", "[PHONE_REDACTED]"),
    (r"\b\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}\b", "[CARD_REDACTED]"),
    (r"\b[A-Z]{5}\d{4}[A-Z]\b", "[PAN_REDACTED]"),
]


def scrub_pii(text: str) -> str:
    """Replace emails, phone numbers, card numbers, and PAN with placeholders."""
    if not isinstance(text, str):
        return ""
    for pattern, replacement in _PII_PATTERNS:
        text = re.sub(pattern, replacement, text)
    return text.strip()


# ─── Play Store Scraper ──────────────────────────────────────────────────────

def fetch_play_store_reviews(weeks: int = REVIEW_WEEKS) -> pd.DataFrame:
    """Fetch recent Google Play Store reviews for Indmoney."""
    print(f"[Phase 1] Fetching Play Store reviews (last {weeks} weeks)...")

    cutoff = datetime.now() - timedelta(weeks=weeks)
    all_reviews = []
    continuation_token = None

    try:
        for sort_order in [Sort.NEWEST, Sort.MOST_RELEVANT]:
            continuation_token = None
            for _ in range(5):  # pagination safety cap
                result, continuation_token = gplay_reviews(
                    PLAY_STORE_APP_ID,
                    lang="en",
                    country="in",
                    sort=sort_order,
                    count=200,
                    continuation_token=continuation_token,
                )
                all_reviews.extend(result)
                if continuation_token is None:
                    break
                time.sleep(1)
            if all_reviews:
                break  # got reviews with this sort order
    except Exception as e:
        print(f"  ❌ Play Store scrape failed: {e}")
        return pd.DataFrame(columns=["text", "rating", "date", "source"])

    df = pd.DataFrame(all_reviews)

    if df.empty:
        print("  ⚠ No Play Store reviews returned (library limitation).")
        return pd.DataFrame(columns=["text", "rating", "date", "source"])

    df = df.rename(columns={"content": "text", "score": "rating", "at": "date"})
    df["source"] = "Play Store"
    df = df[["text", "rating", "date", "source"]]
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df = df[df["date"] >= cutoff]

    print(f"  ✓ {len(df)} Play Store reviews after date filter.")
    return df


# ─── App Store Scraper (Apple RSS Feed) ──────────────────────────────────────

def fetch_app_store_reviews(weeks: int = REVIEW_WEEKS) -> pd.DataFrame:
    """
    Fetch App Store reviews via Apple's public RSS JSON feed.
    The feed returns ~50 reviews per page (up to 10 pages).
    """
    print(f"[Phase 1] Fetching App Store reviews via RSS feed (last {weeks} weeks)...")

    cutoff = datetime.now() - timedelta(weeks=weeks)
    all_entries = []

    for page in range(1, 11):  # Apple RSS supports pages 1-10 (max ~500 reviews)
        url = (
            f"https://itunes.apple.com/in/rss/customerreviews"
            f"/page={page}/id={APP_STORE_APP_ID}/sortBy=mostRecent/json"
        )
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = json.loads(resp.read())

            entries = data.get("feed", {}).get("entry", [])
            if not entries:
                break

            # First entry on page 1 is app metadata, skip it
            review_entries = entries[1:] if page == 1 else entries
            if not review_entries:
                break

            all_entries.extend(review_entries)
            print(f"  Page {page}: +{len(review_entries)} reviews")
            time.sleep(0.5)  # polite pause

        except Exception as e:
            print(f"  ⚠ Page {page} failed: {e}")
            break

    if not all_entries:
        print("  ⚠ No App Store reviews returned.")
        return pd.DataFrame(columns=["text", "rating", "date", "source"])

    # Parse RSS entries into a DataFrame
    rows = []
    for entry in all_entries:
        text = entry.get("content", {}).get("label", "")
        rating = int(entry.get("im:rating", {}).get("label", 0))
        date_str = entry.get("updated", {}).get("label", "")
        rows.append({
            "text": text,
            "rating": rating,
            "date": date_str,
            "source": "App Store",
        })

    df = pd.DataFrame(rows)
    df["date"] = pd.to_datetime(df["date"], errors="coerce", utc=True)
    df["date"] = df["date"].dt.tz_localize(None)
    df = df[df["date"] >= cutoff]

    print(f"  ✓ {len(df)} App Store reviews after date filter.")
    return df


# ─── Preprocessing Pipeline ──────────────────────────────────────────────────

def preprocess(df: pd.DataFrame) -> pd.DataFrame:
    """Clean, filter, and deduplicate the combined review DataFrame."""

    initial_count = len(df)

    # 1. Drop nulls
    df = df.dropna(subset=["text"])

    # 2. Scrub PII
    df["text"] = df["text"].apply(scrub_pii)

    # 3. Filter out short reviews (< 5 words)
    df["word_count"] = df["text"].apply(lambda t: len(t.split()))
    df = df[df["word_count"] >= MIN_WORD_COUNT]
    df = df.drop(columns=["word_count"])

    # 4. Deduplicate by review text
    df = df.drop_duplicates(subset=["text"])

    # 5. Sort by date (newest first) and cap at MAX_REVIEWS
    df = df.sort_values("date", ascending=False).head(MAX_REVIEWS)
    df = df.reset_index(drop=True)

    print(f"[Phase 1] Preprocessing: {initial_count} → {len(df)} reviews "
          f"(removed short/duplicate/empty).")
    return df


# ─── Public API ───────────────────────────────────────────────────────────────

def run_phase1(weeks: int = REVIEW_WEEKS, output_path: str = "output/reviews_sample.csv") -> pd.DataFrame:
    """
    Execute the full Phase 1 pipeline:
      1. Scrape Play Store + App Store
      2. Merge
      3. Preprocess (PII scrub, short-review filter, dedup)
      4. Save separate CSVs per store + combined CSV
    Returns the cleaned DataFrame.
    """
    play_df = fetch_play_store_reviews(weeks)
    app_df = fetch_app_store_reviews(weeks)

    # ── Safety: don't overwrite existing data with empty results ──
    dfs = [df for df in [play_df, app_df] if not df.empty]
    combined = pd.concat(dfs, ignore_index=True) if dfs else pd.DataFrame(columns=["text", "rating", "date", "source"])
    print(f"[Phase 1] Combined raw reviews: {len(combined)}")

    if combined.empty:
        if os.path.exists(output_path) and os.path.getsize(output_path) > 50:
            print("[Phase 1] ⚠ Scrape returned 0 reviews. Keeping existing files intact.")
        else:
            print("[Phase 1] ⚠ No reviews scraped and no existing data found.")
        return pd.DataFrame(columns=["text", "rating", "date", "source"])

    # Ensure output directory exists
    output_dir = os.path.dirname(output_path)
    os.makedirs(output_dir, exist_ok=True)

    # ── Save separate store files (preprocessed individually) ──
    if not play_df.empty:
        play_clean = preprocess(play_df.copy())
        play_path = os.path.join(output_dir, "playstore_reviews.json")
        _save_beautified_json(play_clean, play_path, "Play Store")
        print(f"[Phase 1] 📱 Saved {len(play_clean)} Play Store reviews → {play_path}")

    if not app_df.empty:
        app_clean = preprocess(app_df.copy())
        app_path = os.path.join(output_dir, "appstore_reviews.json")
        _save_beautified_json(app_clean, app_path, "App Store")
        print(f"[Phase 1] 🍎 Saved {len(app_clean)} App Store reviews → {app_path}")

    # ── Combined file ──
    cleaned = preprocess(combined)
    combined_path = output_path.replace(".csv", ".json")
    _save_beautified_json(cleaned, combined_path, "Play Store + App Store")

    # Also save CSV for data portability
    cleaned.to_csv(output_path, index=False)
    print(f"[Phase 1] ✅ Saved {len(cleaned)} combined reviews → {combined_path}")

    return cleaned


def _save_beautified_json(df: pd.DataFrame, filepath: str, source_label: str):
    """Save a DataFrame as a beautifully formatted JSON file."""
    df = df.copy()
    df["date"] = pd.to_datetime(df["date"], errors="coerce").dt.strftime("%d %b %Y")

    reviews = []
    for idx, row in df.iterrows():
        reviews.append({
            "sr_no": int(idx) + 1,
            "review_text": row["text"],
            "rating": int(row["rating"]) if pd.notna(row["rating"]) else None,
            "date": row["date"],
            "source": row["source"],
        })

    output = {
        "metadata": {
            "source": source_label,
            "total_reviews": len(reviews),
            "generated_at": datetime.now().strftime("%d %b %Y, %I:%M %p"),
            "filters_applied": [
                "Reviews with < 5 words removed",
                "PII scrubbed (emails, phones, card/PAN numbers)",
                "Duplicates removed",
            ],
        },
        "reviews": reviews,
    }

    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

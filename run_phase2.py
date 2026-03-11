#!/usr/bin/env python3
"""
Run Phase 2 — Theme Discovery & Review Classification via Groq
Usage:  python run_phase2.py [--api-key YOUR_KEY]
"""

import argparse
from phase2_themes.theme_generator import run_phase2


def main():
    parser = argparse.ArgumentParser(description="Phase 2: Discover themes and classify reviews via Groq")
    parser.add_argument("--playstore", type=str, default="output/playstore_reviews.json",
                        help="Path to Play Store reviews JSON")
    parser.add_argument("--appstore", type=str, default="output/appstore_reviews.json",
                        help="Path to App Store reviews JSON")
    parser.add_argument("--output-dir", type=str, default="output",
                        help="Output directory (default: output)")
    parser.add_argument("--api-key", type=str, default=None,
                        help="Groq API key (falls back to GROQ_API_KEY in .env)")
    args = parser.parse_args()

    result = run_phase2(
        playstore_path=args.playstore,
        appstore_path=args.appstore,
        output_dir=args.output_dir,
        api_key=args.api_key,
    )

    themes = result.get("themes", [])
    by_theme = result.get("by_theme", {})
    total = sum(t["review_count"] for t in by_theme.values())

    print(f"\n{'='*50}")
    print(f"🎯 Phase 2 Complete!")
    print(f"   Themes: {len(themes)}")
    print(f"   Reviews classified: {total}")
    for tid, data in by_theme.items():
        print(f"   • {data['label']}: {data['review_count']} reviews")
    print(f"{'='*50}")


if __name__ == "__main__":
    main()

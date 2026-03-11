#!/usr/bin/env python3
"""
Run Phase 1 — Data Extraction & Preprocessing
Usage:  python run_phase1.py [--weeks 12]
"""

import argparse
from phase1_scraper.scraper import run_phase1


def main():
    parser = argparse.ArgumentParser(description="Phase 1: Scrape & preprocess Indmoney reviews")
    parser.add_argument("--weeks", type=int, default=12, help="Look-back window in weeks (default: 12)")
    parser.add_argument("--output", type=str, default="output/reviews_sample.csv", help="Output CSV path")
    args = parser.parse_args()

    df = run_phase1(weeks=args.weeks, output_path=args.output)
    print(f"\nDone. {len(df)} clean reviews ready for Phase 2.")


if __name__ == "__main__":
    main()

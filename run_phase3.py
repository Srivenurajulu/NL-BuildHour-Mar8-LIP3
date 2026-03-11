#!/usr/bin/env python3
"""
Run Phase 3 — Weekly Pulse Note Generation via Gemini
Usage:  python run_phase3.py [--input output/themes.json] [--api-key YOUR_KEY]
"""

import argparse
from phase3_pulse.pulse_generator import run_phase3


def main():
    parser = argparse.ArgumentParser(description="Phase 3: Generate weekly pulse note via Gemini")
    parser.add_argument("--input", type=str, default="output/themes.json",
                        help="Path to grouped themes JSON from Phase 2")
    parser.add_argument("--output-dir", type=str, default="output",
                        help="Output directory (default: output)")
    parser.add_argument("--api-key", type=str, default=None,
                        help="Gemini API key (falls back to GEMINI_API_KEY in .env)")
    args = parser.parse_args()

    result = run_phase3(
        input_path=args.input,
        output_dir=args.output_dir,
        api_key=args.api_key,
    )

    print(f"\n{'='*50}")
    print(f"🎯 Phase 3 Complete!")
    print(f"   Email Subject: {result['email_subject']}")
    print(f"   Pulse Note: {len(result['pulse_note'].split())} words")
    print(f"{'='*50}")
    print(f"\n--- PULSE NOTE PREVIEW ---\n")
    print(result["pulse_note"])


if __name__ == "__main__":
    main()

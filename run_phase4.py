#!/usr/bin/env python3
"""
Run Phase 4 — Email Delivery
Usage:  python run_phase4.py --to recipient@example.com
"""

import argparse
from phase4_email.email_sender import run_phase4


def main():
    parser = argparse.ArgumentParser(description="Phase 4: Send weekly pulse note via email")
    parser.add_argument("--to", type=str, required=True,
                        help="Recipient email address")
    parser.add_argument("--input", type=str, default="output/pulse_output-{today}.json",
                        help="Path to Phase 3 pulse output JSON")
    parser.add_argument("--output-dir", type=str, default="output",
                        help="Output directory for .eml fallback")
    args = parser.parse_args()

    result = run_phase4(
        input_path=args.input,
        recipient=args.to,
        output_dir=args.output_dir,
    )

    print(f"\n{'='*50}")
    print(f"📧 Phase 4 Complete!")
    print(f"   Subject: {result['subject']}")
    print(f"   Recipient: {result['recipient']}")
    if result["sent_via_smtp"]:
        print(f"   ✅ Sent via SMTP")
    else:
        print(f"   ⚠ SMTP not configured or failed")
    print(f"   📎 Backup .eml: {result['eml_path']}")
    print(f"{'='*50}")


if __name__ == "__main__":
    main()

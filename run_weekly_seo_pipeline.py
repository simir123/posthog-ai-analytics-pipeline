"""
run_weekly_seo_pipeline.py
──────────────────────────
Production entry point for the weekly SEO report pipeline.

Runs the three stages in sequence and fails fast if any stage fails.
Uses sys.executable so it always runs inside the current Python environment.

Usage:
    python run_weekly_seo_pipeline.py
"""

import subprocess
import sys
from datetime import datetime


STAGES = [
    ("Fetch PostHog metrics",  "fetch_metrics.py"),
    ("Generate PDF report",    "run_report_generation.py"),
    ("Post report to Slack",   "post_to_slack.py"),
]


def run() -> None:
    start = datetime.utcnow()
    print("=" * 60)
    print(f"Weekly SEO Pipeline  —  {start.strftime('%Y-%m-%d %H:%M UTC')}")
    print("=" * 60)

    for label, script in STAGES:
        print(f"\n[→] {label}")
        print(f"    running: python {script}")
        print("-" * 40)

        try:
            subprocess.run([sys.executable, script], check=True)
            print(f"[✓] {label} — done")
        except subprocess.CalledProcessError as e:
            print(f"\n[✗] Pipeline failed at: {label}")
            print(f"    Script   : {script}")
            print(f"    Exit code: {e.returncode}")
            sys.exit(e.returncode)

    elapsed = (datetime.utcnow() - start).seconds
    print("\n" + "=" * 60)
    print(f"Pipeline complete in {elapsed}s — report posted to Slack.")
    print("=" * 60)


if __name__ == "__main__":
    run()

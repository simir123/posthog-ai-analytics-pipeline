"""
post_to_slack.py
────────────────
Posts the weekly SEO report PDF to a Slack channel.

Reads SLACK_BOT_TOKEN and SLACK_CHANNEL_ID from environment.
Uses slack-sdk (pip install slack-sdk).

Usage:
    python post_to_slack.py
"""

import os
import sys
from datetime import datetime
from env_config import get_env

REPORT_PATH = "posthog_ai_report.pdf"


def post_report() -> None:
    try:
        from slack_sdk import WebClient
        from slack_sdk.errors import SlackApiError
    except ImportError:
        print("ERROR: slack-sdk is not installed. Run: pip install slack-sdk")
        sys.exit(1)

    token   = get_env("SLACK_BOT_TOKEN")
    channel = get_env("SLACK_CHANNEL_ID")

    if not os.path.exists(REPORT_PATH):
        print(f"ERROR: report file not found: {REPORT_PATH}")
        print("Make sure run_report_generation.py completed successfully before running this script.")
        sys.exit(1)

    client = WebClient(token=token)

    date_label = datetime.utcnow().strftime("%B %d, %Y")
    message = (
        f"*Arka Weekly SEO Report — {date_label}*\n"
        "Automated report from PostHog analytics. "
        "Full breakdown attached below."
    )

    try:
        print(f"Uploading {REPORT_PATH} to Slack...")
        client.files_upload_v2(
            channel=channel,
            file=REPORT_PATH,
            filename=f"arka_seo_report_{datetime.utcnow().strftime('%Y-%m-%d')}.pdf",
            initial_comment=message,
        )
        print("Report posted to Slack successfully.")
    except SlackApiError as e:
        error = e.response.get("error", "unknown_error")
        print(f"ERROR: Slack API returned an error: {error}")
        if error == "not_in_channel":
            print("Hint: invite the bot to the channel first with /invite @<bot-name>")
        elif error == "invalid_auth":
            print("Hint: check that SLACK_BOT_TOKEN is correct and not expired")
        sys.exit(1)


if __name__ == "__main__":
    post_report()

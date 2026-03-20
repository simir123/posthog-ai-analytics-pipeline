"""
env_config.py
─────────────
Shared helper for loading required environment variables.
Raises a clear error immediately if a required variable is missing,
rather than failing silently later with a cryptic auth error.

Usage:
    from env_config import get_env

    API_KEY = get_env("POSTHOG_PERSONAL_API_KEY")
"""

import os
from dotenv import load_dotenv

load_dotenv()


def get_env(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise ValueError(
            f"Missing required environment variable: {name}\n"
            f"  → For local dev: add it to your .env file\n"
            f"  → For GitHub Actions: add it as a repository secret"
        )
    return value

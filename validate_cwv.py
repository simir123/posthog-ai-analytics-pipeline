"""
validate_cwv.py
───────────────
Standalone validation script for Core Web Vitals via Google PageSpeed Insights API.
Run this BEFORE integrating CWV into the main analytics pipeline.

Usage:
    python validate_cwv.py
"""

import os
import time
import requests
from dotenv import load_dotenv

load_dotenv()

# ── Config ────────────────────────────────────────────────────────────────────

API_KEY  = os.getenv("PAGESPEED_API_KEY")
API_URL  = "https://www.googleapis.com/pagespeedonline/v5/runPagespeed"
STRATEGY = "mobile"
DEBUG    = True

# Testing one URL first to confirm the request layer works
URLS_TO_TEST = [
    "https://arka.com",
    # Uncomment once the above succeeds:
    # "https://arka.com/products/custom-mailer-boxes",
    # "https://arka.com/collections/custom-boxes",
]

TIMEOUT             = 90   # seconds — PSI can be slow for real URLs
RETRY_ATTEMPTS      = 3
RETRY_DELAY         = 2    # seconds between retries
DELAY_BETWEEN_CALLS = 1    # seconds between different URLs


# ── Metric classification ─────────────────────────────────────────────────────

def _lcp_grade(ms):
    if ms is None:   return "N/A"
    if ms < 2500:    return "Good"
    if ms <= 4000:   return "Needs Improvement"
    return "Poor"

def _cls_grade(score):
    if score is None:  return "N/A"
    if score < 0.1:    return "Good"
    if score <= 0.25:  return "Needs Improvement"
    return "Poor"

def _inp_grade(ms):
    if ms is None:   return "N/A"
    if ms < 200:     return "Good"
    if ms <= 500:    return "Needs Improvement"
    return "Poor"


# ── Suspicious value checks ───────────────────────────────────────────────────

def _check_suspicious(lcp_ms, cls, inp_ms):
    flags = []
    if lcp_ms is not None and lcp_ms > 10_000:
        flags.append(f"  SUSPICIOUS: LCP={lcp_ms}ms is unrealistically high (>10s)")
    if cls is not None and cls > 1.0:
        flags.append(f"  INVALID: CLS={cls} exceeds maximum possible value of 1.0")
    if inp_ms is not None and inp_ms > 2_000:
        flags.append(f"  SUSPICIOUS: INP={inp_ms}ms is unrealistically high (>2s)")
    return flags


# ── Metric extraction ─────────────────────────────────────────────────────────

def _extract_metrics(metrics_dict):
    """Pull p75 values for LCP, CLS, INP from a CrUX metrics dict."""
    def _p75(key):
        return metrics_dict.get(key, {}).get("percentile")

    lcp_ms = _p75("LARGEST_CONTENTFUL_PAINT_MS")
    cls    = _p75("CUMULATIVE_LAYOUT_SHIFT_SCORE")
    inp_ms = _p75("INTERACTION_TO_NEXT_PAINT")

    # CrUX stores CLS as integer × 100 in some API versions — normalize
    if cls is not None and cls > 10:
        cls = cls / 100.0

    return lcp_ms, cls, inp_ms


# ── API fetch with retry ──────────────────────────────────────────────────────

def fetch_cwv(url):
    """
    Fetches CrUX field data from PageSpeed Insights for the given URL.

    Returns a result dict with keys:
        lcp_ms, cls, inp_ms  — metric values (None if unavailable)
        source               — "page-level field data" | "origin-level field data" | "no field data"
        error                — None or string description
        outcome              — "success" | "timeout" | "http_error" | "no_page_data" | "no_origin_data"
    """
    if not API_KEY:
        raise ValueError(
            "PAGESPEED_API_KEY not set. Add it to your .env file:\n"
            "  PAGESPEED_API_KEY=your_key_here"
        )

    params = {
        "url":      url,
        "key":      API_KEY,
        "strategy": STRATEGY,
        "fields":   "loadingExperience,originLoadingExperience,id",
    }

    # Print full request URL in debug mode so we can verify param formatting
    if DEBUG:
        req = requests.Request("GET", API_URL, params=params).prepare()
        # Mask the key in output — show only the last 6 chars
        safe_url = req.url.replace(API_KEY, f"...{API_KEY[-6:]}")
        print(f"  [debug] request URL: {safe_url}")

    last_exc = None
    for attempt in range(1, RETRY_ATTEMPTS + 1):
        try:
            if DEBUG and attempt > 1:
                print(f"  [debug] retry attempt {attempt}/{RETRY_ATTEMPTS}")

            resp = requests.get(API_URL, params=params, timeout=TIMEOUT)

            if DEBUG:
                print(f"  [debug] HTTP status: {resp.status_code}")

            if resp.status_code != 200:
                preview = resp.text[:500]
                return {
                    "lcp_ms": None, "cls": None, "inp_ms": None,
                    "source":  "no field data",
                    "error":   f"HTTP {resp.status_code}",
                    "outcome": "http_error",
                    "detail":  preview,
                }

            data = resp.json()

            # ── Try page-level field data first ──────────────────────────────
            le = data.get("loadingExperience", {})
            le_metrics = le.get("metrics")
            if le_metrics:
                lcp_ms, cls, inp_ms = _extract_metrics(le_metrics)
                if any(v is not None for v in (lcp_ms, cls, inp_ms)):
                    return {
                        "lcp_ms": lcp_ms, "cls": cls, "inp_ms": inp_ms,
                        "source":  "page-level field data",
                        "error":   None,
                        "outcome": "success",
                    }

            # ── Fallback: origin-level field data ─────────────────────────────
            ole = data.get("originLoadingExperience", {})
            ole_metrics = ole.get("metrics")
            if ole_metrics:
                lcp_ms, cls, inp_ms = _extract_metrics(ole_metrics)
                if any(v is not None for v in (lcp_ms, cls, inp_ms)):
                    return {
                        "lcp_ms": lcp_ms, "cls": cls, "inp_ms": inp_ms,
                        "source":  "origin-level field data",
                        "error":   None,
                        "outcome": "success",
                    }

            # ── No metrics in either location ─────────────────────────────────
            has_le  = "loadingExperience"       in data
            has_ole = "originLoadingExperience" in data
            if not has_le and not has_ole:
                outcome = "no_page_data"
                msg     = "Neither loadingExperience nor originLoadingExperience present in response"
            elif not has_le:
                outcome = "no_page_data"
                msg     = "loadingExperience absent; originLoadingExperience present but empty"
            else:
                outcome = "no_origin_data"
                msg     = "loadingExperience present but metrics dict is empty — page likely has insufficient traffic"

            return {
                "lcp_ms": None, "cls": None, "inp_ms": None,
                "source":  "no field data",
                "error":   msg,
                "outcome": outcome,
            }

        except requests.exceptions.Timeout as exc:
            last_exc = exc
            print(f"  TIMEOUT on attempt {attempt}/{RETRY_ATTEMPTS} — waiting {RETRY_DELAY}s")
            if attempt < RETRY_ATTEMPTS:
                time.sleep(RETRY_DELAY)

        except requests.exceptions.RequestException as exc:
            # Non-timeout network error — don't retry
            return {
                "lcp_ms": None, "cls": None, "inp_ms": None,
                "source":  "no field data",
                "error":   f"Network error: {exc}",
                "outcome": "timeout",
            }

    # All retries exhausted
    return {
        "lcp_ms": None, "cls": None, "inp_ms": None,
        "source":  "no field data",
        "error":   f"Timed out after {RETRY_ATTEMPTS} attempts ({TIMEOUT}s each)",
        "outcome": "timeout",
    }


# ── Per-URL reporting ─────────────────────────────────────────────────────────

def _short_url(url):
    for prefix in ("https://arka.com", "http://arka.com"):
        if url.startswith(prefix):
            return url[len(prefix):] or "/"
    return url


def report_url(url, result):
    short   = _short_url(url)
    outcome = result["outcome"]

    print(f"\nURL: {short}")

    if DEBUG:
        print(f"  [debug] data source: {result['source']}")
        print(f"  [debug] outcome:     {outcome}")

    # ── Distinct outcome handling ─────────────────────────────────────────────
    if outcome == "timeout":
        print(f"  ERROR (timeout): {result['error']}")
        return False

    if outcome == "http_error":
        print(f"  ERROR (HTTP): {result['error']}")
        print(f"  Response preview:\n{result.get('detail', '')}")
        return False

    if outcome in ("no_page_data", "no_origin_data"):
        print(f"  No field data available: {result['error']}")
        return False

    # ── Success path ─────────────────────────────────────────────────────────
    lcp_ms = result["lcp_ms"]
    cls    = result["cls"]
    inp_ms = result["inp_ms"]

    if lcp_ms is not None:
        print(f"  LCP: {lcp_ms:,} ms ({_lcp_grade(lcp_ms)})")
    else:
        print("  LCP: No field data available (likely low traffic page)")

    if cls is not None:
        print(f"  CLS: {cls:.3f} ({_cls_grade(cls)})")
    else:
        print("  CLS: No field data available (likely low traffic page)")

    if inp_ms is not None:
        print(f"  INP: {inp_ms:,} ms ({_inp_grade(inp_ms)})")
    else:
        print("  INP: No field data available (likely low traffic page)")

    for flag in _check_suspicious(lcp_ms, cls, inp_ms):
        print(flag)

    return True


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    print("=" * 60)
    print("Core Web Vitals — Validation Script")
    print(f"Strategy: {STRATEGY.upper()}  |  Debug: {DEBUG}  |  Timeout: {TIMEOUT}s")
    print("=" * 60)

    if not API_KEY:
        print("\nFATAL: PAGESPEED_API_KEY not found in environment.")
        print("Add PAGESPEED_API_KEY=<your_key> to your .env file and retry.")
        return

    total   = len(URLS_TO_TEST)
    valid   = 0
    timed_out  = 0
    http_error = 0
    no_data    = 0

    for i, url in enumerate(URLS_TO_TEST):
        print(f"\nFetching ({i + 1}/{total}): {url}")
        try:
            result   = fetch_cwv(url)
            has_data = report_url(url, result)

            outcome = result["outcome"]
            if has_data:
                valid += 1
            elif outcome == "timeout":
                timed_out += 1
            elif outcome == "http_error":
                http_error += 1
            else:
                no_data += 1

        except ValueError as exc:
            print(f"\nFATAL: {exc}")
            return
        except Exception as exc:
            print(f"  ERROR: Unexpected exception — {exc}")
            no_data += 1

        if i < total - 1:
            time.sleep(DELAY_BETWEEN_CALLS)

    # ── Summary ───────────────────────────────────────────────────────────────
    print("\n" + "=" * 60)
    print("Core Web Vitals validation complete")
    print(f"  Pages tested:          {total}")
    print(f"  Successful (with data):{valid}")
    print(f"  Timed out:             {timed_out}")
    print(f"  HTTP errors:           {http_error}")
    print(f"  No field data:         {no_data}")

    if timed_out > 0:
        print("\n  RESULT: Request timed out.")
        print("  The API key works in the browser but not here — check:")
        print("    - Firewall / proxy blocking outbound HTTPS to googleapis.com")
        print("    - Corporate VPN intercepting TLS")
        print(f"    - Try: curl -s \"{API_URL}?url=https://arka.com&key=...\" from this machine")
    elif http_error > 0:
        print("\n  RESULT: API returned a non-200 response — check key permissions or quota.")
    elif valid == 0:
        print("\n  RESULT: Request succeeded but no CWV field data returned.")
        print("  Pages may have insufficient CrUX traffic (need ~1k real visits/month).")
        print("  Origin-level data (arka.com as a whole) should still be available.")
    elif valid < total:
        print(f"\n  RESULT: Partial data ({valid}/{total} pages). Expected for low-traffic pages.")
    else:
        print(f"\n  RESULT: All {total} pages returned valid CWV data. Pipeline ready.")


if __name__ == "__main__":
    main()

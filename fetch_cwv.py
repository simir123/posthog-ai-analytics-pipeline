"""
fetch_cwv.py
────────────
Core Web Vitals fetcher using the Google PageSpeed Insights API.

Fetches CWV (LCP, CLS, INP) for a list of page paths using CrUX field data.
Tries page-level data first; falls back to origin-level if page-level is unavailable.

Called by fetch_metrics.fetch_core_web_vitals().
"""

import os
import time
import requests
import pandas as pd
from env_config import get_env

PSI_API_KEY    = get_env("PAGESPEED_API_KEY")
PSI_URL        = "https://www.googleapis.com/pagespeedonline/v5/runPagespeed"
STRATEGY       = "mobile"
BASE_DOMAIN    = "https://arka.com"
TIMEOUT        = 90    # PSI runs Lighthouse on a real URL — can be slow
RETRY_ATTEMPTS = 3
RETRY_DELAY    = 2     # seconds between retries
CALL_DELAY     = 1     # seconds between successful sequential calls


# ── Metric grading ─────────────────────────────────────────────────────────────

def lcp_label(ms):
    if ms is None:  return "No Data"
    if ms < 2500:   return "Good"
    if ms <= 4000:  return "Needs Improvement"
    return "Poor"

def cls_label(score):
    if score is None:  return "No Data"
    if score < 0.1:    return "Good"
    if score <= 0.25:  return "Needs Improvement"
    return "Poor"

def inp_label(ms):
    if ms is None:  return "No Data"
    if ms < 200:    return "Good"
    if ms <= 500:   return "Needs Improvement"
    return "Poor"

def overall_cwv_status(lcp_l, cls_l, inp_l):
    """Worst-case status across the three metrics."""
    labels = {lcp_l, cls_l, inp_l} - {"No Data"}
    if not labels:
        return "No Data"
    if "Poor" in labels:
        return "Poor"
    if "Needs Improvement" in labels:
        return "Needs Improvement"
    return "Good"


# ── Metric extraction ──────────────────────────────────────────────────────────

def _extract_metrics(metrics_dict):
    """
    Pull p75 values for LCP, CLS, INP from a CrUX metrics dict.
    Returns (lcp_ms, cls, inp_ms) — each is int/float or None.
    """
    def _p75(key):
        return metrics_dict.get(key, {}).get("percentile")

    lcp_ms = _p75("LARGEST_CONTENTFUL_PAINT_MS")
    cls    = _p75("CUMULATIVE_LAYOUT_SHIFT_SCORE")
    inp_ms = _p75("INTERACTION_TO_NEXT_PAINT")

    # CrUX stores CLS as integer × 100 in some API versions — normalize to 0-1 range
    if cls is not None and cls > 10:
        cls = round(cls / 100.0, 3)

    return lcp_ms, cls, inp_ms


# ── Single-page PSI fetch with retry ──────────────────────────────────────────

def _fetch_one(full_url):
    """
    Fetch CWV for a single URL from PSI.

    Returns: (lcp_ms, cls, inp_ms, source)
      source is one of: "page-level" | "origin-level" | "no data"

    Never raises — errors are printed and treated as no data.
    """
    if not PSI_API_KEY:
        raise ValueError(
            "PAGESPEED_API_KEY not set in .env. "
            "Add PAGESPEED_API_KEY=<your_key> and retry."
        )

    params = {
        "url":      full_url,
        "key":      PSI_API_KEY,
        "strategy": STRATEGY,
        "fields":   "loadingExperience,originLoadingExperience,id",
    }

    for attempt in range(1, RETRY_ATTEMPTS + 1):
        try:
            resp = requests.get(PSI_URL, params=params, timeout=TIMEOUT)

            if resp.status_code != 200:
                print(f"    PSI HTTP {resp.status_code} for {full_url}: {resp.text[:200]}")
                return None, None, None, "no data"

            data = resp.json()

            # ── Try page-level CrUX field data ────────────────────────────────
            le            = data.get("loadingExperience", {})
            le_metrics    = le.get("metrics")
            # PSI sets origin_fallback=True when the page has insufficient traffic
            # and returns origin-wide averages inside loadingExperience instead.
            # Treat those as origin-level, not page-level.
            origin_fallback = le.get("origin_fallback", False)

            if le_metrics and not origin_fallback:
                lcp_ms, cls, inp_ms = _extract_metrics(le_metrics)
                if any(v is not None for v in (lcp_ms, cls, inp_ms)):
                    return lcp_ms, cls, inp_ms, "page-level"

            # ── Origin-level fallback — either explicit or via origin_fallback ─
            # Check originLoadingExperience first (more explicit), then
            # fall back to loadingExperience with origin_fallback=True.
            ole_metrics = data.get("originLoadingExperience", {}).get("metrics")
            if ole_metrics:
                lcp_ms, cls, inp_ms = _extract_metrics(ole_metrics)
                if any(v is not None for v in (lcp_ms, cls, inp_ms)):
                    return lcp_ms, cls, inp_ms, "origin-level"

            if le_metrics and origin_fallback:
                lcp_ms, cls, inp_ms = _extract_metrics(le_metrics)
                if any(v is not None for v in (lcp_ms, cls, inp_ms)):
                    return lcp_ms, cls, inp_ms, "origin-level"

            # Neither source had metric data
            return None, None, None, "no data"

        except requests.exceptions.Timeout:
            print(f"    Timeout (attempt {attempt}/{RETRY_ATTEMPTS}) for {full_url}")
            if attempt < RETRY_ATTEMPTS:
                time.sleep(RETRY_DELAY)

        except requests.exceptions.RequestException as exc:
            print(f"    Network error for {full_url}: {exc}")
            return None, None, None, "no data"

    print(f"    All {RETRY_ATTEMPTS} retries exhausted for {full_url}")
    return None, None, None, "no data"


# ── Public API ─────────────────────────────────────────────────────────────────

def fetch_cwv_for_pages(paths, verbose=True):
    """
    Given a list of URL paths (e.g. ["/", "/products/custom-mailer-boxes"]),
    fetches CWV from PSI for each page and returns a DataFrame.

    Paths may be plain paths ("/products/...") or full URLs ("https://arka.com/...").
    """
    rows  = []
    total = len(paths)

    for i, path in enumerate(paths):
        # Normalize: ensure we have both a clean path and a full URL
        if str(path).startswith("http"):
            full_url = str(path)
            clean_path = full_url
            for prefix in (BASE_DOMAIN, "https://www.arka.com", "http://arka.com"):
                if full_url.startswith(prefix):
                    clean_path = full_url[len(prefix):].rstrip("/") or "/"
                    break
        else:
            clean_path = ("/" + str(path).lstrip("/")).rstrip("/") or "/"
            full_url   = BASE_DOMAIN + clean_path

        if verbose:
            print(f"  CWV [{i + 1}/{total}]: {clean_path}")

        lcp_ms, cls, inp_ms, source = _fetch_one(full_url)

        ll = lcp_label(lcp_ms)
        cl = cls_label(cls)
        il = inp_label(inp_ms)

        rows.append({
            "page_path":          clean_path,
            "full_url":           full_url,
            "cwv_source":         source,
            "lcp_ms":             lcp_ms,
            "lcp_label":          ll,
            "cls":                round(cls, 3) if cls is not None else None,
            "cls_label":          cl,
            "inp_ms":             inp_ms,
            "inp_label":          il,
            "overall_cwv_status": overall_cwv_status(ll, cl, il),
        })

        if i < total - 1:
            time.sleep(CALL_DELAY)

    return pd.DataFrame(rows)


# ── Standalone run for debugging ───────────────────────────────────────────────

if __name__ == "__main__":
    test_paths = [
        "/",
        "/products/custom-mailer-boxes",
        "/collections/custom-boxes",
    ]
    print("Running fetch_cwv.py in standalone debug mode...")
    df = fetch_cwv_for_pages(test_paths)
    print("\nResults:")
    print(df.to_string(index=False))

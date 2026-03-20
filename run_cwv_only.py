"""
run_cwv_only.py
───────────────
Re-fetches Core Web Vitals only, without re-running the full pipeline.

Prerequisite: data/top_landing_pages_organic.csv must exist.
If it doesn't, run fetch_metrics.py first.

Usage:
    python run_cwv_only.py
"""

import os
import sys
import pandas as pd
from urllib.parse import urlparse
from fetch_cwv import fetch_cwv_for_pages

LP_PATH  = os.path.join("data", "top_landing_pages_organic.csv")
CWV_PATH = os.path.join("data", "core_web_vitals.csv")

_CWV_COLS = ["page_path", "full_url", "cwv_source",
             "lcp_ms", "lcp_label", "cls", "cls_label",
             "inp_ms", "inp_label", "overall_cwv_status"]

print("=" * 60)
print("CWV-only refresh")
print("=" * 60)

# ── Pre-flight check ──────────────────────────────────────────────────────────
if not os.path.exists(LP_PATH):
    print(f"\nFATAL: {LP_PATH} not found.")
    print("Run fetch_metrics.py first to generate landing page data.")
    sys.exit(1)

lp_df = pd.read_csv(LP_PATH)
print(f"\nLanding pages available: {len(lp_df)} rows")
print("Top 5 URLs:")
for url in lp_df["url"].head(5).tolist():
    print(f"  {url}")

# ── Extract unique canonical paths ───────────────────────────────────────────
lp_df = lp_df.sort_values("organic_sessions", ascending=False).head(10)
seen, paths = set(), []
for url in lp_df["url"].tolist():
    try:
        p = urlparse(str(url)).path.rstrip("/") or "/"
    except Exception:
        p = str(url)
    if p not in seen:
        seen.add(p)
        paths.append(p)

print(f"\n{len(paths)} unique paths to fetch:")
for p in paths:
    print(f"  {p}")

# ── Fetch CWV from PSI ────────────────────────────────────────────────────────
print("\nStarting PSI fetch (this takes ~1-2 min)...")
df = fetch_cwv_for_pages(paths, verbose=True)
print(f"\nPSI returned {len(df)} rows")

empty = pd.DataFrame({c: [] for c in _CWV_COLS})

if df.empty:
    print("WARNING: no data returned — writing empty CSV")
    empty.to_csv(CWV_PATH, index=False)
    sys.exit(1)

# Sort: Poor → Needs Improvement → Good → No Data
status_order = {"Poor": 0, "Needs Improvement": 1, "Good": 2, "No Data": 3}
df["_sort"] = df["overall_cwv_status"].map(status_order).fillna(4)
df = df.sort_values("_sort").drop(columns=["_sort"])

df[_CWV_COLS].to_csv(CWV_PATH, index=False)

# ── Verify ────────────────────────────────────────────────────────────────────
print("\n" + "=" * 60)
print("Verification")
print("=" * 60)
check = pd.read_csv(CWV_PATH)
print(f"File:    {os.path.abspath(CWV_PATH)}")
print(f"Rows:    {len(check)}")
print(f"Columns: {list(check.columns)}")
print(f"\nStatus breakdown:")
print(check["overall_cwv_status"].value_counts().to_string())
print(f"\nSource breakdown:")
print(check["cwv_source"].value_counts().to_string())
print(f"\nResults:")
print(check[["page_path", "lcp_ms", "lcp_label", "cls", "cls_label",
             "inp_ms", "inp_label", "overall_cwv_status", "cwv_source"]].to_string(index=False))
print("\nSUCCESS: Run run_report_generation.py to rebuild the PDF.")

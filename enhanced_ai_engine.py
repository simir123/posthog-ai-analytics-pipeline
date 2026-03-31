import os
import re
import time
import requests
import pandas as pd
from env_config import get_env

GROQ_API_KEY = get_env("GROQ_API_KEY")
env_model = os.environ.get("GROQ_MODEL", "llama-3.1-8b-instant")
GROQ_MODEL = env_model

SYSTEM_PROMPT = """You are a senior SEO analyst writing a weekly report for Arka, a Shopify-based company selling custom eco-friendly packaging (mailer boxes, shipping boxes, poly mailers, inserts, carton boxes). You write inline annotations for data sections — NOT a standalone report.

Business context:
- Primary conversion funnel: Product Viewed (PDP pageviews) → add_to_cart → checkout_started → order_completed
- "Product Viewed" is measured as $pageview events on /products/* URLs, NOT the custom product_viewed event. This gives a comprehensive count of all product detail page loads.
- Methodology change: reports before 2026-03-31 used the custom product_viewed event which undercounted true product views. View-based metrics (product views, view-to-cart rates) in older reports are not directly comparable.
- Separate "request a quote" flow for custom/bulk orders (/pages/custom-order) and free sample requests (/pages/free-sample)
- Key SEO pages: /products/custom-mailer-boxes, /products/custom-shipping-boxes, /products/custom-poly-mailer, /collections/custom-boxes, /collections/custom-ecommerce-packaging
- "Boxes by size" pages are high-intent long-tail pages — traffic changes there are commercially significant
- Blog serves as content marketing and SEO; posts driving organic traffic are top-of-funnel assets
- WAU counts unique users in the 7-day window — do not sum DAU to get WAU
- Organic bounce rate benchmark for B2B packaging: 40-55% typical, 65%+ is a problem
- Cart abandonment ~70% is industry average; checkout abandonment ~25-35% is typical
- Organic conversion rate benchmark: 1-4% for e-commerce
- $$_posthog_breakdown_other_$$ rows are PostHog internal buckets — ignore them
- web-pixels and sandbox URLs are internal test pages — ignore them
- Revenue $0 or near-zero means tracking was not yet active — flag as data gap, not business failure
- Core Web Vitals and 404 tracking were enabled 2026-03-18 — data before that date does not exist

OUTPUT RULES — follow these exactly:
1. MAX 4 sentences total. No exceptions.
2. No headings, bullet points, subheadings, or lists. Plain paragraph only.
3. Lead with the single most important takeaway.
4. Only mention metrics that are anomalous, broken, or actionable. Skip flat/expected numbers.
5. If something looks like a tracking issue ($0 revenue, 0% conversions), say so in one sentence.
6. Never restate numbers already visible in the chart — interpret what they mean instead.
7. Make recommendations specific: "Add structured data to the top 5 product pages" not "optimize product pages".
8. Do not use bold markdown (**text**) or any markdown formatting.

BANNED PHRASES — never use these:
"warrants further investigation", "it's essential to", "as a packaging e-commerce company",
"for a business like Arka", "data quality appears to be good", "upon closer inspection",
"this could be due to various reasons", "no obvious errors or anomalies", "at first glance",
"which is a concern", "further investigation is needed", "this dataset shows/appears to",
"This is critical for Arka", "this is a concern", "it seems", "it appears", "might be",
"could potentially", "it's worth noting", "may suggest", "suggests a potential",
"could indicate", "may indicate", "no issues are reported", "no issues detected".
Prefer direct declarative language: "X increased", "CLS is causing layout instability",
"This indicates a tracking issue" — not "This suggests there may be a potential issue"."""

os.makedirs("data", exist_ok=True)

_SECTION_HINTS = {
    # SEO core sections
    "Traffic & Engagement":                "Focus on: organic growth rate vs last week and last month, new vs returning split health, and whether session duration suggests engaged landing pages or high bounce intent.",
    "Top Landing Pages by Organic Traffic":"Focus on: which product/collection pages are gaining or losing organic share, any pages that should rank higher but don't appear, and whether the top pages are converting.",
    "Organic Conversions & Revenue":       "CRITICAL: first assess whether conversion data is trustworthy. If counts are zero or implausibly low, state it bluntly. If data looks valid, focus on which conversion type drives most value and which product pages punch above their traffic weight.",
    "Top Blog Posts by Organic Traffic":   "Focus on: are blog posts driving packaging-relevant traffic or pure informational queries with no conversion potential? Any posts gaining unusual traffic deserve a note.",
    "Page-Level Traffic Changes WoW":      "Focus on: only pages with >20% change AND >10 sessions. Call out whether gains are product pages (high value) or blog/other (lower value). Drops on product/collection pages are urgent.",
    "Collection Pages Performance":        "Focus on: which collections are growing or declining organically, and whether organic share is shifting. Flag any collection with >20% organic drop.",
    "Boxes by Size Pages":                 "Focus on: are these high-intent long-tail pages trending up or down in aggregate? Call out any individual page with unusual movement. State whether the segment is improving, flat, or declining.",
    "Technical SEO Issues":                "Focus on: (1) 404s with high hits or Google referrer — if a deleted product/collection page is getting 404 hits, say so explicitly. (2) CWV: 'Needs Improvement' IS a real issue — never write 'no issues reported' when pages are in the Needs Improvement range. Call out which metric (LCP/CLS/INP) is most widespread, name the specific grades, and recommend one concrete fix. CLS causing layout instability and LCP causing slow perceived loads are actionable. State whether values are page-level or origin-level CrUX. Do not write vague CWV commentary.",
    # Appendix sections
    "Supporting Product / UX Insights":    "",
    "User Activity":                       "Focus on: did engagement trend up or down, and is the WoW change significant enough to act on?",
    "Referrers by Traffic":                "Focus on: channel mix shifts and whether any non-direct channels are converting.",
    "E-Commerce Conversion Funnel":        "Focus on: where the biggest drop-off is in the funnel and the cart-to-checkout vs checkout-to-order rates. Note: Product Viewed now counts all PDP pageviews (/products/*), so view-to-cart drop-off rates are more accurate than prior reports.",
    "Top Viewed Products":                 "Focus on: which products have high views but low conversion. Product views now use PDP pageviews for comprehensive coverage.",
    "Popup Performance Metrics":           "Focus on: are the popups helping or hurting — compare click rate to dismissal rate and flag if they're net negative.",
    "Daily Revenue":                       "Focus on: revenue trend shape this week and whether spikes/dips correlate with traffic patterns.",
    "Average Order Value":                 "Focus on: is the AOV increase sustainable or driven by a few large orders?",
    "Abandonment Rates":                   "Focus on: cart abandonment rate vs industry benchmark (~70%) and whether it's improving.",
    "Conversion Rate by Referrer":         "Focus on: why direct traffic converts best — is this a tracking issue or a real pattern?",
    # Legacy label aliases kept so old CSVs still work if run_report_generation is not updated
    "Organic Traffic Overview":            "Focus on: organic growth rate, new vs returning split, and session duration vs e-commerce benchmarks (2-4 min).",
    "Organic Conversions":                 "CRITICAL: first check whether conversion data is trustworthy (is count_this_week > 0?). If all zeros, flag as likely tracking issue. Do not write a confident analysis on empty data.",
    "Organic Revenue":                     "Focus on: if revenue data is actually being captured. If it's $0 or very low, flag as a tracking issue — don't analyze empty data.",
    "Organic Product Conversions":         "Focus on: which product pages convert organic visitors and whether high-traffic pages have proportionally low conversions.",
    "404 Errors":                          "Focus on: which 404s have real user impact (high hit count or from Google). If data is sparse (tracking just enabled), say so.",
    "Bounce Rate":                         "Focus on: is organic bounce rate healthy vs industry benchmarks, and is the WoW/MoM trend improving or worsening?",
    "Rage Clicks by URL":                  "Focus on: the top 2-3 pages with the most rage clicks and what likely UX issue is causing them.",
}

def trim_analysis(text, max_chars=500):
    """Safety net: truncate AI analysis to ~4 sentences if it exceeds target length."""
    if not text or len(text) <= max_chars:
        return text
    truncated = text[:max_chars]
    last_period = truncated.rfind('.')
    if last_period > 50:
        return truncated[:last_period + 1]
    return truncated

# Sections that include week-over-week comparisons get the directional context block injected.
_WOW_SECTIONS = {
    "User Activity",
    "Traffic & Engagement",
    "Organic Traffic Overview",   # legacy alias
    "Daily Revenue",
    "Abandonment Rates",
}

def _dir(a, b):
    """Return 'INCREASED' or 'DECREASED' or 'UNCHANGED' comparing a (previous) to b (current)."""
    if a is None or b is None:
        return "UNKNOWN"
    try:
        a, b = float(a), float(b)
    except (TypeError, ValueError):
        return "UNKNOWN"
    if b > a:
        return "INCREASED"
    if b < a:
        return "DECREASED"
    return "UNCHANGED"

def _pct_change(a, b):
    """Return formatted percentage change string, e.g. '+12.3%' or '-5.1%'."""
    try:
        a, b = float(a), float(b)
        if a == 0:
            return "N/A"
        change = (b - a) / abs(a) * 100
        sign = "+" if change >= 0 else ""
        return f"{sign}{change:.1f}%"
    except (TypeError, ValueError):
        return "N/A"

def _build_wow_context():
    """
    Pre-calculate directional comparisons for all WoW metrics and return a plain-text
    context block to inject into the AI prompt. Prevents the LLM from making numerical
    comparison errors (e.g. claiming 22% is lower than 20.8%).
    """
    lines = ["Directional context (pre-calculated — use these exact directions, do not recompute):"]

    # Organic sessions
    try:
        df = pd.read_csv("data/organic_sessions.csv")
        tw = df[df["period"] == "this_week"].iloc[0]
        lw = df[df["period"] == "last_week"].iloc[0]
        for col, label in [
            ("organic_sessions",        "Organic sessions"),
            ("organic_visitors",        "Organic unique visitors"),
            ("total_sessions",          "Total sessions"),
            ("total_visitors",          "Total unique visitors"),
            ("organic_pct_of_sessions", "Organic % of total sessions"),
        ]:
            if col in df.columns:
                direction = _dir(lw[col], tw[col])
                change    = _pct_change(lw[col], tw[col])
                lines.append(f"- {label}: {direction} from {lw[col]} (last week) to {tw[col]} (this week) ({change})")
    except Exception:
        pass

    # DAU weekly average
    try:
        dau_tw = pd.read_csv("data/dau.csv")["dau"].mean()
        dau_lw = pd.read_csv("data/dau_previous.csv")["dau"].mean()
        direction = _dir(dau_lw, dau_tw)
        change    = _pct_change(dau_lw, dau_tw)
        lines.append(f"- Average DAU: {direction} from {dau_lw:.0f} (last week avg) to {dau_tw:.0f} (this week avg) ({change})")
    except Exception:
        pass

    # Revenue weekly total
    try:
        rev_tw = pd.read_csv("data/revenue.csv")["revenue"].sum()
        rev_lw = pd.read_csv("data/revenue_previous.csv")["revenue"].sum()
        direction = _dir(rev_lw, rev_tw)
        change    = _pct_change(rev_lw, rev_tw)
        lines.append(f"- Total weekly revenue: {direction} from ${rev_lw:,.2f} (last week) to ${rev_tw:,.2f} (this week) ({change})")
    except Exception:
        pass

    # Abandonment rates
    for fname, label in [
        ("data/cart_abandonment.csv",     "Cart abandonment rate"),
        ("data/checkout_abandonment.csv", "Checkout abandonment rate"),
    ]:
        try:
            df = pd.read_csv(fname)
            # Expect a column containing 'rate' or 'abandonment'
            rate_col = next((c for c in df.columns if "rate" in c.lower() or "abandon" in c.lower()), None)
            period_col = next((c for c in df.columns if "period" in c.lower() or "week" in c.lower()), None)
            if rate_col and period_col:
                tw_row = df[df[period_col].astype(str).str.contains("this", case=False)]
                lw_row = df[df[period_col].astype(str).str.contains("last|prev", case=False)]
                if not tw_row.empty and not lw_row.empty:
                    tw_val = tw_row.iloc[0][rate_col]
                    lw_val = lw_row.iloc[0][rate_col]
                    direction = _dir(lw_val, tw_val)
                    change    = _pct_change(lw_val, tw_val)
                    lines.append(f"- {label}: {direction} from {lw_val} (last week) to {tw_val} (this week) ({change})")
        except Exception:
            pass

    if len(lines) == 1:
        return ""  # No data found, don't inject an empty block

    return "\n".join(lines)


def validate_conversion_data():
    """
    Check conversion CSVs for data quality issues.
    Returns a list of warning strings (empty = data looks OK).
    """
    warnings = []
    try:
        df = pd.read_csv("data/organic_conversions.csv")
        combined = df[df["conversion_type"] == "combined"]
        if combined.empty:
            warnings.append("Conversion data file is missing the 'combined' row.")
        else:
            count = int(combined.iloc[0].get("count_this_week", 0))
            if count == 0:
                warnings.append(
                    "All conversion counts are zero this week — organic conversion tracking "
                    "may be incomplete. Verify that order_completed, custom-order pageview, "
                    "and free-sample pageview events are firing in PostHog."
                )
    except Exception:
        warnings.append("Conversion data file (organic_conversions.csv) is missing or unreadable.")

    try:
        df = pd.read_csv("data/organic_revenue.csv")
        row = df.iloc[0]
        rev    = float(row.get("organic_revenue_this_week", 0))
        orders = int(row.get("organic_order_count", 0))
        if rev == 0 and orders == 0:
            warnings.append(
                "Organic revenue is $0 and organic order count is 0 — "
                "revenue tracking or organic attribution may not be working."
            )
        elif rev == 0 and orders > 0:
            warnings.append(
                f"Revenue shows $0 but {orders} organic orders were detected — "
                "total_price property may not be populating on order_completed events."
            )
    except Exception:
        pass

    return warnings


def generate_executive_summary():
    """
    Reads key metric CSVs and returns a deterministic (non-LLM) executive summary
    as a (label, content) tuple compatible with save_pdf().

    Bullet format:  "- Metric: value  (WoW, MoM)"
    Priorities are rules-based, not LLM-generated.
    """
    lines   = []
    priorities = []
    conv_warning = False

    # 1. Organic sessions WoW / MoM
    try:
        df  = pd.read_csv("data/organic_sessions.csv")
        tw  = df[df["period"] == "this_week"].iloc[0]
        org = int(tw["organic_sessions"])
        wow = float(tw["wow_change_percent"]) if pd.notna(tw.get("wow_change_percent")) else None
        mom_row = df[df["period"] == "this_month"]
        mom = (float(mom_row.iloc[0]["mom_change_percent"])
               if not mom_row.empty and pd.notna(mom_row.iloc[0]["mom_change_percent"]) else None)
        wow_str = (f"{'+' if wow >= 0 else ''}{wow:.1f}% vs last week") if wow is not None else "vs last week: unavailable"
        mom_str = (f"{'+' if mom >= 0 else ''}{mom:.1f}% vs last month") if mom is not None else "vs last month: unavailable"
        lines.append(f"- Organic sessions: {org:,}  ({wow_str}, {mom_str})")
    except Exception:
        lines.append("- Organic sessions: data unavailable")

    # 2. Organic conversion rate
    try:
        df       = pd.read_csv("data/organic_conversions.csv")
        combined = df[df["conversion_type"] == "combined"]
        if not combined.empty:
            row   = combined.iloc[0]
            rate  = float(row["conversion_rate"])
            count = int(row.get("count_this_week", 0))
            if count == 0:
                conv_warning = True
                lines.append(
                    "- Organic conversion rate: 0 conversions detected — "
                    "POSSIBLE TRACKING ISSUE, verify conversion events in PostHog"
                )
            else:
                wow = float(row["wow_change_pct"]) if pd.notna(row.get("wow_change_pct")) else None
                wow_str = f", {'+' if wow >= 0 else ''}{wow:.1f}% WoW" if wow is not None else ""
                lines.append(
                    f"- Organic conversion rate: {rate:.2f}%  "
                    f"({count} conversions this week{wow_str})"
                )
        else:
            conv_warning = True
            lines.append("- Organic conversion rate: data unavailable")
    except Exception:
        conv_warning = True
        lines.append("- Organic conversion rate: data unavailable")

    # 3. Organic revenue
    try:
        df  = pd.read_csv("data/organic_revenue.csv")
        row = df.iloc[0]
        rev = float(row["organic_revenue_this_week"])
        wow = float(row["organic_revenue_wow_pct"]) if pd.notna(row.get("organic_revenue_wow_pct")) else None
        pct = float(row["organic_revenue_pct_of_total"]) if pd.notna(row.get("organic_revenue_pct_of_total")) else None
        if rev == 0:
            lines.append("- Organic revenue: $0 — POSSIBLE TRACKING ISSUE (see conversions section)")
        else:
            wow_str = f", {'+' if wow >= 0 else ''}{wow:.1f}% vs last week" if wow is not None else ""
            pct_str = (f"  — organic accounts for approximately {pct:.0f}% of total site revenue this week"
                       if pct is not None else "")
            lines.append(f"- Organic revenue: ${rev:,.2f}{pct_str}{wow_str}")
    except Exception:
        lines.append("- Organic revenue: data unavailable")

    # 4. Biggest traffic winner
    try:
        df = pd.read_csv("data/page_traffic_top_gains.csv")
        if not df.empty:
            top   = df.iloc[0]
            path  = str(top.get("path", "unknown"))[:55]
            pct   = float(top.get("wow_change_pct", 0))
            sess  = int(top.get("sessions_this_week", 0))
            lines.append(f"- Biggest traffic winner: {path}  ({pct:+.0f}% WoW, {sess} sessions)")
        else:
            lines.append("- Biggest traffic winner: no significant gains this week")
    except Exception:
        lines.append("- Biggest traffic winner: data unavailable")

    # 5. Biggest traffic loser
    try:
        df = pd.read_csv("data/page_traffic_top_drops.csv")
        if not df.empty:
            top   = df.iloc[0]
            path  = str(top.get("path", "unknown"))[:55]
            pct   = float(top.get("wow_change_pct", 0))
            sess  = int(top.get("sessions_this_week", 0))
            lines.append(f"- Biggest traffic loser: {path}  ({pct:+.0f}% WoW, {sess} sessions)")
        else:
            lines.append("- Biggest traffic loser: no significant drops this week")
    except Exception:
        lines.append("- Biggest traffic loser: data unavailable")

    # 6. Top converting product page
    try:
        df = pd.read_csv("data/organic_product_conversions.csv")
        df = df[df.get("total_conversions", pd.Series(dtype=int)).fillna(0) > 0]
        if not df.empty:
            top  = df.sort_values("total_conversions", ascending=False).iloc[0]
            slug = str(top["product_slug"])
            tc   = int(top["total_conversions"])
            lines.append(f"- Top converting product (organic): /products/{slug}  ({tc} conversions this week)")
        else:
            lines.append("- Top converting product (organic): insufficient data this week")
    except Exception:
        lines.append("- Top converting product (organic): data unavailable")

    # 7. Top technical issue — 404s
    try:
        df = pd.read_csv("data/404_errors.csv")
        df = df[df["hits"] > 0] if "hits" in df.columns else df
        if not df.empty:
            top  = df.sort_values("hits", ascending=False).iloc[0]
            path = str(top.get("path", "unknown"))[:55]
            hits = int(top.get("hits", 0))
            cat  = str(top.get("category", ""))
            lines.append(f"- Top 404: {path}  ({hits} hits{(', ' + cat) if cat else ''})")
            if hits > 30:
                priorities.append(
                    f"Fix or redirect high-traffic 404: {path[:45]}  ({hits} hits/week)"
                )
        else:
            lines.append("- 404 errors: none detected this week (tracking enabled March 18, 2026)")
    except Exception:
        lines.append("- 404 errors: tracking data unavailable (enabled March 18, 2026)")

    # ── Rules-based Top Priorities ────────────────────────────────────────────

    if conv_warning:
        priorities.insert(
            0,
            "Verify organic conversion tracking — all conversion counts appear at zero or are missing this week"
        )

    # CWV-based priorities
    try:
        cwv_df = pd.read_csv("data/core_web_vitals.csv")
        if not cwv_df.empty:
            poor_pages = cwv_df[cwv_df["overall_cwv_status"] == "Poor"]
            if not poor_pages.empty:
                worst = poor_pages.iloc[0]
                priorities.append(
                    f"Fix CWV: {worst['page_path']} is rated Poor — "
                    f"LCP {worst['lcp_label']}, CLS {worst['cls_label']}, INP {worst['inp_label']}"
                )
            cls_bad = cwv_df[cwv_df["cls_label"].isin(["Poor", "Needs Improvement"])]
            if len(cls_bad) >= 3 and len(priorities) < 3:
                priorities.append(
                    f"Layout stability (CLS) flagged on {len(cls_bad)} pages — "
                    "audit font loading, dynamic content injection, and ad slots"
                )
            lcp_bad = cwv_df[cwv_df["lcp_label"].isin(["Poor", "Needs Improvement"])]
            if len(lcp_bad) >= 3 and len(priorities) < 3:
                priorities.append(
                    f"Load speed (LCP) flagged on {len(lcp_bad)} pages — "
                    "review image optimization, server response time, and render-blocking resources"
                )
    except Exception:
        pass

    # High-traffic product pages with zero conversions (min 20 organic views)
    try:
        df = pd.read_csv("data/organic_product_conversions.csv")
        no_conv = df[(df["organic_views"].fillna(0) >= 20) & (df["total_conversions"].fillna(0) == 0)]
        if not no_conv.empty:
            top   = no_conv.sort_values("organic_views", ascending=False).iloc[0]
            slug  = str(top["product_slug"])
            views = int(top["organic_views"])
            priorities.append(
                f"CRO opportunity: /products/{slug} had {views} organic views but 0 conversions — "
                "review CTA, pricing, or content"
            )
    except Exception:
        pass

    # Boxes-by-size segment declining
    try:
        df  = pd.read_csv("data/size_pages_performance.csv")
        wow_col = next((c for c in df.columns if "wow" in c.lower()), None)
        if wow_col:
            declining = df[pd.to_numeric(df[wow_col], errors='coerce').fillna(0) < -20]
            if not declining.empty:
                priorities.append(
                    "Boxes-by-size segment declining >20% WoW — "
                    "review keyword rankings and on-page content for these long-tail pages"
                )
    except Exception:
        pass

    # Fill remaining slots with defaults if needed
    defaults = [
        "Review top organic landing pages for conversion rate optimization opportunities",
        "Audit collection pages for keyword coverage and internal linking gaps",
        "Check blog content for internal links pointing to high-intent product pages",
    ]
    for d in defaults:
        if len(priorities) >= 3:
            break
        priorities.append(d)
    priorities = priorities[:3]

    # ── Assemble content string ───────────────────────────────────────────────
    content = (
        "\n".join(lines)
        + "\n\nTop Priorities This Week:\n"
        + "\n".join(f"{i + 1}. {p}" for i, p in enumerate(priorities))
    )
    return ("Weekly SEO Executive Summary", content)


def read_csv_summary(path, label):
    if not os.path.exists(path):
        return f"== {label} ==\n[Missing file: {path}]"
    try:
        df = pd.read_csv(path)
        if df.empty:
            return f"== {label} ==\n[File is empty: {path}]"
        # Read all rows (or up to 50 for very large files)
        max_rows = min(len(df), 50)
        csv_data = df.head(max_rows).to_csv(index=False)
        total_rows = len(df)
        summary = f"== {label} ==\n{csv_data}"
        if len(df) > max_rows:
            summary += f"\n... (showing first {max_rows} of {total_rows} rows)"
        return summary
    except Exception as e:
        return f"== {label} ==\n[Error reading file: {e}]"

def generate_section_insights(file_label_pairs):
    insights_per_section = []
    wow_context = _build_wow_context()

    for entry in file_label_pairs:
        path, label = entry

        # Grouped entry: path is a list of (sub_path, sub_label) tuples.
        # All CSVs are combined into one section with one shared AI analysis.
        if isinstance(path, list):
            csv_summary = "\n\n".join(
                read_csv_summary(sub_path, sub_label) for sub_path, sub_label in path
            )
        else:
            csv_summary = read_csv_summary(path, label)

        wow_block = (
            f"\n\n{wow_context}\n"
            if wow_context and label in _WOW_SECTIONS
            else ""
        )

        hint = _SECTION_HINTS.get(label, "")
        hint_line = f"\n\n{hint}" if hint else ""

        # For conversion sections: prepend data quality warnings so the LLM
        # cannot write confident business analysis when tracking is broken.
        conv_warning_block = ""
        if label in ("Organic Conversions & Revenue", "Organic Conversions", "Organic Revenue"):
            warnings = validate_conversion_data()
            if warnings:
                conv_warning_block = (
                    "\n\nDATA QUALITY WARNINGS (do NOT ignore these):\n"
                    + "\n".join(f"- {w}" for w in warnings)
                    + "\nIf any warning above applies, lead your analysis with a clear statement "
                    "that conversion data appears incomplete. Do not write conversion rate "
                    "interpretations as if the numbers are reliable."
                )

        user_prompt = (
            f'Data for the "{label}" section:\n\n'
            + csv_summary
            + wow_block
            + conv_warning_block
            + hint_line
            + "\n\nWrite a 3-4 sentence analysis. Lead with the #1 takeaway. "
            "Only mention metrics that are surprising, actionable, or broken. "
            "Do not restate numbers visible in the chart. Plain text only, no headings or bullets."
        )

        try:
            payload = {
                "model": GROQ_MODEL,
                "messages": [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt}
                ],
                "temperature": 0.4
            }
            response = None
            for _ in range(4):
                response = requests.post(
                    "https://api.groq.com/openai/v1/chat/completions",
                    headers={"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"},
                    json=payload,
                    timeout=60
                )
                if response.status_code == 200:
                    break
                if response.status_code == 429:
                    msg = ""
                    try:
                        msg = response.json().get("error", {}).get("message", "")
                    except Exception:
                        pass
                    match = re.search(r'try again in (\d+\.?\d*)s', msg)
                    wait = float(match.group(1)) + 2 if match else 35
                    print(f"Rate limited for {label}, waiting {wait:.0f}s...")
                    time.sleep(wait)
                else:
                    break

            if response and response.status_code == 200:
                ai_text = trim_analysis(response.json()["choices"][0]["message"]["content"])
                section = f"{csv_summary}\n\n--- AI Insights ---\n{ai_text}"
                insights_per_section.append((label, section))
                time.sleep(12)
            else:
                error_detail = response.text if response else "no response"
                try:
                    error_detail = response.json().get("error", {}).get("message", error_detail)
                except Exception:
                    pass
                print(f"Error for {label}: {response.status_code if response else 'N/A'} - {error_detail}")
                insights_per_section.append((label, f"[Error] {error_detail[:200]}"))
        except Exception as e:
            print(f"Exception for {label}: {str(e)}")
            insights_per_section.append((label, f"[Exception: {str(e)}]"))

    return insights_per_section

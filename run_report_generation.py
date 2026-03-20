
from enhanced_ai_engine import generate_section_insights, generate_executive_summary
from generate_pdf_report import save_pdf

if __name__ == "__main__":
    # ── Section 1: Executive Summary (deterministic, no LLM) ──────────────────
    exec_summary = generate_executive_summary()

    # ── Sections 2–6: SEO core sections (LLM-analyzed) ───────────────────────
    seo_sections = [
        # SECTION 2: Traffic & Engagement
        ([
            ("data/organic_sessions.csv",         "Organic Sessions (WoW + MoM)"),
            ("data/organic_new_vs_returning.csv",  "New vs Returning Organic Users"),
            ("data/organic_session_duration.csv",  "Organic Session Duration"),
            ("data/bounce_rate.csv",               "Bounce Rate"),
        ], "Traffic & Engagement"),
        ("data/top_landing_pages_organic.csv", "Top Landing Pages by Organic Traffic"),

        # SECTION 3: Organic Conversions & Revenue
        ([
            ("data/organic_conversions.csv",         "Organic Conversion Rates"),
            ("data/organic_revenue.csv",             "Organic Revenue"),
            ("data/organic_product_conversions.csv", "Top Converting Products"),
        ], "Organic Conversions & Revenue"),

        # SECTION 4: Content & Blog
        ("data/top_blog_posts.csv", "Top Blog Posts by Organic Traffic"),

        # SECTION 5: Page-Level SEO Insights
        ([
            ("data/page_traffic_top_gains.csv", "Top Traffic Gains"),
            ("data/page_traffic_top_drops.csv", "Top Traffic Drops"),
        ], "Page-Level Traffic Changes WoW"),
        ("data/collection_pages_performance.csv", "Collection Pages Performance"),
        ("data/size_pages_performance.csv",        "Boxes by Size Pages"),

        # SECTION 6: Technical SEO Issues (no Core Web Vitals yet)
        ([
            ("data/404_errors.csv",   "404 Errors"),
            ("data/404_summary.csv",  "404 Summary"),
        ], "Technical SEO Issues"),
    ]

    # ── Section 7: Supporting Appendix (non-SEO analytics) ───────────────────
    appendix_sections = [
        # Appendix divider — rendered as a styled chapter break
        ([], "Supporting Product / UX Insights"),

        # User engagement
        ([
            ("data/dau.csv",          "Daily Active Users (This Week)"),
            ("data/dau_previous.csv", "Daily Active Users (Last Week)"),
            ("data/wau.csv",          "Weekly Active Users"),
        ], "User Activity"),

        # Referrers
        ("data/referrers.csv", "Referrers by Traffic"),

        # E-commerce
        ([
            ("data/product_conversion_funnels.csv", "Per-Product Conversion Funnels"),
            ("data/ecommerce_funnel.csv",            "Overall E-Commerce Funnel"),
        ], "E-Commerce Conversion Funnel"),
        ("data/top_products.csv",  "Top Viewed Products"),
        ("data/popup_metrics.csv", "Popup Performance Metrics"),

        ([
            ("data/revenue.csv",          "Daily Revenue (This Week)"),
            ("data/revenue_previous.csv", "Daily Revenue (Last Week)"),
        ], "Daily Revenue"),
        ("data/aov.csv", "Average Order Value"),
        ([
            ("data/cart_abandonment.csv",     "Cart Abandonment Rate"),
            ("data/checkout_abandonment.csv", "Checkout Abandonment Rate"),
        ], "Abandonment Rates"),
        ("data/referrer_conversion.csv", "Conversion Rate by Referrer"),
    ]

    all_pairs = seo_sections + appendix_sections
    ai_sections = generate_section_insights(all_pairs)

    # Prepend deterministic executive summary
    all_sections = [exec_summary] + ai_sections
    save_pdf(all_sections)

import os
import requests
import pandas as pd
from datetime import datetime
from dotenv import load_dotenv
import matplotlib.pyplot as plt

load_dotenv()

# This is the configuration for the API
project_id = 14686

api_url = os.getenv("POSTHOG_API_URL", "https://us.posthog.com")
api_key = os.getenv("POSTHOG_PERSONAL_API_KEY")

# 
headers = {
    "Authorization": f"Bearer {api_key}",
    "Content-Type": "application/json"
}

os.makedirs("data", exist_ok=True)

# This is the daily active users (DAU)
def fetch_dau():
    print("Fetching Daily Active Users (DAU)")

    # Use the query API with correct TrendsQuery structure
    query = {
        "kind": "TrendsQuery",
        "series": [{"event": "$pageview", "math": "dau"}],
        "interval": "day",
        "dateRange": {"date_from": "-7d"}
    }

    # This sends POST request to the query API
    r = requests.post(f"{api_url}/api/projects/{project_id}/query/", headers=headers, json={"query": query})
    
    # Check if the request was successful 
    if r.status_code != 200:
        print("DAU error:", r.status_code, r.text)
        return
    
    # Extract the result from the response
    result = r.json().get("results", [])
    if not result or len(result) == 0:
        print("DAU: no valid result data.")
        return
    
    # The query API returns results in a different format
    # Extract labels and data from the first result
    first_result = result[0]
    labels = first_result.get("labels", [])
    data = first_result.get("data", [])
    
    if not labels or not data:
        print("DAU: missing labels or data in result.")
        return
    
    # Convert the result into a DataFrame and save it as CSV
    df = pd.DataFrame({
        "date": labels,
        "value": data
    })
    df.to_csv("data/dau.csv", index=False)
    print("DAU saved to data/dau.csv")

def fetch_dau_previous():
    print("Fetching Previous Week DAU")
    query = {
        "kind": "TrendsQuery",
        "series": [{"event": "$pageview", "math": "dau"}],
        "interval": "day",
        "dateRange": {"date_from": "-14d", "date_to": "-7d"}
    }
    r = requests.post(f"{api_url}/api/projects/{project_id}/query/", headers=headers, json={"query": query})
    if r.status_code != 200:
        print("DAU previous error:", r.status_code, r.text)
        pd.DataFrame({"date": [], "value": []}).to_csv("data/dau_previous.csv", index=False)
        return
    result = r.json().get("results", [])
    if not result:
        pd.DataFrame({"date": [], "value": []}).to_csv("data/dau_previous.csv", index=False)
        return
    first = result[0]
    pd.DataFrame({"date": first.get("labels", []), "value": first.get("data", [])}).to_csv("data/dau_previous.csv", index=False)
    print("Previous week DAU saved to data/dau_previous.csv")


def fetch_wau():
    print("Fetching Weekly Active Users (WAU)")

    # Use the query API with correct TrendsQuery structure
    query = {
        "kind": "TrendsQuery",
        "series": [{"event": "$pageview", "math": "weekly_active"}],
        "interval": "week",
        "dateRange": {"date_from": "-7d"}
    }

    # Send POST request to PostHog Query API
    r = requests.post(f"{api_url}/api/projects/{project_id}/query/", headers=headers, json={"query": query})

    # Handle error
    if r.status_code != 200:
        print("WAU error:", r.status_code, r.text)
        return

    # Extract result data
    result = r.json().get("results", [])
    if not result or len(result) == 0:
        print("WAU: no valid result data.")
        return

    # Extract labels and data
    first_result = result[0]
    labels = first_result.get("labels", [])
    data = first_result.get("data", [])

    if not labels or not data:
        print("WAU: missing labels or data in result.")
        return

    # Save result to CSV directly (like DAU)
    df = pd.DataFrame({
        "date": labels,
        "value": data
    })
    df.to_csv("data/wau.csv", index=False)
    print("WAU saved to data/wau.csv")

def fetch_rage_clicks():
    print("Fetching rage clicks")

    # Use the query API with breakdown by URL
    query = {
        "kind": "TrendsQuery",
        "series": [{"event": "$rageclick"}],
        "interval": "day",
        "dateRange": {"date_from": "-7d"},
        "breakdownFilter": {
            "breakdown": "$current_url",
            "breakdown_type": "event"
        }
    }

    # Send POST request to PostHog Query API
    r = requests.post(f"{api_url}/api/projects/{project_id}/query/", headers=headers, json={"query": query})

    # Handle failed response
    if r.status_code != 200:
        print("Rage clicks error:", r.status_code, r.text)
        return

    # Extract result from response
    results = r.json().get("results", [])
    rows = []

    # Process each breakdown entry (each unique URL)
    for entry in results:
        breakdown_value = entry.get("breakdown_value", "unknown")
        data_points = entry.get("data", [])
        total_clicks = sum(data_points) if isinstance(data_points, list) else (data_points if data_points else 0)
        rows.append({
            "url": breakdown_value,
            "rage_clicks": total_clicks
        })

    # Save to CSV
    rows = [r for r in rows if r["url"] != "$$_posthog_breakdown_other_$$"]
    if rows:
        df = pd.DataFrame(rows)
        df.to_csv("data/rage_clicks_by_url.csv", index=False)
        print("Rage clicks saved to data/rage_clicks_by_url.csv")
    else:
        print("Rage clicks: no data found")



def fetch_referrers():
    print("Fetching referrers")

    # Use the query API with breakdown by referrer
    query = {
        "kind": "TrendsQuery",
        "series": [{"event": "$pageview"}],
        "interval": "day",
        "dateRange": {"date_from": "-7d"},
        "breakdownFilter": {
            "breakdown": "$referrer",
            "breakdown_type": "event"
        }
    }

    # Send POST request to PostHog Query API
    r = requests.post(f"{api_url}/api/projects/{project_id}/query/", headers=headers, json={"query": query})

    # Handle failed response
    if r.status_code != 200:
        print("Referrers error:", r.status_code, r.text)
        return

    # Extract results and format into rows
    results = r.json().get("results", [])
    rows = []
    for r in results:
        breakdown_value = r.get("breakdown_value", "unknown")
        data_points = r.get("data", [])
        total = sum(data_points) if isinstance(data_points, list) else (data_points if data_points else 0)
        rows.append({
            "referrer": breakdown_value,
            "total": total
        })

    # Save to CSV
    rows = [r for r in rows if r["referrer"] != "$$_posthog_breakdown_other_$$"]
    if rows:
        df = pd.DataFrame(rows)
        df.to_csv("data/referrers.csv", index=False)
        print("Referrers saved to data/referrers.csv")
    else:
        print("Referrers: no data found")


def fetch_bounce_rate():
    """
    Uses sessions table with native "$is_bounce" field.
    sessions columns: session_id (bare), "$start_timestamp", "$is_bounce",
    "$pageview_count" (all $-prefixed ones need quoting in HogQL).
    Includes overall and organic-specific rates, plus WoW and MoM comparisons.
    Saves data/bounce_rate.csv.
    """
    print("Fetching bounce rate")

    def _overall(date_from_days, date_to_days=None):
        date_where = _organic_date_where(date_from_days, date_to_days)
        q = {"kind": "HogQLQuery", "query": f"""
            SELECT
                count(DISTINCT session_id)                                          AS total_sessions,
                countIf("$is_bounce" = true)                                        AS bounced_sessions,
                round(countIf("$is_bounce" = true)
                      / nullIf(count(DISTINCT session_id), 0) * 100, 2)             AS bounce_rate_pct,
                sum("$pageview_count")                                               AS total_pageviews
            FROM sessions
            WHERE {date_where}
        """}
        r = requests.post(f"{api_url}/api/projects/{project_id}/query/",
                          headers=headers, json={"query": q})
        if r.status_code == 200 and r.json().get("results"):
            row = r.json()["results"][0]
            return int(row[0] or 0), int(row[1] or 0), float(row[2] or 0), int(row[3] or 0)
        print(f"  Bounce rate query error: {r.status_code}", r.text[:200])
        return 0, 0, 0.0, 0

    def _organic(date_from_days, date_to_days=None):
        date_where = _organic_date_where(date_from_days, date_to_days)
        q = {"kind": "HogQLQuery", "query": f"""
            SELECT
                count(DISTINCT session_id)                                          AS organic_sessions,
                countIf("$is_bounce" = true)                                        AS organic_bounced,
                round(countIf("$is_bounce" = true)
                      / nullIf(count(DISTINCT session_id), 0) * 100, 2)             AS organic_bounce_rate
            FROM sessions
            WHERE {date_where}
              AND {_ORGANIC_ENTRY_SQL}
        """}
        r = requests.post(f"{api_url}/api/projects/{project_id}/query/",
                          headers=headers, json={"query": q})
        if r.status_code == 200 and r.json().get("results"):
            row = r.json()["results"][0]
            return int(row[0] or 0), int(row[1] or 0), float(row[2] or 0)
        print(f"  Organic bounce rate query error: {r.status_code}", r.text[:200])
        return 0, 0, 0.0

    total_s, bounced_s, br,     pvs   = _overall(7)
    prev_total, prev_bounced, prev_br, _ = _overall(14, 7)
    mom_total,  mom_bounced,  mom_br,  _ = _overall(30)
    prev_mom_total, _, prev_mom_br,   _  = _overall(60, 30)

    org_s, org_b, org_br       = _organic(7)
    prev_org_s, _, prev_org_br = _organic(14, 7)
    mom_org_s,  _, mom_org_br  = _organic(30)
    prev_mom_org_s, _, prev_mom_org_br = _organic(60, 30)

    wow     = round((br     - prev_br)     / prev_br     * 100, 2) if prev_br     > 0 else None
    mom     = round((mom_br - prev_mom_br) / prev_mom_br * 100, 2) if prev_mom_br > 0 else None
    org_wow = round((org_br - prev_org_br) / prev_org_br * 100, 2) if prev_org_br > 0 else None
    org_mom = round((mom_org_br - prev_mom_org_br) / prev_mom_org_br * 100, 2) if prev_mom_org_br > 0 else None

    pd.DataFrame({
        "metric": [
            "bounce_rate_percent",        "total_sessions",      "bounced_sessions",    "total_pageviews",
            "bounce_rate_last_week",      "bounce_rate_wow_pct", "bounce_rate_mom_pct",
            "organic_bounce_rate_percent","organic_sessions",    "organic_bounced_sessions",
            "organic_bounce_rate_last_week", "organic_bounce_rate_wow_pct", "organic_bounce_rate_mom_pct",
        ],
        "value": [
            br,         total_s,   bounced_s,   pvs,
            prev_br,    wow,       mom,
            org_br,     org_s,     org_b,
            prev_org_br, org_wow,  org_mom,
        ],
    }).to_csv("data/bounce_rate.csv", index=False)
    print(f"Bounce rate: {br:.1f}% overall (WoW: {wow}%), {org_br:.1f}% organic (WoW: {org_wow}%)")


def fetch_popup_metrics():
    """Fetch popup display, interaction, and conversion metrics"""
    print("Fetching popup metrics")
    
    # Track popup displays by popup name/ID
    popup_display_query = {
        "kind": "TrendsQuery",
        "series": [{"event": "popup_shown"}],  # Custom event to track
        "interval": "day",
        "dateRange": {"date_from": "-7d"},
        "breakdownFilter": {
            "breakdown": "popup_name",  # Property: popup_name or popup_id
            "breakdown_type": "event"
        }
    }
    
    r = requests.post(f"{api_url}/api/projects/{project_id}/query/", headers=headers, json={"query": popup_display_query})
    
    popup_data = {}
    if r.status_code == 200:
        results = r.json().get("results", [])
        for entry in results:
            popup_name = entry.get("breakdown_value", "unknown")
            data_points = entry.get("data", [])
            total_displays = sum(data_points) if isinstance(data_points, list) else (data_points if data_points else 0)
            popup_data[popup_name] = {"displays": total_displays, "clicks": 0, "dismissals": 0, "conversions": 0}
    
    # Track popup clicks/interactions
    popup_click_query = {
        "kind": "TrendsQuery",
        "series": [{"event": "popup_clicked"}],  # Custom event
        "interval": "day",
        "dateRange": {"date_from": "-7d"},
        "breakdownFilter": {
            "breakdown": "popup_name",
            "breakdown_type": "event"
        }
    }
    
    r = requests.post(f"{api_url}/api/projects/{project_id}/query/", headers=headers, json={"query": popup_click_query})
    if r.status_code == 200:
        results = r.json().get("results", [])
        for entry in results:
            popup_name = entry.get("breakdown_value", "unknown")
            data_points = entry.get("data", [])
            total_clicks = sum(data_points) if isinstance(data_points, list) else (data_points if data_points else 0)
            if popup_name not in popup_data:
                popup_data[popup_name] = {"displays": 0, "clicks": 0, "dismissals": 0, "conversions": 0}
            popup_data[popup_name]["clicks"] = total_clicks
    
    # Track popup dismissals
    popup_dismiss_query = {
        "kind": "TrendsQuery",
        "series": [{"event": "popup_dismissed"}],  # Custom event
        "interval": "day",
        "dateRange": {"date_from": "-7d"},
        "breakdownFilter": {
            "breakdown": "popup_name",
            "breakdown_type": "event"
        }
    }
    
    r = requests.post(f"{api_url}/api/projects/{project_id}/query/", headers=headers, json={"query": popup_dismiss_query})
    if r.status_code == 200:
        results = r.json().get("results", [])
        for entry in results:
            popup_name = entry.get("breakdown_value", "unknown")
            data_points = entry.get("data", [])
            total_dismissals = sum(data_points) if isinstance(data_points, list) else (data_points if data_points else 0)
            if popup_name not in popup_data:
                popup_data[popup_name] = {"displays": 0, "clicks": 0, "dismissals": 0, "conversions": 0}
            popup_data[popup_name]["dismissals"] = total_dismissals
    
    # Calculate metrics
    rows = []
    for popup_name, metrics in popup_data.items():
        displays = metrics["displays"]
        clicks = metrics["clicks"]
        dismissals = metrics["dismissals"]
        
        # Calculate rates
        click_rate = (clicks / displays * 100) if displays > 0 else 0
        dismissal_rate = (dismissals / displays * 100) if displays > 0 else 0
        engagement_rate = ((clicks + dismissals) / displays * 100) if displays > 0 else 0
        
        rows.append({
            "popup_name": popup_name,
            "total_displays": displays,
            "clicks": clicks,
            "dismissals": dismissals,
            "click_rate_percent": round(click_rate, 2),
            "dismissal_rate_percent": round(dismissal_rate, 2),
            "engagement_rate_percent": round(engagement_rate, 2)
        })
    
    if rows:
        df = pd.DataFrame(rows)
        df = df.sort_values("total_displays", ascending=False)
        df.to_csv("data/popup_metrics.csv", index=False)
        print(f"Popup metrics saved: {len(rows)} popups tracked")
    else:
        # Create empty template if no data
        df = pd.DataFrame({
            "popup_name": [],
            "total_displays": [],
            "clicks": [],
            "dismissals": [],
            "click_rate_percent": [],
            "dismissal_rate_percent": [],
            "engagement_rate_percent": []
        })
        df.to_csv("data/popup_metrics.csv", index=False)
        print("Popup metrics: No popup events found. See popup_tracking_guide.md for setup instructions.")


def fetch_popup_rage_correlation():
    """Analyze correlation between popups and rage clicks"""
    print("Fetching popup-rage click correlation")
    
    # Get rage clicks that occurred within 5 seconds of popup display
    # This requires a custom query or property-based analysis
    # For now, we'll create a placeholder that can be enhanced
    
    try:
        # Query for rage clicks with popup context
        query = {
            "kind": "TrendsQuery",
            "series": [{"event": "$rageclick"}],
            "interval": "day",
            "dateRange": {"date_from": "-7d"}
        }
        
        r = requests.post(f"{api_url}/api/projects/{project_id}/query/", headers=headers, json={"query": query})
        
        total_rage_clicks = 0
        if r.status_code == 200:
            results = r.json().get("results", [])
            if results and len(results) > 0:
                data_points = results[0].get("data", [])
                total_rage_clicks = sum(data_points) if isinstance(data_points, list) else 0
        
        # Estimate correlation (this would need custom properties in PostHog)
        # For now, create a template
        df = pd.DataFrame({
            "metric": [
                "total_rage_clicks",
                "estimated_popup_related_rage_clicks",
                "popup_rage_percentage"
            ],
            "value": [
                total_rage_clicks,
                int(total_rage_clicks * 0.15),  # Estimate 15% of rage clicks are popup-related
                15.0
            ],
            "note": [
                "Total rage clicks in period",
                "Estimated popup-related (requires custom tracking)",
                "Percentage estimate (requires popup_rage property)"
            ]
        })
        df.to_csv("data/popup_rage_correlation.csv", index=False)
        print("Popup-rage correlation saved (estimated - requires custom tracking)")
        
    except Exception as e:
        print(f"Popup-rage correlation error: {e}")


def fetch_popup_conversion_funnel():
    """Track conversion funnel from popup display to conversion"""
    print("Fetching popup conversion funnel")
    
    # This tracks: popup_shown -> popup_clicked -> conversion_event
    # Requires custom events: popup_shown, popup_clicked, and your conversion events
    
    try:
        # Get popup displays
        display_query = {
            "kind": "TrendsQuery",
            "series": [{"event": "popup_shown"}],
            "interval": "day",
            "dateRange": {"date_from": "-7d"}
        }
        
        r = requests.post(f"{api_url}/api/projects/{project_id}/query/", headers=headers, json={"query": display_query})
        total_displays = 0
        if r.status_code == 200:
            results = r.json().get("results", [])
            if results and len(results) > 0:
                data_points = results[0].get("data", [])
                total_displays = sum(data_points) if isinstance(data_points, list) else 0
        
        # Get popup clicks
        click_query = {
            "kind": "TrendsQuery",
            "series": [{"event": "popup_clicked"}],
            "interval": "day",
            "dateRange": {"date_from": "-7d"}
        }
        
        r = requests.post(f"{api_url}/api/projects/{project_id}/query/", headers=headers, json={"query": click_query})
        total_clicks = 0
        if r.status_code == 200:
            results = r.json().get("results", [])
            if results and len(results) > 0:
                data_points = results[0].get("data", [])
                total_clicks = sum(data_points) if isinstance(data_points, list) else 0
        
        # Calculate funnel
        click_through_rate = (total_clicks / total_displays * 100) if total_displays > 0 else 0
        
        df = pd.DataFrame({
            "funnel_stage": ["popup_displayed", "popup_clicked", "conversion"],
            "count": [total_displays, total_clicks, 0],  # Conversion requires custom event
            "conversion_rate_percent": [
                100.0,
                round(click_through_rate, 2),
                0.0  # Requires conversion tracking
            ]
        })
        df.to_csv("data/popup_conversion_funnel.csv", index=False)
        print(f"Popup conversion funnel saved: {total_displays} displays, {total_clicks} clicks ({click_through_rate:.1f}% CTR)")
        
    except Exception as e:
        print(f"Popup conversion funnel error: {e}")


def fetch_ecommerce_funnel():
    print("Fetching e-commerce funnel")

    events = ["product_viewed", "add_to_cart", "checkout_started", "order_completed"]
    rows = []

    for event in events:
        query = {
            "kind": "TrendsQuery",
            "series": [{"event": event}],
            "interval": "day",
            "dateRange": {"date_from": "-7d"}
        }
        r = requests.post(f"{api_url}/api/projects/{project_id}/query/", headers=headers, json={"query": query})
        if r.status_code != 200:
            print(f"Funnel error for {event}:", r.status_code, r.text)
            count = 0
        else:
            results = r.json().get("results", [])
            data_points = results[0].get("data", []) if results else []
            count = sum(data_points) if isinstance(data_points, list) else 0
        rows.append({"event": event, "count": count})

    df = pd.DataFrame(rows)

    # Calculate drop-off rates between steps
    for i in range(1, len(df)):
        prev = df.loc[i - 1, "count"]
        curr = df.loc[i, "count"]
        df.loc[i, "dropoff_rate_percent"] = round((1 - curr / prev) * 100, 2) if prev > 0 else 0
    df.loc[0, "dropoff_rate_percent"] = 0

    df.to_csv("data/ecommerce_funnel.csv", index=False)
    print("E-commerce funnel saved to data/ecommerce_funnel.csv")


def fetch_product_conversion_funnels():
    print("Fetching per-product conversion funnels")

    # Query 1: views and add_to_cart per product
    funnel_query = {
        "kind": "HogQLQuery",
        "query": """
            SELECT
                properties.product_title AS product_title,
                countIf(event = 'product_viewed')  AS views,
                countIf(event = 'add_to_cart')     AS add_to_cart_count,
                round(
                    if(countIf(event = 'product_viewed') > 0,
                       countIf(event = 'add_to_cart') * 100.0 / countIf(event = 'product_viewed'),
                       0),
                    2
                ) AS view_to_cart_rate_pct
            FROM events
            WHERE event IN ('product_viewed', 'add_to_cart')
              AND timestamp >= now() - INTERVAL 7 DAY
              AND properties.product_title IS NOT NULL
              AND properties.product_title != ''
            GROUP BY product_title
            HAVING countIf(event = 'product_viewed') > 0
            ORDER BY views DESC
        """
    }

    # Query 2: order_completed events attributed to a product via distinct_id.
    # order_completed has no product_title property (it's a cart-level event), so we
    # attribute an order to a product when the same user viewed that product in the period.
    orders_query = {
        "kind": "HogQLQuery",
        "query": """
            SELECT pv.product_title, count() AS orders_completed
            FROM events AS oc
            INNER JOIN (
                SELECT DISTINCT distinct_id, properties.product_title AS product_title
                FROM events
                WHERE event = 'product_viewed'
                  AND timestamp >= now() - INTERVAL 7 DAY
                  AND properties.product_title IS NOT NULL
                  AND properties.product_title != ''
            ) AS pv ON oc.distinct_id = pv.distinct_id
            WHERE oc.event = 'order_completed'
              AND oc.timestamp >= now() - INTERVAL 7 DAY
            GROUP BY pv.product_title
        """
    }

    empty_df = pd.DataFrame({
        "product_title": [], "views": [], "add_to_cart_count": [],
        "orders_completed": [], "view_to_cart_rate_pct": [], "view_to_order_rate_pct": []
    })

    r1 = requests.post(f"{api_url}/api/projects/{project_id}/query/", headers=headers, json={"query": funnel_query})
    if r1.status_code != 200:
        print("Product funnels error:", r1.status_code, r1.text)
        empty_df.to_csv("data/product_conversion_funnels.csv", index=False)
        return

    results1 = r1.json().get("results", [])
    if not results1:
        print("Product funnels: no data found")
        empty_df.to_csv("data/product_conversion_funnels.csv", index=False)
        return

    rows = []
    for row in results1:
        rows.append({
            "product_title":         row[0],
            "views":                 int(row[1] or 0),
            "add_to_cart_count":     int(row[2] or 0),
            "view_to_cart_rate_pct": float(row[3] or 0),
        })
    df = pd.DataFrame(rows)
    df = df[~df["product_title"].str.strip().str.lower().eq("test")]

    # Fetch order attribution and merge
    r2 = requests.post(f"{api_url}/api/projects/{project_id}/query/", headers=headers, json={"query": orders_query})
    if r2.status_code == 200:
        orders_map = {row[0]: int(row[1] or 0) for row in r2.json().get("results", [])}
    else:
        print("Order attribution warning:", r2.status_code, "— orders_completed will be 0")
        orders_map = {}

    df["orders_completed"] = df["product_title"].map(orders_map).fillna(0).astype(int)
    df["view_to_order_rate_pct"] = df.apply(
        lambda r: round(r["orders_completed"] / r["views"] * 100, 2) if r["views"] > 0 else 0,
        axis=1
    )

    df = df[["product_title", "views", "add_to_cart_count", "view_to_cart_rate_pct",
             "view_to_order_rate_pct", "orders_completed"]]
    df.to_csv("data/product_conversion_funnels.csv", index=False)
    print(f"Product conversion funnels saved: {len(rows)} products")


def fetch_top_products():
    print("Fetching top viewed products")

    query = {
        "kind": "TrendsQuery",
        "series": [{"event": "product_viewed"}],
        "interval": "day",
        "dateRange": {"date_from": "-7d"},
        "breakdownFilter": {
            "breakdown": "product_title",
            "breakdown_type": "event"
        }
    }

    r = requests.post(f"{api_url}/api/projects/{project_id}/query/", headers=headers, json={"query": query})
    if r.status_code != 200:
        print("Top products error:", r.status_code, r.text)
        return

    results = r.json().get("results", [])
    rows = []
    for entry in results:
        product_title = entry.get("breakdown_value", "unknown")
        data_points = entry.get("data", [])
        total_views = sum(data_points) if isinstance(data_points, list) else 0
        rows.append({"product_title": product_title, "views": total_views})

    rows = [r for r in rows if r["product_title"].strip().lower() != "test"]
    if rows:
        df = pd.DataFrame(rows).sort_values("views", ascending=False)
        df.to_csv("data/top_products.csv", index=False)
        print(f"Top products saved: {len(rows)} products tracked")
    else:
        pd.DataFrame({"product_title": [], "views": []}).to_csv("data/top_products.csv", index=False)
        print("Top products: no data found")


def fetch_revenue():
    print("Fetching revenue from order_completed events")

    query = {
        "kind": "TrendsQuery",
        "series": [{"event": "order_completed", "math": "sum", "math_property": "total_price"}],
        "interval": "day",
        "dateRange": {"date_from": "-7d"}
    }

    r = requests.post(f"{api_url}/api/projects/{project_id}/query/", headers=headers, json={"query": query})
    if r.status_code != 200:
        print("Revenue error:", r.status_code, r.text)
        return

    results = r.json().get("results", [])
    if not results:
        print("Revenue: no data found")
        return

    first_result = results[0]
    labels = first_result.get("labels", [])
    data = first_result.get("data", [])

    df = pd.DataFrame({"date": labels, "revenue": data})
    df.to_csv("data/revenue.csv", index=False)
    print(f"Revenue saved to data/revenue.csv (total: ${sum(data):.2f})")


def fetch_revenue_previous():
    print("Fetching Previous Week Revenue")
    query = {
        "kind": "TrendsQuery",
        "series": [{"event": "order_completed", "math": "sum", "math_property": "total_price"}],
        "interval": "day",
        "dateRange": {"date_from": "-14d", "date_to": "-7d"}
    }
    r = requests.post(f"{api_url}/api/projects/{project_id}/query/", headers=headers, json={"query": query})
    if r.status_code != 200:
        print("Revenue previous error:", r.status_code, r.text)
        pd.DataFrame({"date": [], "revenue": []}).to_csv("data/revenue_previous.csv", index=False)
        return
    results = r.json().get("results", [])
    if not results:
        pd.DataFrame({"date": [], "revenue": []}).to_csv("data/revenue_previous.csv", index=False)
        return
    first = results[0]
    df = pd.DataFrame({"date": first.get("labels", []), "revenue": first.get("data", [])})
    df.to_csv("data/revenue_previous.csv", index=False)
    print(f"Previous week revenue saved (total: ${sum(first.get('data', [])):.2f})")


def fetch_aov():
    """AOV via TrendsQuery (avoids HogQL float-casting issues).
    Saves data/aov.csv with columns: period, total_revenue, order_count, aov.
    """
    print("Fetching Average Order Value (AOV)")

    def _week_aov(date_from, date_to=None):
        dr = {"date_from": date_from}
        if date_to:
            dr["date_to"] = date_to
        r_rev = requests.post(f"{api_url}/api/projects/{project_id}/query/", headers=headers, json={"query": {
            "kind": "TrendsQuery",
            "series": [{"event": "order_completed", "math": "sum", "math_property": "total_price"}],
            "interval": "week", "dateRange": dr
        }})
        r_cnt = requests.post(f"{api_url}/api/projects/{project_id}/query/", headers=headers, json={"query": {
            "kind": "TrendsQuery",
            "series": [{"event": "order_completed"}],
            "interval": "week", "dateRange": dr
        }})
        revenue = sum(r_rev.json()["results"][0]["data"]) if r_rev.status_code == 200 and r_rev.json().get("results") else 0
        orders  = int(sum(r_cnt.json()["results"][0]["data"])) if r_cnt.status_code == 200 and r_cnt.json().get("results") else 0
        aov = round(revenue / orders, 2) if orders > 0 else 0
        return revenue, orders, aov

    this_rev, this_ord, this_aov = _week_aov("-7d")
    prev_rev, prev_ord, prev_aov = _week_aov("-14d", "-7d")

    pd.DataFrame({
        "period":        ["this_week", "last_week"],
        "total_revenue": [this_rev,    prev_rev],
        "order_count":   [this_ord,    prev_ord],
        "aov":           [this_aov,    prev_aov],
    }).to_csv("data/aov.csv", index=False)

    if this_ord > 0:
        print(f"AOV this week: ${this_aov:.2f} ({this_ord} orders, ${this_rev:.2f} revenue)")
    else:
        print("AOV: no order_completed events found this week")


def fetch_cart_abandonment():
    print("Fetching cart abandonment rate")

    q_cart = {"kind": "HogQLQuery", "query": "SELECT uniq(distinct_id) FROM events WHERE event = 'add_to_cart' AND timestamp >= now() - INTERVAL 7 DAY"}
    q_order = {"kind": "HogQLQuery", "query": "SELECT uniq(distinct_id) FROM events WHERE event = 'order_completed' AND timestamp >= now() - INTERVAL 7 DAY"}

    r1 = requests.post(f"{api_url}/api/projects/{project_id}/query/", headers=headers, json={"query": q_cart})
    r2 = requests.post(f"{api_url}/api/projects/{project_id}/query/", headers=headers, json={"query": q_order})

    users_added = int(r1.json()["results"][0][0] or 0) if r1.status_code == 200 else 0
    users_ordered = int(r2.json()["results"][0][0] or 0) if r2.status_code == 200 else 0
    abandoned = max(0, users_added - users_ordered)
    rate = round(abandoned / users_added * 100, 2) if users_added > 0 else 0

    pd.DataFrame({
        "metric": ["users_added_to_cart", "users_completed_order", "users_abandoned", "abandonment_rate_percent"],
        "value": [users_added, users_ordered, abandoned, rate]
    }).to_csv("data/cart_abandonment.csv", index=False)
    print(f"Cart abandonment: {rate}% ({abandoned}/{users_added} users abandoned)")


def fetch_checkout_abandonment():
    print("Fetching checkout abandonment rate")

    q_checkout = {"kind": "HogQLQuery", "query": "SELECT uniq(distinct_id) FROM events WHERE event = 'checkout_started' AND timestamp >= now() - INTERVAL 7 DAY"}
    q_order = {"kind": "HogQLQuery", "query": "SELECT uniq(distinct_id) FROM events WHERE event = 'order_completed' AND timestamp >= now() - INTERVAL 7 DAY"}

    r1 = requests.post(f"{api_url}/api/projects/{project_id}/query/", headers=headers, json={"query": q_checkout})
    r2 = requests.post(f"{api_url}/api/projects/{project_id}/query/", headers=headers, json={"query": q_order})

    users_checked_out = int(r1.json()["results"][0][0] or 0) if r1.status_code == 200 else 0
    users_ordered = int(r2.json()["results"][0][0] or 0) if r2.status_code == 200 else 0
    abandoned = max(0, users_checked_out - users_ordered)
    rate = round(abandoned / users_checked_out * 100, 2) if users_checked_out > 0 else 0

    pd.DataFrame({
        "metric": ["users_started_checkout", "users_completed_order", "users_abandoned", "abandonment_rate_percent"],
        "value": [users_checked_out, users_ordered, abandoned, rate]
    }).to_csv("data/checkout_abandonment.csv", index=False)
    print(f"Checkout abandonment: {rate}% ({abandoned}/{users_checked_out} users abandoned)")



# ── organic traffic helpers ───────────────────────────────────────────────────
# Uses the `sessions` table which has all session-level data pre-computed.
# Column naming on `sessions`:
#   - Plain (no $): session_id, distinct_id
#   - Dollar-prefixed (must be quoted): "$start_timestamp", "$entry_referring_domain",
#     "$is_bounce", "$session_duration", "$pageview_count", "$channel_type"
# JOIN with events: e."$session_id" = s.session_id

_ORGANIC_ENTRY_DOMAINS = [
    'google.com', 'www.google.com',
    'bing.com', 'www.bing.com',
    'yahoo.com', 'search.yahoo.com',
    'duckduckgo.com',
    'baidu.com', 'www.baidu.com',
    'yandex.com', 'yandex.ru',
    'ecosia.org', 'ask.com',
]

# Filter on sessions."$entry_referring_domain" (dollar-prefixed, quoted)
_ORGANIC_ENTRY_SQL = (
    '"$entry_referring_domain" IN ('
    + ', '.join(f"'{d}'" for d in _ORGANIC_ENTRY_DOMAINS)
    + ')'
)

def _organic_date_where(date_from_days, date_to_days=None):
    """Returns a HogQL WHERE fragment for sessions date filtering."""
    if date_to_days is None:
        return f'"$start_timestamp" >= now() - INTERVAL {date_from_days} DAY'
    return (f'"$start_timestamp" >= now() - INTERVAL {date_from_days} DAY '
            f'AND "$start_timestamp" < now() - INTERVAL {date_to_days} DAY')


def fetch_organic_sessions():
    """
    Counts organic sessions and visitors using raw_sessions.$entry_referring_domain.
    Includes WoW (7-day) and MoM (30-day) comparisons.
    Saves data/organic_sessions.csv.
    """
    print("Fetching organic sessions")

    def _query(date_from_days, date_to_days=None):
        date_where = _organic_date_where(date_from_days, date_to_days)
        q = {"kind": "HogQLQuery", "query": f"""
            SELECT
                count(DISTINCT session_id)  AS organic_sessions,
                count(DISTINCT distinct_id) AS organic_visitors
            FROM sessions
            WHERE {date_where}
              AND {_ORGANIC_ENTRY_SQL}
        """}
        r = requests.post(f"{api_url}/api/projects/{project_id}/query/",
                          headers=headers, json={"query": q})
        if r.status_code == 200 and r.json().get("results"):
            row = r.json()["results"][0]
            return int(row[0] or 0), int(row[1] or 0)
        print(f"  Organic sessions query error ({date_from_days}d): {r.status_code}", r.text[:300])
        return 0, 0

    def _query_total(date_from_days, date_to_days=None):
        date_where = _organic_date_where(date_from_days, date_to_days)
        q = {"kind": "HogQLQuery", "query": f"""
            SELECT
                count(DISTINCT session_id)  AS total_sessions,
                count(DISTINCT distinct_id) AS total_visitors
            FROM sessions
            WHERE {date_where}
        """}
        r = requests.post(f"{api_url}/api/projects/{project_id}/query/",
                          headers=headers, json={"query": q})
        if r.status_code == 200 and r.json().get("results"):
            row = r.json()["results"][0]
            return int(row[0] or 0), int(row[1] or 0)
        return 0, 0

    # WoW windows
    this_org,  this_org_vis  = _query(7)
    prev_org,  prev_org_vis  = _query(14, 7)
    this_total, this_vis      = _query_total(7)
    prev_total, prev_vis      = _query_total(14, 7)

    # MoM windows
    mom_org,  mom_org_vis    = _query(30)
    prev_mom_org, _          = _query(60, 30)
    mom_total, mom_vis        = _query_total(30)

    wow = round((this_org - prev_org) / prev_org * 100, 2) if prev_org > 0 else None
    mom = round((mom_org  - prev_mom_org) / prev_mom_org * 100, 2) if prev_mom_org > 0 else None
    organic_pct      = round(this_org  / this_total  * 100, 2) if this_total  > 0 else 0
    prev_organic_pct = round(prev_org  / prev_total  * 100, 2) if prev_total  > 0 else 0
    mom_organic_pct  = round(mom_org   / mom_total   * 100, 2) if mom_total   > 0 else 0

    pd.DataFrame({
        "period":                  ["this_week",  "last_week",  "this_month", "last_month"],
        "organic_sessions":        [this_org,     prev_org,     mom_org,      prev_mom_org],
        "organic_visitors":        [this_org_vis, prev_org_vis, mom_org_vis,  None],
        "total_sessions":          [this_total,   prev_total,   mom_total,    None],
        "total_visitors":          [this_vis,     prev_vis,     mom_vis,      None],
        "organic_pct_of_sessions": [organic_pct,  prev_organic_pct, mom_organic_pct, None],
        "wow_change_percent":      [wow,          None,         None,         None],
        "mom_change_percent":      [None,         None,         mom,          None],
    }).to_csv("data/organic_sessions.csv", index=False)
    print(f"Organic sessions: {this_org} this week ({organic_pct}% of total), "
          f"WoW: {wow}%, MoM: {mom}%")


def fetch_organic_sessions_trend():
    """
    Fetches 8 weeks of weekly organic session counts for the trend line chart.
    Saves data/organic_sessions_trend.csv with columns: week, organic_sessions.
    """
    print("Fetching organic sessions 8-week trend")
    q = {"kind": "HogQLQuery", "query": f"""
        SELECT
            toStartOfWeek("$start_timestamp") AS week,
            count(DISTINCT session_id)         AS organic_sessions
        FROM sessions
        WHERE "$start_timestamp" >= now() - INTERVAL 56 DAY
          AND {_ORGANIC_ENTRY_SQL}
        GROUP BY week
        ORDER BY week
    """}
    r = requests.post(f"{api_url}/api/projects/{project_id}/query/",
                      headers=headers, json={"query": q})
    if r.status_code == 200 and r.json().get("results"):
        rows = [{"week": row[0], "organic_sessions": int(row[1] or 0)}
                for row in r.json()["results"]]
        pd.DataFrame(rows).to_csv("data/organic_sessions_trend.csv", index=False)
        print(f"Organic trend saved: {len(rows)} weeks")
    else:
        print("Organic trend error:", r.status_code, r.text[:200])
        pd.DataFrame({"week": [], "organic_sessions": []}).to_csv(
            "data/organic_sessions_trend.csv", index=False)


def fetch_top_landing_pages_organic():
    """
    Top 15 pages by organic traffic using raw_sessions JOIN.
    Adds page_type column (product / collection / blog / other).
    Saves data/top_landing_pages_organic.csv.
    """
    print("Fetching top landing pages by organic traffic")

    q = {"kind": "HogQLQuery", "query": f"""
        SELECT
            e.properties."$current_url"      AS url,
            count(DISTINCT e."$session_id")  AS organic_sessions,
            count(DISTINCT e.distinct_id)    AS organic_visitors
        FROM events e
        JOIN sessions s ON e."$session_id" = s.session_id
        WHERE e.event = '$pageview'
          AND e.timestamp >= now() - INTERVAL 7 DAY
          AND {_ORGANIC_ENTRY_SQL}
          AND e.properties."$current_url" IS NOT NULL
          AND e.properties."$current_url" != ''
          AND e.properties."$current_url" NOT LIKE '%web-pixels%'
          AND e.properties."$current_url" NOT LIKE '%sandbox%'
          AND e.properties."$current_url" NOT LIKE '%$$_posthog%'
          AND e.properties."$current_url" NOT LIKE '%cdn.shopify%'
        GROUP BY url
        ORDER BY organic_sessions DESC
        LIMIT 20
    """}

    empty = pd.DataFrame({"url": [], "organic_sessions": [], "organic_visitors": [],
                           "percentage_of_total_organic": [], "page_type": []})
    r = requests.post(f"{api_url}/api/projects/{project_id}/query/", headers=headers, json={"query": q})
    if r.status_code != 200 or not r.json().get("results"):
        print("Top landing pages error:", r.status_code, r.text[:200])
        empty.to_csv("data/top_landing_pages_organic.csv", index=False)
        return

    _NOISE_PATTERNS = ['web-pixels', 'sandbox', '$$_posthog', 'cdn.shopify', '__pf_']
    rows = [{"url": row[0], "organic_sessions": int(row[1] or 0), "organic_visitors": int(row[2] or 0)}
            for row in r.json()["results"]
            if row[0] and not any(p in str(row[0]) for p in _NOISE_PATTERNS)]
    if not rows:
        empty.to_csv("data/top_landing_pages_organic.csv", index=False)
        return
    df = pd.DataFrame(rows)
    total = df["organic_sessions"].sum()
    df["percentage_of_total_organic"] = df["organic_sessions"].apply(
        lambda v: round(v / total * 100, 1) if total > 0 else 0)

    def _page_type(url):
        u = str(url).lower()
        if '/products/' in u:   return 'product'
        if '/collections/' in u: return 'collection'
        if '/blogs/' in u or '/blog/' in u: return 'blog'
        return 'other'

    df["page_type"] = df["url"].apply(_page_type)
    type_order = {'product': 0, 'collection': 1, 'blog': 2, 'other': 3}
    df["_sort"] = df["page_type"].map(type_order)
    df = df.sort_values(["_sort", "organic_sessions"], ascending=[True, False]).drop(columns="_sort")
    df.to_csv("data/top_landing_pages_organic.csv", index=False)
    print(f"Top landing pages saved: {len(rows)} pages")


def fetch_top_blog_posts_organic():
    """
    Top 10 blog posts by organic traffic.
    Filters noise, deduplicates URL variants, formats human-readable titles.
    Saves data/top_blog_posts.csv.
    """
    from urllib.parse import urlparse, urlunparse
    print("Fetching top blog posts by organic traffic")

    q = {"kind": "HogQLQuery", "query": f"""
        SELECT
            e.properties."$current_url"      AS url,
            count(DISTINCT e."$session_id")  AS organic_sessions,
            count(DISTINCT e.distinct_id)    AS organic_visitors
        FROM events e
        JOIN sessions s ON e."$session_id" = s.session_id
        WHERE e.event = '$pageview'
          AND e.timestamp >= now() - INTERVAL 7 DAY
          AND {_ORGANIC_ENTRY_SQL}
          AND (e.properties."$current_url" LIKE '%/blogs/%'
               OR e.properties."$current_url" LIKE '%/blog/%')
          AND e.properties."$current_url" NOT LIKE '%web-pixels%'
          AND e.properties."$current_url" NOT LIKE '%sandbox%'
          AND e.properties."$current_url" NOT LIKE '%$$_posthog%'
          AND e.properties."$current_url" IS NOT NULL
        GROUP BY url
        ORDER BY organic_sessions DESC
        LIMIT 20
    """}

    empty = pd.DataFrame({"clean_url": [], "slug": [], "title": [],
                           "organic_sessions": [], "organic_visitors": [], "pct_of_blog_traffic": []})
    r = requests.post(f"{api_url}/api/projects/{project_id}/query/", headers=headers, json={"query": q})
    if r.status_code != 200 or not r.json().get("results"):
        print("Blog posts error:", r.status_code, r.text[:200])
        empty.to_csv("data/top_blog_posts.csv", index=False)
        return

    rows = [{"url": row[0], "organic_sessions": int(row[1] or 0), "organic_visitors": int(row[2] or 0)}
            for row in r.json()["results"] if row[0]]
    if not rows:
        empty.to_csv("data/top_blog_posts.csv", index=False)
        return

    def _clean_url(url):
        try:
            p = urlparse(url)
            clean = urlunparse((p.scheme, p.netloc, p.path.rstrip('/'), '', '', ''))
            return clean.replace('://www.', '://')
        except Exception:
            return url

    def _slug(url):
        try:
            parts = urlparse(url).path.strip('/').split('/')
            if len(parts) >= 3 and parts[0] == 'blogs':
                return parts[2]
            if len(parts) >= 2 and parts[0] == 'blog':
                return parts[1]
            return urlparse(url).path.strip('/')
        except Exception:
            return url

    df = pd.DataFrame(rows)
    df['clean_url'] = df['url'].apply(_clean_url)
    df = df.groupby('clean_url', as_index=False).agg(
        organic_sessions=('organic_sessions', 'sum'),
        organic_visitors=('organic_visitors', 'sum')
    )
    df['slug']  = df['clean_url'].apply(_slug)
    df['title'] = df['slug'].apply(lambda s: s.replace('-', ' ').title())
    total = df['organic_sessions'].sum()
    df['pct_of_blog_traffic'] = df['organic_sessions'].apply(
        lambda v: round(v / total * 100, 1) if total > 0 else 0)
    df = df.sort_values('organic_sessions', ascending=False).head(10)
    df[['clean_url', 'slug', 'title', 'organic_sessions', 'organic_visitors', 'pct_of_blog_traffic']]\
        .to_csv("data/top_blog_posts.csv", index=False)
    print(f"Top blog posts saved: {len(df)} posts")


def fetch_new_vs_returning_organic():
    """
    Splits organic visitors this week into new vs returning.
    New = their very first pageview ever is within the last 7 days.
    Returning = they had pageviews before the last 7 days.
    Saves data/organic_new_vs_returning.csv.
    """
    print("Fetching new vs returning organic users")

    q = {"kind": "HogQLQuery", "query": f"""
        SELECT
            CASE
                WHEN first_seen >= now() - INTERVAL 7 DAY THEN 'new'
                ELSE 'returning'
            END AS user_type,
            count(DISTINCT organic_user) AS user_count
        FROM (
            SELECT
                e.distinct_id                    AS organic_user,
                min(all_pv.first_seen)           AS first_seen
            FROM sessions s
            JOIN events e ON e."$session_id" = s.session_id
            JOIN (
                SELECT distinct_id, min(timestamp) AS first_seen
                FROM events
                WHERE event = '$pageview'
                GROUP BY distinct_id
            ) all_pv ON e.distinct_id = all_pv.distinct_id
            WHERE s."$start_timestamp" >= now() - INTERVAL 7 DAY
              AND {_ORGANIC_ENTRY_SQL}
              AND e.event = '$pageview'
            GROUP BY e.distinct_id
        )
        GROUP BY user_type
    """}

    empty = pd.DataFrame({"user_type": [], "user_count": [], "percentage": []})
    r = requests.post(f"{api_url}/api/projects/{project_id}/query/",
                      headers=headers, json={"query": q})
    if r.status_code != 200 or not r.json().get("results"):
        print("New vs returning error:", r.status_code, r.text[:300])
        empty.to_csv("data/organic_new_vs_returning.csv", index=False)
        return

    rows = [{"user_type": row[0], "user_count": int(row[1] or 0)} for row in r.json()["results"]]
    df = pd.DataFrame(rows)
    total = df["user_count"].sum()
    df["percentage"] = df["user_count"].apply(lambda v: round(v / total * 100, 1) if total > 0 else 0)
    df.to_csv("data/organic_new_vs_returning.csv", index=False)
    new_row = df[df["user_type"] == "new"]["user_count"].sum()
    ret_row = df[df["user_type"] == "returning"]["user_count"].sum()
    print(f"New vs returning organic: {new_row} new / {ret_row} returning")


def fetch_organic_session_duration():
    """
    Average session duration for organic visitors.
    Computes both all-sessions avg and engaged-sessions avg (2+ pageviews).
    Includes WoW and MoM comparisons.
    Saves data/organic_session_duration.csv.
    """
    print("Fetching organic session duration")

    def _format(seconds):
        if seconds is None or seconds == 0:
            return "0s"
        m, s = int(seconds // 60), int(seconds % 60)
        return f"{m}m {s}s" if m > 0 else f"{s}s"

    def _query(date_from_days, date_to_days=None):
        date_where = _organic_date_where(date_from_days, date_to_days)
        q = {"kind": "HogQLQuery", "query": f"""
            SELECT
                round(avg("$session_duration"), 0)                               AS avg_all_secs,
                round(avgIf("$session_duration", "$pageview_count" > 1), 0)      AS avg_engaged_secs
            FROM sessions
            WHERE {date_where}
              AND {_ORGANIC_ENTRY_SQL}
        """}
        r = requests.post(f"{api_url}/api/projects/{project_id}/query/",
                          headers=headers, json={"query": q})
        if r.status_code == 200 and r.json().get("results"):
            row = r.json()["results"][0]
            return float(row[0] or 0), float(row[1] or 0)
        print(f"  Session duration query error: {r.status_code}", r.text[:200])
        return 0.0, 0.0

    this_all, this_eng   = _query(7)
    prev_all, prev_eng   = _query(14, 7)
    mom_all,  mom_eng    = _query(30)
    prev_mom_all, _      = _query(60, 30)

    wow = round((this_all - prev_all) / prev_all * 100, 2) if prev_all > 0 else None
    mom = round((mom_all  - prev_mom_all) / prev_mom_all * 100, 2) if prev_mom_all > 0 else None

    pd.DataFrame({
        "metric": [
            "avg_duration_all_seconds",    "avg_duration_engaged_seconds",
            "avg_duration_all_formatted",  "avg_duration_engaged_formatted",
            "prev_week_all_seconds",       "wow_change_percent",
            "mom_all_seconds",             "mom_change_percent",
        ],
        "value": [
            this_all,           this_eng,
            _format(this_all),  _format(this_eng),
            prev_all,           wow,
            mom_all,            mom,
        ],
    }).to_csv("data/organic_session_duration.csv", index=False)
    print(f"Organic session duration: {_format(this_all)} avg all, "
          f"{_format(this_eng)} avg engaged (WoW: {wow}%)")


def fetch_page_traffic_changes_wow():
    """
    Page-level WoW traffic changes (±20%, min 5 sessions).
    Filters noise URLs, normalises paths, tags page type.
    Saves page_traffic_changes.csv, page_traffic_top_gains.csv, page_traffic_top_drops.csv.
    """
    from urllib.parse import urlparse
    print("Fetching page-level traffic changes WoW")

    _NOISE = ['web-pixels', 'sandbox', '$$_posthog', 'cdn.shopify', '__pf_']
    _NOISE_SQL = " AND ".join(
        f"properties.\"$current_url\" NOT LIKE '%{n}%'" for n in ['web-pixels', 'sandbox'])

    def _page_sessions(this_week=True):
        where_date = ("timestamp >= now() - INTERVAL 7 DAY" if this_week else
                      "timestamp >= now() - INTERVAL 14 DAY AND timestamp < now() - INTERVAL 7 DAY")
        q = {"kind": "HogQLQuery", "query": f"""
            SELECT
                properties."$current_url" AS url,
                count(DISTINCT "$session_id") AS sessions
            FROM events
            WHERE event = '$pageview'
              AND {where_date}
              AND properties."$current_url" IS NOT NULL
              AND properties."$current_url" != ''
              AND {_NOISE_SQL}
            GROUP BY url
            HAVING sessions >= 3
            ORDER BY sessions DESC
            LIMIT 500
        """}
        r = requests.post(f"{api_url}/api/projects/{project_id}/query/", headers=headers, json={"query": q})
        if r.status_code == 200 and r.json().get("results"):
            return {row[0]: int(row[1] or 0) for row in r.json()["results"]
                    if row[0] and not any(n in str(row[0]) for n in _NOISE)}
        return {}

    def _norm_path(url):
        try:
            return urlparse(url).path.rstrip('/') or '/'
        except Exception:
            return url

    def _page_type(path):
        if '/products/' in path:    return 'product'
        if '/collections/' in path: return 'collection'
        if '/blogs/' in path or '/blog/' in path: return 'blog'
        if '/pages/' in path:       return 'page'
        if path in ('/', ''):       return 'homepage'
        return 'other'

    this_week = _page_sessions(True)
    last_week = _page_sessions(False)

    # Aggregate by normalised path
    def _agg(raw):
        agg = {}
        for url, cnt in raw.items():
            p = _norm_path(url)
            agg[p] = agg.get(p, 0) + cnt
        return agg

    tw = _agg(this_week)
    lw = _agg(last_week)

    rows = []
    for path in set(tw.keys()) | set(lw.keys()):
        curr = tw.get(path, 0)
        prev = lw.get(path, 0)
        if max(curr, prev) < 5:
            continue
        change = round((curr - prev) / prev * 100, 1) if prev > 0 else (100.0 if curr > 0 else 0.0)
        if abs(change) < 20:
            continue
        rows.append({
            "path": path,
            "page_type": _page_type(path),
            "sessions_this_week": curr,
            "sessions_last_week": prev,
            "wow_change_pct": change,
            "direction": "gain" if change > 0 else "drop",
        })

    df = pd.DataFrame(rows) if rows else pd.DataFrame({
        "path": [], "page_type": [], "sessions_this_week": [],
        "sessions_last_week": [], "wow_change_pct": [], "direction": []})
    df = df.sort_values("wow_change_pct", ascending=False) if not df.empty else df
    df.to_csv("data/page_traffic_changes.csv", index=False)

    # Top 10 gains / drops — require at least 10 sessions this week to
    # prevent low-baseline noise (e.g. 1→3 sessions = +200%) from dominating.
    _MIN_SESSIONS = 10
    gains = (df[(df["wow_change_pct"] > 0) & (df["sessions_this_week"] >= _MIN_SESSIONS)]
             .nlargest(10, "wow_change_pct"))
    drops = (df[(df["wow_change_pct"] < 0) & (df["sessions_this_week"] >= _MIN_SESSIONS)]
             .nsmallest(10, "wow_change_pct"))
    gains.to_csv("data/page_traffic_top_gains.csv", index=False)
    drops.to_csv("data/page_traffic_top_drops.csv", index=False)
    print(f"Page traffic changes saved: {len(df)} flagged pages "
          f"({len(gains)} gains, {len(drops)} drops)")


def fetch_collection_pages_performance():
    """
    Traffic + organic + WoW for /collections/ pages.
    Saves data/collection_pages_performance.csv.
    """
    from urllib.parse import urlparse
    print("Fetching collection pages performance")

    _NOISE_SQL = ('properties."$current_url" NOT LIKE \'%web-pixels%\' '
                  'AND properties."$current_url" NOT LIKE \'%sandbox%\'')

    def _total_sessions(this_week=True):
        where_date = ("timestamp >= now() - INTERVAL 7 DAY" if this_week else
                      "timestamp >= now() - INTERVAL 14 DAY AND timestamp < now() - INTERVAL 7 DAY")
        q = {"kind": "HogQLQuery", "query": f"""
            SELECT
                properties."$current_url" AS url,
                count(DISTINCT "$session_id") AS sessions,
                count(DISTINCT distinct_id)   AS visitors
            FROM events
            WHERE event = '$pageview'
              AND {where_date}
              AND properties."$current_url" LIKE '%/collections/%'
              AND {_NOISE_SQL}
              AND properties."$current_url" IS NOT NULL
            GROUP BY url
            ORDER BY sessions DESC
        """}
        r = requests.post(f"{api_url}/api/projects/{project_id}/query/", headers=headers, json={"query": q})
        if r.status_code == 200 and r.json().get("results"):
            return pd.DataFrame([{"url": row[0], "sessions": int(row[1] or 0), "visitors": int(row[2] or 0)}
                                  for row in r.json()["results"] if row[0]])
        return pd.DataFrame()

    def _organic_sessions():
        q = {"kind": "HogQLQuery", "query": f"""
            SELECT
                e.properties."$current_url"     AS url,
                count(DISTINCT e."$session_id") AS organic_sessions,
                count(DISTINCT e.distinct_id)   AS organic_visitors
            FROM events e
            JOIN sessions s ON e."$session_id" = s.session_id
            WHERE e.event = '$pageview'
              AND e.timestamp >= now() - INTERVAL 7 DAY
              AND e.properties."$current_url" LIKE '%/collections/%'
              AND {_NOISE_SQL.replace('properties.', 'e.properties.')}
              AND e.properties."$current_url" IS NOT NULL
              AND {_ORGANIC_ENTRY_SQL}
            GROUP BY url
            ORDER BY organic_sessions DESC
        """}
        r = requests.post(f"{api_url}/api/projects/{project_id}/query/", headers=headers, json={"query": q})
        if r.status_code == 200 and r.json().get("results"):
            return pd.DataFrame([{"url": row[0], "organic_sessions": int(row[1] or 0),
                                   "organic_visitors": int(row[2] or 0)}
                                  for row in r.json()["results"] if row[0]])
        return pd.DataFrame()

    def _extract_collection(url):
        try:
            path = urlparse(url).path.rstrip('/')
            parts = path.split('/collections/')
            if len(parts) > 1:
                return parts[1].split('/')[0].split('?')[0]
        except Exception:
            pass
        return ''

    empty_cols = ["collection_name", "display_name", "total_sessions_this_week",
                  "total_sessions_last_week", "wow_change_pct", "organic_sessions",
                  "organic_visitors", "organic_pct", "is_priority"]
    empty = pd.DataFrame({c: [] for c in empty_cols})

    tw_df = _total_sessions(True)
    lw_df = _total_sessions(False)
    org_df = _organic_sessions()

    if tw_df.empty and lw_df.empty:
        print("Collection pages: no data")
        empty.to_csv("data/collection_pages_performance.csv", index=False)
        return

    for df in [tw_df, lw_df, org_df]:
        if not df.empty:
            df['collection_name'] = df['url'].apply(_extract_collection)

    def _agg_by_col(df, cols, suffix=''):
        if df.empty:
            return pd.DataFrame()
        renamed = {c: c + suffix for c in cols if c in df.columns}
        return df.groupby('collection_name')[cols].sum().reset_index().rename(columns=renamed)

    tw_agg = _agg_by_col(tw_df, ['sessions', 'visitors'], '_this_week') if not tw_df.empty else pd.DataFrame()
    lw_agg = _agg_by_col(lw_df, ['sessions', 'visitors'], '_last_week') if not lw_df.empty else pd.DataFrame()
    org_agg = (_agg_by_col(org_df, ['organic_sessions', 'organic_visitors'])
               if not org_df.empty else pd.DataFrame())

    result = tw_agg if not tw_agg.empty else pd.DataFrame({'collection_name': []})
    if not lw_agg.empty:
        result = result.merge(lw_agg, on='collection_name', how='outer')
    if not org_agg.empty:
        result = result.merge(org_agg, on='collection_name', how='left')
    result = result.fillna(0)

    def _wow(row):
        curr = row.get('sessions_this_week', 0)
        prev = row.get('sessions_last_week', 0)
        if prev > 0: return round((curr - prev) / prev * 100, 1)
        return 100.0 if curr > 0 else 0.0

    result['total_sessions_this_week'] = result.get('sessions_this_week', 0)
    result['total_sessions_last_week'] = result.get('sessions_last_week', 0)
    result['wow_change_pct'] = result.apply(_wow, axis=1)
    result['organic_sessions']  = result.get('organic_sessions', 0)
    result['organic_visitors']  = result.get('organic_visitors', 0)
    result['organic_pct'] = result.apply(
        lambda r: round(r['organic_sessions'] / r['total_sessions_this_week'] * 100, 1)
        if r['total_sessions_this_week'] > 0 else 0.0, axis=1)
    result['display_name'] = result['collection_name'].apply(lambda s: str(s).replace('-', ' ').title())
    _PRIORITY = {'custom-boxes', 'custom-ecommerce-packaging'}
    result['is_priority'] = result['collection_name'].isin(_PRIORITY)
    result = result[result['collection_name'] != '']
    result = result.sort_values(['is_priority', 'total_sessions_this_week'], ascending=[False, False])
    result[empty_cols].to_csv("data/collection_pages_performance.csv", index=False)
    print(f"Collection pages saved: {len(result)} collections")


def fetch_size_pages_performance():
    """
    Traffic + organic + WoW for boxes-by-size high-intent pages.
    Saves data/size_pages_performance.csv.
    """
    import re
    from urllib.parse import urlparse
    print("Fetching boxes-by-size page performance")

    _NOISE_SQL = ('properties."$current_url" NOT LIKE \'%web-pixels%\' '
                  'AND properties."$current_url" NOT LIKE \'%sandbox%\'')

    def _total_sessions(this_week=True):
        where_date = ("timestamp >= now() - INTERVAL 7 DAY" if this_week else
                      "timestamp >= now() - INTERVAL 14 DAY AND timestamp < now() - INTERVAL 7 DAY")
        q = {"kind": "HogQLQuery", "query": f"""
            SELECT
                properties."$current_url" AS url,
                count(DISTINCT "$session_id") AS sessions,
                count()                       AS pageviews,
                count(DISTINCT distinct_id)   AS visitors
            FROM events
            WHERE event = '$pageview'
              AND {where_date}
              AND (properties."$current_url" LIKE '%boxes-by-size%'
                   OR properties."$current_url" LIKE '%box-by-size%'
                   OR properties."$current_url" LIKE '%/products/%box%')
              AND {_NOISE_SQL}
              AND properties."$current_url" IS NOT NULL
            GROUP BY url
            ORDER BY sessions DESC
            LIMIT 100
        """}
        r = requests.post(f"{api_url}/api/projects/{project_id}/query/", headers=headers, json={"query": q})
        if r.status_code == 200 and r.json().get("results"):
            return pd.DataFrame([{"url": row[0], "sessions": int(row[1] or 0),
                                   "pageviews": int(row[2] or 0), "visitors": int(row[3] or 0)}
                                  for row in r.json()["results"] if row[0]])
        return pd.DataFrame()

    def _organic_sessions():
        q = {"kind": "HogQLQuery", "query": f"""
            SELECT
                e.properties."$current_url"     AS url,
                count(DISTINCT e."$session_id") AS organic_sessions,
                count(DISTINCT e.distinct_id)   AS organic_visitors
            FROM events e
            JOIN sessions s ON e."$session_id" = s.session_id
            WHERE e.event = '$pageview'
              AND e.timestamp >= now() - INTERVAL 7 DAY
              AND (e.properties."$current_url" LIKE '%boxes-by-size%'
                   OR e.properties."$current_url" LIKE '%box-by-size%'
                   OR e.properties."$current_url" LIKE '%/products/%box%')
              AND e.properties."$current_url" NOT LIKE '%web-pixels%'
              AND e.properties."$current_url" NOT LIKE '%sandbox%'
              AND e.properties."$current_url" IS NOT NULL
              AND {_ORGANIC_ENTRY_SQL}
            GROUP BY url
            ORDER BY organic_sessions DESC
        """}
        r = requests.post(f"{api_url}/api/projects/{project_id}/query/", headers=headers, json={"query": q})
        if r.status_code == 200 and r.json().get("results"):
            return pd.DataFrame([{"url": row[0], "organic_sessions": int(row[1] or 0),
                                   "organic_visitors": int(row[2] or 0)}
                                  for row in r.json()["results"] if row[0]])
        return pd.DataFrame()

    def _is_size_page(url):
        path = urlparse(url).path.lower()
        if 'boxes-by-size' in path or 'box-by-size' in path:
            return True
        if re.search(r'\d+x\d+', path):
            return True
        size_kw = ['small-box', 'medium-box', 'large-box', 'mini-box', 'outside-', 'inside-']
        return any(kw in path for kw in size_kw)

    def _display_name(url):
        try:
            segs = [s for s in urlparse(url).path.rstrip('/').split('/') if s]
            raw = segs[-1] if segs else url
            return raw.replace('-', ' ').title()[:50]
        except Exception:
            return url

    empty_cols = ["url", "display_name", "total_sessions_this_week", "total_sessions_last_week",
                  "wow_change_pct", "organic_sessions", "organic_visitors", "organic_pct", "pageviews"]
    empty = pd.DataFrame({c: [] for c in empty_cols})

    tw_df = _total_sessions(True)
    lw_df = _total_sessions(False)
    org_df = _organic_sessions()

    for df in [tw_df, lw_df, org_df]:
        if not df.empty:
            df['_keep'] = df['url'].apply(_is_size_page)
            df.query('_keep', inplace=True)
            df.drop(columns='_keep', inplace=True)

    if tw_df.empty and lw_df.empty:
        print("Size pages: no results (check URL patterns)")
        empty.to_csv("data/size_pages_performance.csv", index=False)
        return

    tw_clean = tw_df.rename(columns={'sessions': 'total_sessions_this_week',
                                      'pageviews': 'pageviews',
                                      'visitors': 'visitors_tw'}) if not tw_df.empty else pd.DataFrame()
    lw_clean = lw_df[['url', 'sessions']].rename(columns={'sessions': 'total_sessions_last_week'}) \
               if not lw_df.empty else pd.DataFrame()

    result = tw_clean if not tw_clean.empty else lw_clean.rename(
        columns={'total_sessions_last_week': 'total_sessions_this_week'})
    if not lw_clean.empty:
        result = result.merge(lw_clean, on='url', how='outer').fillna(0)
    else:
        result['total_sessions_last_week'] = 0
    if not org_df.empty:
        result = result.merge(org_df, on='url', how='left').fillna(0)
    else:
        result['organic_sessions'] = 0
        result['organic_visitors'] = 0

    result['wow_change_pct'] = result.apply(
        lambda r: round((r['total_sessions_this_week'] - r['total_sessions_last_week'])
                        / r['total_sessions_last_week'] * 100, 1)
        if r.get('total_sessions_last_week', 0) > 0
        else (100.0 if r.get('total_sessions_this_week', 0) > 0 else 0.0), axis=1)
    result['organic_pct'] = result.apply(
        lambda r: round(r['organic_sessions'] / r['total_sessions_this_week'] * 100, 1)
        if r.get('total_sessions_this_week', 0) > 0 else 0.0, axis=1)
    result['display_name'] = result['url'].apply(_display_name)
    if 'pageviews' not in result.columns:
        result['pageviews'] = 0
    result = result.sort_values('total_sessions_this_week', ascending=False)
    result[empty_cols].to_csv("data/size_pages_performance.csv", index=False)
    print(f"Size pages saved: {len(result)} pages")


def fetch_referrer_conversion():
    print("Fetching conversion rate by referrer")

    query = {
        "kind": "HogQLQuery",
        "query": """
            SELECT
                first_referrer,
                uniq(distinct_id) AS visitors,
                uniqIf(distinct_id, has_order > 0) AS converters,
                round(uniqIf(distinct_id, has_order > 0) * 100.0 / uniq(distinct_id), 2) AS conversion_rate_pct
            FROM (
                SELECT
                    distinct_id,
                    anyIf(properties.$referrer, event = '$pageview') AS first_referrer,
                    max(if(event = 'order_completed', 1, 0)) AS has_order
                FROM events
                WHERE event IN ('$pageview', 'order_completed')
                  AND timestamp >= now() - INTERVAL 7 DAY
                GROUP BY distinct_id
            )
            WHERE first_referrer IS NOT NULL
              AND first_referrer != ''
              AND first_referrer != '$$_posthog_breakdown_other_$$'
            GROUP BY first_referrer
            ORDER BY visitors DESC
            LIMIT 20
        """
    }

    r = requests.post(f"{api_url}/api/projects/{project_id}/query/", headers=headers, json={"query": query})
    empty = pd.DataFrame({"referrer": [], "visitors": [], "converters": [], "conversion_rate_pct": []})
    if r.status_code != 200:
        print("Referrer conversion error:", r.status_code, r.text)
        empty.to_csv("data/referrer_conversion.csv", index=False)
        return

    results = r.json().get("results", [])
    if not results:
        print("Referrer conversion: no data found")
        empty.to_csv("data/referrer_conversion.csv", index=False)
        return

    rows = [{"referrer": row[0], "visitors": int(row[1] or 0), "converters": int(row[2] or 0), "conversion_rate_pct": float(row[3] or 0)} for row in results]
    pd.DataFrame(rows).to_csv("data/referrer_conversion.csv", index=False)
    print(f"Referrer conversion saved: {len(rows)} referrer sources")


# ── CONVERSIONS ───────────────────────────────────────────────────────────────

_ORGANIC_REFERRER_SQL = (
    '"$referring_domain" IN ('
    + ', '.join(f"'{d}'" for d in _ORGANIC_ENTRY_DOMAINS)
    + ')'
)


def _get_organic_person_ids(days_from, days_to=None):
    """
    Return set of person_ids that had organic pageviews in the given window.
    Uses person_id (PostHog's resolved identity) so it survives anonymous→identified merges,
    which is required to match order_completed events (identified) with organic sessions (anon).
    """
    if days_to is None:
        date_sql = f'timestamp >= now() - INTERVAL {days_from} DAY'
    else:
        date_sql = (f'timestamp >= now() - INTERVAL {days_from} DAY '
                    f'AND timestamp < now() - INTERVAL {days_to} DAY')
    q = {"kind": "HogQLQuery", "query": f"""
        SELECT DISTINCT person_id
        FROM events
        WHERE event = '$pageview'
          AND {date_sql}
          AND properties."$referring_domain" IN ({', '.join(f"'{d}'" for d in _ORGANIC_ENTRY_DOMAINS)})
    """}
    r = requests.post(f"{api_url}/api/projects/{project_id}/query/",
                      headers=headers, json={"query": q})
    if r.status_code == 200 and r.json().get("results"):
        return {row[0] for row in r.json()["results"] if row[0]}
    return set()


# Keep old name as alias so nothing else breaks
def _get_organic_distinct_ids(days_from, days_to=None):
    return _get_organic_person_ids(days_from, days_to)


def fetch_organic_conversions():
    """
    Organic conversion counts and rates using HogQL subqueries throughout.

    Attribution: a conversion belongs to organic if the person_id had a $pageview
    with an organic referring_domain in the same time window. Identical logic to
    fetch_organic_revenue() so order counts are guaranteed consistent.

    Root cause of the previous 0-order bug: two separate API calls returning
    person_id sets were intersected in Python. PostHog resolves person_ids
    differently between independent query executions vs. nested subqueries, so
    the Python intersection always came up empty. Fix: single HogQL subquery.

    Saves data/organic_conversions.csv.
    """
    print("Fetching organic conversions")
    domain_list = ', '.join(f"'{d}'" for d in _ORGANIC_ENTRY_DOMAINS)

    def _run_int(sql):
        """Execute a HogQL COUNT query and return the integer result."""
        q = {"kind": "HogQLQuery", "query": sql}
        r = requests.post(f"{api_url}/api/projects/{project_id}/query/",
                          headers=headers, json={"query": q})
        if r.status_code == 200 and r.json().get("results"):
            return int(r.json()["results"][0][0] or 0)
        print(f"  [conv] query error: {r.status_code} {r.text[:150]}")
        return 0

    def _organic_sub(date_sql):
        """Canonical organic person filter — same as fetch_organic_revenue."""
        return (f"person_id IN ("
                f"SELECT DISTINCT person_id FROM events "
                f"WHERE event = '$pageview' AND {date_sql} "
                f"AND properties.\"$referring_domain\" IN ({domain_list}))")

    def _query(days_from, days_to=None):
        """
        Returns (orders, quotes, samples, combined, sessions_denom, total_orders)
        for the time window. All counts use HogQL subqueries with the same
        organic person filter so numbers are internally consistent.
        """
        if days_to is None:
            date_sql  = f"timestamp >= now() - INTERVAL {days_from} DAY"
            s_date    = f'"$start_timestamp" >= now() - INTERVAL {days_from} DAY'
        else:
            date_sql  = (f"timestamp >= now() - INTERVAL {days_from} DAY "
                         f"AND timestamp < now() - INTERVAL {days_to} DAY")
            s_date    = (f'"$start_timestamp" >= now() - INTERVAL {days_from} DAY '
                         f'AND "$start_timestamp" < now() - INTERVAL {days_to} DAY')

        org = _organic_sub(date_sql)

        # Orders: count events (one per transaction, not per person)
        orders = _run_int(f"""
            SELECT count() FROM events
            WHERE event = 'order_completed' AND {date_sql} AND {org}
        """)

        # Quote requests: distinct organic persons who visited custom-order
        quotes = _run_int(f"""
            SELECT count(DISTINCT person_id) FROM events
            WHERE event = '$pageview' AND {date_sql}
              AND properties."$current_url" LIKE '%/pages/custom-order%'
              AND properties."$current_url" NOT LIKE '%web-pixels%'
              AND {org}
        """)

        # Sample requests: distinct organic persons who visited free-sample
        samples = _run_int(f"""
            SELECT count(DISTINCT person_id) FROM events
            WHERE event = '$pageview' AND {date_sql}
              AND properties."$current_url" LIKE '%/pages/free-sample%'
              AND properties."$current_url" NOT LIKE '%web-pixels%'
              AND {org}
        """)

        # Combined: distinct organic persons who did ANY of the above
        combined = _run_int(f"""
            SELECT count(DISTINCT person_id) FROM events
            WHERE {date_sql} AND {org}
              AND (
                event = 'order_completed'
                OR (event = '$pageview'
                    AND properties."$current_url" LIKE '%/pages/custom-order%'
                    AND properties."$current_url" NOT LIKE '%web-pixels%')
                OR (event = '$pageview'
                    AND properties."$current_url" LIKE '%/pages/free-sample%'
                    AND properties."$current_url" NOT LIKE '%web-pixels%')
              )
        """)

        # Organic sessions: denominator for conversion rate
        sessions_denom = _run_int(f"""
            SELECT count() FROM sessions
            WHERE {s_date} AND {_ORGANIC_ENTRY_SQL}
        """)

        # Total orders (all channels) — for debug % organic
        total_orders = _run_int(f"""
            SELECT count() FROM events
            WHERE event = 'order_completed' AND {date_sql}
        """)

        return orders, quotes, samples, combined, sessions_denom, total_orders

    def _rate(count, total):
        return round(count / total * 100, 2) if total > 0 else 0.0

    def _chg(curr, prev):
        if prev is None or prev == 0:
            return None
        return round((curr - prev) / prev * 100, 1)

    # ── Fetch all windows ─────────────────────────────────────────────────────
    ord_tw,  qut_tw,  smp_tw,  comb_tw,  sess_tw,  total_tw  = _query(7)
    ord_lw,  qut_lw,  smp_lw,  comb_lw,  sess_lw,  total_lw  = _query(14, 7)
    ord_30,  qut_30,  smp_30,  comb_30,  sess_30,  total_30  = _query(30)
    ord_60,  qut_60,  smp_60,  comb_60,  sess_60,  total_60  = _query(60, 30)

    # ── Debug prints ──────────────────────────────────────────────────────────
    pct_org = round(ord_tw / total_tw * 100, 1) if total_tw > 0 else 0.0
    print(f"  Total orders (this week): {total_tw}")
    print(f"  Organic orders (this week): {ord_tw}")
    print(f"  % organic: {pct_org}%")

    # ── Sanity check ──────────────────────────────────────────────────────────
    # Cross-check with fetch_organic_revenue — re-read the revenue CSV if present
    rev_path = "data/organic_revenue.csv"
    if os.path.exists(rev_path):
        try:
            rev_df = pd.read_csv(rev_path)
            if not rev_df.empty:
                rev_orders = int(rev_df.iloc[0].get("organic_order_count", -1))
                if rev_orders >= 0 and rev_orders != ord_tw:
                    print(f"  WARNING: order count mismatch — "
                          f"conversions={ord_tw}, revenue_csv={rev_orders}. "
                          f"Re-run fetch_organic_revenue() after this fetch.")
                if ord_tw == 0 and float(rev_df.iloc[0].get("organic_revenue_this_week", 0)) > 0:
                    print("  WARNING: organic_orders=0 but organic_revenue>0 — tracking mismatch")
        except Exception:
            pass

    # ── Low-sample flag ───────────────────────────────────────────────────────
    low_sample = ord_tw < 3
    if low_sample:
        print(f"  NOTE: organic_orders={ord_tw} — below 3; report will flag as low sample")

    rows = [
        {"conversion_type": "orders",
         "count_this_week": ord_tw,  "conversion_rate": _rate(ord_tw,  sess_tw),
         "count_last_week": ord_lw,  "rate_last_week":  _rate(ord_lw,  sess_lw),
         "wow_change_pct":  _chg(ord_tw,  ord_lw),
         "count_30d": ord_30, "count_prev_30d": ord_60,
         "mom_change_pct":  _chg(ord_30,  ord_60),
         "low_sample": low_sample},
        {"conversion_type": "quote_requests",
         "count_this_week": qut_tw,  "conversion_rate": _rate(qut_tw,  sess_tw),
         "count_last_week": qut_lw,  "rate_last_week":  _rate(qut_lw,  sess_lw),
         "wow_change_pct":  _chg(qut_tw,  qut_lw),
         "count_30d": qut_30, "count_prev_30d": qut_60,
         "mom_change_pct":  _chg(qut_30,  qut_60),
         "low_sample": qut_tw < 3},
        {"conversion_type": "free_sample_requests",
         "count_this_week": smp_tw,  "conversion_rate": _rate(smp_tw,  sess_tw),
         "count_last_week": smp_lw,  "rate_last_week":  _rate(smp_lw,  sess_lw),
         "wow_change_pct":  _chg(smp_tw,  smp_lw),
         "count_30d": smp_30, "count_prev_30d": smp_60,
         "mom_change_pct":  _chg(smp_30,  smp_60),
         "low_sample": smp_tw < 3},
        {"conversion_type": "combined",
         "count_this_week": comb_tw, "conversion_rate": _rate(comb_tw, sess_tw),
         "count_last_week": comb_lw, "rate_last_week":  _rate(comb_lw, sess_lw),
         "wow_change_pct":  _chg(comb_tw, comb_lw),
         "count_30d": comb_30, "count_prev_30d": comb_60,
         "mom_change_pct":  _chg(comb_30, comb_60),
         "low_sample": comb_tw < 3},
    ]
    pd.DataFrame(rows).to_csv("data/organic_conversions.csv", index=False)
    print(f"  Organic conversions saved: {ord_tw} orders, {qut_tw} quotes, "
          f"{smp_tw} samples, {comb_tw} combined (this week)")


def fetch_organic_revenue():
    """
    Revenue and order count attributed to organic traffic.
    Uses person_id subquery so anonymous→identified merges are resolved.
    order_completed fires in Shopify's web-pixel sandbox with an identified distinct_id,
    so we can't match on session distinct_ids (anonymous). person_id is the resolved link.
    Saves data/organic_revenue.csv.
    """
    print("Fetching organic revenue")
    domain_list = ', '.join(f"'{d}'" for d in _ORGANIC_ENTRY_DOMAINS)

    def _organic_revenue_query(days_from, days_to=None):
        """Single HogQL query: orders from persons who had organic pageviews this period."""
        if days_to is None:
            date_sql = f"timestamp >= now() - INTERVAL {days_from} DAY"
        else:
            date_sql = (f"timestamp >= now() - INTERVAL {days_from} DAY "
                        f"AND timestamp < now() - INTERVAL {days_to} DAY")
        q = {"kind": "HogQLQuery", "query": f"""
            SELECT
                count()                                              AS organic_orders,
                sum(toFloatOrDefault(properties.total_price, 0.0)) AS organic_revenue
            FROM events
            WHERE event = 'order_completed'
              AND {date_sql}
              AND person_id IN (
                  SELECT DISTINCT person_id FROM events
                  WHERE event = '$pageview'
                    AND {date_sql}
                    AND properties."$referring_domain" IN ({domain_list})
              )
        """}
        r = requests.post(f"{api_url}/api/projects/{project_id}/query/",
                          headers=headers, json={"query": q})
        if r.status_code == 200 and r.json().get("results"):
            row = r.json()["results"][0]
            return int(row[0] or 0), float(row[1] or 0)
        print(f"  Organic revenue query error ({days_from}d): {r.status_code} {r.text[:150]}")
        return 0, 0.0

    def _total_revenue(days_from, days_to=None):
        if days_to is None:
            date_sql = f"timestamp >= now() - INTERVAL {days_from} DAY"
        else:
            date_sql = (f"timestamp >= now() - INTERVAL {days_from} DAY "
                        f"AND timestamp < now() - INTERVAL {days_to} DAY")
        q = {"kind": "HogQLQuery", "query": f"""
            SELECT sum(toFloatOrDefault(properties.total_price, 0.0))
            FROM events WHERE event = 'order_completed' AND {date_sql}
        """}
        r = requests.post(f"{api_url}/api/projects/{project_id}/query/",
                          headers=headers, json={"query": q})
        if r.status_code == 200 and r.json().get("results"):
            return float(r.json()["results"][0][0] or 0)
        return 0.0

    cnt_7,  rev_7  = _organic_revenue_query(7)
    cnt_lw, rev_lw = _organic_revenue_query(14, 7)
    cnt_30, rev_30 = _organic_revenue_query(30)
    cnt_60, rev_60 = _organic_revenue_query(60, 30)

    total_7  = _total_revenue(7)
    total_30 = _total_revenue(30)

    def _pct(a, b): return round(a / b * 100, 1) if b > 0 else 0.0
    def _chg(a, b): return round((a - b) / b * 100, 1) if b > 0 else None
    def _aov(rev, cnt): return round(rev / cnt, 2) if cnt > 0 else 0.0

    row = {
        "organic_revenue_this_week":   round(rev_7, 2),
        "organic_revenue_last_week":   round(rev_lw, 2),
        "organic_revenue_wow_pct":     _chg(rev_7, rev_lw),
        "organic_revenue_30d":         round(rev_30, 2),
        "organic_revenue_prev_30d":    round(rev_60, 2),
        "organic_revenue_mom_pct":     _chg(rev_30, rev_60),
        "organic_order_count":         cnt_7,
        "organic_aov":                 _aov(rev_7, cnt_7),
        "organic_aov_last_week":       _aov(rev_lw, cnt_lw),
        "organic_aov_wow_pct":         _chg(_aov(rev_7, cnt_7), _aov(rev_lw, cnt_lw)),
        "organic_revenue_pct_of_total": _pct(rev_7, total_7),
        "total_revenue_this_week":     round(total_7, 2),
        "organic_revenue_pct_30d":     _pct(rev_30, total_30),
    }
    pd.DataFrame([row]).to_csv("data/organic_revenue.csv", index=False)
    print(f"Organic revenue: ${rev_7:,.2f} ({cnt_7} orders, "
          f"{_pct(rev_7, total_7):.1f}% of total)")


def fetch_organic_product_conversions():
    """
    Top product pages by organic views, with conversion breakdown per page.
    Saves data/organic_product_conversions.csv.
    """
    from urllib.parse import urlparse
    print("Fetching organic product conversions")

    domain_list = ', '.join(f"'{d}'" for d in _ORGANIC_ENTRY_DOMAINS)

    # ── Canonical organic person filter (same as conversions + revenue) ───────
    # Using person_id subquery instead of sessions JOIN so order_completed events
    # (fired in Shopify web-pixel sandbox with a different session context) are
    # correctly attributed. This matches the attribution in fetch_organic_revenue().
    org_sub = (f"person_id IN ("
               f"SELECT DISTINCT person_id FROM events "
               f"WHERE event = '$pageview' "
               f"AND timestamp >= now() - INTERVAL 7 DAY "
               f"AND properties.\"$referring_domain\" IN ({domain_list}))")

    # ── Step 1: organic product page views ────────────────────────────────────
    q_views = {"kind": "HogQLQuery", "query": f"""
        SELECT person_id, properties."$current_url" AS url
        FROM events
        WHERE event = '$pageview'
          AND timestamp >= now() - INTERVAL 7 DAY
          AND properties."$current_url" LIKE '%/products/%'
          AND properties."$current_url" NOT LIKE '%web-pixels%'
          AND properties."$current_url" NOT LIKE '%sandbox%'
          AND properties."$current_url" IS NOT NULL
          AND {org_sub}
    """}
    r_views = requests.post(f"{api_url}/api/projects/{project_id}/query/",
                            headers=headers, json={"query": q_views})

    empty_cols = ["product_slug", "product_name", "organic_views", "organic_orders",
                  "quote_requests", "sample_requests", "total_conversions",
                  "view_to_order_rate", "view_to_any_conversion_rate"]
    empty = pd.DataFrame({c: [] for c in empty_cols})

    if r_views.status_code != 200 or not r_views.json().get("results"):
        print(f"  Organic product conversions: no views data "
              f"(status={r_views.status_code})")
        empty.to_csv("data/organic_product_conversions.csv", index=False)
        return

    def _slug(url):
        try:
            parts = urlparse(url).path.rstrip('/').split('/products/')
            if len(parts) > 1:
                return parts[1].split('/')[0].split('?')[0]
        except Exception:
            pass
        return ''

    pv_df = pd.DataFrame([{"person_id": row[0], "url": row[1]}
                           for row in r_views.json()["results"] if row[0] and row[1]])
    pv_df['slug'] = pv_df['url'].apply(_slug)
    pv_df = pv_df[pv_df['slug'] != '']
    print(f"  Product views: {len(pv_df)} rows, {pv_df['slug'].nunique()} unique slugs")

    # ── Step 2: converter person_ids (HogQL subqueries, not Python fetch) ─────
    # All three use the same org_sub filter so sets are consistent with step 1.
    def _fetch_converter_set(extra_where):
        q2 = {"kind": "HogQLQuery", "query": f"""
            SELECT DISTINCT person_id FROM events
            WHERE timestamp >= now() - INTERVAL 7 DAY
              AND {extra_where}
              AND {org_sub}
        """}
        r2 = requests.post(f"{api_url}/api/projects/{project_id}/query/",
                           headers=headers, json={"query": q2})
        if r2.status_code == 200 and r2.json().get("results"):
            return {row[0] for row in r2.json()["results"] if row[0]}
        return set()

    order_ids  = _fetch_converter_set("event = 'order_completed'")
    quote_ids  = _fetch_converter_set(
        "event = '$pageview' "
        "AND properties.\"$current_url\" LIKE '%/pages/custom-order%' "
        "AND properties.\"$current_url\" NOT LIKE '%web-pixels%'")
    sample_ids = _fetch_converter_set(
        "event = '$pageview' "
        "AND properties.\"$current_url\" LIKE '%/pages/free-sample%' "
        "AND properties.\"$current_url\" NOT LIKE '%web-pixels%'")

    print(f"  Organic converter sets: {len(order_ids)} orderers, "
          f"{len(quote_ids)} quote requesters, {len(sample_ids)} sample requesters")

    # ── Step 3: aggregate per product ─────────────────────────────────────────
    rows = []
    for slug, grp in pv_df.groupby('slug'):
        viewers = set(grp['person_id'])   # already filtered to organic via org_sub
        n  = len(viewers)
        o  = len(viewers & order_ids)
        qt = len(viewers & quote_ids)
        sm = len(viewers & sample_ids)
        tc = len(viewers & (order_ids | quote_ids | sample_ids))
        rows.append({
            "product_slug": slug,
            "product_name": slug.replace('-', ' ').title(),
            "organic_views": n,
            "organic_orders": o,
            "quote_requests": qt,
            "sample_requests": sm,
            "total_conversions": tc,
            "view_to_order_rate": round(o / n * 100, 2),
            "view_to_any_conversion_rate": round(tc / n * 100, 2),
        })

    if not rows:
        empty.to_csv("data/organic_product_conversions.csv", index=False)
        print("  Organic product conversions: no rows after grouping")
        return

    df = pd.DataFrame(rows).sort_values('organic_views', ascending=False).head(15)
    df[empty_cols].to_csv("data/organic_product_conversions.csv", index=False)
    print(f"  Organic product conversions saved: {len(df)} products")


# ── TECHNICAL ─────────────────────────────────────────────────────────────────

_CWV_COLS = ["page_path", "full_url", "cwv_source",
             "lcp_ms", "lcp_label", "cls", "cls_label",
             "inp_ms", "inp_label", "overall_cwv_status"]

def fetch_core_web_vitals():
    """
    Core Web Vitals for top organic landing pages via Google PageSpeed Insights API.
    Reads top_landing_pages_organic.csv, fetches CWV for the top 10 unique paths,
    and saves data/core_web_vitals.csv with labels and overall status per page.

    Uses page-level CrUX field data where available; falls back to origin-level.
    No WoW/MoM yet — historical storage not implemented.
    """
    from fetch_cwv import fetch_cwv_for_pages
    from urllib.parse import urlparse

    OUT_PATH = os.path.join("data", "core_web_vitals.csv")
    print("CWV fetch: starting")

    empty = pd.DataFrame({c: [] for c in _CWV_COLS})

    # ── Load top organic landing pages ────────────────────────────────────────
    lp_path = os.path.join("data", "top_landing_pages_organic.csv")
    if not os.path.exists(lp_path):
        print(f"  CWV fetch: {lp_path} not found — run fetch_top_landing_pages_organic() first")
        empty.to_csv(OUT_PATH, index=False)
        return

    lp_df = pd.read_csv(lp_path)
    if lp_df.empty or "url" not in lp_df.columns:
        print("  CWV fetch: landing page CSV is empty or missing 'url' column — skipping")
        empty.to_csv(OUT_PATH, index=False)
        return

    # ── Extract unique paths from top 10 URLs ─────────────────────────────────
    # Strip query params (?variant=...) and deduplicate — multiple Shopify variant
    # URLs resolve to the same path, and PSI needs the canonical product URL.
    lp_df = lp_df.sort_values("organic_sessions", ascending=False).head(10)
    seen_paths = set()
    paths = []
    for url in lp_df["url"].tolist():
        try:
            p = urlparse(str(url)).path.rstrip("/") or "/"
        except Exception:
            p = str(url)
        if p not in seen_paths:
            seen_paths.add(p)
            paths.append(p)

    print(f"  CWV fetch: {len(paths)} unique paths to measure: {paths}")

    # ── Fetch from PSI ────────────────────────────────────────────────────────
    df = fetch_cwv_for_pages(paths, verbose=True)
    print(f"  CWV fetch: PSI returned {len(df)} rows")

    if df.empty:
        print("  CWV fetch: no rows returned from PSI — writing empty CSV")
        empty.to_csv(OUT_PATH, index=False)
        return

    # Debug: show what we got
    print(f"  CWV fetch: columns = {list(df.columns)}")
    print(f"  CWV fetch: overall_cwv_status counts = {df['overall_cwv_status'].value_counts().to_dict()}")
    print(f"  CWV fetch: sources = {df['cwv_source'].value_counts().to_dict()}")

    # ── Sort: Poor first → Needs Improvement → Good → No Data ────────────────
    status_order = {"Poor": 0, "Needs Improvement": 1, "Good": 2, "No Data": 3}
    df["_sort"] = df["overall_cwv_status"].map(status_order).fillna(4)
    df = df.sort_values("_sort").drop(columns=["_sort"])

    # ── Write output ──────────────────────────────────────────────────────────
    abs_path = os.path.abspath(OUT_PATH)
    df[_CWV_COLS].to_csv(OUT_PATH, index=False)
    print(f"  CWV fetch: wrote {len(df)} rows to {abs_path}")

    # Verify the write
    check = pd.read_csv(OUT_PATH)
    print(f"  CWV fetch: verified — {len(check)} rows readable from disk")

    good    = (df["overall_cwv_status"] == "Good").sum()
    ni      = (df["overall_cwv_status"] == "Needs Improvement").sum()
    poor    = (df["overall_cwv_status"] == "Poor").sum()
    no_data = (df["overall_cwv_status"] == "No Data").sum()
    print(f"  CWV saved: {len(df)} pages — "
          f"{good} Good, {ni} Needs Improvement, {poor} Poor, {no_data} No Data")


def fetch_404_errors():
    """
    404 error tracking via page_not_found custom event.
    Gracefully handles no data (tracking enabled 2026-03-18).
    Saves data/404_errors.csv and data/404_summary.csv.
    """
    from urllib.parse import urlparse
    print("Fetching 404 errors")

    # Availability check
    check_q = {"kind": "HogQLQuery", "query": """
        SELECT count(*) FROM events
        WHERE event = 'page_not_found'
          AND timestamp >= now() - INTERVAL 7 DAY
    """}
    r_check = requests.post(f"{api_url}/api/projects/{project_id}/query/",
                             headers=headers, json={"query": check_q})
    total_404s = 0
    if r_check.status_code == 200 and r_check.json().get("results"):
        total_404s = int(r_check.json()["results"][0][0] or 0)
    print(f"  Total 404 events this week: {total_404s}")

    empty_errors = pd.DataFrame({"path": [], "hits": [], "unique_users": [],
                                  "top_referrer": [], "category": []})
    empty_summary = pd.DataFrame({"total_404s_this_week": [0], "total_404s_last_week": [0],
                                   "wow_change_pct": [None], "unique_404_pages": [0],
                                   "data_available": [False],
                                   "message": ["404 tracking enabled 2026-03-18. Data populates next report."]})

    if total_404s == 0:
        empty_errors.to_csv("data/404_errors.csv", index=False)
        empty_summary.to_csv("data/404_summary.csv", index=False)
        print("  No 404 data yet — placeholder saved")
        return

    q = {"kind": "HogQLQuery", "query": """
        SELECT
            properties.path         AS path,
            properties.url          AS url,
            properties.referrer     AS referrer,
            count(*)                AS hits,
            count(DISTINCT distinct_id) AS unique_users
        FROM events
        WHERE event = 'page_not_found'
          AND timestamp >= now() - INTERVAL 7 DAY
        GROUP BY properties.path, properties.url, properties.referrer
        ORDER BY hits DESC
        LIMIT 20
    """}
    r = requests.post(f"{api_url}/api/projects/{project_id}/query/",
                      headers=headers, json={"query": q})

    if r.status_code != 200 or not r.json().get("results"):
        print("  404 query error:", r.status_code, r.text[:200])
        empty_errors.to_csv("data/404_errors.csv", index=False)
        empty_summary.to_csv("data/404_summary.csv", index=False)
        return

    def _categorize(path, referrer):
        path = (path or '').lower()
        ref  = (referrer or '').lower()
        if '/products/' in path:    return 'Deleted/moved product'
        if '/collections/' in path: return 'Deleted/moved collection'
        if '/blogs/' in path:       return 'Deleted/moved blog post'
        if 'google' in ref:         return 'Broken from Google (stale index)'
        if ref:                     return 'Broken external link'
        return 'Direct/unknown'

    rows = []
    path_groups = {}
    for row in r.json()["results"]:
        path, url, ref, hits, uniq = row[0], row[1], row[2], int(row[3] or 0), int(row[4] or 0)
        key = path or url or 'unknown'
        if key not in path_groups:
            path_groups[key] = {"path": key, "hits": 0, "unique_users": 0,
                                 "top_referrer": ref or '', "category": _categorize(key, ref)}
        path_groups[key]["hits"]         += hits
        path_groups[key]["unique_users"] += uniq

    errors_df = pd.DataFrame(list(path_groups.values()))\
        .sort_values("hits", ascending=False).head(20)
    errors_df.to_csv("data/404_errors.csv", index=False)

    # Last week count for WoW
    lw_q = {"kind": "HogQLQuery", "query": """
        SELECT count(*) FROM events
        WHERE event = 'page_not_found'
          AND timestamp >= now() - INTERVAL 14 DAY
          AND timestamp < now() - INTERVAL 7 DAY
    """}
    r_lw = requests.post(f"{api_url}/api/projects/{project_id}/query/",
                          headers=headers, json={"query": lw_q})
    lw_count = 0
    if r_lw.status_code == 200 and r_lw.json().get("results"):
        lw_count = int(r_lw.json()["results"][0][0] or 0)

    wow = round((total_404s - lw_count) / lw_count * 100, 1) if lw_count > 0 else None
    pd.DataFrame([{
        "total_404s_this_week": total_404s,
        "total_404s_last_week": lw_count,
        "wow_change_pct": wow,
        "unique_404_pages": errors_df['path'].nunique(),
        "data_available": True,
        "message": "",
    }]).to_csv("data/404_summary.csv", index=False)
    print(f"  404 errors saved: {total_404s} hits, {errors_df['path'].nunique()} unique pages")


def detect_load_time_regressions():
    """
    Flags pages where LCP increased >20% WoW.
    Reads from core_web_vitals.csv. Saves data/load_time_issues.csv.
    """
    print("Detecting load time regressions")
    cwv_path = "data/core_web_vitals.csv"
    empty = pd.DataFrame({"url": [], "display_name": [], "avg_lcp_ms": [],
                           "lcp_wow_change": [], "lcp_grade": []})
    try:
        df = pd.read_csv(cwv_path)
        if df.empty or 'lcp_wow_change' not in df.columns:
            empty.to_csv("data/load_time_issues.csv", index=False)
            print("  No WoW data available yet")
            return
        regressions = df[df['lcp_wow_change'].notna() & (df['lcp_wow_change'] > 20)]\
            .sort_values('lcp_wow_change', ascending=False)
        regressions[["url", "display_name", "avg_lcp_ms", "lcp_wow_change", "lcp_grade"]]\
            .to_csv("data/load_time_issues.csv", index=False)
        print(f"  Load time regressions: {len(regressions)} pages")
    except Exception as e:
        print(f"  Load time regression error: {e}")
        empty.to_csv("data/load_time_issues.csv", index=False)


if __name__ == "__main__":
    fetch_dau()
    fetch_dau_previous()
    fetch_wau()
    fetch_rage_clicks()
    fetch_referrers()
    fetch_bounce_rate()
    fetch_organic_sessions()
    fetch_organic_sessions_trend()
    fetch_new_vs_returning_organic()
    fetch_organic_session_duration()
    fetch_top_landing_pages_organic()
    fetch_top_blog_posts_organic()  # saves data/top_blog_posts.csv
    fetch_page_traffic_changes_wow()
    fetch_collection_pages_performance()
    fetch_size_pages_performance()
    fetch_popup_metrics()
    fetch_ecommerce_funnel()
    fetch_product_conversion_funnels()
    fetch_top_products()
    fetch_revenue()
    fetch_revenue_previous()
    fetch_aov()
    fetch_cart_abandonment()
    fetch_checkout_abandonment()
    fetch_referrer_conversion()
    # Conversions
    fetch_organic_conversions()
    fetch_organic_revenue()
    fetch_organic_product_conversions()
    # Technical
    fetch_core_web_vitals()
    fetch_404_errors()
    detect_load_time_regressions()
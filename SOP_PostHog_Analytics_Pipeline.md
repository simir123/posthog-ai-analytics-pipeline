# Standard Operating Procedure (SOP): PostHog AI Analytics Pipeline

**Version:** 1.0  
**Last Updated:** January 2026  

---

## Table of Contents
1. [Overview](#overview)
2. [Prerequisites](#prerequisites)
3. [Setup Instructions](#setup-instructions)
4. [Running the Pipeline](#running-the-pipeline)
5. [Understanding the Outputs](#understanding-the-outputs)
6. [Adding New Metrics](#adding-new-metrics)
7. [Troubleshooting](#troubleshooting)
8. [Maintenance & Updates](#maintenance--updates)

---

## Overview

### What is This Pipeline?
The PostHog AI Analytics Pipeline is an automated system that:
- Pulls product analytics data from PostHog API
- Processes metrics into structured CSV datasets
- Uses AI (GROQ/Llama) to generate narrative insights
- Creates weekly PDF reports for team distribution

### What Metrics Are Currently Tracked?
- **Daily Active Users (DAU)** - Unique users per day
- **Weekly Active Users (WAU)** - Unique users per week
- **Rage Clicks by URL** - Frustration signals by page
- **Referrers by Traffic** - Top acquisition channels
- **Bounce Rate** - Session engagement metrics
- **Popup Performance** - Display, click, and dismissal rates (requires event tracking)
- **Popup-Rage Correlation** - Relationship between popups and frustration

### Potential Uses By Team:
- **SEO Team**: Bounce rates, traffic sources, user engagement
- **Product Team**: User activity trends, friction points, UX issues
- **Growth Team**: Acquisition channels, retention patterns
- **Engineering Team**: Technical performance, rage clicks, popup impact

---

## Prerequisites

### Required Access
- PostHog account with API access
- GROQ API account (for AI insights)
- Access to the project directory
- Python 3.8+ installed

### Required Files
- `.env` file with API credentials (see Setup)
- `requirements.txt` (dependencies)
- All Python scripts in the project directory

---

## Setup Instructions

### Step 1: Environment Setup

1. **Navigate to project directory:**
   ```bash
   cd /path/to/Posthog
   ```

2. **Create/activate virtual environment:**
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

### Step 2: Configure API Keys

1. **Create `.env` file** in the project root:
   ```env
   # PostHog API Configuration
   POSTHOG_API_URL=https://us.posthog.com
   POSTHOG_PERSONAL_API_KEY=your_posthog_api_key_here
   
   # GROQ API Configuration
   GROQ_API_KEY=your_groq_api_key_here
   GROQ_MODEL=llama-3.1-8b-instant
   ```

2. **Get API Keys:**
   - **PostHog**: Settings → Project API Key → Personal API Key
   - **GROQ**: https://console.groq.com/ → API Keys section

3. **Update Project ID** (if needed):
   - Edit `fetch_metrics.py`, line 11: `project_id = 14686`
   - Replace with your PostHog project ID

### Step 3: Verify Setup

```bash
# Test that everything works
python fetch_metrics.py
python run_report_generation.py
```

You should see:
- CSV files created in `data/` folder
- PDF report generated: `posthog_ai_report.pdf`

---

## Running the Pipeline

### Weekly Report Generation (Standard Process)

**Step 1: Fetch Metrics**
```bash
# Activate virtual environment
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Fetch all metrics from PostHog
python fetch_metrics.py
```

**Expected Output:**
```
Fetching Daily Active Users (DAU)
DAU saved to data/dau.csv
Fetching Weekly Active Users (WAU)
WAU saved to data/wau.csv
Fetching rage clicks
Rage clicks saved to data/rage_clicks_by_url.csv
Fetching referrers
Referrers saved to data/referrers.csv
Fetching bounce rate
Bounce rate calculated: 40.0% (from 5753 visitors, 12879 pageviews)
...
```

**Step 2: Generate AI Report**
```bash
# Generate PDF report with AI insights
python run_report_generation.py
```

**Expected Output:**
```
✓ PDF saved to: posthog_ai_report.pdf
```

### Output Files

**CSV Files** (in `data/` folder):
- `dau.csv` - Daily active users
- `wau.csv` - Weekly active users
- `rage_clicks_by_url.csv` - Rage click analysis
- `referrers.csv` - Traffic sources
- `bounce_rate.csv` - Bounce rate metrics
- `popup_metrics.csv` - Popup performance (if tracking implemented)
- `popup_rage_correlation.csv` - Popup-rage correlation

**PDF Report:**
- `posthog_ai_report.pdf` - Complete report with AI insights

### Delivery

1. **Review the PDF report** for key insights
2. **Share via Slack/Email** to relevant teams
3. **Archive reports** (optional: save with date in filename)

---

## Understanding the Outputs

### CSV Files Structure

**DAU/WAU Files:**
```
date,value
14-Jan-2026,766
15-Jan-2026,758
```

**Rage Clicks:**
```
url,rage_clicks
https://example.com/page,76.0
```

**Referrers:**
```
referrer,total
$direct,5156.0
https://www.google.com/,3587.0
```

**Bounce Rate:**
```
metric,value
bounce_rate_percent,40.0
total_sessions,6903.0
total_visitors,5753.0
total_views,12879.0
```

### PDF Report Sections

Each section includes:
1. **Raw Data** - CSV summary
2. **AI Insights** with:
   - Summary of Observations
   - Key Trends
   - Issues or Friction Points
   - Recommendations

---

## Troubleshooting

### Common Issues

**Issue: "Authentication Error" (403)**
- **Cause**: Invalid or expired API key
- **Solution**: 
  1. Check `.env` file has correct keys
  2. Verify API keys in PostHog/GROQ dashboards
  3. Regenerate keys if needed

**Issue: "No data found"**
- **Cause**: No events in PostHog for that metric
- **Solution**: 
  1. Check PostHog dashboard for events
  2. Verify event names match exactly
  3. Check date range (default: last 7 days)

**Issue: "Module not found"**
- **Cause**: Dependencies not installed
- **Solution**: 
  ```bash
  pip install -r requirements.txt
  ```

**Issue: "PDF generation fails"**
- **Cause**: GROQ API error or model issue
- **Solution**: 
  1. Check GROQ API key in `.env`
  2. Verify model name: `llama-3.1-8b-instant`
  3. Check GROQ API status/dashboard

**Issue: "CSV files empty"**
- **Cause**: No data in PostHog for that period
- **Solution**: 
  1. Verify events are being tracked
  2. Check PostHog dashboard
  3. Adjust date range if needed

### Getting Help

1. **Check Error Messages**: Read the full error output
2. **Verify Setup**: Ensure `.env` file is correct
3. **Test Individual Functions**: Run `python fetch_metrics.py` to see which metric fails
4. **Contact**: Reach out to the analytics team with:
   - Error message
   - What you were trying to do
   - Screenshot if helpful

---

## Maintenance & Updates

### Weekly Tasks
- Run the pipeline (fetch + generate report)
- Review PDF report
- Share with relevant teams
- Archive old reports (optional)

### Monthly Tasks
- Review if new metrics are needed
- Check API key expiration
- Update dependencies if needed: `pip install -r requirements.txt --upgrade`

### When to Update
- **New metrics requested** → Add fetch function
- **API changes** → Update query format
- **New team needs** → Add relevant metrics
- **Dependencies outdated** → Update requirements.txt

### Version Control
- Keep track of changes in this SOP
- Update version number when making significant changes
- Document new metrics added

---

## Quick Reference

### One-Line Commands

**Full Pipeline:**
```bash
source venv/bin/activate && python fetch_metrics.py && python run_report_generation.py
```

**Just Fetch Data:**
```bash
source venv/bin/activate && python fetch_metrics.py
```

**Just Generate Report:**
```bash
source venv/bin/activate && python run_report_generation.py
```

### File Locations

- **Scripts**: `/path/to/Posthog/`
- **Data**: `/path/to/Posthog/data/`
- **Reports**: `/path/to/Posthog/posthog_ai_report.pdf`
- **Config**: `/path/to/Posthog/.env`

### Key Contacts

- **Analytics Team**: For pipeline questions, new metrics
- **Shopify Dev Team**: For event tracking implementation
- **SEO Team**: For SEO-specific metric requests

---

## Appendix

### Current Metrics Reference

| Metric | File | Description |
|--------|------|-------------|
| DAU | `dau.csv` | Daily unique users |
| WAU | `wau.csv` | Weekly unique users |
| Rage Clicks | `rage_clicks_by_url.csv` | Frustration signals by page |
| Referrers | `referrers.csv` | Traffic sources |
| Bounce Rate | `bounce_rate.csv` | Session engagement |
| Popup Metrics | `popup_metrics.csv` | Popup performance (requires tracking) |
| Popup-Rage | `popup_rage_correlation.csv` | Popup frustration correlation |

### API Documentation
- PostHog Query API: https://posthog.com/docs/api/query
- GROQ API: https://console.groq.com/docs

---

**End of SOP**

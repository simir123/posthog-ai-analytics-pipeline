import os
import tempfile
import pandas as pd

try:
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    import matplotlib.patches as mpatches
    HAS_MATPLOTLIB = True
except ImportError:
    HAS_MATPLOTLIB = False

from reportlab.platypus import Image, Spacer, Paragraph, Table, TableStyle
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.pagesizes import LETTER

BLUE   = '#3d5675'
GREEN  = '#72bda3'
RED    = '#E14744'
ORANGE = '#f2ae4d'
DARK   = '#2c3e50'

W = 6.5
H = 3.5
DATA_DIR = 'data'

_note_style = ParagraphStyle('ChartNote', fontName='Times-Italic', fontSize=11,
                              textColor=colors.HexColor('#666666'), spaceAfter=8)
_sub_style  = ParagraphStyle('ChartSub',  fontName='Times-Bold',   fontSize=11,
                              textColor=colors.HexColor(DARK), spaceAfter=4)
_tbl_header = ParagraphStyle('TH', fontName='Times-Bold',  fontSize=9, leading=11, textColor=colors.white)
_tbl_cell   = ParagraphStyle('TC', fontName='Times-Roman', fontSize=9, leading=11)
_tbl_bold   = ParagraphStyle('TB', fontName='Times-Bold',  fontSize=9, leading=11)


# ── helpers ───────────────────────────────────────────────────────────────────

def _save_fig(fig):
    tmp = tempfile.NamedTemporaryFile(suffix='.png', delete=False)
    fig.savefig(tmp.name, dpi=150, bbox_inches='tight', facecolor='white')
    plt.close(fig)
    return tmp.name

def _img(path, w=W, h=H):
    return Image(path, width=w * inch, height=h * inch)

def _base_ax_style(ax):
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)

def _truncate_url(url):
    """Strip domain prefix and query string. Returns None for PostHog noise rows."""
    url = str(url).strip()
    if '$$_posthog' in url:
        return None
    for p in ['https://www.', 'https://', 'http://www.', 'http://']:
        if url.startswith(p):
            url = url[len(p):]
    url = url.split('?')[0].rstrip('/')
    if len(url) > 55:
        url = url[:52] + '...'
    return url or None

def _base_url(url):
    """Strip domain AND query string, keeping only the path portion."""
    url = str(url).strip()
    if '$$_posthog' in url:
        return None
    for p in ['https://www.', 'https://', 'http://www.', 'http://']:
        if url.startswith(p):
            url = url[len(p):]
    url = url.split('?')[0].rstrip('/')
    return url or None

def _group_referrer(ref):
    ref = str(ref).lower().strip()
    if ref in ('$direct', '(direct)', '', 'direct', 'none', '(none)'):
        return 'Direct'
    if 'google' in ref:
        return 'Google'
    if 'facebook' in ref or 'fb.com' in ref:
        return 'Facebook'
    if 'instagram' in ref:
        return 'Instagram'
    if any(s in ref for s in ('bing', 'yahoo', 'duckduckgo', 'baidu', 'yandex')):
        return 'Other Search'
    return 'Other'

def _wow_change(curr, prev):
    """Return (change_pct, color, arrow_char)."""
    if prev and prev > 0:
        pct = (curr - prev) / prev * 100
        color = GREEN if pct >= 0 else RED
        arrow = '+' if pct >= 0 else ''
        return pct, color, arrow
    return None, '#888888', ''

def _stat_boxes_fig(stats):
    """
    stats: list of (label, value_str, delta_str, delta_color)
    Returns a small matplotlib figure with side-by-side stat boxes.
    """
    n = len(stats)
    fig, axes = plt.subplots(1, n, figsize=(W, 1.6))
    if n == 1:
        axes = [axes]
    for ax, (label, val_str, delta_str, delta_color) in zip(axes, stats):
        ax.set_xlim(0, 1); ax.set_ylim(0, 1); ax.axis('off')
        rect = plt.Rectangle((0.03, 0.03), 0.94, 0.94, fill=False,
                              edgecolor='#d0d0d0', linewidth=1, transform=ax.transAxes,
                              clip_on=False)
        ax.add_patch(rect)
        ax.text(0.5, 0.82, label,    ha='center', va='top',    transform=ax.transAxes,
                fontsize=8.5, color='#777777')
        ax.text(0.5, 0.50, val_str,  ha='center', va='center', transform=ax.transAxes,
                fontsize=19, fontweight='bold', color=DARK)
        ax.text(0.5, 0.15, delta_str, ha='center', va='bottom', transform=ax.transAxes,
                fontsize=9, color=delta_color, fontweight='bold')
    plt.tight_layout(pad=0.3)
    return fig

def _csv_exists_nonempty(path):
    if not os.path.exists(path):
        return False
    try:
        df = pd.read_csv(path)
        return len(df) > 0
    except Exception:
        return False

def _build_plain_table(df, col_labels=None, highlight_col=None, highlight_fn=None):
    headers = col_labels or list(df.columns)
    table_data = [[Paragraph(h, _tbl_header) for h in headers]]
    style = [
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor(DARK)),
        ('TEXTCOLOR',  (0,0), (-1,0), colors.white),
        ('GRID',       (0,0), (-1,-1), 0.5, colors.HexColor('#cccccc')),
        ('BOX',        (0,0), (-1,-1), 1,   colors.HexColor(DARK)),
        ('TOPPADDING',    (0,0), (-1,-1), 5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 5),
    ]
    for row_idx, (_, row) in enumerate(df.iterrows(), start=1):
        cells = [Paragraph(str(v).replace('&','&amp;').replace('<','&lt;').replace('>','&gt;'), _tbl_cell)
                 for v in row]
        table_data.append(cells)
        row_bg = colors.HexColor('#f8f9fa') if row_idx % 2 == 1 else colors.white
        style.append(('BACKGROUND', (0, row_idx), (-1, row_idx), row_bg))
        if highlight_col is not None and highlight_fn:
            bg = highlight_fn(float(row.iloc[highlight_col]))
            style.append(('BACKGROUND', (highlight_col, row_idx), (highlight_col, row_idx), bg))
    pw = LETTER[0] - 1.5 * inch
    col_w = pw / len(headers)
    tbl = Table(table_data, colWidths=[col_w]*len(headers), repeatRows=1)
    tbl.setStyle(TableStyle(style))
    return tbl


# ── section chart functions ───────────────────────────────────────────────────

def _chart_user_activity():
    dau_path  = os.path.join(DATA_DIR, 'dau.csv')
    prev_path = os.path.join(DATA_DIR, 'dau_previous.csv')
    if not _csv_exists_nonempty(dau_path):
        return [Paragraph('No DAU data available.', _note_style)], True

    df = pd.read_csv(dau_path)
    vals = df['value'].tolist()
    x    = list(range(len(df)))
    flowables = []

    # Line chart
    fig, ax = plt.subplots(figsize=(W, H))
    ax.plot(x, vals, color=BLUE, linewidth=2.5, marker='o', markersize=6, zorder=3)
    ax.fill_between(x, vals, alpha=0.12, color=BLUE)
    ax.set_xticks(x)
    ax.set_xticklabels(df['date'].tolist(), rotation=45, ha='right', fontsize=8)
    ax.set_ylabel('Active Users', fontsize=9)
    ax.set_title('Daily Active Users (This Week)', fontsize=13, fontweight='bold', color=DARK, pad=10)
    ax.yaxis.grid(True, alpha=0.3, linestyle='--')
    ax.set_axisbelow(True)
    _base_ax_style(ax)
    plt.tight_layout()
    flowables += [_img(_save_fig(fig)), Spacer(1, 0.15*inch)]

    # WoW stat boxes
    curr_avg = sum(vals) / len(vals) if vals else 0
    curr_total = sum(vals)
    stats = []
    if _csv_exists_nonempty(prev_path):
        prev_df   = pd.read_csv(prev_path)
        prev_vals = prev_df['value'].tolist()
        prev_avg  = sum(prev_vals) / len(prev_vals) if prev_vals else 0
        prev_total = sum(prev_vals)

        avg_pct, avg_color, avg_arrow = _wow_change(curr_avg, prev_avg)
        tot_pct, tot_color, tot_arrow = _wow_change(curr_total, prev_total)

        stats = [
            ("Avg DAU This Week",   f"{curr_avg:.0f}",
             f"{avg_arrow}{avg_pct:.1f}% vs last week" if avg_pct is not None else "no prior data",
             avg_color),
            ("Total WAU This Week", f"{int(curr_total):,}",
             f"{tot_arrow}{tot_pct:.1f}% vs last week" if tot_pct is not None else "no prior data",
             tot_color),
        ]
    else:
        stats = [
            ("Avg DAU This Week",   f"{curr_avg:.0f}",   "no prior week data", '#888888'),
            ("Total WAU This Week", f"{int(curr_total):,}", "no prior week data", '#888888'),
        ]

    fig2 = _stat_boxes_fig(stats)
    flowables += [_img(_save_fig(fig2), h=1.6), Spacer(1, 0.1*inch)]
    return flowables, True


def _chart_rage_clicks():
    path = os.path.join(DATA_DIR, 'rage_clicks_by_url.csv')
    if not _csv_exists_nonempty(path):
        return [], False
    df = pd.read_csv(path)

    # Aggregate by base URL (strip query params)
    df['base'] = df['url'].apply(_base_url)
    df = df[df['base'].notna()]
    df = df.groupby('base', as_index=False)['rage_clicks'].sum()
    df = df.nlargest(10, 'rage_clicks').sort_values('rage_clicks')

    if df.empty:
        return [], False

    h = max(3.0, len(df) * 0.5)
    fig, ax = plt.subplots(figsize=(W, h))
    bars = ax.barh(df['base'], df['rage_clicks'], color=RED, alpha=0.85, zorder=3)
    ax.set_xlabel('Rage Click Count', fontsize=9)
    ax.set_title('Top Rage Click Pages (aggregated, query params stripped)', fontsize=11,
                 fontweight='bold', color=DARK, pad=10)
    ax.xaxis.grid(True, alpha=0.3, linestyle='--')
    ax.set_axisbelow(True)
    mx = df['rage_clicks'].max()
    for bar, val in zip(bars, df['rage_clicks']):
        ax.text(bar.get_width() + mx*0.01, bar.get_y() + bar.get_height()/2,
                f'{int(val)}', va='center', fontsize=8, color=DARK)
    _base_ax_style(ax)
    plt.tight_layout()
    return [_img(_save_fig(fig), h=h), Spacer(1, 0.1*inch)], True


def _chart_referrers():
    path = os.path.join(DATA_DIR, 'referrers.csv')
    if not _csv_exists_nonempty(path):
        return [], False
    df = pd.read_csv(path)
    df['label'] = df['referrer'].apply(_truncate_url)
    df = df[df['label'].notna()]
    df_top = df.nlargest(10, 'total').sort_values('total')
    flowables = []

    # Chart 1: top-10 horizontal bar
    h = max(3.0, len(df_top) * 0.5)
    fig, ax = plt.subplots(figsize=(W, h))
    ax.barh(df_top['label'], df_top['total'], color=BLUE, alpha=0.85, zorder=3)
    ax.set_xlabel('Sessions', fontsize=9)
    ax.set_title('Top 10 Traffic Sources', fontsize=13, fontweight='bold', color=DARK, pad=10)
    ax.xaxis.grid(True, alpha=0.3, linestyle='--')
    ax.set_axisbelow(True)
    _base_ax_style(ax)
    plt.tight_layout()
    flowables += [_img(_save_fig(fig), h=h), Spacer(1, 0.2*inch)]

    # Chart 2: grouped pie with 3% threshold
    df['group'] = df['referrer'].apply(_group_referrer)
    grouped = df.groupby('group')['total'].sum()
    total_traffic = grouped.sum()
    # Merge groups below 3% into "Other"
    small = grouped[grouped / total_traffic < 0.03].index.tolist()
    if small:
        other_sum = grouped[small].sum()
        grouped = grouped.drop(index=small)
        grouped['Other'] = grouped.get('Other', 0) + other_sum
    grouped = grouped.sort_values(ascending=False)

    pie_colors = {
        'Direct': BLUE, 'Google': '#4285F4', 'Facebook': '#1877F2',
        'Instagram': '#E1306C', 'Other Search': ORANGE, 'Other': '#aaaaaa',
    }
    clrs = [pie_colors.get(g, '#aaaaaa') for g in grouped.index]
    fig2, ax2 = plt.subplots(figsize=(5, 4))
    _, texts, autotexts = ax2.pie(
        grouped.values, labels=grouped.index, colors=clrs,
        autopct='%1.1f%%', startangle=90, pctdistance=0.78,
        wedgeprops={'linewidth': 1, 'edgecolor': 'white'}
    )
    for t in autotexts:
        t.set_fontsize(9)
    ax2.set_title('Traffic Channel Mix', fontsize=13, fontweight='bold', color=DARK, pad=10)
    plt.tight_layout()
    flowables += [_img(_save_fig(fig2), w=4.5, h=3.5), Spacer(1, 0.1*inch)]
    return flowables, True


def _chart_bounce_rate():
    path = os.path.join(DATA_DIR, 'bounce_rate.csv')
    if not _csv_exists_nonempty(path):
        return [], False
    df = pd.read_csv(path)
    data = dict(zip(df['metric'], df['value'].astype(float)))
    rate       = data.get('bounce_rate_percent', 0)
    total_sess = int(data.get('total_sessions', 0))
    bounced    = int(data.get('bounced_sessions', 0))
    total_pv   = int(data.get('total_pageviews', 0))
    if total_sess == 0:
        return [], False

    fig, ax = plt.subplots(figsize=(W, 2.6))
    ax.set_xlim(0, 100); ax.set_ylim(0, 1); ax.axis('off')
    ax.barh(0.5, 45, left=0,  height=0.28, color='#27ae60', alpha=0.75)
    ax.barh(0.5, 20, left=45, height=0.28, color=ORANGE,    alpha=0.75)
    ax.barh(0.5, 35, left=65, height=0.28, color=RED,       alpha=0.75)
    for x, lbl in [(22.5,'Good\n(0–45%)'),(55,'Elevated\n(45–65%)'),(82.5,'High\n(65%+)')]:
        ax.text(x, 0.5, lbl, ha='center', va='center', fontsize=8, color='white', fontweight='bold')
    ax.annotate('', xy=(min(rate, 99), 0.64), xytext=(min(rate, 99), 0.88),
                arrowprops=dict(arrowstyle='->', color=DARK, lw=2.5))
    ax.text(min(rate, 99), 0.93, f'{rate:.1f}%',
            ha='center', va='bottom', fontsize=18, fontweight='bold', color=DARK)
    ax.set_title('Bounce Rate vs. Industry Benchmark', fontsize=13, fontweight='bold', color=DARK, pad=12)
    fig.text(0.5, 0.04,
             f'Sessions: {total_sess:,}   |   Bounced: {bounced:,}   |   Pageviews: {total_pv:,}',
             ha='center', fontsize=9, color='#555555')
    plt.tight_layout(rect=[0, 0.08, 1, 1])
    flowables = [_img(_save_fig(fig), h=2.6), Spacer(1, 0.12*inch)]

    # WoW / MoM stat boxes for overall bounce rate
    wow_val = data.get('bounce_rate_wow_pct')
    mom_val = data.get('bounce_rate_mom_pct')
    def _br_delta(v, label):
        if v is None or (isinstance(v, float) and (v != v)):  # NaN check
            return "no prior data"
        # For bounce rate, a decrease is good (green)
        return f"{'+' if v >= 0 else ''}{v:.1f}% {label}"
    def _br_color(v):
        if v is None or (isinstance(v, float) and (v != v)):
            return '#888888'
        return RED if v >= 0 else GREEN   # Higher bounce = bad
    stats_br = [
        ("Bounce Rate",      f"{rate:.1f}%",    _br_delta(wow_val, "vs last week"),  _br_color(wow_val)),
        ("Total Sessions",   f"{total_sess:,}", _br_delta(mom_val, "vs last month"), _br_color(mom_val)),
    ]
    fig_br = _stat_boxes_fig(stats_br)
    flowables += [_img(_save_fig(fig_br), h=1.6), Spacer(1, 0.12*inch)]

    # Organic bounce rate gauge (if available)
    org_rate    = data.get('organic_bounce_rate_percent', 0)
    org_sess    = int(data.get('organic_sessions', 0))
    org_bounced = int(data.get('organic_bounced_sessions', 0))
    if org_sess > 0:
        fig2, ax2 = plt.subplots(figsize=(W, 2.6))
        ax2.set_xlim(0, 100); ax2.set_ylim(0, 1); ax2.axis('off')
        ax2.barh(0.5, 45, left=0,  height=0.28, color='#27ae60', alpha=0.75)
        ax2.barh(0.5, 20, left=45, height=0.28, color=ORANGE,    alpha=0.75)
        ax2.barh(0.5, 35, left=65, height=0.28, color=RED,       alpha=0.75)
        for x, lbl in [(22.5,'Good\n(0–45%)'),(55,'Elevated\n(45–65%)'),(82.5,'High\n(65%+)')]:
            ax2.text(x, 0.5, lbl, ha='center', va='center', fontsize=8, color='white', fontweight='bold')
        ax2.annotate('', xy=(min(org_rate, 99), 0.64), xytext=(min(org_rate, 99), 0.88),
                    arrowprops=dict(arrowstyle='->', color=DARK, lw=2.5))
        ax2.text(min(org_rate, 99), 0.93, f'{org_rate:.1f}%',
                ha='center', va='bottom', fontsize=18, fontweight='bold', color=DARK)
        ax2.set_title('Organic Bounce Rate vs. Industry Benchmark', fontsize=13, fontweight='bold', color=DARK, pad=12)
        fig2.text(0.5, 0.04,
                 f'Organic Sessions: {org_sess:,}   |   Bounced: {org_bounced:,}',
                 ha='center', fontsize=9, color='#555555')
        plt.tight_layout(rect=[0, 0.08, 1, 1])
        flowables += [_img(_save_fig(fig2), h=2.6), Spacer(1, 0.1*inch)]

    return flowables, True


def _chart_popup():
    path = os.path.join(DATA_DIR, 'popup_metrics.csv')
    if not _csv_exists_nonempty(path):
        return [], False
    df = pd.read_csv(path)
    if df.empty:
        return [], False
    popup_map = {name: f'Popup {chr(65+i)}' for i, name in enumerate(df['popup_name'].tolist())}
    df['popup_name'] = df['popup_name'].map(popup_map)
    headers = ['Popup', 'Displays', 'Clicks', 'Dismissals', 'Click Rate %', 'Dismiss Rate %', 'Engagement %']
    keys    = ['popup_name','total_displays','clicks','dismissals',
               'click_rate_percent','dismissal_rate_percent','engagement_rate_percent']
    table_data = [[Paragraph(h, _tbl_header) for h in headers]]
    style = [
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor(DARK)),
        ('TEXTCOLOR',  (0,0), (-1,0), colors.white),
        ('GRID',       (0,0), (-1,-1), 0.5, colors.HexColor('#cccccc')),
        ('BOX',        (0,0), (-1,-1), 1,   colors.HexColor(DARK)),
        ('ALIGN',      (1,1), (-1,-1), 'CENTER'),
        ('TOPPADDING',    (0,0), (-1,-1), 5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 5),
    ]
    for ri, (_, row) in enumerate(df.iterrows(), start=1):
        table_data.append([Paragraph(str(row[k]), _tbl_cell) for k in keys])
        style.append(('BACKGROUND', (0,ri), (-1,ri), colors.HexColor('#f8f9fa')))
        cr = float(row['click_rate_percent'])
        dr = float(row['dismissal_rate_percent'])
        cr_color = colors.HexColor('#d4edda') if cr >= 2 else (colors.HexColor('#fff3cd') if cr >= 1 else colors.HexColor('#f8d7da'))
        dr_color = colors.HexColor('#f8d7da') if dr >= 50 else (colors.HexColor('#fff3cd') if dr >= 20 else colors.HexColor('#d4edda'))
        style.append(('BACKGROUND', (4,ri), (4,ri), cr_color))
        style.append(('BACKGROUND', (5,ri), (5,ri), dr_color))
    pw = LETTER[0] - 1.5 * inch
    col_widths = [pw*0.17, pw*0.12, pw*0.10, pw*0.13, pw*0.14, pw*0.14, pw*0.14]
    tbl = Table(table_data, colWidths=col_widths, repeatRows=1)
    tbl.setStyle(TableStyle(style))
    return [tbl, Spacer(1, 0.15*inch)], True


def _chart_ecommerce_funnel():
    funnel_path  = os.path.join(DATA_DIR, 'ecommerce_funnel.csv')
    product_path = os.path.join(DATA_DIR, 'product_conversion_funnels.csv')
    flowables = []

    # ── overall funnel bar chart ──
    if _csv_exists_nonempty(funnel_path):
        df = pd.read_csv(funnel_path)
        stage_order  = ['product_viewed', 'add_to_cart', 'checkout_started', 'order_completed']
        stage_labels = ['Product Viewed', 'Add to Cart', 'Checkout Started', 'Order Completed']
        df = df[df['event'].isin(stage_order)].copy()
        df['event'] = pd.Categorical(df['event'], categories=stage_order, ordered=True)
        df = df.sort_values('event')
        counts = df['count'].tolist()
        labels = [stage_labels[stage_order.index(e)] for e in df['event'].tolist()]
        stage_colors = [BLUE, '#4a7a9b', '#5a9a8a', GREEN][:len(counts)]
        mx = max(counts) if counts else 1
        fig, ax = plt.subplots(figsize=(W, 3.5))
        bars = ax.barh(labels[::-1], counts[::-1], color=stage_colors[::-1], alpha=0.9, zorder=3, height=0.55)
        for bar, val in zip(bars, counts[::-1]):
            ax.text(bar.get_width() + mx*0.012, bar.get_y() + bar.get_height()/2,
                    f'{int(val):,}', va='center', fontsize=10, fontweight='bold', color=DARK)
        ax.set_xlabel('Event Count', fontsize=9)
        ax.set_title('Overall E-Commerce Conversion Funnel', fontsize=13, fontweight='bold', color=DARK, pad=10)
        ax.xaxis.grid(True, alpha=0.3, linestyle='--')
        ax.set_axisbelow(True)
        _base_ax_style(ax)
        plt.tight_layout()
        flowables += [_img(_save_fig(fig), h=3.5), Spacer(1, 0.2*inch)]

    # ── per-product grouped bar chart ──
    if _csv_exists_nonempty(product_path):
        pdf = pd.read_csv(product_path)
        pdf = pdf[~pdf['product_title'].str.lower().str.contains('test', na=False)]
        pdf = pdf[pdf['view_to_cart_rate_pct'] <= 500]
        if not pdf.empty:
            # Grouped bar: views, add_to_cart, orders per product
            n = len(pdf)
            x = list(range(n))
            bar_w = 0.25
            fig2, ax2 = plt.subplots(figsize=(W, max(3.5, n * 0.6)))
            ax2.bar([i - bar_w for i in x], pdf['views'],           width=bar_w, label='Views',       color=BLUE,   alpha=0.85)
            ax2.bar(x,                       pdf['add_to_cart_count'], width=bar_w, label='Add to Cart', color=ORANGE, alpha=0.85)
            ax2.bar([i + bar_w for i in x], pdf['orders_completed'], width=bar_w, label='Orders',      color=GREEN,  alpha=0.85)
            ax2.set_xticks(x)
            ax2.set_xticklabels(pdf['product_title'].tolist(), rotation=30, ha='right', fontsize=8)
            ax2.set_ylabel('Count', fontsize=9)
            ax2.set_title('Per-Product: Views vs Add-to-Cart vs Orders', fontsize=12, fontweight='bold', color=DARK, pad=10)
            ax2.legend(fontsize=9, frameon=False)
            ax2.yaxis.grid(True, alpha=0.3, linestyle='--')
            ax2.set_axisbelow(True)
            _base_ax_style(ax2)
            plt.tight_layout()
            flowables += [_img(_save_fig(fig2), h=max(3.5, n*0.6)), Spacer(1, 0.15*inch)]

            # Keep per-product table
            flowables.append(Paragraph('Per-Product Conversion Details', _sub_style))
            flowables.append(Spacer(1, 0.08*inch))
            col_labels = ['Product', 'Views', 'Add to Cart', 'View→Cart %', 'View→Order %', 'Orders']
            pdf_display = pdf[['product_title','views','add_to_cart_count',
                                'view_to_cart_rate_pct','view_to_order_rate_pct','orders_completed']].copy()
            pdf_display.columns = col_labels
            for col in ['Views', 'Add to Cart', 'Orders']:
                pdf_display[col] = pdf_display[col].astype(int)
            flowables += [_build_plain_table(pdf_display, col_labels=col_labels), Spacer(1, 0.15*inch)]

    return flowables, True


def _chart_top_products():
    path = os.path.join(DATA_DIR, 'top_products.csv')
    if not _csv_exists_nonempty(path):
        return [], False
    df = pd.read_csv(path)
    df = df[~df['product_title'].str.lower().str.contains('test', na=False)]
    df = df.nlargest(5, 'views').sort_values('views')
    if df.empty:
        return [], False
    h = max(2.5, len(df) * 0.65)
    fig, ax = plt.subplots(figsize=(W, h))
    bars = ax.barh(df['product_title'], df['views'], color=BLUE, alpha=0.85, zorder=3)
    ax.set_xlabel('Views', fontsize=9)
    ax.set_title('Top Viewed Products', fontsize=13, fontweight='bold', color=DARK, pad=10)
    ax.xaxis.grid(True, alpha=0.3, linestyle='--')
    ax.set_axisbelow(True)
    mx = df['views'].max()
    for bar, val in zip(bars, df['views']):
        ax.text(bar.get_width() + mx*0.01, bar.get_y() + bar.get_height()/2,
                f'{int(val):,}', va='center', fontsize=9, color=DARK)
    _base_ax_style(ax)
    plt.tight_layout()
    return [_img(_save_fig(fig), h=h), Spacer(1, 0.1*inch)], True


def _chart_revenue():
    path      = os.path.join(DATA_DIR, 'revenue.csv')
    prev_path = os.path.join(DATA_DIR, 'revenue_previous.csv')
    if not _csv_exists_nonempty(path):
        return [], False

    df   = pd.read_csv(path)
    vals = df['revenue'].tolist()
    x    = list(range(len(df)))
    first_nonzero = next((i for i, v in enumerate(vals) if v > 0), 0)
    flowables = []

    fig, ax = plt.subplots(figsize=(W, H))
    if first_nonzero > 0:
        ax.plot(x[:first_nonzero+1], vals[:first_nonzero+1],
                color=BLUE, linewidth=1.5, linestyle='--', alpha=0.35)
        ax.plot(x[first_nonzero:], vals[first_nonzero:],
                color=BLUE, linewidth=2.5, marker='o', markersize=5)
        ax.fill_between(x[first_nonzero:], vals[first_nonzero:], alpha=0.12, color=BLUE)
        ax.text(first_nonzero // 2, max(vals) * 0.12, 'tracking not yet active',
                ha='center', fontsize=8, color='#999999', fontstyle='italic')
    else:
        ax.plot(x, vals, color=BLUE, linewidth=2.5, marker='o', markersize=5)
        ax.fill_between(x, vals, alpha=0.12, color=BLUE)
    ax.set_xticks(x)
    ax.set_xticklabels(df['date'].tolist(), rotation=45, ha='right', fontsize=8)
    ax.set_ylabel('Revenue ($)', fontsize=9)
    ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda v, _: f'${v:,.0f}'))
    ax.set_title('Daily Revenue (This Week)', fontsize=13, fontweight='bold', color=DARK, pad=10)
    ax.yaxis.grid(True, alpha=0.3, linestyle='--')
    ax.set_axisbelow(True)
    _base_ax_style(ax)
    plt.tight_layout()
    flowables += [_img(_save_fig(fig)), Spacer(1, 0.15*inch)]

    # WoW stat boxes
    curr_total = sum(vals)
    curr_avg   = curr_total / len(vals) if vals else 0
    stats = []
    if _csv_exists_nonempty(prev_path):
        prev_df    = pd.read_csv(prev_path)
        prev_vals  = prev_df['revenue'].tolist()
        prev_total = sum(prev_vals)
        prev_avg   = prev_total / len(prev_vals) if prev_vals else 0

        tot_pct, tot_color, tot_arrow = _wow_change(curr_total, prev_total)
        avg_pct, avg_color, avg_arrow = _wow_change(curr_avg,   prev_avg)

        stats = [
            ("Total Revenue This Week", f"${curr_total:,.0f}",
             f"{tot_arrow}{tot_pct:.1f}% vs last week" if tot_pct is not None else "no prior data",
             tot_color),
            ("Avg Daily Revenue",       f"${curr_avg:,.0f}",
             f"{avg_arrow}{avg_pct:.1f}% vs last week" if avg_pct is not None else "no prior data",
             avg_color),
        ]
    else:
        stats = [
            ("Total Revenue This Week", f"${curr_total:,.0f}", "no prior week data", '#888888'),
            ("Avg Daily Revenue",       f"${curr_avg:,.0f}",   "no prior week data", '#888888'),
        ]

    fig2 = _stat_boxes_fig(stats)
    flowables += [_img(_save_fig(fig2), h=1.6), Spacer(1, 0.1*inch)]
    return flowables, True


def _chart_aov():
    path = os.path.join(DATA_DIR, 'aov.csv')
    if not _csv_exists_nonempty(path):
        return [], False
    df = pd.read_csv(path)
    this = df[df['period'] == 'this_week']
    last = df[df['period'] == 'last_week']
    if this.empty or float(this['order_count'].iloc[0]) == 0:
        return [], False

    curr_aov   = float(this['aov'].iloc[0])
    curr_ord   = int(this['order_count'].iloc[0])
    curr_rev   = float(this['total_revenue'].iloc[0])
    prev_aov   = float(last['aov'].iloc[0]) if not last.empty else 0
    prev_ord   = int(last['order_count'].iloc[0]) if not last.empty else 0

    aov_pct, aov_color, aov_arrow = _wow_change(curr_aov, prev_aov)
    ord_pct, ord_color, ord_arrow = _wow_change(curr_ord, prev_ord)

    stats = [
        ("Avg Order Value (AOV)", f"${curr_aov:,.2f}",
         f"{aov_arrow}{aov_pct:.1f}% vs last week" if aov_pct is not None else "no prior data",
         aov_color),
        ("Orders This Week", f"{curr_ord}",
         f"{ord_arrow}{ord_pct:.1f}% vs last week" if ord_pct is not None else "no prior data",
         ord_color),
        ("Total Revenue", f"${curr_rev:,.0f}", "this week", '#555555'),
    ]
    fig = _stat_boxes_fig(stats)
    return [_img(_save_fig(fig), h=1.6), Spacer(1, 0.1*inch)], True


def _chart_abandonment():
    cart_path     = os.path.join(DATA_DIR, 'cart_abandonment.csv')
    checkout_path = os.path.join(DATA_DIR, 'checkout_abandonment.csv')
    if not _csv_exists_nonempty(cart_path) and not _csv_exists_nonempty(checkout_path):
        return [], False
    try:
        cart_data     = dict(zip(*[pd.read_csv(cart_path)[c].tolist() for c in ['metric','value']])) if _csv_exists_nonempty(cart_path) else {}
        checkout_data = dict(zip(*[pd.read_csv(checkout_path)[c].tolist() for c in ['metric','value']])) if _csv_exists_nonempty(checkout_path) else {}
        cart_rate     = float(cart_data.get('abandonment_rate_percent', 0))
        checkout_rate = float(checkout_data.get('abandonment_rate_percent', 0))
    except Exception:
        return [], False

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(W, 3.8))

    def donut(ax, rate, title, color):
        ax.pie([rate, 100-rate], colors=[color, '#e8e8e8'], startangle=90,
               wedgeprops=dict(width=0.45, linewidth=1.5, edgecolor='white'))
        ax.text(0, 0, f'{rate:.1f}%', ha='center', va='center',
                fontsize=17, fontweight='bold', color=DARK)
        ax.set_title(title, fontsize=10, fontweight='bold', color=DARK, pad=12)
        ax.legend(
            handles=[mpatches.Patch(color=color, label='Abandoned'),
                     mpatches.Patch(color='#e8e8e8', label='Completed')],
            loc='lower center', fontsize=8, frameon=False, bbox_to_anchor=(0.5, -0.18)
        )

    donut(ax1, cart_rate,     'Cart Abandonment',     RED)
    donut(ax2, checkout_rate, 'Checkout Abandonment', ORANGE)
    fig.suptitle('Abandonment Rates', fontsize=13, fontweight='bold', color=DARK, y=1.0)
    plt.tight_layout()
    return [_img(_save_fig(fig), h=3.8), Spacer(1, 0.1*inch)], True



def _chart_referrer_conversion():
    path = os.path.join(DATA_DIR, 'referrer_conversion.csv')
    if not _csv_exists_nonempty(path):
        return [], False
    df = pd.read_csv(path)
    df['referrer'] = df['referrer'].apply(lambda x: _truncate_url(str(x)) or str(x))
    df = df[~df['referrer'].str.lower().str.contains('posthog', na=False)]
    df = df.sort_values('conversion_rate_pct', ascending=False)

    col_labels = ['Referrer', 'Visitors', 'Converters', 'Conv. Rate %']
    table_data = [[Paragraph(h, _tbl_header) for h in col_labels]]
    style = [
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor(DARK)),
        ('TEXTCOLOR',  (0,0), (-1,0), colors.white),
        ('GRID',       (0,0), (-1,-1), 0.5, colors.HexColor('#cccccc')),
        ('BOX',        (0,0), (-1,-1), 1,   colors.HexColor(DARK)),
        ('TOPPADDING',    (0,0), (-1,-1), 5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 5),
    ]
    for ri, (_, row) in enumerate(df.iterrows(), start=1):
        cr   = float(row['conversion_rate_pct'])
        s    = _tbl_bold if cr > 0 else _tbl_cell
        table_data.append([
            Paragraph(str(row['referrer']), s),
            Paragraph(str(int(row['visitors'])),   _tbl_cell),
            Paragraph(str(int(row['converters'])), _tbl_cell),
            Paragraph(f'{cr:.2f}%', _tbl_cell),
        ])
        row_bg = colors.HexColor('#f8f9fa') if ri % 2 == 1 else colors.white
        style.append(('BACKGROUND', (0,ri), (2,ri), row_bg))
        cr_color = (colors.HexColor('#d4edda') if cr >= 1 else
                    colors.HexColor('#fff3cd') if cr > 0 else
                    colors.HexColor('#f8d7da'))
        style.append(('BACKGROUND', (3,ri), (3,ri), cr_color))

    pw = LETTER[0] - 1.5 * inch
    col_widths = [pw*0.46, pw*0.18, pw*0.18, pw*0.18]
    tbl = Table(table_data, colWidths=col_widths, repeatRows=1)
    tbl.setStyle(TableStyle(style))
    return [tbl, Spacer(1, 0.15*inch)], True


# ── SEO / organic chart functions ────────────────────────────────────────────

def _chart_organic_sessions():
    path = os.path.join(DATA_DIR, 'organic_sessions.csv')
    if not _csv_exists_nonempty(path):
        return [], False
    df = pd.read_csv(path)
    this = df[df['period'] == 'this_week'].iloc[0] if len(df[df['period'] == 'this_week']) else None
    if this is None:
        return [], False

    this_org  = int(this['organic_sessions'])
    this_pct  = float(this['organic_pct_of_sessions']) if pd.notna(this['organic_pct_of_sessions']) else 0
    wow       = float(this['wow_change_percent']) if pd.notna(this.get('wow_change_percent', None)) else None

    # MoM from this_month row
    mom_row = df[df['period'] == 'this_month']
    mom = float(mom_row.iloc[0]['mom_change_percent']) if not mom_row.empty and pd.notna(mom_row.iloc[0]['mom_change_percent']) else None

    # 8-week trend line (preferred) — fall back to 2-bar if trend CSV missing
    trend_path = os.path.join(DATA_DIR, 'organic_sessions_trend.csv')
    flowables = []
    if _csv_exists_nonempty(trend_path):
        tdf = pd.read_csv(trend_path)
        tdf = tdf[tdf['organic_sessions'] > 0]
        if len(tdf) >= 2:
            import matplotlib.dates as mdates
            tdf['week_dt'] = pd.to_datetime(tdf['week'])
            fig, ax = plt.subplots(figsize=(W, 3.2))
            vals = tdf['organic_sessions'].tolist()
            ax.fill_between(tdf['week_dt'], vals, alpha=0.12, color=BLUE)
            ax.plot(tdf['week_dt'], vals, color=BLUE, linewidth=2.2, marker='o',
                    markersize=5, zorder=4)
            for x, y in zip(tdf['week_dt'], vals):
                ax.annotate(f'{y:,}', (x, y), textcoords='offset points',
                            xytext=(0, 7), ha='center', fontsize=7.5, color=DARK)
            ax.xaxis.set_major_formatter(mdates.DateFormatter('%b %d'))
            ax.xaxis.set_major_locator(mdates.WeekdayLocator(byweekday=0))
            plt.xticks(rotation=30, ha='right', fontsize=8)
            ax.set_ylabel('Organic Sessions', fontsize=9)
            ax.set_title('Organic Search Sessions — 8-Week Trend',
                         fontsize=13, fontweight='bold', color=DARK, pad=10)
            ax.yaxis.grid(True, alpha=0.3, linestyle='--')
            ax.set_axisbelow(True)
            # WoW / MoM annotations top-right
            ann_parts = []
            if wow is not None:
                arrow = '▲' if wow >= 0 else '▼'
                ann_parts.append(f"{arrow} {abs(wow):.1f}% WoW")
            if mom is not None:
                arrow = '▲' if mom >= 0 else '▼'
                ann_parts.append(f"{arrow} {abs(mom):.1f}% MoM")
            if ann_parts:
                ax.text(0.98, 0.96, '  '.join(ann_parts), transform=ax.transAxes,
                        ha='right', va='top', fontsize=9, color=DARK,
                        bbox=dict(boxstyle='round,pad=0.3', fc='white', alpha=0.7))
            _base_ax_style(ax)
            plt.tight_layout()
            flowables = [_img(_save_fig(fig), w=W, h=3.2), Spacer(1, 0.12*inch)]

    # Stat boxes
    def _delta_str(val, label="vs last week"):
        if val is None: return "no prior data"
        return f"{'+' if val >= 0 else ''}{val:.1f}% {label}"
    def _delta_color(val):
        if val is None: return '#888888'
        return GREEN if val >= 0 else RED

    stats = [
        ("Organic Sessions",   f"{this_org:,}",     _delta_str(wow),       _delta_color(wow)),
        ("% of Total Traffic", f"{this_pct:.1f}%",  _delta_str(mom, "vs last month"), _delta_color(mom)),
    ]
    fig2 = _stat_boxes_fig(stats)
    flowables += [_img(_save_fig(fig2), h=1.6), Spacer(1, 0.1*inch)]

    # New vs returning donut (if available)
    nvr_path = os.path.join(DATA_DIR, 'organic_new_vs_returning.csv')
    if _csv_exists_nonempty(nvr_path):
        nvr = pd.read_csv(nvr_path)
        nvr = nvr[nvr['user_count'] > 0]
        if not nvr.empty:
            labels  = nvr['user_type'].str.capitalize().tolist()
            sizes   = nvr['user_count'].tolist()
            clrs    = [BLUE, GREEN][:len(sizes)]
            total_u = sum(sizes)
            fig3, ax3 = plt.subplots(figsize=(4.5, 3.5))
            ax3.pie(
                sizes, labels=None, colors=clrs,
                wedgeprops=dict(width=0.4), startangle=90)
            ax3.text(0, 0, f'{total_u:,}\nusers', ha='center', va='center',
                     fontsize=11, fontweight='bold', color=DARK)
            ax3.legend(
                [f"{l}: {v:,} ({p:.0f}%)" for l, v, p in zip(labels, sizes, nvr['percentage'].tolist())],
                loc='lower center', bbox_to_anchor=(0.5, -0.08), ncol=2, fontsize=9)
            ax3.set_title('New vs Returning Organic Visitors', fontsize=11,
                          fontweight='bold', color=DARK, pad=10)
            plt.tight_layout()
            flowables += [_img(_save_fig(fig3), w=4.5, h=3.5), Spacer(1, 0.1*inch)]

    # Session duration KPI (if available)
    dur_path = os.path.join(DATA_DIR, 'organic_session_duration.csv')
    if _csv_exists_nonempty(dur_path):
        dur = pd.read_csv(dur_path).set_index('metric')['value']
        all_fmt = str(dur.get('avg_duration_all_formatted', '—'))
        eng_fmt = str(dur.get('avg_duration_engaged_formatted', '—'))
        dur_wow = float(dur['wow_change_percent']) if pd.notna(dur.get('wow_change_percent')) else None
        dur_stats = [
            ("Avg Session Duration (All)",      all_fmt, _delta_str(dur_wow), _delta_color(dur_wow)),
            ("Avg Session Duration (Engaged)",  eng_fmt, "2+ pageview sessions", '#555555'),
        ]
        fig4 = _stat_boxes_fig(dur_stats)
        flowables += [_img(_save_fig(fig4), h=1.6), Spacer(1, 0.1*inch)]

    return flowables, True


def _chart_landing_pages_organic():
    path = os.path.join(DATA_DIR, 'top_landing_pages_organic.csv')
    if not _csv_exists_nonempty(path):
        return [], False
    df = pd.read_csv(path)
    def _path_label(url, max_len=38):
        """Extract path only (strip domain) and cap length."""
        from urllib.parse import urlparse
        try:
            path = urlparse(str(url)).path.rstrip('/')
        except Exception:
            path = str(url)
        if not path or path == '':
            path = '/'
        if len(path) > max_len:
            path = path[:max_len - 3] + '...'
        return path

    df['label'] = df['url'].apply(_path_label)
    df = df[df['label'].notna()].head(15).sort_values('organic_sessions')
    if df.empty:
        return [], False

    # Color by page_type if column exists
    type_colors = {'product': BLUE, 'collection': GREEN, 'blog': ORANGE, 'other': '#aaaaaa'}
    if 'page_type' in df.columns:
        bar_colors = df['page_type'].map(type_colors).fillna('#aaaaaa').tolist()
    else:
        bar_colors = BLUE

    h = max(3.5, len(df) * 0.5)
    fig, ax = plt.subplots(figsize=(W, h))
    ax.barh(df['label'], df['organic_sessions'], color=bar_colors, alpha=0.85, zorder=3)
    ax.set_xlabel('Organic Sessions', fontsize=9)
    ax.set_title('Top Landing Pages by Organic Traffic', fontsize=12, fontweight='bold', color=DARK, pad=10)
    ax.xaxis.grid(True, alpha=0.3, linestyle='--')
    ax.set_axisbelow(True)
    mx = df['organic_sessions'].max()
    for i, (_, row) in enumerate(df.iterrows()):
        ax.text(row['organic_sessions'] + mx * 0.01, i,
                f'{int(row["organic_sessions"]):,}', va='center', fontsize=8, color=DARK)

    # Legend for page types
    if 'page_type' in df.columns:
        seen_types = df['page_type'].unique()
        legend_patches = [mpatches.Patch(color=type_colors[t], label=t.capitalize())
                          for t in ['product', 'collection', 'blog', 'other'] if t in seen_types]
        ax.legend(handles=legend_patches, loc='lower right', fontsize=8)

    _base_ax_style(ax)
    fig.subplots_adjust(left=0.4, right=0.92, top=0.92, bottom=0.08)
    return [_img(_save_fig(fig), h=h), Spacer(1, 0.1*inch)], True


def _chart_blog_posts_organic():
    path = os.path.join(DATA_DIR, 'top_blog_posts.csv')
    if not _csv_exists_nonempty(path):
        return [], False
    df = pd.read_csv(path)
    # Use human-readable title column; fall back to slug or URL
    if 'title' in df.columns:
        df['label'] = df['title'].apply(lambda t: str(t)[:38] + '…' if len(str(t)) > 38 else str(t))
    elif 'slug' in df.columns:
        df['label'] = df['slug'].apply(lambda s: str(s)[:38] + '…' if len(str(s)) > 38 else str(s))
    else:
        df['label'] = df['url'].apply(_base_url)
    df = df[df['label'].notna()].head(10).sort_values('organic_sessions')
    if df.empty:
        return [], False
    h = max(3.0, len(df) * 0.5)
    fig, ax = plt.subplots(figsize=(W, h))
    bars = ax.barh(df['label'], df['organic_sessions'], color=GREEN, alpha=0.85, zorder=3)
    ax.set_xlabel('Organic Sessions', fontsize=9)
    ax.set_title('Top Blog Posts by Organic Traffic', fontsize=12, fontweight='bold', color=DARK, pad=10)
    ax.xaxis.grid(True, alpha=0.3, linestyle='--')
    ax.set_axisbelow(True)
    mx = df['organic_sessions'].max() or 1
    for bar, val in zip(bars, df['organic_sessions']):
        ax.text(bar.get_width() + mx*0.01, bar.get_y() + bar.get_height()/2,
                f'{int(val):,}', va='center', fontsize=8, color=DARK)
    _base_ax_style(ax)
    fig.subplots_adjust(left=0.35, right=0.92, top=0.92, bottom=0.08)
    return [_img(_save_fig(fig), h=h), Spacer(1, 0.1*inch)], True


def _chart_page_traffic_changes():
    gains_path = os.path.join(DATA_DIR, 'page_traffic_top_gains.csv')
    drops_path = os.path.join(DATA_DIR, 'page_traffic_top_drops.csv')
    # Fall back to old single CSV if new split files don't exist yet
    if not _csv_exists_nonempty(gains_path) and not _csv_exists_nonempty(drops_path):
        old = os.path.join(DATA_DIR, 'page_traffic_changes.csv')
        if not _csv_exists_nonempty(old):
            return [], False
        df = pd.read_csv(old)
        col = 'wow_change_pct' if 'wow_change_pct' in df.columns else 'change_percent'
        df = df.rename(columns={col: 'wow_change_pct',
                                 'url': 'path',
                                 'this_week_views': 'sessions_this_week',
                                 'last_week_views': 'sessions_last_week'})
        gains = df[df['wow_change_pct'] > 0].nlargest(10, 'wow_change_pct')
        drops = df[df['wow_change_pct'] < 0].nsmallest(10, 'wow_change_pct')
    else:
        gains = pd.read_csv(gains_path) if _csv_exists_nonempty(gains_path) else pd.DataFrame()
        drops = pd.read_csv(drops_path) if _csv_exists_nonempty(drops_path) else pd.DataFrame()

    def _label(path, max_len=42):
        s = str(path)
        return s if len(s) <= max_len else s[:max_len - 3] + '...'

    def _annot(row):
        tw = int(row.get('sessions_this_week', 0))
        lw = int(row.get('sessions_last_week', 0))
        chg = float(row.get('wow_change_pct', 0))
        sign = '+' if chg >= 0 else ''
        return f"{lw}→{tw}  {sign}{chg:.0f}%"

    flowables = []

    if not gains.empty:
        gains = gains.sort_values('wow_change_pct')
        gains['label'] = gains['path'].apply(_label)
        h = max(2.5, len(gains) * 0.55)
        fig, ax = plt.subplots(figsize=(W, h))
        ax.barh(gains['label'], gains['wow_change_pct'], color=GREEN, alpha=0.85, zorder=3)
        ax.set_xlabel('WoW Change (%)', fontsize=9)
        ax.set_title('Pages with Significant Traffic Gains (WoW)', fontsize=11,
                     fontweight='bold', color=DARK, pad=10)
        ax.xaxis.grid(True, alpha=0.3, linestyle='--')
        ax.set_axisbelow(True)
        mx = gains['wow_change_pct'].max() or 1
        for i, (_, row) in enumerate(gains.iterrows()):
            ax.text(row['wow_change_pct'] + mx * 0.01, i,
                    _annot(row), va='center', fontsize=7.5, color=DARK)
        _base_ax_style(ax)
        fig.subplots_adjust(left=0.38, right=0.88, top=0.92, bottom=0.08)
        flowables += [_img(_save_fig(fig), h=h), Spacer(1, 0.15 * inch)]

    if not drops.empty:
        drops = drops.sort_values('wow_change_pct', ascending=False)
        drops['label'] = drops['path'].apply(_label)
        h = max(2.5, len(drops) * 0.55)
        fig2, ax2 = plt.subplots(figsize=(W, h))
        ax2.barh(drops['label'], drops['wow_change_pct'], color=RED, alpha=0.85, zorder=3)
        ax2.set_xlabel('WoW Change (%)', fontsize=9)
        ax2.set_title('Pages with Significant Traffic Drops (WoW)', fontsize=11,
                      fontweight='bold', color=DARK, pad=10)
        ax2.xaxis.grid(True, alpha=0.3, linestyle='--')
        ax2.set_axisbelow(True)
        mn = drops['wow_change_pct'].min() or -1
        for i, (_, row) in enumerate(drops.iterrows()):
            ax2.text(row['wow_change_pct'] + mn * 0.01, i,
                     _annot(row), va='center', fontsize=7.5, color=DARK)
        _base_ax_style(ax2)
        fig2.subplots_adjust(left=0.38, right=0.88, top=0.92, bottom=0.08)
        flowables += [_img(_save_fig(fig2), h=h), Spacer(1, 0.1 * inch)]

    if not flowables:
        return [], False
    return flowables, True


def _chart_collection_pages():
    path = os.path.join(DATA_DIR, 'collection_pages_performance.csv')
    if not _csv_exists_nonempty(path):
        return [], False
    df = pd.read_csv(path).fillna(0)
    if df.empty or 'display_name' not in df.columns:
        return [], False

    df = df.sort_values('total_sessions_this_week').tail(20)  # top 20, bottom = highest

    def _lbl(row):
        name = str(row.get('display_name', row.get('collection_name', '')))[:40]
        return ('★ ' + name) if row.get('is_priority') else name

    df['label'] = df.apply(_lbl, axis=1)

    x = range(len(df))
    w = 0.38
    h = max(3.5, len(df) * 0.55)
    fig, ax = plt.subplots(figsize=(W, h))
    ax.barh([i + w/2 for i in x], df['total_sessions_this_week'],
            height=w, color=BLUE, alpha=0.85, label='Total Sessions', zorder=3)
    ax.barh([i - w/2 for i in x], df['organic_sessions'],
            height=w, color=GREEN, alpha=0.85, label='Organic Sessions', zorder=3)
    ax.set_yticks(list(x))
    ax.set_yticklabels(df['label'], fontsize=8)
    ax.set_xlabel('Sessions', fontsize=9)
    ax.set_title('Collection Pages — Total vs Organic Sessions', fontsize=11,
                 fontweight='bold', color=DARK, pad=10)
    ax.xaxis.grid(True, alpha=0.3, linestyle='--')
    ax.set_axisbelow(True)
    ax.legend(fontsize=8, loc='lower right')
    # Annotate organic % and WoW on right side
    mx = df['total_sessions_this_week'].max() or 1
    for i, (_, row) in enumerate(df.iterrows()):
        wow = float(row.get('wow_change_pct', 0))
        sign = '+' if wow >= 0 else ''
        ax.text(mx * 1.02, i, f"{sign}{wow:.0f}% WoW", va='center', fontsize=7, color=DARK)
    _base_ax_style(ax)
    fig.subplots_adjust(left=0.35, right=0.88, top=0.92, bottom=0.08)
    return [_img(_save_fig(fig), h=h), Spacer(1, 0.1 * inch)], True


def _chart_size_pages():
    path = os.path.join(DATA_DIR, 'size_pages_performance.csv')
    if not _csv_exists_nonempty(path):
        return [], False
    df = pd.read_csv(path).fillna(0)
    if df.empty:
        return [], False

    df = df.sort_values('total_sessions_this_week').tail(15)
    df['label'] = df['display_name'].apply(lambda s: str(s)[:42] + '…' if len(str(s)) > 42 else str(s))

    h = max(2.5, len(df) * 0.5)
    fig, ax = plt.subplots(figsize=(W, h))
    ax.barh(df['label'], df['organic_sessions'], color=ORANGE, alpha=0.85, zorder=3)
    ax.set_xlabel('Organic Sessions', fontsize=9)
    ax.set_title('Boxes-by-Size Pages — Organic Traffic', fontsize=11,
                 fontweight='bold', color=DARK, pad=10)
    ax.xaxis.grid(True, alpha=0.3, linestyle='--')
    ax.set_axisbelow(True)
    mx = df['organic_sessions'].max() or 1
    for i, (_, row) in enumerate(df.iterrows()):
        wow = float(row.get('wow_change_pct', 0))
        sign = '+' if wow >= 0 else ''
        label = f"{int(row['organic_sessions']):,}  ({sign}{wow:.0f}% WoW)"
        ax.text(row['organic_sessions'] + mx * 0.01, i,
                label, va='center', fontsize=7.5, color=DARK)
    _base_ax_style(ax)
    fig.subplots_adjust(left=0.35, right=0.88, top=0.92, bottom=0.08)
    return [_img(_save_fig(fig), h=h), Spacer(1, 0.1 * inch)], True


# ── CONVERSIONS charts ────────────────────────────────────────────────────────

def _fmt_delta(value, reverse=False):
    """Returns (text, color). reverse=True means down is good (bounce, LCP, etc.)."""
    if value is None:
        return 'N/A', '#999999'
    is_good = (value < 0) if reverse else (value > 0)
    arrow = '▲' if value > 0 else ('▼' if value < 0 else '–')
    color = '#22c55e' if is_good else '#ef4444'
    return f'{arrow} {abs(value):.1f}%', color


def _chart_organic_conversions():
    path = os.path.join(DATA_DIR, 'organic_conversions.csv')
    if not _csv_exists_nonempty(path):
        return [], False
    df = pd.read_csv(path)
    df = df[df['conversion_type'] != 'combined']
    if df.empty:
        return [], False

    labels   = df['conversion_type'].str.replace('_', ' ').str.title().tolist()
    tw_rates = df['conversion_rate'].tolist()
    lw_rates = df['rate_last_week'].tolist()
    x = range(len(labels))
    w = 0.35

    fig, ax = plt.subplots(figsize=(W, 3.5))
    bars_tw = ax.bar([i - w/2 for i in x], tw_rates, width=w,
                     color=BLUE, alpha=0.9, label='This Week', zorder=3)
    ax.bar([i + w/2 for i in x], lw_rates, width=w,
           color='#a0b4c8', alpha=0.9, label='Last Week', zorder=3)
    ax.set_xticks(list(x))
    ax.set_xticklabels(labels, fontsize=9)
    ax.set_ylabel('Conversion Rate (%)', fontsize=9)
    ax.set_title('Organic Conversion Rates by Type', fontsize=12,
                 fontweight='bold', color=DARK, pad=10)
    ax.yaxis.grid(True, alpha=0.3, linestyle='--')
    ax.set_axisbelow(True)
    ax.legend(fontsize=8)
    mx = max(tw_rates + lw_rates) or 0.1
    for bar, rate in zip(bars_tw, tw_rates):
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + mx*0.02,
                f'{rate:.2f}%', ha='center', va='bottom', fontsize=8, color=DARK)
    _base_ax_style(ax)
    plt.tight_layout()

    flowables = [_img(_save_fig(fig), w=W, h=3.5), Spacer(1, 0.12*inch)]

    # Combined rate stat box
    combined = pd.read_csv(path)
    combined = combined[combined['conversion_type'] == 'combined']
    if not combined.empty:
        row = combined.iloc[0]
        wow = float(row['wow_change_pct']) if pd.notna(row['wow_change_pct']) else None
        mom = float(row['mom_change_pct']) if pd.notna(row['mom_change_pct']) else None
        wow_txt, wow_clr = _fmt_delta(wow)
        mom_txt, mom_clr = _fmt_delta(mom)
        stats = [
            ("Combined Organic Conversion Rate",
             f"{float(row['conversion_rate']):.2f}%", wow_txt, wow_clr),
            ("Total Organic Conversions (All Types)",
             f"{float(row.get('count_30d', 0)):.0f}",
             mom_txt, mom_clr),
        ]
        fig2 = _stat_boxes_fig(stats)
        flowables += [_img(_save_fig(fig2), h=1.6), Spacer(1, 0.1*inch)]

    return flowables, True


def _chart_organic_revenue():
    path = os.path.join(DATA_DIR, 'organic_revenue.csv')
    if not _csv_exists_nonempty(path):
        return [], False
    df = pd.read_csv(path)
    if df.empty:
        return [], False
    row = df.iloc[0]

    rev_tw   = float(row.get('organic_revenue_this_week', 0))
    total_tw = float(row.get('total_revenue_this_week', 0))
    non_org  = max(total_tw - rev_tw, 0)
    pct_tot  = float(row.get('organic_revenue_pct_of_total', 0))
    aov      = float(row.get('organic_aov', 0))
    cnt      = int(row.get('organic_order_count', 0))

    # Donut: organic vs non-organic
    fig, (ax_kpi, ax_donut) = plt.subplots(1, 2, figsize=(W, 3.2),
                                            gridspec_kw={'width_ratios': [1.4, 1]})

    # Left: KPI text panel
    ax_kpi.axis('off')
    kpis = [
        (f'${rev_tw:,.2f}', 'Organic Revenue'),
        (f'${aov:,.2f}',    'Organic AOV'),
        (f'{cnt}',          'Organic Orders'),
        (f'{pct_tot:.1f}%', '% of Total Revenue'),
    ]
    for i, (val, lbl) in enumerate(kpis):
        y = 0.82 - i * 0.22
        ax_kpi.text(0.05, y,      val, fontsize=13, fontweight='bold', color=DARK,
                    transform=ax_kpi.transAxes, va='top')
        ax_kpi.text(0.05, y-0.08, lbl, fontsize=8,  color='#666666',
                    transform=ax_kpi.transAxes, va='top')

    # Right: donut
    if total_tw > 0:
        sizes  = [max(rev_tw, 0), max(non_org, 0)]
        clrs   = [GREEN, '#d1dde8']
        ax_donut.pie(sizes, colors=clrs, wedgeprops=dict(width=0.4), startangle=90)
        ax_donut.text(0, 0, f'{pct_tot:.0f}%\norganic', ha='center', va='center',
                      fontsize=10, fontweight='bold', color=DARK)
        ax_donut.legend(['Organic', 'Other'], loc='lower center',
                         bbox_to_anchor=(0.5, -0.1), ncol=2, fontsize=8)
    else:
        ax_donut.text(0.5, 0.5, 'No\nrevenue data', ha='center', va='center',
                      fontsize=10, color='#888888', transform=ax_donut.transAxes)
        ax_donut.axis('off')

    plt.suptitle('Organic Revenue Attribution', fontsize=12,
                 fontweight='bold', color=DARK, y=1.0)
    plt.tight_layout()
    return [_img(_save_fig(fig), w=W, h=3.2), Spacer(1, 0.12*inch)], True


def _chart_organic_product_conversions():
    path = os.path.join(DATA_DIR, 'organic_product_conversions.csv')
    if not _csv_exists_nonempty(path):
        return [], False
    df = pd.read_csv(path).fillna(0)
    df = df[df['organic_views'] > 0].sort_values('organic_views').tail(15)
    if df.empty:
        return [], False

    labels  = df['product_name'].apply(lambda s: str(s)[:40] + '…' if len(str(s)) > 40 else str(s)).tolist()
    orders  = df['organic_orders'].tolist()
    quotes  = df['quote_requests'].tolist()
    samples = df['sample_requests'].tolist()

    h = max(3.5, len(df) * 0.55)
    fig, ax = plt.subplots(figsize=(W, h))

    y = range(len(labels))
    ax.barh(list(y), orders,  color=BLUE,   alpha=0.9, label='Orders',       zorder=3)
    ax.barh(list(y), quotes,  left=orders,  color=GREEN,  alpha=0.9, label='Quote Requests',  zorder=3)
    ax.barh(list(y), samples, left=[o+q for o,q in zip(orders, quotes)],
            color=ORANGE, alpha=0.9, label='Sample Requests', zorder=3)

    ax.set_yticks(list(y))
    ax.set_yticklabels(labels, fontsize=8)
    ax.set_xlabel('Conversions', fontsize=9)
    ax.set_title('Top Product Pages — Organic Conversions', fontsize=11,
                 fontweight='bold', color=DARK, pad=10)
    ax.xaxis.grid(True, alpha=0.3, linestyle='--')
    ax.set_axisbelow(True)
    ax.legend(fontsize=8, loc='lower right')
    _base_ax_style(ax)
    fig.subplots_adjust(left=0.38, right=0.95, top=0.92, bottom=0.08)
    return [_img(_save_fig(fig), h=h), Spacer(1, 0.1*inch)], True


# ── TECHNICAL charts ──────────────────────────────────────────────────────────

def _chart_web_vitals():
    path = os.path.join(DATA_DIR, 'core_web_vitals.csv')
    if not _csv_exists_nonempty(path):
        return [], False
    df = pd.read_csv(path).fillna({'avg_lcp_ms': 0, 'avg_cls': 0, 'avg_inp_ms': 0})
    if df.empty or not df.get('data_available', pd.Series([False])).any():
        note = Paragraph(
            "Core Web Vitals tracking was enabled on March 18, 2026. "
            "Full data will appear in the next weekly report.",
            _note_style)
        return [note], True

    df['label'] = df['display_name'].apply(
        lambda s: str(s)[:45] + '…' if len(str(s)) > 45 else str(s))

    grade_color = {'Good': '#86efac', 'Needs Improvement': '#fde68a',
                   'Poor': '#fca5a5', 'N/A': '#e5e7eb'}

    cols   = ['Page', 'Sessions', 'LCP (ms)', 'LCP Grade', 'CLS', 'CLS Grade', 'INP (ms)', 'INP Grade', 'Pass']
    data   = [cols]
    for _, r in df.iterrows():
        lcp_ms = f"{r['avg_lcp_ms']:.0f}" if r.get('avg_lcp_ms') else '—'
        cls_v  = f"{r['avg_cls']:.3f}"    if r.get('avg_cls')    else '—'
        inp_ms = f"{r['avg_inp_ms']:.0f}" if r.get('avg_inp_ms') else '—'
        data.append([
            str(r.get('label', r.get('display_name', '')))[:40],
            str(int(r.get('sessions', 0))),
            lcp_ms, str(r.get('lcp_grade', 'N/A')),
            cls_v,  str(r.get('cls_grade', 'N/A')),
            inp_ms, str(r.get('inp_grade', 'N/A')),
            '✓' if r.get('cwv_pass') else '✗',
        ])

    style = TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor(DARK)),
        ('TEXTCOLOR',  (0,0), (-1,0), colors.white),
        ('FONTNAME',   (0,0), (-1,0), 'Helvetica-Bold'),
        ('FONTSIZE',   (0,0), (-1,-1), 8),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, colors.HexColor('#f8fafc')]),
        ('GRID', (0,0), (-1,-1), 0.4, colors.HexColor('#e2e8f0')),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('TOPPADDING', (0,0), (-1,-1), 4),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
    ])
    # Color grade cells
    grade_cols = [3, 5, 7]  # LCP Grade, CLS Grade, INP Grade columns
    for row_i, row_data in enumerate(data[1:], start=1):
        for col_i in grade_cols:
            grade = row_data[col_i]
            bg = grade_color.get(grade, '#e5e7eb')
            style.add('BACKGROUND', (col_i, row_i), (col_i, row_i), colors.HexColor(bg))

    col_widths = [130, 55, 55, 75, 45, 75, 55, 75, 35]
    tbl = Table(data, colWidths=col_widths)
    tbl.setStyle(style)
    return [tbl, Spacer(1, 0.15*inch)], True


def _chart_404_errors():
    path = os.path.join(DATA_DIR, '404_errors.csv')
    summary_path = os.path.join(DATA_DIR, '404_summary.csv')

    # Check if data available
    if _csv_exists_nonempty(summary_path):
        summ = pd.read_csv(summary_path)
        if not summ.empty and not bool(summ.iloc[0].get('data_available', False)):
            note = Paragraph(
                "404 error tracking was enabled on March 18, 2026. "
                "Data will appear in the next weekly report.",
                _note_style)
            return [note], True

    if not _csv_exists_nonempty(path):
        return [], False
    df = pd.read_csv(path).fillna({'hits': 0})
    if df.empty:
        return [], False

    df = df.sort_values('hits').tail(15)
    df['label'] = df['path'].apply(
        lambda s: str(s)[:45] + '…' if len(str(s)) > 45 else str(s))

    h = max(2.5, len(df) * 0.45)
    fig, ax = plt.subplots(figsize=(W, h))
    ax.barh(df['label'], df['hits'], color=RED, alpha=0.85, zorder=3)
    ax.set_xlabel('404 Hits', fontsize=9)
    ax.set_title('404 Error Pages (This Week)', fontsize=11,
                 fontweight='bold', color=DARK, pad=10)
    ax.xaxis.grid(True, alpha=0.3, linestyle='--')
    ax.set_axisbelow(True)
    mx = df['hits'].max() or 1
    for i, (_, row) in enumerate(df.iterrows()):
        ax.text(row['hits'] + mx*0.01, i,
                f"{int(row['hits'])} hits", va='center', fontsize=7.5, color=DARK)
    _base_ax_style(ax)
    fig.subplots_adjust(left=0.35, right=0.92, top=0.92, bottom=0.08)
    return [_img(_save_fig(fig), h=h), Spacer(1, 0.1*inch)], True


# ── new section-level composite chart functions ───────────────────────────────

def _warning_banner(text):
    """Return a list of flowables that render as a yellow/amber warning box."""
    from reportlab.platypus import Table as RLTable, TableStyle as RLTS
    cell_para = Paragraph(
        f"<b>Data Quality Warning:</b> {text.replace('&','&amp;').replace('<','&lt;').replace('>','&gt;')}",
        ParagraphStyle('WarnCell', fontName='Times-Roman', fontSize=10, leading=14,
                       textColor=colors.HexColor('#7d4e00'))
    )
    tbl = RLTable([[cell_para]], colWidths=[6.5 * inch])
    tbl.setStyle(RLTS([
        ('BACKGROUND',    (0, 0), (-1, -1), colors.HexColor('#fff3cd')),
        ('BOX',           (0, 0), (-1, -1), 1.5, colors.HexColor('#e6a817')),
        ('TOPPADDING',    (0, 0), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ('LEFTPADDING',   (0, 0), (-1, -1), 10),
        ('RIGHTPADDING',  (0, 0), (-1, -1), 10),
    ]))
    return [tbl, Spacer(1, 0.12 * inch)]


def _chart_seo_executive_summary():
    """
    KPI stat boxes for the executive summary page.
    Reads organic_sessions, organic_conversions, and organic_revenue CSVs.
    The bullet-point text is already embedded in the content string
    from generate_executive_summary() so we only produce the top KPI row here.
    """
    stats = []

    try:
        df  = pd.read_csv(os.path.join(DATA_DIR, 'organic_sessions.csv'))
        tw  = df[df['period'] == 'this_week'].iloc[0]
        org = int(tw['organic_sessions'])
        wow = float(tw['wow_change_percent']) if pd.notna(tw.get('wow_change_percent')) else None
        wow_str   = (f"{'+' if wow >= 0 else ''}{wow:.1f}% WoW") if wow is not None else "—"
        wow_color = GREEN if (wow or 0) >= 0 else RED
        stats.append(("Organic Sessions", f"{org:,}", wow_str, wow_color))
    except Exception:
        stats.append(("Organic Sessions", "N/A", "—", '#888888'))

    try:
        df       = pd.read_csv(os.path.join(DATA_DIR, 'organic_conversions.csv'))
        combined = df[df['conversion_type'] == 'combined']
        if not combined.empty:
            rate  = float(combined.iloc[0]['conversion_rate'])
            count = int(combined.iloc[0].get('count_this_week', 0))
            wow   = float(combined.iloc[0]['wow_change_pct']) if pd.notna(combined.iloc[0].get('wow_change_pct')) else None
            wow_str   = (f"{'+' if wow >= 0 else ''}{wow:.1f}% WoW") if wow is not None else "—"
            wow_color = GREEN if (wow or 0) >= 0 else RED
            lbl   = "Organic Conv. Rate" if count > 0 else "Conv. Rate (0 — check tracking)"
            stats.append((lbl, f"{rate:.2f}%", wow_str, wow_color))
        else:
            stats.append(("Organic Conv. Rate", "—", "—", '#888888'))
    except Exception:
        stats.append(("Organic Conv. Rate", "—", "—", '#888888'))

    try:
        df  = pd.read_csv(os.path.join(DATA_DIR, 'organic_revenue.csv'))
        row = df.iloc[0]
        rev = float(row.get('organic_revenue_this_week', 0))
        wow = float(row['organic_revenue_wow_pct']) if pd.notna(row.get('organic_revenue_wow_pct')) else None
        wow_str   = (f"{'+' if wow >= 0 else ''}{wow:.1f}% WoW") if wow is not None else "—"
        wow_color = GREEN if (wow or 0) >= 0 else RED
        lbl   = "Organic Revenue" if rev > 0 else "Organic Revenue (check tracking)"
        stats.append((lbl, f"${rev:,.0f}", wow_str, wow_color))
    except Exception:
        stats.append(("Organic Revenue", "—", "—", '#888888'))

    fig = _stat_boxes_fig(stats)
    return [_img(_save_fig(fig), h=1.6), Spacer(1, 0.1 * inch)], True


def _chart_traffic_engagement():
    """
    Section 2: Traffic & Engagement.
    Combines organic sessions trend, new/returning donut, session duration,
    and the organic bounce rate gauge — all in one section.
    """
    flowables, _ = _chart_organic_sessions()
    if not flowables:
        return [], False

    # Append organic bounce rate stat boxes (compact, not the full gauge)
    br_path = os.path.join(DATA_DIR, 'bounce_rate.csv')
    if _csv_exists_nonempty(br_path):
        df = pd.read_csv(br_path)
        data = dict(zip(df['metric'], df['value'].astype(float)))
        org_rate   = data.get('organic_bounce_rate_percent', 0)
        org_sess   = int(data.get('organic_sessions', 0))
        wow_val    = data.get('organic_bounce_rate_wow_pct')
        mom_val    = data.get('organic_bounce_rate_mom_pct')
        if org_sess > 0:
            def _br_delta(v, lbl):
                if v is None or (isinstance(v, float) and v != v):
                    return f"{lbl}: unavailable"
                return f"{'+' if v >= 0 else ''}{v:.1f}% {lbl}"
            def _br_color(v):
                if v is None or (isinstance(v, float) and v != v):
                    return '#888888'
                return RED if v >= 0 else GREEN   # higher bounce = worse
            stats_br = [
                ("Organic Bounce Rate", f"{org_rate:.1f}%",
                 _br_delta(wow_val, "vs last week"),  _br_color(wow_val)),
                ("Organic Bounce Rate (30-day)", f"{org_rate:.1f}%",
                 _br_delta(mom_val, "vs last month"), _br_color(mom_val)),
            ]
            fig_br = _stat_boxes_fig(stats_br)
            flowables += [_img(_save_fig(fig_br), h=1.6), Spacer(1, 0.1 * inch)]

    return flowables, True


def _chart_organic_conversions_revenue():
    """
    Section 3: Organic Conversions & Revenue.
    Renders a validation warning banner if conversion data is zero/missing,
    then shows conversion rates, revenue attribution, and top product converters.
    """
    from enhanced_ai_engine import validate_conversion_data
    flowables = []

    # Data quality check — prepend warning if needed
    warnings = validate_conversion_data()
    for w in warnings:
        flowables += _warning_banner(w)

    # Conversion rate chart
    conv_fl, _ = _chart_organic_conversions()
    flowables += conv_fl

    # Revenue chart
    rev_fl, _ = _chart_organic_revenue()
    flowables += rev_fl

    # Product conversions chart (suppress if empty / all-zero)
    prod_path = os.path.join(DATA_DIR, 'organic_product_conversions.csv')
    if _csv_exists_nonempty(prod_path):
        df = pd.read_csv(prod_path).fillna(0)
        # Only show if at least one product has >0 total conversions or >20 organic views
        if (df['total_conversions'].sum() > 0 or df['organic_views'].sum() > 0):
            prod_fl, _ = _chart_organic_product_conversions()
            flowables += prod_fl
        else:
            flowables += _warning_banner(
                "No product page conversion data available this week. "
                "This may indicate that organic product page views are below the minimum threshold (20 sessions)."
            )

    return (flowables, True) if flowables else ([], False)


def _build_cwv_table(df):
    """
    Build a compact ReportLab Table for Core Web Vitals data.
    Columns: Page | LCP | CLS | INP | Status | Source
    Status cells are color-coded: red=Poor, orange=Needs Improvement, green=Good.
    Returns a Table flowable or None if df is empty.
    """
    from reportlab.platypus import Table as RLTable, TableStyle as RLTS

    STATUS_COLORS = {
        "Poor":             colors.HexColor('#fde8e8'),
        "Needs Improvement":colors.HexColor('#fff3cd'),
        "Good":             colors.HexColor('#e8f5e9'),
        "No Data":          colors.HexColor('#f5f5f5'),
    }
    STATUS_TEXT = {
        "Poor":             colors.HexColor('#b71c1c'),
        "Needs Improvement":colors.HexColor('#7d4e00'),
        "Good":             colors.HexColor('#1b5e20'),
        "No Data":          colors.HexColor('#888888'),
    }
    SOURCE_SHORT = {"page-level": "Page", "origin-level": "Origin", "no data": "No Data"}

    headers = ["Page", "LCP", "CLS", "INP", "Status", "Source"]
    col_widths = [2.2*inch, 0.85*inch, 0.75*inch, 0.85*inch, 1.15*inch, 0.65*inch]

    table_data = [[Paragraph(h, _tbl_header) for h in headers]]
    style = [
        ('BACKGROUND',    (0, 0), (-1, 0), colors.HexColor(DARK)),
        ('TEXTCOLOR',     (0, 0), (-1, 0), colors.white),
        ('GRID',          (0, 0), (-1, -1), 0.4, colors.HexColor('#cccccc')),
        ('BOX',           (0, 0), (-1, -1), 1,   colors.HexColor(DARK)),
        ('TOPPADDING',    (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ('LEFTPADDING',   (0, 0), (-1, -1), 5),
        ('FONTSIZE',      (0, 1), (-1, -1), 8),
    ]

    for row_idx, (_, row) in enumerate(df.iterrows(), start=1):
        path   = str(row.get("page_path", ""))[:38]
        lcp    = f"{int(row['lcp_ms']):,} ms" if pd.notna(row.get("lcp_ms")) else "—"
        cls    = f"{float(row['cls']):.3f}"   if pd.notna(row.get("cls"))    else "—"
        inp    = f"{int(row['inp_ms']):,} ms" if pd.notna(row.get("inp_ms")) else "—"
        status = str(row.get("overall_cwv_status", "No Data"))
        source = SOURCE_SHORT.get(str(row.get("cwv_source", "no data")), "—")

        # Color metric cells by their individual label
        def _metric_bg(label_col):
            lbl = str(row.get(label_col, "No Data"))
            return STATUS_COLORS.get(lbl, colors.white)

        cells = [
            Paragraph(path,   _tbl_cell),
            Paragraph(lcp,    _tbl_cell),
            Paragraph(cls,    _tbl_cell),
            Paragraph(inp,    _tbl_cell),
            Paragraph(f"<b>{status}</b>",
                      ParagraphStyle('CWVStatus', parent=_tbl_cell,
                                     textColor=STATUS_TEXT.get(status, colors.black))),
            Paragraph(source, _tbl_cell),
        ]
        table_data.append(cells)

        row_bg = colors.HexColor('#f8f9fa') if row_idx % 2 == 1 else colors.white
        style.append(('BACKGROUND', (0, row_idx), (-1, row_idx), row_bg))
        # Color the metric cells by grade
        for col_i, label_col in [(1, "lcp_label"), (2, "cls_label"), (3, "inp_label")]:
            bg = _metric_bg(label_col)
            style.append(('BACKGROUND', (col_i, row_idx), (col_i, row_idx), bg))
        # Color the status cell
        style.append(('BACKGROUND', (4, row_idx), (4, row_idx),
                       STATUS_COLORS.get(status, colors.white)))

    tbl = RLTable(table_data, colWidths=col_widths, repeatRows=1)
    tbl.setStyle(RLTS(style))
    return tbl


def _cwv_summary_paragraph(df):
    """
    Return a one-line Paragraph summarizing CWV results.
    Example: "3 Good, 4 Needs Improvement, 1 Poor across 8 pages (mix of page- and origin-level data)."
    """
    if df.empty:
        return Paragraph("No Core Web Vitals data available.", _note_style)

    counts = df["overall_cwv_status"].value_counts().to_dict()
    good   = counts.get("Good", 0)
    ni     = counts.get("Needs Improvement", 0)
    poor   = counts.get("Poor", 0)
    no_d   = counts.get("No Data", 0)
    total  = len(df)

    parts = []
    if good:   parts.append(f"{good} Good")
    if ni:     parts.append(f"{ni} Needs Improvement")
    if poor:   parts.append(f"{poor} Poor")
    if no_d:   parts.append(f"{no_d} No Data")
    summary = ", ".join(parts) + f" across {total} pages."

    # Most common failing metric
    if poor + ni > 0:
        data_rows = df[df["overall_cwv_status"].isin(["Poor", "Needs Improvement"])]
        metric_fails = {}
        for col in ["lcp_label", "cls_label", "inp_label"]:
            metric_fails[col] = (data_rows[col].isin(["Poor", "Needs Improvement"])).sum()
        worst_col  = max(metric_fails, key=metric_fails.get)
        worst_name = {"lcp_label": "LCP", "cls_label": "CLS", "inp_label": "INP"}[worst_col]
        summary += f" Most common issue: {worst_name}."

    # Source note
    sources = df["cwv_source"].value_counts().to_dict()
    if sources.get("page-level", 0) > 0 and sources.get("origin-level", 0) > 0:
        summary += " Data mix: page-level and origin-level CrUX."
    elif sources.get("origin-level", 0) == total:
        summary += " All values from origin-level CrUX (page-level data insufficient)."
    elif sources.get("page-level", 0) == total:
        summary += " All values from page-level CrUX field data."

    return Paragraph(summary, _note_style)


def _chart_technical_seo():
    """
    Section 6: Technical SEO Issues.
    A. 404 errors chart
    B. Core Web Vitals compact table (PSI-sourced)
    """
    flowables = []

    # A. 404 errors
    f404, _ = _chart_404_errors()
    if f404:
        sub_style = ParagraphStyle('TechSub', fontName='Times-Bold', fontSize=11,
                                   textColor=colors.HexColor(DARK), spaceAfter=6, spaceBefore=4)
        flowables += [Paragraph("A. 404 Errors", sub_style)] + f404

    # B. Core Web Vitals
    cwv_path = os.path.join(DATA_DIR, 'core_web_vitals.csv')
    sub_style = ParagraphStyle('TechSub', fontName='Times-Bold', fontSize=11,
                               textColor=colors.HexColor(DARK), spaceAfter=6, spaceBefore=12)
    flowables.append(Spacer(1, 0.1 * inch))
    flowables.append(Paragraph("B. Core Web Vitals (PageSpeed Insights)", sub_style))

    _NEW_SCHEMA_COL = "overall_cwv_status"   # present only in PSI-based output

    if not os.path.exists(cwv_path):
        print(f"  [CWV chart] {cwv_path} does not exist — run fetch_metrics.py")
        flowables.append(Paragraph(
            "Core Web Vitals data not yet available. Run fetch_metrics.py to populate.",
            _note_style))
        return (flowables, True) if flowables else ([], False)

    cwv_df = pd.read_csv(cwv_path)
    print(f"  [CWV chart] loaded {len(cwv_df)} rows, columns: {list(cwv_df.columns)}")

    # Detect stale old-schema CSV (PostHog-based, written before PSI integration)
    if _NEW_SCHEMA_COL not in cwv_df.columns:
        print("  [CWV chart] old schema detected (missing 'overall_cwv_status') — treating as stale")
        flowables.append(Paragraph(
            "Core Web Vitals CSV has an outdated schema. "
            "Re-run fetch_metrics.py to refresh with PageSpeed Insights data.",
            _note_style))
        return (flowables, True) if flowables else ([], False)

    if cwv_df.empty:
        flowables.append(Paragraph(
            "No Core Web Vitals data returned for the top organic pages this week.",
            _note_style))
        return flowables, True

    # Summary sentence
    flowables.append(_cwv_summary_paragraph(cwv_df))
    flowables.append(Spacer(1, 0.08 * inch))

    # Compact table
    tbl = _build_cwv_table(cwv_df)
    if tbl:
        flowables.append(tbl)
        flowables.append(Spacer(1, 0.1 * inch))

    return flowables, True


def _chart_appendix_header():
    """
    Renders a visible chapter-divider for the Supporting Appendix.
    The text content from generate_section_insights is intentionally empty for this label.
    """
    from reportlab.platypus import Table as RLTable, TableStyle as RLTS
    heading = Paragraph(
        "Supporting Product / UX Insights",
        ParagraphStyle('AppendixHead', fontName='Times-Bold', fontSize=16,
                       textColor=colors.white, leading=22)
    )
    note = Paragraph(
        "The following metrics are included for broader context. "
        "They are product and UX analytics, not primary SEO KPIs.",
        ParagraphStyle('AppendixNote', fontName='Times-Italic', fontSize=11,
                       textColor=colors.HexColor('#c8d8e8'), leading=14)
    )
    tbl = RLTable([[heading], [note]], colWidths=[6.5 * inch])
    tbl.setStyle(RLTS([
        ('BACKGROUND',    (0, 0), (-1, -1), colors.HexColor('#2c3e50')),
        ('TOPPADDING',    (0, 0), (-1, -1), 16),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 16),
        ('LEFTPADDING',   (0, 0), (-1, -1), 18),
        ('RIGHTPADDING',  (0, 0), (-1, -1), 18),
    ]))
    return [tbl, Spacer(1, 0.2 * inch)], True


# ── dispatch ──────────────────────────────────────────────────────────────────

_HANDLERS = {
    # ── SEO report sections (new structure) ───────────────────────────────────
    'Weekly SEO Executive Summary':           _chart_seo_executive_summary,
    'Traffic & Engagement':                   _chart_traffic_engagement,
    'Top Landing Pages by Organic Traffic':   _chart_landing_pages_organic,
    'Organic Conversions & Revenue':          _chart_organic_conversions_revenue,
    'Top Blog Posts by Organic Traffic':      _chart_blog_posts_organic,
    'Page-Level Traffic Changes WoW':         _chart_page_traffic_changes,
    'Collection Pages Performance':           _chart_collection_pages,
    'Boxes by Size Pages':                    _chart_size_pages,
    'Technical SEO Issues':                   _chart_technical_seo,
    # ── Appendix ──────────────────────────────────────────────────────────────
    'Supporting Product / UX Insights':       _chart_appendix_header,
    'User Activity':                          _chart_user_activity,
    'Bounce Rate':                            _chart_bounce_rate,
    'Rage Clicks by URL':                     _chart_rage_clicks,
    'Referrers by Traffic':                   _chart_referrers,
    'E-Commerce Conversion Funnel':           _chart_ecommerce_funnel,
    'Top Viewed Products':                    _chart_top_products,
    'Popup Performance Metrics':              _chart_popup,
    'Daily Revenue':                          _chart_revenue,
    'Average Order Value':                    _chart_aov,
    'Abandonment Rates':                      _chart_abandonment,
    'Conversion Rate by Referrer':            _chart_referrer_conversion,
    # ── Legacy label aliases (keep so old CSVs still work) ────────────────────
    'Organic Traffic Overview':               _chart_organic_sessions,
    'Organic Conversions':                    _chart_organic_conversions,
    'Organic Revenue':                        _chart_organic_revenue,
    'Organic Product Conversions':            _chart_organic_product_conversions,
    'Core Web Vitals':                        _chart_web_vitals,
    '404 Errors':                             _chart_404_errors,
}

def get_section_chart(label):
    """
    Returns (flowables, skip_raw_table).
    If flowables is empty list, the section should be skipped entirely.
    """
    handler = _HANDLERS.get(label)
    if not handler:
        return [], False
    if not HAS_MATPLOTLIB:
        return [], False
    try:
        return handler()
    except Exception as e:
        print(f"Chart error for '{label}': {e}")
        import traceback; traceback.print_exc()
        return [], False


def section_has_data(label):
    """Return True if this section has meaningful data to show."""
    flowables, _ = get_section_chart(label)
    return len(flowables) > 0

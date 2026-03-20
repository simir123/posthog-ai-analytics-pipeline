from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.pagesizes import LETTER
from reportlab.lib.units import inch
from reportlab.lib.enums import TA_LEFT
from reportlab.lib import colors
from datetime import datetime
import csv, io, os

from generate_charts import get_section_chart


# ── CSV table helpers ─────────────────────────────────────────────────────────

def _is_csv_line(line):
    return ',' in line and not line.startswith('---')

def _parse_csv_block(csv_lines):
    text = '\n'.join(csv_lines)
    reader = csv.reader(io.StringIO(text))
    return [row for row in reader if any(cell.strip() for cell in row)]

_cell_style = ParagraphStyle(
    'TableCell', fontName='Times-Roman', fontSize=9, leading=11,
    wordWrap='LTR', textColor=colors.HexColor('#333333'),
)
_header_cell_style = ParagraphStyle(
    'TableHeader', fontName='Times-Bold', fontSize=10, leading=12,
    wordWrap='LTR', textColor=colors.white,
)

def _build_table(rows):
    if not rows:
        return None
    col_count = max(len(r) for r in rows)
    padded = []
    for i, row in enumerate(rows):
        padded_row = row + [''] * (col_count - len(row))
        style = _header_cell_style if i == 0 else _cell_style
        padded.append([
            Paragraph(str(cell).replace('&','&amp;').replace('<','&lt;').replace('>','&gt;'), style)
            for cell in padded_row
        ])
    page_width = LETTER[0] - 1.5 * inch
    col_width  = page_width / col_count
    table = Table(padded, colWidths=[col_width]*col_count, repeatRows=1)
    table.setStyle(TableStyle([
        ('BACKGROUND',    (0,0), (-1,0),  colors.HexColor('#2c3e50')),
        ('TEXTCOLOR',     (0,0), (-1,0),  colors.white),
        ('FONTNAME',      (0,0), (-1,0),  'Times-Bold'),
        ('FONTSIZE',      (0,0), (-1,0),  10),
        ('ALIGN',         (0,0), (-1,0),  'CENTER'),
        ('BOTTOMPADDING', (0,0), (-1,0),  8),
        ('TOPPADDING',    (0,0), (-1,0),  8),
        ('FONTNAME',      (0,1), (-1,-1), 'Times-Roman'),
        ('FONTSIZE',      (0,1), (-1,-1), 9),
        ('ALIGN',         (0,1), (-1,-1), 'LEFT'),
        ('TOPPADDING',    (0,1), (-1,-1), 5),
        ('BOTTOMPADDING', (0,1), (-1,-1), 5),
        ('ROWBACKGROUNDS',(0,1), (-1,-1), [colors.HexColor('#f8f9fa'), colors.white]),
        ('GRID',          (0,0), (-1,-1), 0.5, colors.HexColor('#cccccc')),
        ('BOX',           (0,0), (-1,-1), 1,   colors.HexColor('#2c3e50')),
    ]))
    return table


# ── main PDF builder ──────────────────────────────────────────────────────────

def save_pdf(sections, output_path="posthog_ai_report.pdf"):
    doc = SimpleDocTemplate(output_path, pagesize=LETTER,
                            rightMargin=0.75*inch, leftMargin=0.75*inch,
                            topMargin=0.75*inch, bottomMargin=0.75*inch)

    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        'CustomTitle', parent=styles['Heading1'],
        fontName='Times-Roman', fontSize=18, textColor='#1a1a1a',
        spaceAfter=30, alignment=TA_LEFT
    )
    heading_style = ParagraphStyle(
        'CustomHeading', parent=styles['Heading2'],
        fontName='Times-Bold', fontSize=14, textColor='#2c3e50',
        spaceBefore=24, spaceAfter=12, alignment=TA_LEFT
    )
    normal_style = ParagraphStyle(
        'CustomNormal', parent=styles['Normal'],
        fontName='Times-Roman', fontSize=11, leading=14,
        textColor='#333333', spaceAfter=8, alignment=TA_LEFT
    )
    bullet_style = ParagraphStyle(
        'Bullet', parent=normal_style,
        leftIndent=0.2*inch, spaceAfter=4
    )
    ai_section_style = ParagraphStyle(
        'AISection', parent=normal_style,
        fontName='Times-Italic', fontSize=11,
        textColor='#666666', spaceBefore=12, spaceAfter=8
    )

    appendix_heading_style = ParagraphStyle(
        'AppendixHeading', parent=heading_style,
        fontName='Times-Bold', fontSize=13, textColor=colors.HexColor('#5a5a5a'),
        spaceBefore=18, spaceAfter=8,
        borderPad=4, borderColor=colors.HexColor('#cccccc'), borderWidth=0,
        leftIndent=0,
    )
    exec_summary_style = ParagraphStyle(
        'ExecSummaryBody', parent=normal_style,
        fontName='Times-Roman', fontSize=11, leading=16,
        textColor='#1a1a1a', spaceAfter=6,
    )
    priority_style = ParagraphStyle(
        'Priority', parent=normal_style,
        fontName='Times-Bold', fontSize=11, leading=15,
        textColor=colors.HexColor('#2c3e50'), leftIndent=0.15*inch, spaceAfter=5,
    )
    priority_header_style = ParagraphStyle(
        'PriorityHeader', parent=heading_style,
        fontName='Times-Bold', fontSize=12, textColor=colors.HexColor('#2c3e50'),
        spaceBefore=14, spaceAfter=6,
    )

    _APPENDIX_LABEL = "Supporting Product / UX Insights"
    _EXEC_SUMMARY_LABEL = "Weekly SEO Executive Summary"
    in_appendix = False

    story = []

    report_date = datetime.now().strftime("%B %d, %Y")
    story.append(Paragraph("<b>Arka Packaging — Weekly SEO Report</b>", title_style))
    story.append(Paragraph(f"Week of {report_date}", normal_style))
    story.append(Spacer(1, 0.2*inch))

    for idx, (label, content) in enumerate(sections):
        # Get chart flowables — empty list means no data → skip section
        chart_flowables, skip_raw_table = get_section_chart(label)
        if not chart_flowables:
            continue                        # skip empty sections entirely

        is_exec_summary = (label == _EXEC_SUMMARY_LABEL)
        is_appendix_divider = (label == _APPENDIX_LABEL)

        # Page breaks: no break before first section (exec summary shares page with title)
        # Appendix divider always gets its own page break
        if idx > 0 and not is_exec_summary:
            story.append(PageBreak())

        if is_appendix_divider:
            in_appendix = True
            # Chart function already renders the styled banner; skip heading + content
            for f in chart_flowables:
                story.append(f)
            continue

        # Section heading
        if in_appendix:
            story.append(Paragraph(f"<b>{label}</b>", appendix_heading_style))
        elif not is_exec_summary:
            story.append(Paragraph(f"<b>{label}</b>", heading_style))
        else:
            # Exec summary: no separate heading — the title IS the heading
            story.append(Paragraph(f"<b>{label}</b>", heading_style))
        story.append(Spacer(1, 0.1*inch))

        for f in chart_flowables:
            story.append(f)

        # AI text (CSV table lines skipped when skip_raw_table=True)
        lines      = content.split('\n')
        csv_buffer = []
        in_ai_section  = False
        in_priorities  = False

        def flush_csv_buffer():
            if csv_buffer:
                rows = _parse_csv_block(csv_buffer)
                if rows:
                    t = _build_table(rows)
                    if t:
                        story.append(Spacer(1, 0.1*inch))
                        story.append(t)
                        story.append(Spacer(1, 0.15*inch))
                csv_buffer.clear()

        for line in lines:
            line = line.strip()

            if not line:
                if not skip_raw_table:
                    flush_csv_buffer()
                story.append(Spacer(1, 6))
                continue

            if line.startswith('=='):
                continue

            if line.startswith('---'):
                if not skip_raw_table:
                    flush_csv_buffer()
                in_ai_section = True
                # Exec summary has no AI analysis header — it's all first-class content
                if not is_exec_summary:
                    story.append(Spacer(1, 0.15*inch))
                    story.append(Paragraph("<i>AI Analysis</i>", ai_section_style))
                continue

            # "Top Priorities This Week:" triggers a bold sub-header
            if line.startswith('Top Priorities This Week'):
                if not skip_raw_table:
                    flush_csv_buffer()
                in_priorities = True
                story.append(Spacer(1, 0.1*inch))
                story.append(Paragraph("<b>Top Priorities This Week</b>", priority_header_style))
                continue

            if not in_ai_section and _is_csv_line(line):
                if not skip_raw_table:
                    csv_buffer.append(line)
                continue

            if not skip_raw_table:
                flush_csv_buffer()

            safe = line.replace('&','&amp;').replace('<','&lt;').replace('>','&gt;')

            if in_priorities and (line[0].isdigit() or line.startswith('-')):
                story.append(Paragraph(safe, priority_style))
            elif line.startswith('-') or line.startswith('•'):
                formatted = safe.replace('- ', '• ', 1)
                body_style = exec_summary_style if is_exec_summary else bullet_style
                story.append(Paragraph(formatted, body_style))
            else:
                body_style = exec_summary_style if is_exec_summary else normal_style
                story.append(Paragraph(safe, body_style))

        if not skip_raw_table:
            flush_csv_buffer()
        story.append(Spacer(1, 0.2*inch))

    doc.build(story)
    print(f"PDF saved to: {output_path}")

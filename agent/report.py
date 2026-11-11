"""Turn the finished report text into a short Discord message and a formatted PDF.

Both work from the report text itself, so a stored report can be re-rendered or re-posted later
without rerunning the pipeline.
"""
import io
import re
from urllib.parse import urlparse
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.enums import TA_RIGHT
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import (
    BaseDocTemplate, Frame, KeepTogether, NextPageTemplate, PageTemplate, Paragraph, Spacer, Table, TableStyle,
)

SHORT_LIMIT = 1900  # Discord rejects messages over 2000 characters
CANDIDATES = re.compile(r"^\*\*(Top candidates|Candidates)\*\*$")


def short_message(text: str) -> str:
    """The glanceable top of the report: title, market line, overview and top picks."""
    head = []
    for line in text.split("\n"):
        if CANDIDATES.match(line.strip()):
            break
        head.append(line)
    message = "\n".join(head).strip()
    if len(message) > SHORT_LIMIT:
        message = message[: SHORT_LIMIT - 40].rsplit(" ", 1)[0] + " …"
    return message + "\n\n_Full brief attached (PDF)._"


# ---- palette -------------------------------------------------------------------------------
NAVY, ACCENT = colors.HexColor("#0f1b3d"), colors.HexColor("#2f6fed")
INK, MUTED = colors.HexColor("#1f2328"), colors.HexColor("#6e7781")
CARD, BORDER = colors.HexColor("#f6f8fa"), colors.HexColor("#d8dee4")
GREEN, RED, AMBER, GRAY, BLUE = "#1a7f37", "#cf222e", "#9a6700", "#6e7781", "#0969da"
GREEN_BG, RED_BG, AMBER_BG, GRAY_BG, BLUE_BG = "#dafbe1", "#ffebe9", "#fff8c5", "#eaeef2", "#ddf4ff"
STANCE = {  # word -> (text color, background)
    "bullish": (GREEN, GREEN_BG), "long": (GREEN, GREEN_BG),
    "bearish": (RED, RED_BG), "short": (RED, RED_BG),
    "neutral": (GRAY, GRAY_BG), "watch": (BLUE, BLUE_BG), "avoid": (AMBER, AMBER_BG),
}
PAGE_W, PAGE_H = letter
MARGIN = 0.75 * inch
WIDTH = PAGE_W - 2 * MARGIN


def _clean(text: str) -> str:
    """Drop characters the built-in PDF font cannot draw, then escape for reportlab markup."""
    return escape(text.encode("cp1252", errors="ignore").decode("cp1252"))


def _bold(text: str) -> str:
    return re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", _clean(text))


def _signed(text: str) -> str:
    """Colour every +x.x% green and every -x.x% red."""
    def paint(m):
        return f'<font color="{GREEN if m.group(1) == "+" else RED}">{m.group(0)}</font>'
    return re.sub(r"([+-])\d+(?:\.\d+)?%", paint, text)


def _badge(word: str, extra: str = "") -> str:
    fg, bg = STANCE.get(word.lower(), (GRAY, GRAY_BG))
    label = f"{word.upper()}" + (f" \u00b7 {extra.upper()}" if extra else "")
    return f'<font color="{fg}" backColor="{bg}" size="7.5"><b>&nbsp;{_clean(label)}&nbsp;</b></font>'


# ---- parse the report text ------------------------------------------------------------------
def parse(text: str) -> dict:
    out = {"date": "", "market": [], "overview": [], "picks": [], "candidates": [], "note": ""}
    section, block = "head", None
    for i, raw in enumerate(text.split("\n")):
        line, stripped = raw.rstrip(), raw.strip()
        if not stripped:
            continue
        if i == 0:
            out["date"] = stripped.strip("*").split("\u00b7", 1)[-1].strip()
        elif stripped.startswith("Market:"):
            for part in stripped[7:].split(","):
                m = re.match(r"\s*(\w+) ([+-][\d.]+)% ([\w-]+)", part)
                if m:
                    out["market"].append((m.group(1), float(m.group(2)), m.group(3)))
        elif stripped == "**Worth a look**":
            section = "picks"
        elif CANDIDATES.match(stripped):
            section = "cands"
        elif stripped.startswith("_") and stripped.endswith("_"):
            out["note"] = stripped.strip("_")
        elif section == "head":
            out["overview"].append(stripped)
        elif section == "picks":
            m = re.match(r"\d+\. \*\*(.+?)\*\* \((\w+)\): (.*)", stripped)
            if m:
                out["picks"].append({"ticker": m.group(1), "direction": m.group(2), "reason": m.group(3)})
        elif section == "cands":
            if not line.startswith(" "):  # a new ticker heading
                m = re.match(r"\*\*(.+?)\*\*(.*)", stripped)
                block = {"ticker": m.group(1) if m else stripped, "name": "", "mentions": "", "tradestie": "",
                         "price": "", "reddit": "", "bullets": [], "stance": "", "horizon": "", "take": ""}
                for part in (m.group(2) if m else "").split(" \u00b7 "):
                    part = part.strip()
                    if part.startswith("(") and part.endswith(")"):
                        block["name"] = part[1:-1]
                    elif "mentions" in part:
                        block["mentions"] = part
                    elif part.startswith("Tradestie"):
                        block["tradestie"] = part
                out["candidates"].append(block)
            elif block is not None:
                if stripped.startswith("Reddit"):
                    block["reddit"] = stripped
                elif stripped.startswith("\u2022"):
                    m = re.match(r"\u2022 (?:\[([\w-]+)\] )?(.*)", stripped)
                    title, url = m.group(2), ""
                    link = re.fullmatch(r"\[(.*)\]\((https?://\S+?)\)", title)  # a [title](url) markdown link
                    if link:
                        title, url = link.group(1), link.group(2)
                    block["bullets"].append((m.group(1) or "", title, url))
                elif stripped.startswith("**Lean:"):
                    m = re.match(r"\*\*Lean: (\w+)(?: \u00b7 ([\w ]+))?\.\*\* ?(.*)", stripped)
                    if m:
                        block["stance"], block["horizon"], block["take"] = m.group(1), m.group(2) or "", m.group(3)
                else:
                    block["price"] = stripped
    return out


# ---- layout ---------------------------------------------------------------------------------
def _styles() -> dict[str, ParagraphStyle]:
    base = ParagraphStyle("base", fontName="Helvetica", fontSize=9.2, leading=13, textColor=INK)
    return {
        "base": base,
        "overview": ParagraphStyle("overview", parent=base, fontSize=10.5, leading=15.5),
        "section": ParagraphStyle("section", parent=base, fontName="Helvetica-Bold", fontSize=8.5, leading=11,
                                  textColor=ACCENT, spaceBefore=14, spaceAfter=6),
        "muted": ParagraphStyle("muted", parent=base, fontSize=8.6, leading=12, textColor=MUTED),
        "small": ParagraphStyle("small", parent=base, fontSize=8.6, leading=12),
        "right": ParagraphStyle("right", parent=base, alignment=TA_RIGHT),
        "ticker": ParagraphStyle("ticker", parent=base, fontSize=13, leading=16),
        "take": ParagraphStyle("take", parent=base, fontSize=9.2, leading=13.2, spaceBefore=4),
        "note": ParagraphStyle("note", parent=base, fontSize=7.8, leading=11, textColor=MUTED),
    }


def _sentiment_bar(reddit: str, width: float):
    """A thin stacked bar of bullish / bearish / neutral counts, or None when there are none."""
    m = re.search(r"(\d+) bullish / (\d+) bearish / (\d+) neutral", reddit)
    if not m:
        return None
    counts = [int(x) for x in m.groups()]
    total = sum(counts)
    if not total:
        return None
    cols = [(c, color) for c, color in zip(counts, (GREEN, RED, "#c0c7cf")) if c]
    bar = Table([[""] * len(cols)], colWidths=[width * c / total for c, _ in cols], rowHeights=[5])
    bar.setStyle(TableStyle([("BACKGROUND", (i, 0), (i, 0), colors.HexColor(color)) for i, (_, color) in enumerate(cols)]
                            + [("LEFTPADDING", (0, 0), (-1, -1), 0), ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                               ("TOPPADDING", (0, 0), (-1, -1), 0), ("BOTTOMPADDING", (0, 0), (-1, -1), 0)]))
    return bar


def _card(c: dict, st: dict) -> KeepTogether:
    inner = WIDTH - 4 - 20
    word = c["stance"] or "neutral"
    accent = colors.HexColor(STANCE.get(word.lower(), (GRAY, GRAY_BG))[0])
    name = f' <font color="{MUTED.hexval().replace("0x", "#")}" size="9">{_clean(c["name"])}</font>' if c["name"] else ""
    left = Paragraph(f'<b>{_clean(c["ticker"])}</b>{name}', st["ticker"])
    right = Paragraph(_badge(word, c["horizon"]) if c["stance"] else "", st["right"])
    header = Table([[left, right]], colWidths=[inner * 0.62, inner * 0.38])
    header.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "MIDDLE"), ("LEFTPADDING", (0, 0), (-1, -1), 0),
                                ("RIGHTPADDING", (0, 0), (-1, -1), 0), ("TOPPADDING", (0, 0), (-1, -1), 0),
                                ("BOTTOMPADDING", (0, 0), (-1, -1), 2)]))
    rows = [header]
    facts = " \u00b7 ".join(x for x in (c["mentions"], c["tradestie"]) if x)
    if facts:
        rows.append(Paragraph(_clean(facts), st["muted"]))
    if c["price"]:
        rows.append(Paragraph(_signed(_clean(c["price"])), st["small"]))
    if c["reddit"]:
        bar = _sentiment_bar(c["reddit"], inner)
        rows += [Spacer(1, 3)] + ([bar, Spacer(1, 2)] if bar else []) + [Paragraph(_clean(c["reddit"]), st["muted"])]
    for tag, title, url in c["bullets"]:
        label = f'<font color="{GRAY}" size="6.8"><b>{_clean(tag.upper())}</b></font>  ' if tag else ""
        if url:
            domain = re.sub(r"^www\.", "", urlparse(url).netloc)
            href = escape(url, {'"': "&quot;"})
            text = (f'<link href="{href}" color="{BLUE}">{_clean(title)}</link> '
                    f'<font color="{GRAY}" size="7">{_clean(domain)}</font>')
        else:
            text = _clean(title)
        rows.append(Paragraph(f"{label}{text}", st["small"]))
    if c["take"]:
        rows.append(Paragraph(_bold(c["take"]), st["take"]))
    card = Table([["", rows]], colWidths=[4, WIDTH - 4])
    card.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (0, 0), accent), ("BACKGROUND", (1, 0), (1, 0), CARD),
        ("BOX", (1, 0), (1, 0), 0.5, BORDER), ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (0, 0), 0), ("RIGHTPADDING", (0, 0), (0, 0), 0),
        ("LEFTPADDING", (1, 0), (1, 0), 10), ("RIGHTPADDING", (1, 0), (1, 0), 10),
        ("TOPPADDING", (1, 0), (1, 0), 8), ("BOTTOMPADDING", (1, 0), (1, 0), 9),
    ]))
    return KeepTogether([card, Spacer(1, 9)])


def _pick(i: int, p: dict, st: dict) -> KeepTogether:
    num = Paragraph(f'<font color="{ACCENT.hexval().replace("0x", "#")}" size="15"><b>{i}</b></font>', st["base"])
    text = Paragraph(f'<b>{_clean(p["ticker"])}</b>  {_badge(p["direction"])}<br/>{_clean(p["reason"])}', st["base"])
    row = Table([[num, text]], colWidths=[22, WIDTH - 22])
    row.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("LEFTPADDING", (0, 0), (-1, -1), 0),
                             ("RIGHTPADDING", (0, 0), (-1, -1), 0), ("TOPPADDING", (0, 0), (-1, -1), 0),
                             ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
                             ("LINEBELOW", (0, 0), (-1, 0), 0.4, BORDER)]))
    return KeepTogether([row, Spacer(1, 6)])


def _market_strip(market: list, st: dict):
    cells = []
    for ticker, pct, session in market:
        color = GREEN if pct >= 0 else RED
        label = {"pre": "pre-market", "post": "after-hours", "regular": "live"}.get(session, session)
        cells.append(Paragraph(f'<b>{_clean(ticker)}</b>  <font color="{color}"><b>{pct:+.1f}%</b></font> '
                               f'<font color="{GRAY}" size="7.5">{_clean(label)}</font>', st["base"]))
    strip = Table([cells], colWidths=[WIDTH / max(len(cells), 1)] * len(cells), rowHeights=[26])
    strip.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), CARD), ("BOX", (0, 0), (-1, -1), 0.5, BORDER),
                               ("INNERGRID", (0, 0), (-1, -1), 0.5, BORDER), ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                               ("LEFTPADDING", (0, 0), (-1, -1), 12)]))
    return strip


def to_pdf(text: str) -> bytes:
    """Render the report as a designed PDF: header band, market strip, top-pick list and ticker cards."""
    data, st = parse(text), _styles()
    story = [NextPageTemplate("later")]
    if data["market"]:
        story += [_market_strip(data["market"], st), Spacer(1, 10)]
    for line in data["overview"]:
        story.append(Paragraph(_bold(line), st["overview"]))
    if data["picks"]:
        story.append(Paragraph("WORTH A LOOK", st["section"]))
        story += [_pick(i, p, st) for i, p in enumerate(data["picks"], 1)]
    if data["candidates"]:
        story.append(Paragraph("ALL CANDIDATES", st["section"]))
        story += [_card(c, st) for c in data["candidates"]]
    if data["note"]:
        story += [Spacer(1, 4), Paragraph(_clean(data["note"]), st["note"])]

    def footer(canvas, doc):
        canvas.saveState()
        canvas.setFont("Helvetica", 7.5)
        canvas.setFillColor(MUTED)
        canvas.drawString(MARGIN, 0.45 * inch, "Automated analysis from public data. Verify before trading.")
        canvas.drawRightString(PAGE_W - MARGIN, 0.45 * inch, f"Page {doc.page}")
        canvas.restoreState()

    def first_page(canvas, doc):
        canvas.saveState()
        band = 1.25 * inch
        canvas.setFillColor(NAVY)
        canvas.rect(0, PAGE_H - band, PAGE_W, band, stroke=0, fill=1)
        canvas.setFillColor(ACCENT)
        canvas.rect(0, PAGE_H - band, PAGE_W, 3, stroke=0, fill=1)
        canvas.setFillColor(colors.white)
        canvas.setFont("Helvetica-Bold", 22)
        canvas.drawString(MARGIN, PAGE_H - 0.62 * inch, "Market Sentiment Brief")
        canvas.setFont("Helvetica", 10.5)
        canvas.setFillColor(colors.HexColor("#b6c2e2"))
        canvas.drawString(MARGIN, PAGE_H - 0.92 * inch, _clean(data["date"]) + "  \u00b7  r/wallstreetbets attention, pre-market view".encode("cp1252").decode("cp1252"))
        canvas.restoreState()
        footer(canvas, doc)

    def later_page(canvas, doc):
        canvas.saveState()
        canvas.setFillColor(NAVY)
        canvas.rect(0, PAGE_H - 0.4 * inch, PAGE_W, 0.4 * inch, stroke=0, fill=1)
        canvas.setFillColor(colors.white)
        canvas.setFont("Helvetica-Bold", 9)
        canvas.drawString(MARGIN, PAGE_H - 0.26 * inch, "Market Sentiment Brief")
        canvas.setFont("Helvetica", 9)
        canvas.drawRightString(PAGE_W - MARGIN, PAGE_H - 0.26 * inch, _clean(data["date"]))
        canvas.restoreState()
        footer(canvas, doc)

    buffer = io.BytesIO()
    doc = BaseDocTemplate(buffer, pagesize=letter, title="Market Sentiment Brief", author="market-sentiment-agent")
    doc.addPageTemplates([
        PageTemplate("first", [Frame(MARGIN, 0.75 * inch, WIDTH, PAGE_H - 1.25 * inch - 0.75 * inch - 0.3 * inch, id="f1",
                                     leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0)], onPage=first_page),
        PageTemplate("later", [Frame(MARGIN, 0.75 * inch, WIDTH, PAGE_H - 0.4 * inch - 0.75 * inch - 0.3 * inch, id="f2",
                                     leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0)], onPage=later_page),
    ])
    doc.build(story)
    return buffer.getvalue()

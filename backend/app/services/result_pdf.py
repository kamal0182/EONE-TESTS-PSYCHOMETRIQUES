"""PDF des résultats d'un candidat : même contenu que la fenêtre « Voir les résultats »
(score global, synthèse, vue radar par core value et détail des réponses)."""

import math
import re
from io import BytesIO
from xml.sax.saxutils import escape

from django.utils import timezone
from reportlab.graphics.shapes import Circle, Drawing, Line, Polygon, Rect, String
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)


GREEN = colors.HexColor("#1f7a55")
GREEN_DARK = colors.HexColor("#13553a")
GREEN_LIGHT = colors.HexColor("#e9f5ef")
INK = colors.HexColor("#14211b")
MUTED = colors.HexColor("#5d6f86")
TRACK = colors.HexColor("#e3e8ee")
GRID = colors.HexColor("#cfd8e3")
RED = colors.HexColor("#b42318")

# Niveaux d'alignement affichés sous le score global (identiques au frontend).
LEVELS = [
    (85, "Très bon alignement"),
    (70, "Bon alignement"),
    (50, "Alignement moyen"),
    (0, "Alignement faible"),
]

PAGE_WIDTH = A4[0] - 36 * mm

STYLES = {
    "title": ParagraphStyle("title", fontName="Helvetica-Bold", fontSize=16, leading=20, textColor=INK),
    "subtitle": ParagraphStyle("subtitle", fontName="Helvetica", fontSize=9, leading=12, textColor=MUTED),
    "h2": ParagraphStyle("h2", fontName="Helvetica-Bold", fontSize=12, leading=16, textColor=GREEN_DARK, spaceBefore=6, spaceAfter=6),
    "label": ParagraphStyle("label", fontName="Helvetica", fontSize=8, leading=10, textColor=MUTED),
    "hero": ParagraphStyle("hero", fontName="Helvetica-Bold", fontSize=30, leading=34, textColor=GREEN),
    "level": ParagraphStyle("level", fontName="Helvetica-Bold", fontSize=10, leading=13, textColor=GREEN_DARK),
    "cell": ParagraphStyle("cell", fontName="Helvetica", fontSize=9, leading=12, textColor=INK),
    "cell_bold": ParagraphStyle("cell_bold", fontName="Helvetica-Bold", fontSize=9, leading=12, textColor=INK),
    "question": ParagraphStyle("question", fontName="Helvetica-Bold", fontSize=9, leading=12, textColor=INK),
    "answer": ParagraphStyle("answer", fontName="Helvetica", fontSize=9, leading=12, textColor=GREEN_DARK),
    "missing": ParagraphStyle("missing", fontName="Helvetica-Oblique", fontSize=9, leading=12, textColor=RED),
    "empty": ParagraphStyle("empty", fontName="Helvetica-Oblique", fontSize=9, leading=12, textColor=MUTED),
}


def build_result_pdf(result):
    """`result` : dictionnaire renvoyé par TestService.detail()."""
    dimensions = _dimensions(result)
    candidat = " ".join(v for v in [result["prenom"], result["nom"]] if v) or result["email"]

    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=18 * mm,
        rightMargin=18 * mm,
        topMargin=16 * mm,
        bottomMargin=18 * mm,
        title=f"Résultats du test - {candidat}",
        author="EONE-Test",
    )
    story = [
        Paragraph(f"Résultats du test · {escape(candidat)}", STYLES["title"]),
        Paragraph("Test psychométrique · Core values", STYLES["subtitle"]),
        Spacer(1, 8 * mm),
        _summary(result, dimensions),
        Spacer(1, 8 * mm),
        Paragraph("Vue radar", STYLES["h2"]),
        _radar_block(dimensions),
        Spacer(1, 6 * mm),
        _cards(dimensions),
        # Page 1 : synthèse ; pages suivantes : détail des réponses.
        PageBreak(),
        Paragraph("Détail des réponses", STYLES["h2"]),
    ]
    for section in result["sections"]:
        story.append(_section(section))
        story.append(Spacer(1, 5 * mm))
    doc.build(story, onFirstPage=_footer, onLaterPages=_footer)
    return buffer.getvalue()


def _dimensions(result):
    return [
        {
            "name": section["core_value_name"],
            "version": re.sub(r"^version\s*", "V", str(section["version_name"] or ""), flags=re.I),
            "value": _number(section.get("percentage")),
            "total": len(section["questions"]),
            "answered": sum(1 for q in section["questions"] if q["selected_answer_id"]),
        }
        for section in result["sections"]
    ]


def _summary(result, dimensions):
    score = _number(result["score_global"])
    level = next((label for minimum, label in LEVELS if score is not None and score >= minimum), "Non disponible")
    total = sum(item["total"] for item in dimensions)
    answered = sum(item["answered"] for item in dimensions)

    hero = [
        [Paragraph("Score global pondéré", STYLES["label"])],
        [Paragraph(_pct(score), STYLES["hero"])],
        [Paragraph(escape(level), STYLES["level"])],
        [_bar(score, 70 * mm, 7)],
    ]
    hero_table = Table(hero, colWidths=[78 * mm])
    hero_table.setStyle(TableStyle([("LEFTPADDING", (0, 0), (-1, -1), 0), ("BOTTOMPADDING", (0, 0), (-1, -1), 3)]))

    meta = [
        ("Email", result["email"] or "-"),
        ("Terminé le", _date(result["submitted_at"])),
        ("Durée", _duration(result["started_at"], result["submitted_at"])),
        ("Réponses", f"{answered}/{total}"),
    ]
    meta_table = Table(
        [[Paragraph(label, STYLES["label"]), Paragraph(escape(str(value)), STYLES["cell_bold"])] for label, value in meta],
        colWidths=[24 * mm, PAGE_WIDTH - 78 * mm - 24 * mm - 12 * mm],
    )
    meta_table.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LINEBELOW", (0, 0), (-1, -2), 0.5, TRACK),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))

    table = Table([[hero_table, meta_table]], colWidths=[84 * mm, PAGE_WIDTH - 84 * mm])
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (0, 0), GREEN_LIGHT),
        ("BOX", (0, 0), (-1, -1), 0.5, TRACK),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 10),
        ("RIGHTPADDING", (0, 0), (-1, -1), 10),
        ("TOPPADDING", (0, 0), (-1, -1), 10),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
    ]))
    return table


def _radar_block(dimensions):
    if len(dimensions) < 3:
        return Paragraph("Au moins trois core values sont nécessaires pour la vue radar.", STYLES["empty"])
    return _radar(dimensions)


def _radar(dimensions, width=PAGE_WIDTH, height=95 * mm):
    """Radar comme dans la fenêtre des résultats : grille 20 → 100, une branche par core value."""
    drawing = Drawing(width, height)
    cx, cy, radius = width / 2, height / 2 - 2, min(width, height) / 2 - 22
    count = len(dimensions)

    def angle(index):
        # Première branche en haut, sens horaire (repère PDF : y vers le haut).
        return math.pi / 2 - index * 2 * math.pi / count

    def point(index, ratio):
        return cx + math.cos(angle(index)) * radius * ratio, cy + math.sin(angle(index)) * radius * ratio

    for ratio in (0.2, 0.4, 0.6, 0.8, 1):
        ring = [coord for index in range(count) for coord in point(index, ratio)]
        drawing.add(Polygon(ring, strokeColor=GRID, strokeWidth=0.6, fillColor=None))
    for index in range(count):
        x, y = point(index, 1)
        drawing.add(Line(cx, cy, x, y, strokeColor=GRID, strokeWidth=0.6))
    for tick in (20, 40, 60, 80, 100):
        drawing.add(String(cx - 4, cy + radius * tick / 100 - 2.5, str(tick), fontName="Helvetica", fontSize=6, fillColor=MUTED, textAnchor="end"))

    values = [point(index, min(100, max(0, item["value"] or 0)) / 100) for index, item in enumerate(dimensions)]
    drawing.add(Polygon(
        [coord for xy in values for coord in xy],
        strokeColor=GREEN, strokeWidth=1.5, fillColor=colors.Color(0.12, 0.48, 0.33, alpha=0.22),
    ))
    for x, y in values:
        drawing.add(Circle(x, y, 2.6, fillColor=GREEN, strokeColor=colors.white, strokeWidth=0.8))

    for index, item in enumerate(dimensions):
        x, y = point(index, 1.13)
        cos = math.cos(angle(index))
        anchor = "middle" if abs(cos) < 0.2 else ("start" if cos > 0 else "end")
        label = f"{item['name']} ({_pct(item['value'])})"
        drawing.add(String(x, y - 3, label, fontName="Helvetica-Bold", fontSize=7.5, fillColor=INK, textAnchor=anchor))
    return drawing


def _cards(dimensions):
    """Une ligne par core value : score, barre, version et réponses."""
    header = [Paragraph(text, STYLES["label"]) for text in ("Core value", "Score", "", "Version", "Réponses")]
    rows = [header] + [
        [
            Paragraph(escape(item["name"]), STYLES["cell_bold"]),
            Paragraph(_pct(item["value"]), STYLES["cell_bold"]),
            _bar(item["value"], 52 * mm, 6),
            Paragraph(escape(item["version"] or "-"), STYLES["cell"]),
            Paragraph(f"{item['answered']}/{item['total']}", STYLES["cell"]),
        ]
        for item in dimensions
    ]
    table = Table(rows, colWidths=[PAGE_WIDTH - 124 * mm, 18 * mm, 58 * mm, 24 * mm, 24 * mm], repeatRows=1)
    table.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LINEBELOW", (0, 0), (-1, -1), 0.5, TRACK),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))
    return table


def _section(section):
    """Détail d'une core value : chaque question et la réponse choisie.

    L'en-tête de section est la première ligne du tableau, répétée en haut de
    chaque page : il ne reste jamais seul en bas d'une page."""
    head = [
        Paragraph(escape(section["core_value_name"]), STYLES["cell_bold"]),
        "",
        Paragraph(_pct(_number(section.get("percentage"))), STYLES["cell_bold"]),
    ]
    rows = [head]
    for index, question in enumerate(section["questions"], start=1):
        chosen = next((a for a in question["answers"] if a["id"] == question["selected_answer_id"]), None)
        body = [Paragraph(escape(question["text"]), STYLES["question"])]
        if chosen:
            body.append(Paragraph(f"→ {escape(chosen['text'])}", STYLES["answer"]))
            score = _pct(_number(chosen.get("percentage")))
        else:
            body.append(Paragraph("Sans réponse", STYLES["missing"]))
            score = "-"
        rows.append([Paragraph(str(index), STYLES["label"]), body, Paragraph(score, STYLES["cell_bold"])])

    if len(rows) == 1:
        rows.append(["", Paragraph("Aucune question.", STYLES["empty"]), ""])
    table = Table(rows, colWidths=[8 * mm, PAGE_WIDTH - 32 * mm, 24 * mm], repeatRows=1)
    table.setStyle(TableStyle([
        ("SPAN", (0, 0), (1, 0)),
        ("BACKGROUND", (0, 0), (-1, 0), GREEN_LIGHT),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("ALIGN", (2, 0), (2, -1), "RIGHT"),
        ("LINEBELOW", (0, 1), (-1, -1), 0.5, TRACK),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))
    return table


def _bar(value, width, height):
    drawing = Drawing(width, height)
    drawing.add(Rect(0, 0, width, height, rx=height / 2, ry=height / 2, fillColor=TRACK, strokeColor=None))
    filled = width * min(100, max(0, value or 0)) / 100
    if filled > 0:
        drawing.add(Rect(0, 0, max(filled, height), height, rx=height / 2, ry=height / 2, fillColor=GREEN, strokeColor=None))
    return drawing


def _footer(canvas, doc):
    canvas.saveState()
    canvas.setFont("Helvetica", 7.5)
    canvas.setFillColor(MUTED)
    generated = timezone.localtime().strftime("%d/%m/%Y %H:%M")
    canvas.drawString(18 * mm, 10 * mm, f"EONE-Test · Document confidentiel · Généré le {generated}")
    canvas.drawRightString(A4[0] - 18 * mm, 10 * mm, f"Page {doc.page}")
    canvas.restoreState()


def _number(value):
    try:
        return None if value is None or value == "" else float(value)
    except (TypeError, ValueError):
        return None


def _pct(value, digits=0):
    if value is None:
        return "-"
    text = f"{value:.{digits}f}".replace(".", ",")
    return f"{text}%"


def _date(value):
    return timezone.localtime(value).strftime("%d/%m/%Y %H:%M") if value else "-"


def _duration(start, end):
    if not start or not end:
        return "-"
    seconds = max(0, round((end - start).total_seconds()))
    return f"{seconds // 60} min {seconds % 60:02d} s"

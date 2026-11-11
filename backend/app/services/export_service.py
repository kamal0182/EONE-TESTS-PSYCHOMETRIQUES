"""Export Excel des tests terminés : une ligne par candidat, avec le lien vers son PDF."""

from io import BytesIO

from django.utils import timezone
from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter


COLUMNS = [
    ("Nom", 22),
    ("Prénom", 22),
    ("Email", 34),
    ("Score global (%)", 17),
    ("Date de passage", 18),
    ("Résultat (PDF)", 22),
]
HEADER_FILL = PatternFill("solid", fgColor="1F7A55")
HEADER_FONT = Font(bold=True, color="FFFFFF")
# Une cellule qui commence par l'un de ces caractères serait lue comme une formule.
FORMULA_PREFIXES = ("=", "+", "-", "@")


def build_tests_workbook(rows):
    """`rows` : [{nom, prenom, email, score_global, submitted_at, pdf_url}]."""
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Tests psychométriques"

    for index, (title, width) in enumerate(COLUMNS, start=1):
        cell = sheet.cell(row=1, column=index, value=title)
        cell.fill = HEADER_FILL
        cell.font = HEADER_FONT
        cell.alignment = Alignment(vertical="center")
        sheet.column_dimensions[get_column_letter(index)].width = width
    sheet.row_dimensions[1].height = 20

    for line, row in enumerate(rows, start=2):
        _text(sheet.cell(row=line, column=1), row["nom"])
        _text(sheet.cell(row=line, column=2), row["prenom"])
        _text(sheet.cell(row=line, column=3), row["email"])

        score = sheet.cell(row=line, column=4)
        if row["score_global"] is not None:
            score.value = float(row["score_global"])
            score.number_format = "0.00"

        date = sheet.cell(row=line, column=5)
        if row["submitted_at"]:
            # Excel ne gère pas les fuseaux horaires : heure locale sans fuseau.
            date.value = timezone.localtime(row["submitted_at"]).replace(tzinfo=None)
            date.number_format = "dd/mm/yyyy hh:mm"

        link = sheet.cell(row=line, column=6)
        link.value = "Ouvrir le PDF"
        link.hyperlink = row["pdf_url"]
        link.style = "Hyperlink"

    sheet.freeze_panes = "A2"
    sheet.auto_filter.ref = f"A1:{get_column_letter(len(COLUMNS))}{max(1, len(rows) + 1)}"

    buffer = BytesIO()
    workbook.save(buffer)
    return buffer.getvalue()


def _text(cell, value):
    """Texte saisi par l'admin ou importé : toujours écrit comme texte, jamais comme formule."""
    cell.value = value or ""
    if isinstance(cell.value, str) and cell.value.startswith(FORMULA_PREFIXES):
        cell.data_type = "s"

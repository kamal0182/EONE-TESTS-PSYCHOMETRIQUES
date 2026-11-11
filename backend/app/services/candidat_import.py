"""Lecture du fichier de candidats importé par l'admin (Excel .xlsx ou CSV).

La première ligne non vide contient les en-têtes Prénom, Nom et Email (ordre libre,
majuscules et accents ignorés) ; chaque ligne suivante non vide est un candidat.
"""

import csv
import io
import unicodedata
from pathlib import Path
from zipfile import BadZipFile

from openpyxl import load_workbook
from openpyxl.utils.exceptions import InvalidFileException

from app.exceptions import BusinessError


MAX_FILE_SIZE = 2 * 1024 * 1024
MAX_CANDIDATS = 1000

# En-têtes acceptés pour chaque colonne, une fois normalisés (voir _normalize).
COLUMN_ALIASES = {
    "prenom": {"prenom", "firstname", "givenname"},
    "nom": {"nom", "nomdefamille", "lastname", "surname", "familyname"},
    "email": {"email", "mail", "courriel", "adresseemail", "adressemail", "emailaddress"},
}
COLUMN_LABELS = {"prenom": "Prénom", "nom": "Nom", "email": "Email"}


def read_candidats(uploaded_file):
    """[(numéro de ligne dans le fichier, {prenom, nom, email})]."""
    if uploaded_file is None:
        raise BusinessError("Aucun fichier reçu.")
    if uploaded_file.size > MAX_FILE_SIZE:
        raise BusinessError("Fichier trop volumineux (2 Mo maximum).")
    extension = Path(uploaded_file.name or "").suffix.lower()
    if extension == ".xlsx":
        rows = _xlsx_rows(uploaded_file)
    elif extension == ".csv":
        rows = _csv_rows(uploaded_file)
    else:
        raise BusinessError(
            "Format non pris en charge : utilisez un fichier Excel (.xlsx) ou CSV."
        )
    return _extract(rows)


def _xlsx_rows(uploaded_file):
    """Lignes de la première feuille du classeur."""
    try:
        workbook = load_workbook(uploaded_file, read_only=True, data_only=True)
    except (InvalidFileException, BadZipFile, KeyError, OSError, ValueError) as exc:
        raise BusinessError("Fichier Excel illisible.") from exc
    try:
        if not workbook.worksheets:
            return []
        return list(workbook.worksheets[0].iter_rows(values_only=True))
    finally:
        workbook.close()


def _csv_rows(uploaded_file):
    raw = uploaded_file.read()
    # latin-1 accepte tous les octets : c'est le dernier recours.
    for encoding in ("utf-8-sig", "cp1252", "latin-1"):
        try:
            text = raw.decode(encoding)
            break
        except UnicodeDecodeError:
            continue
    try:
        # Excel en français enregistre les CSV avec « ; ».
        dialect = csv.Sniffer().sniff(text[:4096], delimiters=";,\t")
    except csv.Error:
        dialect = csv.excel
    return list(csv.reader(io.StringIO(text), dialect))


def _extract(rows):
    columns = None
    candidats = []
    for line, row in enumerate(rows, start=1):
        values = [_cell(value) for value in row]
        if not any(values):
            continue
        if columns is None:
            columns = _find_columns(values)
            continue
        if len(candidats) >= MAX_CANDIDATS:
            raise BusinessError(
                f"Trop de candidats : {MAX_CANDIDATS} lignes maximum par import."
            )
        candidats.append(
            (
                line,
                {
                    field: values[index] if index < len(values) else ""
                    for field, index in columns.items()
                },
            )
        )
    if columns is None:
        raise BusinessError("Le fichier est vide.")
    return candidats


def _find_columns(header):
    normalized = [_normalize(value) for value in header]
    columns = {}
    for field, aliases in COLUMN_ALIASES.items():
        index = next((i for i, name in enumerate(normalized) if name in aliases), None)
        if index is not None:
            columns[field] = index
    missing = [COLUMN_LABELS[field] for field in COLUMN_ALIASES if field not in columns]
    if missing:
        raise BusinessError(
            "Colonne(s) introuvable(s) : "
            + ", ".join(missing)
            + ". La première ligne doit contenir les en-têtes Prénom, Nom et Email."
        )
    return columns


def _normalize(value):
    """« Adresse e-mail » -> « adresseemail » : minuscules, sans accents ni séparateurs."""
    text = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode()
    return "".join(char for char in text.lower() if char.isalnum())


def _cell(value):
    if value is None:
        return ""
    if isinstance(value, float) and value.is_integer():
        value = int(value)
    return str(value).strip()

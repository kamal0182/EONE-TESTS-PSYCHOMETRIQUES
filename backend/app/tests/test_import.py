import io

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from openpyxl import Workbook
from rest_framework.test import APIClient

from app.models import Test, TestVersion
from app.services.test_service import TestService
from .test_tests import CANDIDAT, build_bank

URL = "/api/tests-psychometriques/importer/"
XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


def xlsx_file(rows, name="candidats.xlsx"):
    workbook = Workbook()
    for row in rows:
        workbook.active.append(row)
    buffer = io.BytesIO()
    workbook.save(buffer)
    return SimpleUploadedFile(name, buffer.getvalue(), content_type=XLSX)


class CandidatImportTests(TestCase):
    def setUp(self):
        build_bank()
        self.admin = APIClient()
        self.admin.force_authenticate(
            get_user_model().objects.create_user(username="admin", password="secret-pass")
        )

    def _import(self, upload):
        return self.admin.post(URL, {"file": upload}, format="multipart")

    def test_import_xlsx_creates_one_test_per_candidate(self):
        TestService().generate(**CANDIDAT)  # email déjà présent en base
        upload = xlsx_file(
            [
                ["E-mail", "Prénom", "NOM"],  # ordre libre, accents et casse ignorés
                ["ali@example.com", "Ali", "Benali"],
                [None, None, None],  # ligne vide ignorée
                ["SALMA@example.com", "Salma", "Idrissi"],  # déjà un test
                ["pas-un-email", "Omar", "Alaoui"],
                ["nadia@example.com", "Nadia", ""],
                ["ALI@example.com", "Ali", "Bis"],  # doublon dans le fichier
                ["  karim@example.com ", " Karim ", "Tazi"],
            ]
        )
        response = self._import(upload)
        self.assertEqual(response.status_code, 200, response.data)

        created = response.data["created"]
        self.assertEqual(
            sorted(item["email"] for item in created),
            ["ali@example.com", "karim@example.com"],
        )
        for item in created:
            self.assertEqual(item["statut"], Test.STATUT_A_ENVOYER)
            self.assertEqual(len(item["versions"]), 2)
        self.assertEqual(Test.objects.get(email="karim@example.com").prenom, "Karim")

        rejected = {item["ligne"]: item["message"] for item in response.data["rejected"]}
        self.assertEqual(
            rejected,
            {
                4: "Un test existe déjà pour cet email.",
                5: "Email invalide.",
                6: "Champ(s) manquant(s) : Nom.",
                7: "Email en double dans le fichier.",
            },
        )
        self.assertEqual(Test.objects.count(), 3)
        self.assertEqual(TestVersion.objects.count(), 6)

    def test_import_csv_with_semicolons(self):
        content = "Prénom;Nom;Email\r\nAli;Benali;ali@example.com\r\n".encode("cp1252")
        upload = SimpleUploadedFile("candidats.csv", content, content_type="text/csv")
        response = self._import(upload)
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual([item["nom"] for item in response.data["created"]], ["Benali"])

    def test_import_rejects_missing_columns(self):
        response = self._import(xlsx_file([["Prénom", "Nom"], ["Ali", "Benali"]]))
        self.assertEqual(response.status_code, 400)
        self.assertIn("Email", response.data["detail"])
        self.assertFalse(Test.objects.exists())

    def test_import_rejects_bad_files(self):
        bad_excel = SimpleUploadedFile("candidats.xlsx", b"not a zip", content_type=XLSX)
        self.assertEqual(self._import(bad_excel).status_code, 400)
        old_excel = SimpleUploadedFile("candidats.xls", b"...", content_type="application/vnd.ms-excel")
        self.assertIn("Format non pris en charge", self._import(old_excel).data["detail"])
        self.assertEqual(self.admin.post(URL, {}, format="multipart").status_code, 400)

    def test_import_requires_admin(self):
        response = APIClient().post(URL, {"file": xlsx_file([["Prénom", "Nom", "Email"]])}, format="multipart")
        self.assertEqual(response.status_code, 401)

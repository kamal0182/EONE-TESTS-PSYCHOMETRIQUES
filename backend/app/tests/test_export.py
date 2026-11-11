import io
from datetime import timedelta
from unittest import mock

from django.contrib.auth import get_user_model
from django.core import signing
from django.test import TestCase, override_settings
from django.utils import timezone
from openpyxl import load_workbook
from rest_framework.test import APIClient

from app.models import Test, TestVersionAnswer
from app.services.test_service import TestService
from .test_tests import CANDIDAT, build_bank

EXPORT_URL = "/api/tests-psychometriques/exporter/"


@override_settings(FRONTEND_URL="http://test.local")
class ExportTests(TestCase):
    def setUp(self):
        self.bank = build_bank()
        self.admin = APIClient()
        self.admin.force_authenticate(
            get_user_model().objects.create_user(username="admin", password="secret-pass")
        )
        # Un test terminé (une réponse à 100 %) et un test pas encore passé.
        self.done = TestService().generate(**{**CANDIDAT, "nom": "=HYPERLINK(\"x\")"})["id"]
        test = Test.objects.get(id=self.done)
        test_version = test.test_versions.get(version__core_value=self.bank["integrite"])
        TestVersionAnswer.objects.create(test_version=test_version, answer=self.bank["good_answer"])
        now = timezone.now()
        Test.objects.filter(id=self.done).update(
            statut=Test.STATUT_REPONDU, started_at=now - timedelta(minutes=7), submitted_at=now
        )
        self.pending = TestService().generate(**{**CANDIDAT, "email": "pending@example.com"})["id"]

    def _pdf_url(self):
        sheet = self._sheet()
        row = next(r for r in sheet.iter_rows(min_row=2) if r[2].value == CANDIDAT["email"])
        return row[5].hyperlink.target.replace("http://test.local", "")

    def _sheet(self):
        response = self.admin.get(EXPORT_URL)
        self.assertEqual(response.status_code, 200)
        self.assertIn("attachment;", response["Content-Disposition"])
        return load_workbook(io.BytesIO(response.content)).active

    def test_export_contains_only_answered_tests_with_pdf_links(self):
        sheet = self._sheet()
        self.assertEqual(
            [cell.value for cell in sheet[1]],
            ["Nom", "Prénom", "Email", "Score global (%)", "Date de passage", "Résultat (PDF)"],
        )
        rows = list(sheet.iter_rows(min_row=2))
        # Le test « pending » (non terminé) n'est pas exporté.
        self.assertEqual([row[2].value for row in rows], [CANDIDAT["email"]])

        done = rows[0]
        self.assertEqual(done[0].value, '=HYPERLINK("x")')  # écrit comme texte
        self.assertEqual(done[0].data_type, "s")
        # Score pondéré : (100 × 2 + 0 × 1) / 3, la question « Respect » étant sans réponse.
        self.assertEqual(done[3].value, 66.67)
        self.assertIsNotNone(done[4].value)  # date de passage
        self.assertEqual(done[5].value, "Ouvrir le PDF")
        self.assertTrue(done[5].hyperlink.target.startswith("http://test.local/api/resultats-pdf/"))

    def test_export_refused_when_no_answered_test(self):
        Test.objects.filter(id=self.done).update(statut=Test.STATUT_ENVOYE)
        response = self.admin.get(EXPORT_URL)
        self.assertEqual(response.status_code, 400)
        self.assertIn("Répondu", response.json()["detail"])

    def test_pdf_link_opens_pdf_without_login(self):
        response = APIClient().get(self._pdf_url(), HTTP_ACCEPT="text/html")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "application/pdf")
        self.assertTrue(response.content.startswith(b"%PDF"))
        self.assertIn("inline;", response["Content-Disposition"])

    def test_pdf_link_rejects_tampered_expired_and_unfinished(self):
        url = self._pdf_url()
        public = APIClient()
        self.assertEqual(public.get(url[:-3] + "xx/").status_code, 404)
        self.assertEqual(public.get("/api/resultats-pdf/n-importe-quoi/").status_code, 404)

        later = timezone.now() + timedelta(days=31)
        with mock.patch("django.core.signing.time.time", return_value=later.timestamp()):
            self.assertEqual(public.get(url).status_code, 410)

        unfinished = signing.TimestampSigner(salt=TestService.PDF_SALT).sign(self.pending)
        self.assertEqual(public.get(f"/api/resultats-pdf/{unfinished}/").status_code, 400)

    def test_pdf_builds_for_many_questions_and_unanswered(self):
        # Le PDF se génère aussi avec des questions sans réponse et des textes à échapper.
        from app.services.result_pdf import build_result_pdf

        detail = TestService().detail(self.done)
        detail["sections"][0]["questions"][0]["text"] = "Texte <b>&</b> « spécial » " * 20
        detail["sections"][0]["questions"] *= 40
        self.assertTrue(build_result_pdf(detail).startswith(b"%PDF"))

    def test_export_requires_admin(self):
        self.assertEqual(APIClient().get(EXPORT_URL).status_code, 401)

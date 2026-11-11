import smtplib
import uuid
from datetime import timedelta
from unittest import mock

from django.contrib.auth import get_user_model
from django.core import mail
from django.core.mail.backends import locmem
from django.db import connection
from django.test import TestCase, override_settings
from django.test.utils import CaptureQueriesContext
from django.utils import timezone
from rest_framework.test import APIClient

from app.models import Test
from app.services import email_service
from app.services.test_service import TestService
from .test_tests import CANDIDAT, build_bank

BULK_URL = "/api/tests-psychometriques/envoyer-emails/"

# Le lanceur de tests Django remplace le backend SMTP par une boîte mémoire (mail.outbox).
@override_settings(
    FRONTEND_URL="http://test.local", DEFAULT_FROM_EMAIL="rh@test.local", EMAIL_CC=[]
)
class EnvoyerEmailTests(TestCase):
    def setUp(self):
        build_bank()
        self.admin = APIClient()
        self.admin.force_authenticate(
            get_user_model().objects.create_user(username="admin", password="secret-pass")
        )
        self.test_id = TestService().generate(**{**CANDIDAT, "prenom": "<Salma>"})["id"]
        self.url = f"/api/tests-psychometriques/{self.test_id}/envoyer-email/"

    def test_send_creates_link_and_emails_candidate(self):
        response = self.admin.post(self.url)
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data["statut"], Test.STATUT_ENVOYE)
        self.assertIsNotNone(response.data["email_sent_at"])

        token = Test.objects.get(id=self.test_id).token
        link = f"http://test.local/passer-test?token={token}"
        self.assertEqual(len(mail.outbox), 1)
        sent = mail.outbox[0]
        self.assertEqual(sent.to, [CANDIDAT["email"]])
        self.assertEqual(sent.from_email, "rh@test.local")
        self.assertIn(link, sent.body)
        html = sent.alternatives[0][0]
        self.assertIn(f'href="{link}"', html)
        self.assertIn("&lt;Salma&gt;", html)  # nom échappé dans le HTML

    @override_settings(EMAIL_CC=["copie@test.local"])
    def test_cc_receives_visible_copy(self):
        other = TestService().generate(**{**CANDIDAT, "email": "ok@example.com"})["id"]
        self.admin.post(self.url)
        self.admin.post(BULK_URL, {"ids": [other]}, format="json")
        self.assertEqual(len(mail.outbox), 2)
        for sent in mail.outbox:
            self.assertEqual(sent.cc, ["copie@test.local"])
            self.assertEqual(sent.bcc, [])
            self.assertIn("copie@test.local", sent.recipients())  # reçoit bien la copie
            self.assertEqual(sent.message()["Cc"], "copie@test.local")  # visible dans l'en-tête
        self.assertEqual(mail.outbox[0].to, [CANDIDAT["email"]])

    def test_resend_keeps_same_link_and_reactivates_expired_one(self):
        self.admin.post(self.url)
        token = Test.objects.get(id=self.test_id).token
        Test.objects.filter(id=self.test_id).update(
            token_expires_at=timezone.now() - timedelta(days=1)
        )
        response = self.admin.post(self.url)
        self.assertEqual(response.status_code, 200, response.data)
        test = Test.objects.get(id=self.test_id)
        self.assertEqual(test.token, token)
        self.assertGreater(test.token_expires_at, timezone.now() + timedelta(days=6))
        self.assertEqual(len(mail.outbox), 2)

    def test_refused_once_test_started(self):
        self.admin.post(self.url)
        Test.objects.filter(id=self.test_id).update(
            statut=Test.STATUT_EN_COURS, started_at=timezone.now()
        )
        self.assertEqual(self.admin.post(self.url).status_code, 400)
        self.assertEqual(len(mail.outbox), 1)

    def test_smtp_failure_rolls_back(self):
        with mock.patch(
            "django.core.mail.EmailMultiAlternatives.send",
            side_effect=smtplib.SMTPAuthenticationError(535, b"bad credentials"),
        ):
            response = self.admin.post(self.url)
        self.assertEqual(response.status_code, 400)
        self.assertIn("mot de passe", response.data["detail"])
        test = Test.objects.get(id=self.test_id)
        self.assertEqual(test.statut, Test.STATUT_A_ENVOYER)
        self.assertIsNone(test.token)
        self.assertIsNone(test.email_sent_at)

    def test_bulk_send_uses_one_connection_and_skips_started_tests(self):
        envoye = TestService().generate(**{**CANDIDAT, "email": "envoye@example.com"})["id"]
        self.admin.post(f"/api/tests-psychometriques/{envoye}/envoyer-email/")
        started = TestService().generate(**{**CANDIDAT, "email": "started@example.com"})["id"]
        Test.objects.filter(id=started).update(
            statut=Test.STATUT_EN_COURS, started_at=timezone.now(), token=uuid.uuid4()
        )
        mail.outbox.clear()

        with mock.patch(
            "app.services.email_service.get_connection", wraps=email_service.get_connection
        ) as get_connection:
            response = self.admin.post(
                BULK_URL,
                {"ids": [self.test_id, envoye, started, "pas-un-uuid", self.test_id]},
                format="json",
            )
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(get_connection.call_count, 1)
        expected = sorted([CANDIDAT["email"], "envoye@example.com"])
        self.assertEqual(sorted(item["email"] for item in response.data["sent"]), expected)
        self.assertEqual(
            sorted(item["message"] for item in response.data["rejected"]),
            ["Le candidat a déjà commencé le test.", "Test introuvable."],
        )
        self.assertEqual(sorted(m.to[0] for m in mail.outbox), expected)
        self.assertEqual(Test.objects.get(id=self.test_id).statut, Test.STATUT_ENVOYE)

    def test_bulk_queries_do_not_grow_with_selection(self):
        ids = [
            TestService().generate(**{**CANDIDAT, "email": f"c{i}@example.com"})["id"]
            for i in range(10)
        ]
        with CaptureQueriesContext(connection) as queries:
            response = self.admin.post(BULK_URL, {"ids": ids}, format="json")
        self.assertEqual(len(response.data["sent"]), 10)
        self.assertLessEqual(len(queries), 15)

    def test_bulk_refused_address_is_reverted_others_sent(self):
        other = TestService().generate(**{**CANDIDAT, "email": "ok@example.com"})["id"]
        real_send = locmem.EmailBackend.send_messages

        def send(backend, messages):
            if messages[0].to[0] == CANDIDAT["email"]:
                raise smtplib.SMTPRecipientsRefused({CANDIDAT["email"]: (550, b"unknown")})
            return real_send(backend, messages)

        with mock.patch.object(locmem.EmailBackend, "send_messages", send):
            response = self.admin.post(BULK_URL, {"ids": [self.test_id, other]}, format="json")
        self.assertEqual([item["email"] for item in response.data["sent"]], ["ok@example.com"])
        self.assertIn("refusée", response.data["rejected"][0]["message"])
        refused = Test.objects.get(id=self.test_id)
        self.assertEqual(refused.statut, Test.STATUT_A_ENVOYER)
        self.assertIsNone(refused.token)
        self.assertIsNone(refused.email_sent_at)
        self.assertEqual(Test.objects.get(id=other).statut, Test.STATUT_ENVOYE)

    def test_bulk_connection_lost_stops_and_reverts(self):
        ids = [self.test_id] + [
            TestService().generate(**{**CANDIDAT, "email": f"c{i}@example.com"})["id"]
            for i in range(3)
        ]
        with mock.patch.object(
            locmem.EmailBackend, "send_messages", side_effect=smtplib.SMTPServerDisconnected()
        ) as send:
            response = self.admin.post(BULK_URL, {"ids": ids}, format="json")
        self.assertEqual(response.data["sent"], [])
        self.assertEqual(len(response.data["rejected"]), 4)
        self.assertEqual(send.call_count, 2)  # 1 essai + 1 après reconnexion, puis arrêt
        self.assertEqual(
            Test.objects.filter(statut=Test.STATUT_A_ENVOYER, token__isnull=True).count(), 4
        )

    def test_bulk_validates_input(self):
        self.assertEqual(self.admin.post(BULK_URL, {"ids": []}, format="json").status_code, 400)
        self.assertEqual(self.admin.post(BULK_URL, {"ids": "x"}, format="json").status_code, 400)
        too_many = [str(uuid.uuid4()) for _ in range(TestService.MAX_EMAILS_PAR_ENVOI + 1)]
        self.assertEqual(self.admin.post(BULK_URL, {"ids": too_many}, format="json").status_code, 400)

    @override_settings(
        EMAIL_BACKEND="django.core.mail.backends.smtp.EmailBackend", EMAIL_HOST=""
    )
    def test_not_configured(self):
        response = self.admin.post(self.url)
        self.assertEqual(response.status_code, 400)
        self.assertIn("EMAIL_HOST", response.data["detail"])
        self.assertEqual(Test.objects.get(id=self.test_id).statut, Test.STATUT_A_ENVOYER)

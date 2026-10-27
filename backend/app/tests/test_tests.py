from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIClient

from app.exceptions import BusinessError
from app.models import Test, TestVersion
from app.services.question_bank_service import (
    AnswerService,
    CoreValueService,
    QuestionService,
    VersionService,
)
from app.services.test_service import TestService

CANDIDAT = {"prenom": "Salma", "nom": "Idrissi", "email": "salma@example.com"}


def build_bank():
    """Deux core values ; « Respect » a trois versions d'une question chacune."""
    integrite = CoreValueService().create({"name": "Intégrité"})
    version = VersionService().create({"name": "V1", "core_value_id": integrite.id})
    question = QuestionService().create(
        {"text": "Q1", "ponderation": Decimal("2"), "version_id": version.id}
    )
    good = AnswerService().create({"question_id": question.id, "text": "Bien", "percentage": 100})
    AnswerService().create({"question_id": question.id, "text": "Moyen", "percentage": 50})

    respect = CoreValueService().create({"name": "Respect"})
    for name in ("A", "B", "C"):
        other = VersionService().create({"name": name, "core_value_id": respect.id})
        other_question = QuestionService().create(
            {"text": f"Q{name}", "ponderation": Decimal("1"), "version_id": other.id}
        )
        AnswerService().create({"question_id": other_question.id, "text": "R", "percentage": 40})
    return {"integrite": integrite, "respect": respect, "good_answer": good}


class TestGenerationTests(TestCase):
    def test_generate_picks_one_version_per_core_value(self):
        bank = build_bank()
        for _ in range(10):
            created = TestService().generate(**CANDIDAT)
            self.assertEqual(
                [item["core_value_name"] for item in created["versions"]],
                ["Intégrité", "Respect"],
            )
            self.assertEqual(created["statut"], Test.STATUT_A_ENVOYER)
            self.assertEqual(created["email"], CANDIDAT["email"])
        self.assertGreater(
            TestVersion.objects.filter(version__core_value=bank["respect"])
            .values("version")
            .distinct()
            .count(),
            1,
        )

    def test_generate_refuses_core_value_without_version(self):
        CoreValueService().create({"name": "Respect"})
        with self.assertRaisesMessage(BusinessError, "Respect"):
            TestService().generate(**CANDIDAT)
        self.assertFalse(Test.objects.exists())

    def test_generate_refuses_when_no_core_value(self):
        with self.assertRaises(BusinessError):
            TestService().generate(**CANDIDAT)


@override_settings(FRONTEND_URL="http://test.local")
class TestApiFlowTests(TestCase):
    def setUp(self):
        self.bank = build_bank()
        self.admin = APIClient()
        self.admin.force_authenticate(
            get_user_model().objects.create_user(username="admin", password="secret-pass")
        )
        self.public = APIClient()

    def _generate(self):
        response = self.admin.post("/api/tests-psychometriques/", CANDIDAT, format="json")
        self.assertEqual(response.status_code, 201, response.data)
        return response.data

    def test_generate_validates_input(self):
        response = self.admin.post(
            "/api/tests-psychometriques/", {"prenom": "", "nom": "X", "email": "pas-un-email"}, format="json"
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("email", response.data)
        self.assertEqual(APIClient().post("/api/tests-psychometriques/", CANDIDAT, format="json").status_code, 401)

    def test_full_flow_link_pass_and_score(self):
        test = self._generate()
        self.assertIsNone(test["lien"])

        created = self.admin.post(f"/api/tests-psychometriques/{test['id']}/lien/")
        self.assertEqual(created.status_code, 200, created.data)
        self.assertEqual(created.data["statut"], Test.STATUT_ENVOYE)
        token = Test.objects.get(id=test["id"]).token
        self.assertEqual(created.data["lien"], f"http://test.local/passer-test?token={token}")
        self.assertEqual(
            self.admin.post(f"/api/tests-psychometriques/{test['id']}/lien/").status_code, 400
        )

        # Prolonger : même lien, nouvelle date d'expiration.
        Test.objects.filter(id=test["id"]).update(
            token_expires_at=timezone.now() + timedelta(days=1)
        )
        extended = self.admin.post(f"/api/tests-psychometriques/{test['id']}/prolonger/")
        self.assertEqual(extended.status_code, 200, extended.data)
        self.assertEqual(extended.data["relance_count"], 1)
        self.assertEqual(extended.data["lien"], created.data["lien"])
        self.assertGreater(
            Test.objects.get(id=test["id"]).token_expires_at,
            timezone.now() + timedelta(days=6),
        )

        base = f"/api/test-candidat/{token}"
        state = self.public.get(f"{base}/")
        self.assertEqual(state.data["statut"], Test.STATUT_ENVOYE)
        self.assertEqual(state.data["nb_questions"], 2)
        self.assertNotIn("sections", state.data)

        started = self.public.post(f"{base}/demarrer/")
        self.assertEqual(started.data["statut"], Test.STATUT_EN_COURS)
        # Seule la question en cours est envoyée, sans pondération ni pourcentage.
        self.assertNotIn("sections", started.data)
        self.assertEqual(started.data["question_index"], 0)
        self.assertEqual(started.data["question"]["core_value_name"], "Intégrité")
        self.assertNotIn("ponderation", started.data["question"])
        self.assertNotIn("percentage", started.data["question"]["answers"][0])

        answered = self.public.post(
            f"{base}/repondre/", {"answer_id": str(self.bank["good_answer"].id)}, format="json"
        )
        self.assertEqual(answered.status_code, 200, answered.data)
        self.assertEqual(
            str(answered.data["question"]["selected_answer_id"]), str(self.bank["good_answer"].id)
        )
        moved = self.public.post(f"{base}/suivant/")
        self.assertEqual(moved.data["question_index"], 1)
        self.assertEqual(moved.data["question"]["core_value_name"], "Respect")
        done = self.public.post(f"{base}/terminer/")
        self.assertEqual(done.data["statut"], Test.STATUT_REPONDU)

        detail = self.admin.get(f"/api/tests-psychometriques/{test['id']}/")
        # (100 × 2 + 0 × 1) / (2 + 1) : la question sans réponse compte 0.
        self.assertEqual(Decimal(detail.data["score_global"]), Decimal("66.67"))
        sections = {item["core_value_name"]: item for item in detail.data["sections"]}
        self.assertEqual(Decimal(sections["Intégrité"]["percentage"]), Decimal("100"))
        self.assertEqual(Decimal(sections["Respect"]["percentage"]), Decimal("0"))

    def test_cannot_extend_link_before_creation_or_after_start(self):
        test = self._generate()
        self.assertEqual(
            self.admin.post(f"/api/tests-psychometriques/{test['id']}/prolonger/").status_code, 400
        )
        self.admin.post(f"/api/tests-psychometriques/{test['id']}/lien/")
        Test.objects.filter(id=test["id"]).update(
            statut=Test.STATUT_EN_COURS, started_at=timezone.now()
        )
        self.assertEqual(
            self.admin.post(f"/api/tests-psychometriques/{test['id']}/prolonger/").status_code, 400
        )

    def test_expired_link_and_timeout(self):
        test = self._generate()
        self.admin.post(f"/api/tests-psychometriques/{test['id']}/lien/")
        instance = Test.objects.get(id=test["id"])
        base = f"/api/test-candidat/{instance.token}"

        Test.objects.filter(id=instance.id).update(
            token_expires_at=timezone.now() - timedelta(minutes=1)
        )
        self.assertEqual(self.public.get(f"{base}/").status_code, 410)

        Test.objects.filter(id=instance.id).update(
            statut=Test.STATUT_EN_COURS,
            started_at=timezone.now() - Test.DUREE_TEST - timedelta(minutes=1),
        )
        late = self.public.post(
            f"{base}/repondre/", {"answer_id": str(self.bank["good_answer"].id)}, format="json"
        )
        self.assertEqual(late.status_code, 400)
        self.assertEqual(Test.objects.get(id=instance.id).statut, Test.STATUT_REPONDU)

    def _start(self):
        test = self._generate()
        self.admin.post(f"/api/tests-psychometriques/{test['id']}/lien/")
        instance = Test.objects.get(id=test["id"])
        base = f"/api/test-candidat/{instance.token}"
        self.public.post(f"{base}/demarrer/")
        return instance, base

    def test_no_going_back_is_enforced_by_server(self):
        instance, base = self._start()
        first = self.bank["good_answer"]
        other_first = first.question.answers.exclude(id=first.id).get()

        # « Suivant » sans réponse : refusé.
        self.assertEqual(self.public.post(f"{base}/suivant/").status_code, 400)
        # Une réponse d'une autre question (pas encore atteinte) : refusée.
        later = Test.objects.get(id=instance.id).test_versions.exclude(
            version__core_value=self.bank["integrite"]
        ).get().version.questions.get().answers.first()
        self.assertEqual(
            self.public.post(f"{base}/repondre/", {"answer_id": str(later.id)}, format="json").status_code,
            400,
        )
        # Changer d'avis sur la question en cours : autorisé.
        self.public.post(f"{base}/repondre/", {"answer_id": str(other_first.id)}, format="json")
        self.public.post(f"{base}/repondre/", {"answer_id": str(first.id)}, format="json")
        self.public.post(f"{base}/suivant/")

        # Revenir sur la question validée : refusé, la réponse reste inchangée.
        back = self.public.post(f"{base}/repondre/", {"answer_id": str(other_first.id)}, format="json")
        self.assertEqual(back.status_code, 400)
        detail = self.admin.get(f"/api/tests-psychometriques/{instance.id}/")
        integrite = next(s for s in detail.data["sections"] if s["core_value_name"] == "Intégrité")
        self.assertEqual(str(integrite["questions"][0]["selected_answer_id"]), str(first.id))

        # La dernière question validée termine le test.
        self.public.post(f"{base}/repondre/", {"answer_id": str(later.id)}, format="json")
        finished = self.public.post(f"{base}/suivant/")
        self.assertEqual(finished.data["statut"], Test.STATUT_REPONDU)
        self.assertNotIn("question", finished.data)
        self.assertEqual(self.public.post(f"{base}/suivant/").status_code, 400)

    def test_answer_accepted_within_network_margin(self):
        instance, base = self._start()
        # 5 s après la fin du chrono : encore dans la marge de 15 s.
        Test.objects.filter(id=instance.id).update(
            started_at=timezone.now() - Test.DUREE_TEST - timedelta(seconds=5)
        )
        ok = self.public.post(
            f"{base}/repondre/", {"answer_id": str(self.bank["good_answer"].id)}, format="json"
        )
        self.assertEqual(ok.status_code, 200, ok.data)

    def test_candidate_endpoints_are_rate_limited(self):
        _, base = self._start()
        statuses = [self.public.get(f"{base}/").status_code for _ in range(60)]
        self.assertNotIn(429, statuses[:59])
        limited = self.public.get(f"{base}/")
        self.assertEqual(limited.status_code, 429)
        self.assertIn("Trop de requêtes", limited.data["detail"])
        self.assertIn("Retry-After", limited)

    def test_invalid_token_and_delete(self):
        self.assertEqual(self.public.get("/api/test-candidat/pas-un-jeton/").status_code, 404)
        test = self._generate()
        self.assertEqual(len(self.admin.get("/api/tests-psychometriques/").data), 1)
        self.assertEqual(self.admin.delete(f"/api/tests-psychometriques/{test['id']}/").status_code, 204)
        self.assertFalse(Test.objects.exists())


class AuthSecurityTests(TestCase):
    def setUp(self):
        get_user_model().objects.create_user(username="admin", password="secret-pass")

    def _login(self, client=None, **extra):
        return (client or APIClient()).post(
            "/api/auth/login/",
            {"username": "admin", "password": "secret-pass"},
            format="json",
            **extra,
        )

    def test_expired_token_is_rejected_and_renewed_on_login(self):
        from rest_framework.authtoken.models import Token

        token = self._login().data["token"]
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
        self.assertEqual(client.get("/api/auth/me/").status_code, 200)

        Token.objects.filter(key=token).update(
            created=timezone.now() - timedelta(hours=13)
        )
        expired = client.get("/api/auth/me/")
        self.assertEqual(expired.status_code, 401)
        self.assertIn("expirée", expired.data["detail"])
        self.assertFalse(Token.objects.filter(key=token).exists())
        self.assertNotEqual(self._login().data["token"], token)

    def test_login_throttle_ignores_spoofed_forwarded_for(self):
        from django.core.cache import cache

        cache.clear()
        # Caddy remplace X-Forwarded-For par l'IP réelle, nginx y ajoute celle de Caddy :
        # l'avant-dernière entrée est le client, quoi qu'il ait envoyé avant.
        statuses = [
            self._login(
                HTTP_X_FORWARDED_FOR=f"10.0.0.{index}, 203.0.113.7, 172.18.0.5"
            ).status_code
            for index in range(12)
        ]
        self.assertEqual(statuses[:10], [200] * 10)
        self.assertEqual(statuses[10:], [429, 429])
        cache.clear()


class AuthApiTests(TestCase):
    def test_login_me_logout(self):
        get_user_model().objects.create_user(username="admin", password="secret-pass")
        client = APIClient()
        bad = client.post("/api/auth/login/", {"username": "admin", "password": "x"}, format="json")
        self.assertEqual(bad.status_code, 400)
        ok = client.post(
            "/api/auth/login/", {"username": "admin", "password": "secret-pass"}, format="json"
        )
        self.assertEqual(ok.status_code, 200, ok.data)
        client.credentials(HTTP_AUTHORIZATION=f"Bearer {ok.data['token']}")
        self.assertEqual(client.get("/api/auth/me/").data["username"], "admin")
        self.assertEqual(client.post("/api/auth/logout/").status_code, 204)
        self.assertEqual(client.get("/api/auth/me/").status_code, 401)

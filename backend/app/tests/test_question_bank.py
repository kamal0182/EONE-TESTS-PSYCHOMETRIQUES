import uuid
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient

from app.exceptions import BusinessError, NotFoundError
from app.models import Answer, CoreValue, Question, Test, TestVersionAnswer, Version
from app.services.question_bank_service import (
    AnswerService,
    CoreValueService,
    QuestionService,
    VersionService,
)
from app.services.test_service import TestService


class QuestionBankServiceTests(TestCase):
    def setUp(self):
        self.core_value = CoreValueService().create({"name": " Intégrité "}, "Admin")
        self.version = VersionService().create(
            {"name": "V1", "core_value_id": self.core_value.id}, "Admin"
        )
        self.question = QuestionService().create(
            {"text": "Question ?", "ponderation": Decimal("3"), "version_id": self.version.id},
            "Admin",
        )

    def test_core_value_name_is_stripped_and_unique(self):
        self.assertEqual(self.core_value.name, "Intégrité")
        with self.assertRaises(BusinessError):
            CoreValueService().create({"name": "Intégrité"})
        # Renommer avec son propre nom reste autorisé.
        CoreValueService().update(self.core_value.id, {"name": "Intégrité"})

    def test_version_name_unique_within_core_value_only(self):
        with self.assertRaises(BusinessError):
            VersionService().create({"name": "V1", "core_value_id": self.core_value.id})
        other = CoreValueService().create({"name": "Respect"})
        moved = VersionService().create({"name": "V1", "core_value_id": other.id})
        with self.assertRaises(BusinessError):
            VersionService().update(moved.id, {"core_value_id": self.core_value.id})

    def test_version_requires_existing_core_value(self):
        with self.assertRaises(BusinessError):
            VersionService().create({"name": "V2", "core_value_id": uuid.uuid4()})

    def test_create_and_update_record_author(self):
        self.assertEqual(self.question.modifie_par_nom, "Admin")
        self.assertIsNotNone(self.question.modifie_le)
        updated = QuestionService().update(
            self.question.id, {"ponderation": Decimal("7.5")}, "Autre admin"
        )
        self.assertEqual(updated.ponderation, Decimal("7.5"))
        self.assertEqual(updated.modifie_par_nom, "Autre admin")

    def test_deleting_child_stamps_parent(self):
        answer = AnswerService().create(
            {"question_id": self.question.id, "text": "R", "percentage": 50}
        )
        AnswerService().delete(answer.id, "Autre admin")
        self.question.refresh_from_db()
        self.assertEqual(self.question.modifie_par_nom, "Autre admin")
        with self.assertRaises(NotFoundError):
            AnswerService().get_by_id(answer.id)

    def test_used_items_cannot_be_deleted(self):
        answer = AnswerService().create(
            {"question_id": self.question.id, "text": "R", "percentage": 100}
        )
        service = TestService()
        created = service.generate("Salma", "Idrissi", "salma@example.com")
        test = service.get(created["id"])
        service.save_answer(test, answer.id)
        with self.assertRaisesMessage(BusinessError, "déjà utilisée dans un test candidat"):
            AnswerService().delete(answer.id)
        with self.assertRaises(BusinessError):
            QuestionService().delete(self.question.id)
        with self.assertRaises(BusinessError):
            VersionService().delete(self.version.id)
        # Supprimer le test libère la banque.
        service.delete(test.id)
        self.assertFalse(TestVersionAnswer.objects.exists())
        CoreValueService().delete(self.core_value.id)
        self.assertFalse(Version.objects.exists())
        self.assertFalse(Question.objects.exists())


class QuestionBankApiTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="admin", password="secret-pass", first_name="Salma", last_name="Idrissi"
        )
        self.client = APIClient()
        self.client.force_authenticate(self.user)

    def test_requires_authentication(self):
        self.assertEqual(APIClient().get("/api/core-values/").status_code, 401)

    def test_full_crud_flow(self):
        core_value = self.client.post("/api/core-values/", {"name": "Intégrité"}, format="json")
        self.assertEqual(core_value.status_code, 201, core_value.data)
        self.assertEqual(core_value.data["modifie_par_nom"], "Salma Idrissi")
        duplicate = self.client.post("/api/core-values/", {"name": "Intégrité"}, format="json")
        self.assertEqual(duplicate.status_code, 400)

        version = self.client.post(
            "/api/core-value-versions/",
            {"name": "V1", "core_value_id": core_value.data["id"]},
            format="json",
        )
        self.assertEqual(version.status_code, 201, version.data)
        question = self.client.post(
            "/api/core-value-questions/",
            {"text": "Comment priorisez-vous ?", "ponderation": "1.5", "version_id": version.data["id"]},
            format="json",
        )
        self.assertEqual(question.status_code, 201, question.data)
        answer = self.client.post(
            "/api/core-value-answers/",
            {"question_id": question.data["id"], "text": "Un plan clair.", "percentage": "25"},
            format="json",
        )
        self.assertEqual(answer.status_code, 201, answer.data)
        invalid = self.client.post(
            "/api/core-value-answers/",
            {"question_id": question.data["id"], "text": "R", "percentage": "101"},
            format="json",
        )
        self.assertEqual(invalid.status_code, 400)
        self.assertEqual(Answer.objects.count(), 1)

        patched = self.client.patch(
            f"/api/core-value-answers/{answer.data['id']}/", {"percentage": "80"}, format="json"
        )
        self.assertEqual(patched.status_code, 200, patched.data)
        self.assertEqual(Decimal(patched.data["percentage"]), Decimal("80"))

        listed = self.client.get("/api/core-value-versions/", {"core_value_id": core_value.data["id"]})
        self.assertEqual(len(listed.data), 1)
        self.assertEqual(
            self.client.get("/api/core-value-versions/", {"core_value_id": "pas-un-uuid"}).status_code,
            400,
        )
        self.assertEqual(self.client.get("/api/core-value-versions/pas-un-uuid/").status_code, 404)

        deleted = self.client.delete(f"/api/core-values/{core_value.data['id']}/")
        self.assertEqual(deleted.status_code, 204)
        self.assertFalse(CoreValue.objects.exists())
        self.assertFalse(Test.objects.exists())

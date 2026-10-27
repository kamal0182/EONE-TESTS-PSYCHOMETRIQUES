import random
import uuid
from decimal import Decimal

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from app.exceptions import BusinessError, NotFoundError
from app.models import Test
from app.repositories import (
    CoreValueRepository,
    TestRepository,
    TestVersionAnswerRepository,
    TestVersionRepository,
    VersionRepository,
)


class TestService:
    """Génération, lien candidat et résultats des tests psychométriques (côté admin)."""

    def __init__(self):
        self.repository = TestRepository()
        self.core_value_repository = CoreValueRepository()
        self.version_repository = VersionRepository()
        self.test_version_repository = TestVersionRepository()
        self.test_version_answer_repository = TestVersionAnswerRepository()

    def list(self):
        tests = self.repository.list_all()
        for test in tests:
            self.refresh_statut(test)
        return [self.serialize(test) for test in tests]

    def generate(self, prenom, nom, email):
        """Crée un test avec une version tirée au hasard par core value."""
        core_values = self.core_value_repository.get_all()
        if not core_values:
            raise BusinessError(
                "Aucune core value n'est configurée : impossible de générer un test."
            )

        versions_by_core_value = {}
        for version in self.version_repository.get_all():
            versions_by_core_value.setdefault(version.core_value_id, []).append(
                version
            )

        missing = [
            core_value.name
            for core_value in core_values
            if core_value.id not in versions_by_core_value
        ]
        if missing:
            raise BusinessError(
                "Impossible de générer un test : aucune version pour "
                + ", ".join(missing)
                + "."
            )

        picked = [
            random.choice(versions_by_core_value[core_value.id])
            for core_value in core_values
        ]
        with transaction.atomic():
            test = self.repository.create(
                prenom=prenom.strip(), nom=nom.strip(), email=email.strip()
            )
            self.test_version_repository.bulk_create(test, picked)
        return self.serialize(self.get(test.id))

    def get(self, test_id):
        test = self.repository.get_by_id(test_id)
        if test is None:
            raise NotFoundError("Test introuvable.")
        return test

    def detail(self, test_id):
        test = self.refresh_statut(self.get(test_id))
        sections = self.build_sections(test, with_scoring=True)
        scores = {
            item.id: self._ratio(*self._section_totals(item))
            for item in test.test_versions.all()
        }
        for section in sections:
            section["percentage"] = scores.get(section["test_version_id"])
        return {
            **self.serialize(test),
            "started_at": test.started_at,
            "sections": sections,
        }

    def delete(self, test_id):
        self.repository.delete(self.get(test_id))

    def creer_lien(self, test_id):
        """Crée le lien du candidat (valable 7 jours) : l'admin le transmet lui-même."""
        test = self.get(test_id)
        if test.statut != Test.STATUT_A_ENVOYER:
            raise BusinessError("Le lien de ce test a déjà été créé.")
        now = timezone.now()
        self.repository.update(
            test,
            {
                "statut": Test.STATUT_ENVOYE,
                "token": uuid.uuid4(),
                "token_expires_at": now + Test.LIEN_VALIDITE,
                "sent_at": now,
            },
        )
        return self.serialize(test)

    def prolonger_lien(self, test_id):
        test = self.refresh_statut(self.get(test_id))
        if test.statut != Test.STATUT_ENVOYE:
            raise BusinessError(
                "Seul le lien d'un test envoyé et non commencé peut être prolongé."
            )
        now = timezone.now()
        # Même lien, validité prolongée de 7 jours à partir d'aujourd'hui.
        self.repository.update(
            test,
            {
                "token_expires_at": now + Test.LIEN_VALIDITE,
                "last_relance_at": now,
                "relance_count": test.relance_count + 1,
            },
        )
        return self.serialize(test)

    @staticmethod
    def test_url(token):
        return f"{settings.FRONTEND_URL.rstrip('/')}/passer-test?token={token}"

    def refresh_statut(self, test):
        """Clôture le test quand le chrono de 15 minutes est dépassé."""
        if test.statut == Test.STATUT_EN_COURS and test.is_time_over():
            self.repository.update(
                test,
                {"statut": Test.STATUT_REPONDU, "submitted_at": test.deadline},
            )
        return test

    def save_answer(self, test, answer_id):
        """Enregistre la réponse choisie, quelle que soit la question du test."""
        for test_version, question, _, _ in self.ordered_questions(test):
            answer = self.find_answer(question, answer_id)
            if answer is not None:
                self.store_answer(test_version, question, answer)
                return {"question_id": question.id, "answer_id": answer.id}
        raise NotFoundError("Réponse introuvable dans ce test.")

    def store_answer(self, test_version, question, answer):
        """Une seule réponse par question : la nouvelle remplace l'ancienne."""
        existing = self.selected_answer(test_version, question)
        if existing is None:
            self.test_version_answer_repository.create(
                answer=answer, test_version=test_version
            )
        elif existing.answer_id != answer.id:
            self.test_version_answer_repository.update(existing, {"answer": answer})

    @staticmethod
    def find_answer(question, answer_id):
        return next(
            (item for item in question.answers.all() if str(item.id) == str(answer_id)),
            None,
        )

    @staticmethod
    def selected_answer(test_version, question):
        return next(
            (
                item
                for item in test_version.test_version_answers.all()
                if item.answer.question_id == question.id
            ),
            None,
        )

    @staticmethod
    def ordered_questions(test):
        """Questions dans l'ordre de passage :
        [(test_version, question, position dans la section, taille de la section)]."""
        versions = sorted(
            test.test_versions.all(),
            key=lambda item: item.version.core_value.name,
        )
        items = []
        for test_version in versions:
            questions = list(test_version.version.questions.all())
            for index, question in enumerate(questions):
                items.append((test_version, question, index, len(questions)))
        return items

    @staticmethod
    def build_sections(test, with_scoring):
        """Questions du test ; sans pondération ni pourcentages pour le candidat."""
        selected = {
            (item.test_version_id, item.answer.question_id): item.answer_id
            for test_version in test.test_versions.all()
            for item in test_version.test_version_answers.all()
        }
        versions = sorted(
            test.test_versions.all(),
            key=lambda item: item.version.core_value.name,
        )
        sections = []
        for item in versions:
            questions = []
            for question in item.version.questions.all():
                answers = []
                for answer in question.answers.all():
                    entry = {"id": answer.id, "text": answer.text}
                    if with_scoring:
                        entry["percentage"] = answer.percentage
                    answers.append(entry)
                entry = {
                    "id": question.id,
                    "text": question.text,
                    "selected_answer_id": selected.get((item.id, question.id)),
                    "answers": answers,
                }
                if with_scoring:
                    entry["ponderation"] = question.ponderation
                questions.append(entry)
            sections.append(
                {
                    "test_version_id": item.id,
                    "core_value_name": item.version.core_value.name,
                    "version_name": item.version.name,
                    "questions": questions,
                }
            )
        return sections

    def serialize(self, test):
        versions = sorted(
            test.test_versions.all(),
            key=lambda item: item.version.core_value.name,
        )
        return {
            "id": test.id,
            "created_at": test.created_at,
            "prenom": test.prenom,
            "nom": test.nom,
            "email": test.email,
            "versions": [
                {
                    "test_version_id": item.id,
                    "core_value_name": item.version.core_value.name,
                    "version_name": item.version.name,
                }
                for item in versions
            ],
            "statut": test.statut,
            "statut_label": test.get_statut_display(),
            "lien": self.test_url(test.token) if test.token else None,
            "sent_at": test.sent_at,
            "last_relance_at": test.last_relance_at,
            "relance_count": test.relance_count,
            "token_expires_at": test.token_expires_at,
            "submitted_at": test.submitted_at,
            "score_global": self._compute_score_global(test),
        }

    @classmethod
    def _compute_score_global(cls, test):
        """Score calculé à la volée (jamais stocké) :
        Σ(pourcentage réponse choisie × pondération) / Σ pondération.
        Une question sans réponse compte 0 mais garde sa pondération."""
        numerator = Decimal("0")
        denominator = Decimal("0")
        for test_version in test.test_versions.all():
            num, den = cls._section_totals(test_version)
            numerator += num
            denominator += den
        return cls._ratio(numerator, denominator)

    @staticmethod
    def _section_totals(test_version):
        """(Σ pourcentage × pondération, Σ pondération) pour une core value."""
        chosen = {
            item.answer.question_id: item.answer.percentage
            for item in test_version.test_version_answers.all()
        }
        numerator = Decimal("0")
        denominator = Decimal("0")
        for question in test_version.version.questions.all():
            numerator += chosen.get(question.id, Decimal("0")) * question.ponderation
            denominator += question.ponderation
        return numerator, denominator

    @staticmethod
    def _ratio(numerator, denominator):
        if not denominator:
            return None
        return (numerator / denominator).quantize(Decimal("0.01"))

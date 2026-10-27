from django.core.exceptions import ValidationError

from app.models import (
    Answer,
    CoreValue,
    Question,
    Test,
    TestVersion,
    TestVersionAnswer,
    Version,
)


class CrudRepository:
    model = None
    related_fields = ()

    def queryset(self):
        return self.model.objects.select_related(*self.related_fields)

    def get_by_id(self, item_id):
        try:
            return self.queryset().filter(id=item_id).first()
        except (ValidationError, ValueError):
            return None

    def get_all(self, **filters):
        return list(self.queryset().filter(**filters))

    def exists(self, exclude_id=None, **filters):
        queryset = self.model.objects.filter(**filters)
        if exclude_id is not None:
            queryset = queryset.exclude(id=exclude_id)
        return queryset.exists()

    def create(self, **fields):
        return self.model.objects.create(**fields)

    def update(self, instance, fields):
        for name, value in fields.items():
            setattr(instance, name, value)
        instance.save()
        return instance

    def delete(self, instance):
        instance.delete()


class CoreValueRepository(CrudRepository):
    model = CoreValue


class VersionRepository(CrudRepository):
    model = Version
    related_fields = ("core_value",)


class QuestionRepository(CrudRepository):
    model = Question
    related_fields = ("version",)


class AnswerRepository(CrudRepository):
    model = Answer
    related_fields = ("question",)


class TestVersionRepository(CrudRepository):
    model = TestVersion
    related_fields = ("test", "version")

    def bulk_create(self, test, versions):
        return TestVersion.objects.bulk_create(
            [TestVersion(test=test, version=version) for version in versions]
        )


class TestVersionAnswerRepository(CrudRepository):
    model = TestVersionAnswer
    related_fields = ("answer", "answer__question", "test_version")


class TestRepository(CrudRepository):
    model = Test

    def queryset(self):
        # Tout le contenu du test est préchargé : statut, sections et score.
        return Test.objects.prefetch_related(
            "test_versions__version__core_value",
            "test_versions__version__questions__answers",
            "test_versions__test_version_answers__answer",
        )

    def get_by_token(self, token):
        try:
            return self.queryset().filter(token=token).first()
        except (ValidationError, ValueError):
            return None

    def lock_by_token(self, token):
        """Verrouille la ligne du test (à appeler dans une transaction) :
        les requêtes d'un même candidat sont traitées l'une après l'autre."""
        try:
            return Test.objects.select_for_update().filter(token=token).first()
        except (ValidationError, ValueError):
            return None

    def list_all(self):
        return list(self.queryset().order_by("-created_at"))

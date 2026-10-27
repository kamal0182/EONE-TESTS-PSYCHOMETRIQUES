import uuid

from django.db import models


class TestVersionAnswer(models.Model):
    """Réponse choisie par le candidat (une seule par question)."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    answer = models.ForeignKey(
        "Answer",
        on_delete=models.PROTECT,
        related_name="test_version_answers",
    )
    test_version = models.ForeignKey(
        "TestVersion",
        on_delete=models.CASCADE,
        related_name="test_version_answers",
    )

    class Meta:
        db_table = "test_version_answers"
        constraints = [
            models.UniqueConstraint(
                fields=["answer", "test_version"],
                name="uniq_test_version_answer",
            )
        ]

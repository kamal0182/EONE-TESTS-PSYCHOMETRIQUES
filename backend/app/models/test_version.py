import uuid

from django.db import models


class TestVersion(models.Model):
    """Version d'une core value tirée pour un test."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    test = models.ForeignKey(
        "Test",
        on_delete=models.CASCADE,
        related_name="test_versions",
    )
    version = models.ForeignKey(
        "Version",
        on_delete=models.PROTECT,
        related_name="test_versions",
    )

    class Meta:
        db_table = "test_versions"
        constraints = [
            models.UniqueConstraint(
                fields=["test", "version"],
                name="uniq_test_version",
            )
        ]

import uuid

from django.db import models

from .modification_trace import ModificationTrace


class Version(ModificationTrace):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    core_value = models.ForeignKey(
        "CoreValue",
        on_delete=models.CASCADE,
        related_name="versions",
    )

    class Meta:
        db_table = "core_value_versions"
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(
                fields=["core_value", "name"],
                name="uniq_version_name_per_core_value",
            )
        ]

    def __str__(self):
        return self.name

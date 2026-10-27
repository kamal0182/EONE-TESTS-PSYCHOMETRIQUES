import uuid

from django.db import models

from .modification_trace import ModificationTrace


class CoreValue(ModificationTrace):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255, unique=True)

    class Meta:
        db_table = "core_values"
        ordering = ["name"]

    def __str__(self):
        return self.name

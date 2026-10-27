import uuid
from decimal import Decimal

from django.core.validators import MinValueValidator
from django.db import models

from .modification_trace import ModificationTrace


class Question(ModificationTrace):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    text = models.TextField()
    ponderation = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0"))],
    )
    version = models.ForeignKey(
        "Version",
        on_delete=models.CASCADE,
        related_name="questions",
    )
    # Ordre d'affichage stable (ordre de saisie) pour le candidat.
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "questions"
        ordering = ["created_at", "id"]

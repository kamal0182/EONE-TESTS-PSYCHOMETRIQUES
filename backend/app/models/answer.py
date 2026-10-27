import uuid
from decimal import Decimal

from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

from .modification_trace import ModificationTrace


class Answer(ModificationTrace):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    question = models.ForeignKey(
        "Question",
        on_delete=models.CASCADE,
        related_name="answers",
    )
    text = models.TextField()
    percentage = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        validators=[
            MinValueValidator(Decimal("0")),
            MaxValueValidator(Decimal("100")),
        ],
    )
    # Ordre d'affichage stable (A, B, C, D) pour le candidat.
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "answers"
        ordering = ["created_at", "id"]

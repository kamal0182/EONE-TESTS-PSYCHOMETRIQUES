from django.db import models


class ModificationTrace(models.Model):
    """Auteur et date de la dernière modification (banque de questions)."""

    modifie_par_nom = models.CharField(max_length=255, blank=True, default="")
    modifie_le = models.DateTimeField(null=True, blank=True)

    class Meta:
        abstract = True

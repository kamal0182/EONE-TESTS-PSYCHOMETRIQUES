import uuid
from datetime import timedelta

from django.db import models
from django.utils import timezone


class Test(models.Model):
    STATUT_A_ENVOYER = "a_envoyer"
    STATUT_ENVOYE = "envoye"
    STATUT_EN_COURS = "en_cours"
    STATUT_REPONDU = "repondu"
    STATUT_CHOICES = [
        (STATUT_A_ENVOYER, "À envoyer"),
        (STATUT_ENVOYE, "Envoyé"),
        (STATUT_EN_COURS, "En cours"),
        (STATUT_REPONDU, "Répondu"),
    ]

    # Durée de validité du lien envoyé au candidat, et durée du chrono.
    LIEN_VALIDITE = timedelta(days=7)
    DUREE_TEST = timedelta(minutes=15)
    # Tolérance réseau : une réponse envoyée dans les dernières secondes reste acceptée.
    MARGE_REPONSE = timedelta(seconds=15)

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    # Candidat saisi directement par l'administrateur.
    prenom = models.CharField(max_length=150)
    nom = models.CharField(max_length=150)
    email = models.EmailField()
    statut = models.CharField(
        max_length=20, choices=STATUT_CHOICES, default=STATUT_A_ENVOYER
    )
    # Jeton du lien public ; généré au premier envoi.
    token = models.UUIDField(unique=True, null=True, blank=True, editable=False)
    token_expires_at = models.DateTimeField(null=True, blank=True)
    sent_at = models.DateTimeField(null=True, blank=True)
    last_relance_at = models.DateTimeField(null=True, blank=True)
    relance_count = models.PositiveIntegerField(default=0)
    started_at = models.DateTimeField(null=True, blank=True)
    # Position du candidat dans le test (0 = première question). Seule la question
    # à cette position est envoyée et modifiable : pas de retour en arrière.
    current_index = models.PositiveIntegerField(default=0)
    submitted_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "tests"
        ordering = ["-created_at"]

    @property
    def full_name(self):
        return " ".join(value for value in [self.prenom, self.nom] if value)

    @property
    def deadline(self):
        return self.started_at + self.DUREE_TEST if self.started_at else None

    def is_link_expired(self):
        return bool(self.token_expires_at and timezone.now() > self.token_expires_at)

    def is_time_over(self):
        """Temps écoulé, marge réseau comprise."""
        return bool(self.deadline and timezone.now() > self.deadline + self.MARGE_REPONSE)

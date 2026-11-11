import logging
import smtplib

from django.conf import settings
from django.core.mail import EmailMultiAlternatives, get_connection
from django.utils import timezone
from django.utils.html import format_html

from app.exceptions import BusinessError


logger = logging.getLogger(__name__)

SMTP_BACKEND = "django.core.mail.backends.smtp.EmailBackend"


class EmailService:
    """Envoi du lien de test au candidat via le serveur SMTP configuré dans .env."""

    SUBJECT = "Votre test psychométrique"

    def send_test_link(self, test, url, duree_minutes):
        """Envoi unitaire : toute erreur SMTP devient une BusinessError lisible."""
        self.ensure_configured()
        message = self.build_test_link_message(test, url, duree_minutes)
        try:
            message.send()
        except (smtplib.SMTPException, OSError) as exc:
            logger.exception("SMTP : échec de l'envoi à %s", test.email)
            raise BusinessError(self.error_message(exc, test.email)) from exc

    def open_connection(self):
        """Une seule connexion SMTP (connexion + authentification) pour un lot d'emails."""
        self.ensure_configured()
        connection = get_connection(fail_silently=False)
        try:
            connection.open()
        except (smtplib.SMTPException, OSError) as exc:
            logger.exception("SMTP : connexion impossible")
            raise BusinessError(self.error_message(exc)) from exc
        return connection

    def send_on(self, connection, message):
        """Envoie un message sur une connexion déjà ouverte.

        Renvoie (message d'erreur ou None, connexion perdue ?). Si le serveur a
        coupé la connexion, elle est rouverte une fois ; si c'est impossible,
        la connexion est perdue et le lot doit s'arrêter."""
        error, lost = self._send_once(connection, message)
        if not lost:
            return error, False
        connection.close()
        try:
            connection.open()
        except (smtplib.SMTPException, OSError) as exc:
            logger.exception("SMTP : reconnexion impossible")
            return self.error_message(exc), True
        return self._send_once(connection, message)

    def _send_once(self, connection, message):
        try:
            connection.send_messages([message])
            return None, False
        except (smtplib.SMTPException, OSError) as exc:
            logger.exception("SMTP : échec de l'envoi à %s", message.to[0])
            return self.error_message(exc, message.to[0]), self._is_connection_error(exc)

    @staticmethod
    def _is_connection_error(exc):
        # SMTPException hérite d'OSError : seules les vraies erreurs réseau comptent.
        return isinstance(exc, smtplib.SMTPServerDisconnected) or (
            isinstance(exc, OSError) and not isinstance(exc, smtplib.SMTPException)
        )

    def build_test_link_message(self, test, url, duree_minutes):
        expires = timezone.localtime(test.token_expires_at).strftime("%d/%m/%Y à %H:%M")
        message = EmailMultiAlternatives(
            subject=self.SUBJECT,
            body=self._text(test, url, duree_minutes, expires),
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[test.email],
            # Copie (CC) : reçue par ces adresses, visible par le candidat.
            cc=list(settings.EMAIL_CC),
        )
        message.attach_alternative(
            self._html(test, url, duree_minutes, expires), "text/html"
        )
        return message

    @classmethod
    def error_message(cls, exc, email=None):
        if isinstance(exc, smtplib.SMTPAuthenticationError):
            return "Email non envoyé : le serveur SMTP a refusé l'identifiant ou le mot de passe."
        if isinstance(exc, smtplib.SMTPRecipientsRefused) and email:
            return f"Email non envoyé : l'adresse {email} a été refusée par le serveur."
        if cls._is_connection_error(exc):
            return (
                "Email non envoyé : impossible de joindre le serveur SMTP. "
                "Vérifiez la configuration (EMAIL_HOST, EMAIL_PORT, TLS/SSL)."
            )
        return "Email non envoyé : le serveur SMTP a refusé le message."

    @staticmethod
    def ensure_configured():
        if settings.EMAIL_BACKEND == SMTP_BACKEND and not settings.EMAIL_HOST:
            raise BusinessError(
                "L'envoi d'emails n'est pas configuré (EMAIL_HOST manquant dans backend/.env). "
                "Utilisez « Copier le lien » ou configurez le serveur SMTP."
            )
        if not settings.DEFAULT_FROM_EMAIL:
            raise BusinessError(
                "L'expéditeur des emails n'est pas configuré "
                "(DEFAULT_FROM_EMAIL ou EMAIL_HOST_USER dans backend/.env)."
            )

    @staticmethod
    def _text(test, url, duree_minutes, expires):
        return (
            f"Bonjour {test.prenom},\n\n"
            "Vous êtes invité(e) à passer un test psychométrique.\n\n"
            f"Lien personnel : {url}\n\n"
            f"- Le lien est valable jusqu'au {expires}.\n"
            f"- Durée du test : {duree_minutes} minutes, le chrono démarre lorsque "
            "vous cliquez sur « Commencer ».\n"
            "- Une question validée ne peut plus être modifiée.\n"
            "- Prévoyez une connexion stable et un moment sans interruption.\n\n"
            "Ce lien vous est personnel : merci de ne pas le partager.\n\n"
            "Cordialement,\nL'équipe Recrutement"
        )

    @staticmethod
    def _html(test, url, duree_minutes, expires):
        return format_html(
            """<div style="font-family:Arial,sans-serif;font-size:14px;color:#14211b;line-height:1.5">
  <p>Bonjour {prenom},</p>
  <p>Vous êtes invité(e) à passer un test psychométrique.</p>
  <p style="margin:24px 0">
    <a href="{url}" style="background:#1f7a55;color:#ffffff;padding:12px 22px;border-radius:6px;text-decoration:none;font-weight:bold">Commencer le test</a>
  </p>
  <ul>
    <li>Le lien est valable jusqu'au <strong>{expires}</strong>.</li>
    <li>Durée du test : <strong>{duree} minutes</strong>, le chrono démarre lorsque vous cliquez sur « Commencer ».</li>
    <li>Une question validée ne peut plus être modifiée.</li>
    <li>Prévoyez une connexion stable et un moment sans interruption.</li>
  </ul>
  <p style="color:#5d6f86;font-size:12px">Si le bouton ne fonctionne pas, copiez ce lien dans votre navigateur :<br>{url}</p>
  <p>Ce lien vous est personnel : merci de ne pas le partager.</p>
  <p>Cordialement,<br>L'équipe Recrutement</p>
</div>""",
            prenom=test.prenom,
            url=url,
            expires=expires,
            duree=duree_minutes,
        )

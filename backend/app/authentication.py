from django.conf import settings
from django.utils import timezone
from rest_framework import exceptions
from rest_framework.authentication import TokenAuthentication
from rest_framework.authtoken.models import Token


def is_token_expired(token):
    return token.created < timezone.now() - settings.TOKEN_TTL


def get_valid_token(user):
    """Jeton en cours de l'utilisateur, renouvelé s'il a expiré."""
    token = Token.objects.filter(user=user).first()
    if token is not None and is_token_expired(token):
        token.delete()
        token = None
    return token or Token.objects.create(user=user)


class BearerTokenAuthentication(TokenAuthentication):
    """Jeton DRF transmis comme `Authorization: Bearer <jeton>`, valable TOKEN_TTL."""

    keyword = "Bearer"

    def authenticate_credentials(self, key):
        user, token = super().authenticate_credentials(key)
        if is_token_expired(token):
            token.delete()
            raise exceptions.AuthenticationFailed(
                "Session expirée. Veuillez vous reconnecter."
            )
        return user, token

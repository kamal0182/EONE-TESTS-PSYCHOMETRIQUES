import math

from rest_framework import status
from rest_framework.exceptions import Throttled
from rest_framework.response import Response
from rest_framework.views import exception_handler as drf_exception_handler


class AppError(Exception):
    pass


class NotFoundError(AppError):
    pass


class BusinessError(AppError):
    """Règle métier non respectée : renvoyée en 400 avec le message."""


class LinkExpiredError(AppError):
    pass


_STATUS_BY_ERROR = (
    (NotFoundError, status.HTTP_404_NOT_FOUND),
    (LinkExpiredError, status.HTTP_410_GONE),
    (BusinessError, status.HTTP_400_BAD_REQUEST),
)


def exception_handler(exc, context):
    for error_class, http_status in _STATUS_BY_ERROR:
        if isinstance(exc, error_class):
            return Response({"detail": str(exc)}, status=http_status)
    if isinstance(exc, Throttled):
        wait = max(1, math.ceil(exc.wait or 1))
        return Response(
            {"detail": f"Trop de requêtes. Réessayez dans {wait} seconde(s)."},
            status=status.HTTP_429_TOO_MANY_REQUESTS,
            headers={"Retry-After": str(wait)},
        )
    return drf_exception_handler(exc, context)

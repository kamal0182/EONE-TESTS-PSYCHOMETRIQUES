from django.http import HttpResponse
from rest_framework.negotiation import BaseContentNegotiation
from rest_framework.permissions import AllowAny
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from app.services.test_service import TestService


class IgnoreAcceptHeader(BaseContentNegotiation):
    """Le lien est ouvert par Excel ou un navigateur, avec des en-têtes Accept
    variés : on ne refuse jamais la requête (les erreurs restent en JSON)."""

    def select_renderer(self, request, renderers, format_suffix=None):
        return renderers[0], renderers[0].media_type

    def select_parser(self, request, parsers):
        return parsers[0] if parsers else None


class ResultatPdfView(APIView):
    """PDF des résultats d'un candidat, ouvert depuis le lien de l'export Excel.

    Pas de connexion : le lien signé (impossible à deviner ou à modifier, valable
    EXPORT_LINK_DAYS jours) tient lieu d'accès. Limité à 30 requêtes par minute et par IP."""

    permission_classes = [AllowAny]
    authentication_classes = []
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "resultat_pdf"
    content_negotiation_class = IgnoreAcceptHeader

    def get(self, request, signature):
        filename, content = TestService().result_pdf(signature)
        response = HttpResponse(content, content_type="application/pdf")
        # « inline » : le PDF s'ouvre dans le navigateur (téléchargeable depuis la visionneuse).
        response["Content-Disposition"] = f'inline; filename="{filename}"'
        response["Cache-Control"] = "private, no-store"
        response["X-Robots-Tag"] = "noindex"
        return response

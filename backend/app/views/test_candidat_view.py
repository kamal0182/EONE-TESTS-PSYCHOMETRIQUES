from rest_framework.decorators import action
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.viewsets import ViewSet

from app.services.test_candidat_service import TestCandidatService


class TestCandidatViewSet(ViewSet):
    """Endpoints publics du lien envoyé au candidat : le jeton tient lieu d'accès.
    Limités à 60 requêtes par minute et par IP (largement assez pour un candidat)."""

    permission_classes = [AllowAny]
    authentication_classes = []
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "candidat"
    lookup_field = "token"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.service = TestCandidatService()

    def retrieve(self, request, token=None):
        return Response(self.service.get_state(token))

    @action(detail=True, methods=["post"], url_path="demarrer")
    def demarrer(self, request, token=None):
        return Response(self.service.demarrer(token))

    @action(detail=True, methods=["post"], url_path="repondre")
    def repondre(self, request, token=None):
        return Response(self.service.repondre(token, request.data.get("answer_id")))

    @action(detail=True, methods=["post"], url_path="suivant")
    def suivant(self, request, token=None):
        return Response(self.service.suivant(token))

    @action(detail=True, methods=["post"], url_path="terminer")
    def terminer(self, request, token=None):
        return Response(self.service.terminer(token))

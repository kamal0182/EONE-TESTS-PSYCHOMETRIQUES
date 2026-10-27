from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.viewsets import ViewSet

from app.serializers import TestCreateSerializer
from app.services.test_service import TestService


class TestViewSet(ViewSet):
    """Tests psychométriques gérés par l'administrateur."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.service = TestService()

    def list(self, request):
        return Response(self.service.list())

    def create(self, request):
        """Génère un test pour le candidat saisi (prénom, nom, email)."""
        serializer = TestCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        return Response(
            self.service.generate(**serializer.validated_data),
            status=status.HTTP_201_CREATED,
        )

    def retrieve(self, request, pk=None):
        return Response(self.service.detail(pk))

    def destroy(self, request, pk=None):
        self.service.delete(pk)
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=["post"], url_path="lien")
    def lien(self, request, pk=None):
        """Crée le lien du candidat ; l'admin le copie et le transmet lui-même."""
        return Response(self.service.creer_lien(pk))

    @action(detail=True, methods=["post"], url_path="prolonger")
    def prolonger(self, request, pk=None):
        return Response(self.service.prolonger_lien(pk))

from django.http import HttpResponse
from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.parsers import MultiPartParser
from rest_framework.response import Response
from rest_framework.viewsets import ViewSet

from app.serializers import TestCreateSerializer
from app.services.candidat_import import read_candidats
from app.services.test_service import TestService

XLSX_CONTENT_TYPE = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


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

    @action(
        detail=False,
        methods=["post"],
        url_path="importer",
        parser_classes=[MultiPartParser],
    )
    def importer(self, request):
        """Importe un fichier Excel/CSV (Prénom, Nom, Email) : un test par candidat."""
        candidats = read_candidats(request.FILES.get("file"))
        return Response(self.service.import_candidats(candidats))

    @action(detail=False, methods=["get"], url_path="exporter")
    def exporter(self, request):
        """Fichier Excel des tests terminés (Nom, Prénom, Email, Score, Date, lien PDF)."""
        content = self.service.export_excel()
        filename = f"tests-psychometriques-{timezone.localdate():%Y-%m-%d}.xlsx"
        response = HttpResponse(content, content_type=XLSX_CONTENT_TYPE)
        response["Content-Disposition"] = f'attachment; filename="{filename}"'
        response["Cache-Control"] = "private, no-store"
        return response

    def retrieve(self, request, pk=None):
        return Response(self.service.detail(pk))

    def destroy(self, request, pk=None):
        self.service.delete(pk)
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=["post"], url_path="lien")
    def lien(self, request, pk=None):
        """Crée le lien du candidat ; l'admin le copie et le transmet lui-même."""
        return Response(self.service.creer_lien(pk))

    @action(detail=True, methods=["post"], url_path="envoyer-email")
    def envoyer_email(self, request, pk=None):
        """Envoie le lien au candidat par email (SMTP), en le créant si besoin."""
        return Response(self.service.envoyer_email(pk))

    @action(detail=False, methods=["post"], url_path="envoyer-emails")
    def envoyer_emails(self, request):
        """Envoi groupé : `{ids: [...]}` (50 maximum), une seule connexion SMTP."""
        ids = request.data.get("ids")
        if not isinstance(ids, list):
            return Response(
                {"detail": "Le champ « ids » doit être une liste."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response(self.service.envoyer_emails(ids))

    @action(detail=True, methods=["post"], url_path="prolonger")
    def prolonger(self, request, pk=None):
        return Response(self.service.prolonger_lien(pk))

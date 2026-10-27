from rest_framework import serializers, status
from rest_framework.response import Response
from rest_framework.viewsets import ViewSet

from app.serializers import (
    AnswerSerializer,
    CoreValueSerializer,
    QuestionSerializer,
    VersionSerializer,
)
from app.services.question_bank_service import (
    AnswerService,
    CoreValueService,
    QuestionService,
    VersionService,
)
from .auth_view import display_name


class QuestionBankViewSet(ViewSet):
    """CRUD d'un niveau de la banque ; chaque écriture trace son auteur."""

    service_class = None
    serializer_class = None
    # Paramètres de requête (UUID) acceptés comme filtres sur la liste.
    filter_params = ()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.service = self.service_class()

    @staticmethod
    def _author(request):
        return display_name(request.user)

    def list(self, request):
        filters = {
            name: serializers.UUIDField().run_validation(request.query_params[name])
            for name in self.filter_params
            if request.query_params.get(name)
        }
        return Response(
            self.serializer_class(self.service.get_all(**filters), many=True).data
        )

    def retrieve(self, request, pk=None):
        return Response(self.serializer_class(self.service.get_by_id(pk)).data)

    def create(self, request):
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)
        item = self.service.create(
            serializer.validated_data, author=self._author(request)
        )
        return Response(
            self.serializer_class(item).data, status=status.HTTP_201_CREATED
        )

    def update(self, request, pk=None):
        serializer = self.serializer_class(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        item = self.service.update(
            pk, serializer.validated_data, author=self._author(request)
        )
        return Response(self.serializer_class(item).data)

    def partial_update(self, request, pk=None):
        return self.update(request, pk=pk)

    def destroy(self, request, pk=None):
        self.service.delete(pk, author=self._author(request))
        return Response(status=status.HTTP_204_NO_CONTENT)


class CoreValueViewSet(QuestionBankViewSet):
    service_class = CoreValueService
    serializer_class = CoreValueSerializer


class VersionViewSet(QuestionBankViewSet):
    service_class = VersionService
    serializer_class = VersionSerializer
    filter_params = ("core_value_id",)


class QuestionViewSet(QuestionBankViewSet):
    service_class = QuestionService
    serializer_class = QuestionSerializer
    filter_params = ("version_id",)


class AnswerViewSet(QuestionBankViewSet):
    service_class = AnswerService
    serializer_class = AnswerSerializer
    filter_params = ("question_id",)

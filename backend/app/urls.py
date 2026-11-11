from django.urls import include, path
from rest_framework.routers import DefaultRouter

from app.views import (
    AnswerViewSet,
    CoreValueViewSet,
    LoginView,
    LogoutView,
    MeView,
    QuestionViewSet,
    ResultatPdfView,
    TestCandidatViewSet,
    TestViewSet,
    VersionViewSet,
)


router = DefaultRouter()
# Banque de questions.
router.register("core-values", CoreValueViewSet, basename="core-values")
router.register("core-value-versions", VersionViewSet, basename="core-value-versions")
router.register("core-value-questions", QuestionViewSet, basename="core-value-questions")
router.register("core-value-answers", AnswerViewSet, basename="core-value-answers")
# Tests (admin) et passage du test (public, par jeton).
router.register("tests-psychometriques", TestViewSet, basename="tests-psychometriques")
router.register("test-candidat", TestCandidatViewSet, basename="test-candidat")

urlpatterns = [
    path("auth/login/", LoginView.as_view(), name="auth-login"),
    path("auth/logout/", LogoutView.as_view(), name="auth-logout"),
    path("auth/me/", MeView.as_view(), name="auth-me"),
    # Lien signé vers le PDF des résultats (export Excel), sans connexion.
    path("resultats-pdf/<str:signature>/", ResultatPdfView.as_view(), name="resultat-pdf"),
    path("", include(router.urls)),
]

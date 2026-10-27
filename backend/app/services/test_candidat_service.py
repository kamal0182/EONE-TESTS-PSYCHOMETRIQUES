from django.db import transaction
from django.utils import timezone

from app.exceptions import BusinessError, LinkExpiredError, NotFoundError
from app.models import Test
from .test_service import TestService


class TestCandidatService:
    """Passage du test par le candidat via son lien.

    Le serveur impose le déroulement : seule la question en cours est envoyée au
    navigateur et seule elle peut recevoir une réponse. « Suivant » la valide
    définitivement : les questions passées ne sont plus modifiables et les
    suivantes ne sont jamais envoyées à l'avance.
    """

    def __init__(self):
        self.tests = TestService()
        self.repository = self.tests.repository

    def get_state(self, token):
        return self._state(self._get(token))

    def demarrer(self, token):
        test = self._get(token)
        if test.statut == Test.STATUT_ENVOYE:
            self.repository.update(
                test,
                {
                    "statut": Test.STATUT_EN_COURS,
                    "started_at": timezone.now(),
                    "current_index": 0,
                },
            )
        return self._state(test)

    def repondre(self, token, answer_id):
        """Choisit (ou change) la réponse de la question en cours uniquement."""
        self._ensure_running(self._get(token))
        with transaction.atomic():
            test = self._get_locked(token)
            test_version, question, _, _ = self._current(test)
            answer = self.tests.find_answer(question, answer_id)
            if answer is None:
                raise BusinessError(
                    "Cette réponse ne correspond pas à la question en cours."
                )
            self.tests.store_answer(test_version, question, answer)
        return self.get_state(token)

    def suivant(self, token):
        """Valide la question en cours et passe à la suivante (ou termine le test)."""
        self._ensure_running(self._get(token))
        with transaction.atomic():
            test = self._get_locked(token)
            items = self.tests.ordered_questions(test)
            test_version, question, _, _ = self._current(test, items)
            if self.tests.selected_answer(test_version, question) is None:
                raise BusinessError("Choisissez une réponse avant de continuer.")
            fields = {"current_index": test.current_index + 1}
            if fields["current_index"] >= len(items):
                fields.update(
                    {"statut": Test.STATUT_REPONDU, "submitted_at": timezone.now()}
                )
            self.repository.update(test, fields)
        return self.get_state(token)

    def terminer(self, token):
        test = self._get(token)
        if test.statut == Test.STATUT_EN_COURS:
            self.repository.update(
                test,
                {"statut": Test.STATUT_REPONDU, "submitted_at": timezone.now()},
            )
        return self._state(test)

    def _get(self, token):
        test = self.repository.get_by_token(token)
        if test is None:
            raise NotFoundError("Ce lien de test est invalide.")
        # Clôture (et enregistre) le test si le temps est écoulé.
        self.tests.refresh_statut(test)
        # Le lien n'expire que tant que le test n'a pas démarré.
        if test.statut == Test.STATUT_ENVOYE and test.is_link_expired():
            raise LinkExpiredError("Ce lien a expiré. Merci de contacter le recruteur.")
        return test

    def _get_locked(self, token):
        """Dans une transaction : verrouille le test puis le relit à jour."""
        if self.repository.lock_by_token(token) is None:
            raise NotFoundError("Ce lien de test est invalide.")
        test = self._get(token)
        self._ensure_running(test)
        return test

    @staticmethod
    def _ensure_running(test):
        if test.statut == Test.STATUT_REPONDU:
            raise BusinessError("Le test est terminé.")
        if test.statut != Test.STATUT_EN_COURS:
            raise BusinessError("Ce test n'est pas en cours.")

    def _current(self, test, items=None):
        items = items if items is not None else self.tests.ordered_questions(test)
        if test.current_index >= len(items):
            raise BusinessError("Le test est terminé.")
        return items[test.current_index]

    def _state(self, test):
        items = self.tests.ordered_questions(test)
        state = {
            "statut": test.statut,
            "prenom": test.prenom,
            "nom": test.nom,
            "duree_minutes": int(Test.DUREE_TEST.total_seconds() // 60),
            "nb_questions": len(items),
        }
        if test.statut == Test.STATUT_EN_COURS:
            remaining = (test.deadline - timezone.now()).total_seconds()
            state["remaining_seconds"] = max(0, int(remaining))
            state["question_index"] = test.current_index
            state["question"] = None
            if test.current_index < len(items):
                test_version, question, index, size = items[test.current_index]
                selected = self.tests.selected_answer(test_version, question)
                # Uniquement la question en cours, sans pondération ni pourcentages.
                state["question"] = {
                    "id": question.id,
                    "text": question.text,
                    "core_value_name": test_version.version.core_value.name,
                    "index_in_section": index,
                    "section_size": size,
                    "selected_answer_id": selected.answer_id if selected else None,
                    "answers": [
                        {"id": answer.id, "text": answer.text}
                        for answer in question.answers.all()
                    ],
                }
        return state

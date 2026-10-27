from django.db.models.deletion import ProtectedError
from django.utils import timezone

from app.exceptions import BusinessError
from app.repositories import (
    AnswerRepository,
    CoreValueRepository,
    QuestionRepository,
    VersionRepository,
)
from .crud_service import CrudService


class QuestionBankService(CrudService):
    """Base de la banque de questions : trace l'auteur de chaque modification."""

    # Attribut pointant vers l'élément parent, dont la trace est mise à jour
    # lorsqu'un enfant est supprimé (la suppression reste ainsi visible).
    parent_field = None

    @staticmethod
    def _trace(author):
        if not author:
            return {}
        return {"modifie_par_nom": author, "modifie_le": timezone.now()}

    def delete(self, item_id, author=None):
        item = self.get_by_id(item_id)
        parent = getattr(item, self.parent_field) if self.parent_field else None
        try:
            self.repository.delete(item)
        except ProtectedError as exc:
            raise BusinessError(
                f"{self.label} déjà utilisée dans un test candidat : "
                "suppression impossible. Vous pouvez la modifier."
            ) from exc
        trace = self._trace(author)
        if parent is not None and trace:
            for name, value in trace.items():
                setattr(parent, name, value)
            parent.save(update_fields=list(trace))


class CoreValueService(QuestionBankService):
    repository_class = CoreValueRepository
    label = "Core value"

    def create(self, data, author=None):
        name = data["name"].strip()
        self._ensure_unique(name)
        return self._save(
            lambda: self.repository.create(name=name, **self._trace(author))
        )

    def update(self, core_value_id, data, author=None):
        core_value = self.get_by_id(core_value_id)
        fields = {}
        if "name" in data:
            fields["name"] = data["name"].strip()
            self._ensure_unique(fields["name"], exclude_id=core_value.id)
        fields.update(self._trace(author))
        return self._save(lambda: self.repository.update(core_value, fields))

    def _ensure_unique(self, name, exclude_id=None):
        if self.repository.exists(exclude_id=exclude_id, name=name):
            raise BusinessError(f"{self.label} existe déjà.")


class VersionService(QuestionBankService):
    repository_class = VersionRepository
    label = "Version"
    parent_field = "core_value"

    def __init__(self):
        super().__init__()
        self.core_value_repository = CoreValueRepository()

    def create(self, data, author=None):
        core_value = self._require(
            self.core_value_repository, data["core_value_id"], "Core value"
        )
        name = data["name"].strip()
        self._ensure_unique(core_value.id, name)
        return self._save(
            lambda: self.repository.create(
                name=name, core_value=core_value, **self._trace(author)
            )
        )

    def update(self, version_id, data, author=None):
        version = self.get_by_id(version_id)
        fields = {}
        if "name" in data:
            fields["name"] = data["name"].strip()
        if "core_value_id" in data:
            fields["core_value"] = self._require(
                self.core_value_repository, data["core_value_id"], "Core value"
            )
        core_value = fields.get("core_value", version.core_value)
        self._ensure_unique(
            core_value.id,
            fields.get("name", version.name),
            exclude_id=version.id,
        )
        fields.update(self._trace(author))
        return self._save(lambda: self.repository.update(version, fields))

    def _ensure_unique(self, core_value_id, name, exclude_id=None):
        if self.repository.exists(
            exclude_id=exclude_id, core_value_id=core_value_id, name=name
        ):
            raise BusinessError(
                "Une version portant ce nom existe déjà pour cette core value."
            )


class QuestionService(QuestionBankService):
    repository_class = QuestionRepository
    label = "Question"
    parent_field = "version"

    def __init__(self):
        super().__init__()
        self.version_repository = VersionRepository()

    def create(self, data, author=None):
        version = self._require(self.version_repository, data["version_id"], "Version")
        return self._save(
            lambda: self.repository.create(
                text=data["text"],
                ponderation=data["ponderation"],
                version=version,
                **self._trace(author),
            )
        )

    def update(self, question_id, data, author=None):
        question = self.get_by_id(question_id)
        fields = {}
        if "text" in data:
            fields["text"] = data["text"]
        if "ponderation" in data:
            fields["ponderation"] = data["ponderation"]
        if "version_id" in data:
            fields["version"] = self._require(
                self.version_repository, data["version_id"], "Version"
            )
        fields.update(self._trace(author))
        return self._save(lambda: self.repository.update(question, fields))


class AnswerService(QuestionBankService):
    repository_class = AnswerRepository
    label = "Réponse"
    parent_field = "question"

    def __init__(self):
        super().__init__()
        self.question_repository = QuestionRepository()

    def create(self, data, author=None):
        question = self._require(
            self.question_repository, data["question_id"], "Question"
        )
        return self._save(
            lambda: self.repository.create(
                question=question,
                text=data["text"],
                percentage=data["percentage"],
                **self._trace(author),
            )
        )

    def update(self, answer_id, data, author=None):
        answer = self.get_by_id(answer_id)
        fields = {}
        if "text" in data:
            fields["text"] = data["text"]
        if "percentage" in data:
            fields["percentage"] = data["percentage"]
        if "question_id" in data:
            fields["question"] = self._require(
                self.question_repository, data["question_id"], "Question"
            )
        fields.update(self._trace(author))
        return self._save(lambda: self.repository.update(answer, fields))

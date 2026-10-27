from django.db import IntegrityError, transaction
from django.db.models.deletion import ProtectedError

from app.exceptions import BusinessError, NotFoundError


class CrudService:
    repository_class = None
    label = "Élément"

    def __init__(self):
        self.repository = self.repository_class()

    def get_all(self, **filters):
        return self.repository.get_all(**filters)

    def get_by_id(self, item_id):
        item = self.repository.get_by_id(item_id)
        if item is None:
            raise NotFoundError(f"{self.label} introuvable.")
        return item

    def delete(self, item_id):
        item = self.get_by_id(item_id)
        try:
            self.repository.delete(item)
        except ProtectedError as exc:
            raise BusinessError(
                f"{self.label} est utilisé et ne peut pas être supprimé."
            ) from exc

    def _save(self, operation):
        try:
            with transaction.atomic():
                return operation()
        except IntegrityError as exc:
            raise BusinessError(f"{self.label} existe déjà.") from exc

    @staticmethod
    def _require(repository, item_id, label):
        item = repository.get_by_id(item_id)
        if item is None:
            raise BusinessError(f"{label} introuvable.")
        return item

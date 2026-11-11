import random
import uuid
from decimal import Decimal

from django.conf import settings
from django.core import signing
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.db import transaction
from django.utils import timezone
from django.utils.text import slugify

from app.exceptions import BusinessError, LinkExpiredError, NotFoundError
from app.models import Test
from app.repositories import (
    CoreValueRepository,
    TestRepository,
    TestVersionAnswerRepository,
    TestVersionRepository,
    VersionRepository,
)
from .email_service import EmailService
from .export_service import build_tests_workbook
from .result_pdf import build_result_pdf


class TestService:
    """Génération, lien candidat et résultats des tests psychométriques (côté admin)."""

    # Taille maximale d'un envoi groupé : le frontend découpe la sélection en lots
    # plus petits pour rester loin du délai maximal d'une requête.
    MAX_EMAILS_PAR_ENVOI = 50
    LINK_FIELDS = ["statut", "token", "token_expires_at", "sent_at", "email_sent_at"]

    def __init__(self):
        self.repository = TestRepository()
        self.core_value_repository = CoreValueRepository()
        self.version_repository = VersionRepository()
        self.test_version_repository = TestVersionRepository()
        self.test_version_answer_repository = TestVersionAnswerRepository()
        self.email_service = EmailService()

    def list(self):
        tests = self.repository.list_all()
        for test in tests:
            self.refresh_statut(test)
        return [self.serialize(test) for test in tests]

    def generate(self, prenom, nom, email):
        """Crée un test avec une version tirée au hasard par core value."""
        pick_versions = self._version_picker()
        with transaction.atomic():
            test = self._create_test(prenom, nom, email, pick_versions())
        return self.serialize(self.get(test.id))

    def import_candidats(self, candidats):
        """Génère un test par ligne valide du fichier importé.

        `candidats` : [(numéro de ligne, {prenom, nom, email})]. Les lignes
        incomplètes, les emails invalides, les doublons du fichier et les emails
        ayant déjà un test sont ignorés et renvoyés dans `rejected`."""
        pick_versions = self._version_picker()
        existing = {email.lower() for email in self.repository.emails()}
        in_file = set()
        accepted, rejected = [], []
        for line, row in candidats:
            problem = self._import_problem(row, existing, in_file)
            if problem:
                rejected.append({"ligne": line, "email": row["email"], "message": problem})
                continue
            in_file.add(row["email"].lower())
            accepted.append(row)

        with transaction.atomic():
            ids = [
                self._create_test(versions=pick_versions(), **row).id
                for row in accepted
            ]
        return {
            "created": [self.serialize(test) for test in self.repository.get_many(ids)],
            "rejected": rejected,
        }

    @staticmethod
    def _import_problem(row, existing, in_file):
        missing = [
            label
            for field, label in (("prenom", "Prénom"), ("nom", "Nom"), ("email", "Email"))
            if not row[field]
        ]
        if missing:
            return "Champ(s) manquant(s) : " + ", ".join(missing) + "."
        if len(row["prenom"]) > 150 or len(row["nom"]) > 150:
            return "Prénom ou nom trop long (150 caractères maximum)."
        try:
            if len(row["email"]) > 254:
                raise ValidationError("too long")
            validate_email(row["email"])
        except ValidationError:
            return "Email invalide."
        email = row["email"].lower()
        if email in in_file:
            return "Email en double dans le fichier."
        if email in existing:
            return "Un test existe déjà pour cet email."
        return None

    def _create_test(self, prenom, nom, email, versions):
        test = self.repository.create(
            prenom=prenom.strip(), nom=nom.strip(), email=email.strip()
        )
        self.test_version_repository.bulk_create(test, versions)
        return test

    def _version_picker(self):
        """Fonction qui tire une version au hasard pour chaque core value.
        Refuse si la banque de questions ne permet pas de générer un test."""
        core_values = self.core_value_repository.get_all()
        if not core_values:
            raise BusinessError(
                "Aucune core value n'est configurée : impossible de générer un test."
            )

        versions_by_core_value = {}
        for version in self.version_repository.get_all():
            versions_by_core_value.setdefault(version.core_value_id, []).append(
                version
            )

        missing = [
            core_value.name
            for core_value in core_values
            if core_value.id not in versions_by_core_value
        ]
        if missing:
            raise BusinessError(
                "Impossible de générer un test : aucune version pour "
                + ", ".join(missing)
                + "."
            )

        def pick_versions():
            return [
                random.choice(versions_by_core_value[core_value.id])
                for core_value in core_values
            ]

        return pick_versions

    def get(self, test_id):
        test = self.repository.get_by_id(test_id)
        if test is None:
            raise NotFoundError("Test introuvable.")
        return test

    def detail(self, test_id):
        test = self.refresh_statut(self.get(test_id))
        sections = self.build_sections(test, with_scoring=True)
        scores = {
            item.id: self._ratio(*self._section_totals(item))
            for item in test.test_versions.all()
        }
        for section in sections:
            section["percentage"] = scores.get(section["test_version_id"])
        return {
            **self.serialize(test),
            "started_at": test.started_at,
            "sections": sections,
        }

    def delete(self, test_id):
        self.repository.delete(self.get(test_id))

    def creer_lien(self, test_id):
        """Crée le lien du candidat (valable 7 jours) : l'admin le transmet lui-même."""
        test = self.get(test_id)
        if test.statut != Test.STATUT_A_ENVOYER:
            raise BusinessError("Le lien de ce test a déjà été créé.")
        now = timezone.now()
        self.repository.update(
            test,
            {
                "statut": Test.STATUT_ENVOYE,
                "token": uuid.uuid4(),
                "token_expires_at": now + Test.LIEN_VALIDITE,
                "sent_at": now,
            },
        )
        return self.serialize(test)

    def envoyer_email(self, test_id):
        """Envoie le lien au candidat par email (SMTP), en le créant si besoin.

        Tout est annulé si l'envoi échoue : le test garde son statut précédent."""
        with transaction.atomic():
            test = self.refresh_statut(self.get(test_id))
            if test.statut not in (Test.STATUT_A_ENVOYER, Test.STATUT_ENVOYE):
                raise BusinessError(
                    "Le candidat a déjà commencé le test : le lien ne peut plus être envoyé."
                )
            self.repository.update(test, self._link_fields(test, timezone.now()))
            self.email_service.send_test_link(
                test, self.test_url(test.token), self._duree_minutes()
            )
        return self.serialize(test)

    def envoyer_emails(self, test_ids):
        """Envoi groupé du lien par email aux tests sélectionnés.

        Optimisé pour le volume : les tests sont chargés en quelques requêtes,
        les liens sont enregistrés en une seule requête et tous les emails partent
        sur une seule connexion SMTP. Un email refusé n'arrête pas les autres :
        son test est remis dans son état précédent et signalé dans `rejected`."""
        ids = list(dict.fromkeys(str(test_id) for test_id in test_ids or []))
        if not ids:
            raise BusinessError("Aucun test sélectionné.")
        if len(ids) > self.MAX_EMAILS_PAR_ENVOI:
            raise BusinessError(
                f"{self.MAX_EMAILS_PAR_ENVOI} tests maximum par envoi."
            )

        found = {str(test.id): test for test in self.repository.get_many(self._valid_uuids(ids))}
        rejected = [
            {"id": test_id, "email": None, "message": "Test introuvable."}
            for test_id in ids
            if test_id not in found
        ]
        eligible = []
        for test in found.values():
            self.refresh_statut(test)
            if test.statut in (Test.STATUT_A_ENVOYER, Test.STATUT_ENVOYE):
                eligible.append(test)
            else:
                rejected.append(self._rejection(test, "Le candidat a déjà commencé le test."))
        if not eligible:
            return {"sent": [], "rejected": rejected}

        # Connexion (et authentification) avant toute modification : si le
        # serveur SMTP est injoignable, rien n'est changé.
        connection = self.email_service.open_connection()
        sent, failed = [], []
        try:
            now = timezone.now()
            previous = {
                test.id: {name: getattr(test, name) for name in self.LINK_FIELDS}
                for test in eligible
            }
            for test in eligible:
                for name, value in self._link_fields(test, now).items():
                    setattr(test, name, value)
            # Liens enregistrés avant l'envoi : un lien reçu est toujours valide.
            self.repository.bulk_update(eligible, self.LINK_FIELDS)

            duree = self._duree_minutes()
            connection_error = None
            for test in eligible:
                if connection_error:
                    failed.append(test)
                    rejected.append(self._rejection(test, connection_error))
                    continue
                message = self.email_service.build_test_link_message(
                    test, self.test_url(test.token), duree
                )
                error, lost = self.email_service.send_on(connection, message)
                if error:
                    failed.append(test)
                    rejected.append(self._rejection(test, error))
                    if lost:
                        connection_error = error
                else:
                    sent.append(test)

            if failed:
                for test in failed:
                    for name, value in previous[test.id].items():
                        setattr(test, name, value)
                self.repository.bulk_update(failed, self.LINK_FIELDS)
        finally:
            connection.close()
        return {"sent": [self.serialize(test) for test in sent], "rejected": rejected}

    @staticmethod
    def _link_fields(test, now):
        """Champs à enregistrer quand le lien est envoyé par email :
        création du lien si besoin, réactivation pour 7 jours s'il a expiré."""
        fields = {"email_sent_at": now}
        if test.statut == Test.STATUT_A_ENVOYER:
            fields.update(
                {
                    "statut": Test.STATUT_ENVOYE,
                    "token": uuid.uuid4(),
                    "token_expires_at": now + Test.LIEN_VALIDITE,
                    "sent_at": now,
                }
            )
        elif test.is_link_expired():
            fields["token_expires_at"] = now + Test.LIEN_VALIDITE
        return fields

    @staticmethod
    def _duree_minutes():
        return int(Test.DUREE_TEST.total_seconds() // 60)

    @staticmethod
    def _rejection(test, message):
        return {"id": str(test.id), "email": test.email, "message": message}

    @staticmethod
    def _valid_uuids(ids):
        valid = []
        for test_id in ids:
            try:
                valid.append(uuid.UUID(test_id))
            except ValueError:
                continue
        return valid

    def prolonger_lien(self, test_id):
        test = self.refresh_statut(self.get(test_id))
        if test.statut != Test.STATUT_ENVOYE:
            raise BusinessError(
                "Seul le lien d'un test envoyé et non commencé peut être prolongé."
            )
        now = timezone.now()
        # Même lien, validité prolongée de 7 jours à partir d'aujourd'hui.
        self.repository.update(
            test,
            {
                "token_expires_at": now + Test.LIEN_VALIDITE,
                "last_relance_at": now,
                "relance_count": test.relance_count + 1,
            },
        )
        return self.serialize(test)

    # ----- Export Excel et PDF des résultats -----

    PDF_SALT = "eone-test.resultat-pdf"

    def export_excel(self):
        """Fichier Excel des tests terminés (statut Répondu), avec un lien signé
        vers le PDF de chaque résultat."""
        rows = [
            {**test, "pdf_url": self.result_pdf_url(test["id"])}
            for test in self.list()
            if test["statut"] == Test.STATUT_REPONDU
        ]
        if not rows:
            raise BusinessError("Aucun test terminé (statut Répondu) à exporter.")
        return build_tests_workbook(rows)

    def result_pdf_url(self, test_id):
        """Lien direct vers le PDF, sans connexion : signé (impossible à deviner ou
        à modifier) et valable EXPORT_LINK_DAYS jours."""
        signature = signing.TimestampSigner(salt=self.PDF_SALT).sign(str(test_id))
        return f"{settings.FRONTEND_URL.rstrip('/')}/api/resultats-pdf/{signature}/"

    def result_pdf(self, signature):
        """(nom du fichier, contenu du PDF) pour un lien signé."""
        try:
            test_id = signing.TimestampSigner(salt=self.PDF_SALT).unsign(
                signature, max_age=settings.EXPORT_LINK_TTL
            )
        except signing.SignatureExpired as exc:
            raise LinkExpiredError(
                "Ce lien a expiré : exportez à nouveau le fichier Excel."
            ) from exc
        except signing.BadSignature as exc:
            raise NotFoundError("Ce lien de résultats est invalide.") from exc
        result = self.detail(test_id)
        if result["statut"] != Test.STATUT_REPONDU:
            raise BusinessError("Ce candidat n'a pas encore terminé le test.")
        name = slugify(f"resultats {result['prenom']} {result['nom']}") or "resultats"
        return f"{name}.pdf", build_result_pdf(result)

    @staticmethod
    def test_url(token):
        return f"{settings.FRONTEND_URL.rstrip('/')}/passer-test?token={token}"

    def refresh_statut(self, test):
        """Clôture le test quand le chrono (Test.DUREE_TEST) est dépassé."""
        if test.statut == Test.STATUT_EN_COURS and test.is_time_over():
            self.repository.update(
                test,
                {"statut": Test.STATUT_REPONDU, "submitted_at": test.deadline},
            )
        return test

    def save_answer(self, test, answer_id):
        """Enregistre la réponse choisie, quelle que soit la question du test."""
        for test_version, question, _, _ in self.ordered_questions(test):
            answer = self.find_answer(question, answer_id)
            if answer is not None:
                self.store_answer(test_version, question, answer)
                return {"question_id": question.id, "answer_id": answer.id}
        raise NotFoundError("Réponse introuvable dans ce test.")

    def store_answer(self, test_version, question, answer):
        """Une seule réponse par question : la nouvelle remplace l'ancienne."""
        existing = self.selected_answer(test_version, question)
        if existing is None:
            self.test_version_answer_repository.create(
                answer=answer, test_version=test_version
            )
        elif existing.answer_id != answer.id:
            self.test_version_answer_repository.update(existing, {"answer": answer})

    @staticmethod
    def find_answer(question, answer_id):
        return next(
            (item for item in question.answers.all() if str(item.id) == str(answer_id)),
            None,
        )

    @staticmethod
    def selected_answer(test_version, question):
        return next(
            (
                item
                for item in test_version.test_version_answers.all()
                if item.answer.question_id == question.id
            ),
            None,
        )

    @staticmethod
    def ordered_questions(test):
        """Questions dans l'ordre de passage :
        [(test_version, question, position dans la section, taille de la section)]."""
        versions = sorted(
            test.test_versions.all(),
            key=lambda item: item.version.core_value.name,
        )
        items = []
        for test_version in versions:
            questions = list(test_version.version.questions.all())
            for index, question in enumerate(questions):
                items.append((test_version, question, index, len(questions)))
        return items

    @staticmethod
    def build_sections(test, with_scoring):
        """Questions du test ; sans pondération ni pourcentages pour le candidat."""
        selected = {
            (item.test_version_id, item.answer.question_id): item.answer_id
            for test_version in test.test_versions.all()
            for item in test_version.test_version_answers.all()
        }
        versions = sorted(
            test.test_versions.all(),
            key=lambda item: item.version.core_value.name,
        )
        sections = []
        for item in versions:
            questions = []
            for question in item.version.questions.all():
                answers = []
                for answer in question.answers.all():
                    entry = {"id": answer.id, "text": answer.text}
                    if with_scoring:
                        entry["percentage"] = answer.percentage
                    answers.append(entry)
                entry = {
                    "id": question.id,
                    "text": question.text,
                    "selected_answer_id": selected.get((item.id, question.id)),
                    "answers": answers,
                }
                if with_scoring:
                    entry["ponderation"] = question.ponderation
                questions.append(entry)
            sections.append(
                {
                    "test_version_id": item.id,
                    "core_value_name": item.version.core_value.name,
                    "version_name": item.version.name,
                    "questions": questions,
                }
            )
        return sections

    def serialize(self, test):
        versions = sorted(
            test.test_versions.all(),
            key=lambda item: item.version.core_value.name,
        )
        return {
            "id": test.id,
            "created_at": test.created_at,
            "prenom": test.prenom,
            "nom": test.nom,
            "email": test.email,
            "versions": [
                {
                    "test_version_id": item.id,
                    "core_value_name": item.version.core_value.name,
                    "version_name": item.version.name,
                }
                for item in versions
            ],
            "statut": test.statut,
            "statut_label": test.get_statut_display(),
            "lien": self.test_url(test.token) if test.token else None,
            "sent_at": test.sent_at,
            "last_relance_at": test.last_relance_at,
            "relance_count": test.relance_count,
            "email_sent_at": test.email_sent_at,
            "token_expires_at": test.token_expires_at,
            "submitted_at": test.submitted_at,
            "score_global": self._compute_score_global(test),
        }

    @classmethod
    def _compute_score_global(cls, test):
        """Score calculé à la volée (jamais stocké) :
        Σ(pourcentage réponse choisie × pondération) / Σ pondération.
        Une question sans réponse compte 0 mais garde sa pondération."""
        numerator = Decimal("0")
        denominator = Decimal("0")
        for test_version in test.test_versions.all():
            num, den = cls._section_totals(test_version)
            numerator += num
            denominator += den
        return cls._ratio(numerator, denominator)

    @staticmethod
    def _section_totals(test_version):
        """(Σ pourcentage × pondération, Σ pondération) pour une core value."""
        chosen = {
            item.answer.question_id: item.answer.percentage
            for item in test_version.test_version_answers.all()
        }
        numerator = Decimal("0")
        denominator = Decimal("0")
        for question in test_version.version.questions.all():
            numerator += chosen.get(question.id, Decimal("0")) * question.ponderation
            denominator += question.ponderation
        return numerator, denominator

    @staticmethod
    def _ratio(numerator, denominator):
        if not denominator:
            return None
        return (numerator / denominator).quantize(Decimal("0.01"))

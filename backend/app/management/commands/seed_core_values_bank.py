import json
from decimal import Decimal
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from app.models import Answer, CoreValue, Question, Version

DEFAULT_BANK = Path(__file__).resolve().parent / "data" / "banque_questions_enosis.json"


class Command(BaseCommand):
    help = (
        "Charge la banque de questions des core values "
        "(core values, versions, questions, réponses). Idempotent."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--file",
            default=str(DEFAULT_BANK),
            help="Chemin du fichier JSON de la banque de questions.",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        path = Path(options["file"])
        if not path.exists():
            raise CommandError(f"Fichier introuvable : {path}")
        sections = json.loads(path.read_text(encoding="utf-8"))["sections"]

        created = {"core_values": 0, "versions": 0, "questions": 0, "answers": 0}
        for section in sections:
            core_value, was_created = CoreValue.objects.get_or_create(
                name=section["name"].strip()
            )
            created["core_values"] += was_created
            for version_data in section["versions"]:
                version, was_created = Version.objects.get_or_create(
                    core_value=core_value,
                    name=f"Version {version_data['version']}",
                )
                created["versions"] += was_created
                for question_data in version_data["questions"]:
                    question, was_created = Question.objects.update_or_create(
                        version=version,
                        text=question_data["text"].strip(),
                        defaults={"ponderation": Decimal(str(question_data["weight"]))},
                    )
                    created["questions"] += was_created
                    for answer_data in question_data["answers"]:
                        _, was_created = Answer.objects.update_or_create(
                            question=question,
                            text=answer_data["text"].strip(),
                            defaults={
                                "percentage": Decimal(
                                    str(answer_data["alignmentPercentage"])
                                )
                            },
                        )
                        created["answers"] += was_created

        self.stdout.write(
            self.style.SUCCESS(
                "Banque de questions chargée : "
                f"{created['core_values']} core values, "
                f"{created['versions']} versions, "
                f"{created['questions']} questions, "
                f"{created['answers']} réponses créées."
            )
        )

import os

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = (
        "Crée le compte administrateur (ADMIN_USERNAME / ADMIN_PASSWORD) "
        "s'il n'existe pas encore. Idempotent."
    )

    def add_arguments(self, parser):
        parser.add_argument("--username", default=os.environ.get("ADMIN_USERNAME", "admin"))
        parser.add_argument("--password", default=os.environ.get("ADMIN_PASSWORD", ""))
        parser.add_argument(
            "--reset-password",
            action="store_true",
            help="Remplace le mot de passe si le compte existe déjà.",
        )

    def handle(self, *args, **options):
        username = options["username"].strip()
        password = options["password"]
        User = get_user_model()
        user = User.objects.filter(username=username).first()

        if user is not None and not options["reset_password"]:
            self.stdout.write(f"Compte administrateur « {username} » déjà présent.")
            return
        if not password:
            raise CommandError(
                "Mot de passe manquant : définissez ADMIN_PASSWORD ou passez --password."
            )

        if user is None:
            User.objects.create_superuser(username=username, password=password)
            self.stdout.write(self.style.SUCCESS(f"Compte administrateur « {username} » créé."))
        else:
            user.set_password(password)
            user.save(update_fields=["password"])
            self.stdout.write(self.style.SUCCESS(f"Mot de passe de « {username} » mis à jour."))

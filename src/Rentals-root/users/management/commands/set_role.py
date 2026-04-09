# command
from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth import get_user_model

User = get_user_model()

VALID_ROLES = {
    "commuter": User.ROLE_COMMUTER,
    "provider": User.ROLE_PROVIDER,
    "admin": User.ROLE_ADMIN,
}


class Command(BaseCommand):
    help = "Set the role of a user. Usage: set_role <username> <commuter|provider|admin>"

    def add_arguments(self, parser):
        parser.add_argument("username", type=str)
        parser.add_argument("role", type=str, choices=list(VALID_ROLES))

    def handle(self, *args, **kwargs):
        username = kwargs["username"]
        role_key = kwargs["role"].lower()

        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            raise CommandError(f'User "{username}" not found.')

        user.role = VALID_ROLES[role_key]
        user.save(update_fields=["role"])
        self.stdout.write(self.style.SUCCESS(
            f'"{username}" is now a {user.get_role_display()}.'
        ))

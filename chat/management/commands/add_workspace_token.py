from django.core.management.base import BaseCommand
from chat.models import WorkspaceToken

class Command(BaseCommand):
    help = 'Adds a workspace token to the database'

    def add_arguments(self, parser):
        parser.add_argument('team_id', type=str)
        parser.add_argument('bot_token', type=str)

    def handle(self, *args, **options):
        WorkspaceToken.objects.update_or_create(
            team_id=options['team_id'],
            defaults={'bot_token': options['bot_token']}
        )
        self.stdout.write(self.style.SUCCESS(f'Successfully added token for team {options["team_id"]}'))
import subprocess
import time
from django.core.management.base import BaseCommand
from accounts.models import Team

class Command(BaseCommand):
    help = 'Starts bots for all teams'

    def handle(self, *args, **options):
        self.teams = []
        self.bot_status = []
        self.wakeup()

    def get_teams(self):
        for team in Team.objects.filter(slack_team_id__isnull=False, active=True):
            if team.id not in self.teams:
                self.teams.append(team.id)

    def wakeup(self):
        while True:
            self.get_teams()
            print("checking for all teams..")
            for team_id in self.teams:
                if team_id not in self.bot_status:
                    team = Team.objects.filter(id=team_id).first()
                    print("starting process for %d" % team_id)
                    subprocess.Popen(["python", "start_listening_for_team.py", str(team_id), str(team.slack_bot_access_token)])
                    self.bot_status.append(team_id)
            time.sleep(1)
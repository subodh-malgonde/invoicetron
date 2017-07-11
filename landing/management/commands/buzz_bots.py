import time
from django.core.management.base import BaseCommand
from accounts.models import Team
from slackclient import SlackClient
from landing.utils import handle_slack_events
from websocket import WebSocketConnectionClosedException

class Command(BaseCommand):
    help = 'Starts bots for all teams'

    def add_arguments(self, parser):
        parser.add_argument('team_id', nargs='+', type=str)

    def clean_data(self, data):
        cleaned_data = []

        if len(data) == 0:
            return False

        for dt in data:
            if not (dt['type'] in ['hello', 'reconnect_url', 'user_typing', 'presence_change', 'desktop_notification']):

                if 'subtype' in dt:
                    if dt['subtype'] in ['bot_message', 'message_changed', 'message_deleted']:
                        continue
                cleaned_data.append(dt)

        return cleaned_data

    def start_listening(self, team_id):
        team_bot = Team.objects.filter(id=team_id, slack_team_id__isnull=False, active=True).first()
        if team_bot:
            sc = SlackClient(team_bot.slack_bot_access_token)
            if sc.rtm_connect():
                while (True):
                    try:
                        dt_rx = sc.rtm_read()
                        print("%s----%s" % (team_id, dt_rx))
                        if ((len(dt_rx) == 1) and (not dt_rx[0])):
                            if not sc.rtm_connect():
                                # todo deactivate team
                                return (1)

                        cleaned_data = self.clean_data(dt_rx)

                        if cleaned_data:
                            handle_slack_events(cleaned_data)
                            print(dt_rx)
                    except WebSocketConnectionClosedException:
                        print("Websocket Exception for %s. Reconnecting.." % (team_id))
                        sc.rtm_connect()
                        print("Connected again.")
                    time.sleep(0.1)
            else:
                team_bot.active = False
                team_bot.save()

    def handle(self, *args, **options):
        self.start_listening(options['team_id'][0])
from slackclient import SlackClient
from django.core.management.base import BaseCommand
import time

class Command(BaseCommand):
    help = 'Starts the bot for the first'

    def handle(self, *args, **options):
    
        client = SlackClient("xoxb-191129993653-uItT8p3Ipj4hiWL4bEE8I5rk")
        if client.rtm_connect():
            while True:
                events = client.rtm_read()
                for event in events:
                    if 'type' in event.keys() and event['type']=='message': # and event['text']=='hi':
                        client.rtm_send_message(event['channel'],event['text'])
                time.sleep(1)
        else:
            print("unable to connect");

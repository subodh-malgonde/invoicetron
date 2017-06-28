import os
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "invoicetron.settings")

import time, sys
from slackclient import SlackClient
from websocket import WebSocketConnectionClosedException
import django_rq

def clean_data(data):
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

def start_listening(team_id, access_token):
    sc = SlackClient(access_token)
    queue = django_rq.get_queue('high')
    if sc.rtm_connect():
        while(True):
            try:
                dt_rx = sc.rtm_read()
                print("%s----%s" % (team_id, dt_rx))
                if ((len(dt_rx) == 1) and (not dt_rx[0])):
                    if not sc.rtm_connect():
                        # todo deactivate team
                        return(1)

                cleaned_data = clean_data(dt_rx)

                if cleaned_data:
                    queue.enqueue('landing.utils.handle_slack_events', events=cleaned_data)
                    print(dt_rx)
            except WebSocketConnectionClosedException:
                print("Websocket Exception for %s. Reconnecting.." % (team_id))
                sc.rtm_connect()
                print("Connected again.")
            time.sleep(0.1)
    else:
        return None

if __name__ == '__main__':
    start_listening(sys.argv[1], sys.argv[2])
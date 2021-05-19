# Bot module

from python_webex.v1.Bot import Bot
from requests_toolbelt.multipart.encoder import MultipartEncoder
import requests
from AmplitudeInteraction import getErrorPlots
import schedule
import json
import time

from ChooseProjectCard import chooseProjectCard
from ConfigCard import configCard
from EventCard import eventCard
from EventCard2 import eventCard2
from EventCard3 import eventCard3

bot_url = "http://0b894d0717d7.eu.ngrok.io"

with open(r'./.secret/api_keys.txt','r') as keyFile:
    keys = keyFile.read().split('\n')
    auth_token = keys[2]

with open(r'./.secret/permittedUsers.txt', 'r') as userFile:
    permittedUsers = userFile.read().split('\n')

frequency = {'daily' : 1, 'weekly' : 7, 'monthly' : 30}

class MetricsBotClass(Bot):
    def permute(self, input_string):
        if not input_string:
            yield ""
        else:
            first = input_string[:1]
            if first.lower() == first.upper():
                for sub_casing in self.permute(input_string[1:]):
                    yield first + sub_casing
            else:
                for sub_casing in self.permute(input_string[1:]):
                    yield first.lower() + sub_casing
                    yield first.upper() + sub_casing

    def listen(self, message_text):
        all_permutation = list(self.permute(message_text))

        def on_hears_decorator(f):
            for p in all_permutation:
                Bot.on_hears(self, p)(f)
        return on_hears_decorator


metricsBot = MetricsBotClass()
metricsBot.create_webhook(
    name="message_webhook", target_url=bot_url, resource="messages", event="created"
)
metricsBot.create_webhook(
    name='cards_webhook', target_url=bot_url+"/attachment-response", resource="attachmentActions", event="created"
)


@metricsBot.on_hears("*")
def default_response(room_id=None, message = None):
    print("The Message is :", message['text'].replace('TestBot', '').strip())
    tempText = message['text'].replace('TestBot', '').strip().lower()
    if tempText == 'help':
        return help_user(room_id=room_id)
    elif tempText == "hi":
        return greet_back(room_id=room_id)
    elif tempText == "choose project":
        return send_choose_project_card(room_id=room_id)
    elif tempText == "configure bot":
        return send_config_card(room_id=room_id)
    elif tempText == "single event":
        return send_single_event_card(room_id=room_id)
    elif tempText == "two events":
        return send_two_events_card(room_id=room_id)
    elif tempText == "three events":
        return send_three_events_card(room_id=room_id)
    else:
        return metricsBot.send_message(room_id=room_id, text="Sorry, could not understand that.\nType help to know about supported commands")


@metricsBot.set_default_file_response()
def respond_file(files = None, room_id = None, message = None):
    respond_to_file(files=files, room_id=room_id,message=message)


@metricsBot.set_file_action(message_text="*")
def respond_file(files = None, room_id = None, message = None):
    respond_to_file(files=files, room_id= room_id, message= message)


# Helper Functions

def respond_to_file(files= None, room_id= None, message = None):
    print("Message: ", message)
    response = requests.get(files[0],
                  headers={'Authorization': 'Bearer '+auth_token})
    if response.headers['Content-Type'].split('/')[-1] != "json":
        metricsBot.send_message(room_id=room_id, text= "Metrics Bot can only support files of json Format")
        return
    filename = response.headers['Content-Disposition'].split('"')[1::1][0]
    message = metricsBot.send_message(room_id=room_id, text= "File named " + filename +" received")
    encodedMessage = MultipartEncoder({'roomId': room_id,
                    'text': 'You will receive response if the Input is correct',
                    'parentId':message.json()['id']})

    r = requests.post('https://webexapis.com/v1/messages', data=encodedMessage,
                    headers={'Authorization': 'Bearer ' + auth_token,
                    'Content-Type': encodedMessage.content_type})
    jsonname = room_id + response.headers['Content-Disposition'].split('"')[1::1][0]
    with open(jsonname, "wb") as newFile:
        newFile.write(response.content)
    resultPlot = getErrorPlots(jsonname)
    if resultPlot == 'API call Failed':
        encodedMessage = MultipartEncoder({'roomId': room_id,
                        'text': 'API call error occurred, please re-check the input JSON',
                        'parentId':message.json()['id']})
        r = requests.post('https://webexapis.com/v1/messages', data=encodedMessage,
                        headers={'Authorization': 'Bearer ' + auth_token,
                        'Content-Type': encodedMessage.content_type})
    else:
        with open(jsonname) as f:
            inputJson = json.load(f)
        freq = frequency[inputJson['body']['repeat_interval']]
        errorstrings = [i for i in inputJson['body']['events']]
        outString = ''
        for i in errorstrings:
            filters = ''
            for j in i['filters']:
                filters = filters + j['subprop_key'] + ' ' + j['subprop_op'] + ' ' + str(j['subprop_value']) + ', '
            filters = filters.rstrip(', ')
            groupby = ''
            for j in i['group_by']:
                groupby = groupby + j['value'] + ', '
            groupby = groupby.rstrip(', ')
            outString = outString + '-  ' + i['event_type'] + '; ' + 'where: ' + filters + '; ' + 'grouped by: ' + groupby
            outString = outString + '\n'
        textString = "Ola! here's your update for the errors:\n" + outString
        id = room_id
        pid = message.json()['id']
        if inputJson['body']['repeat'] == 't':
            return
            # SCHEDULE CODE
        else:
            plotMessage(id, resultPlot, textString, pid)

def help_user(room_id=None):
    messageString = """
Help
==========
This is the list of available commands

help - Show this help
hi - Greet the user
choose project - Select between the supported Amplitude Projects.
configure bot - Create the configuration the bot will follow
single event - Query for a single Event
two events - Query for 2 Events
three events - Query for 3 events

Or you can directly send a json configured as an attatchment
    """
    return metricsBot.send_message(room_id=room_id, text=messageString)

def plotMessage(roomid, plotName, text, parentid):
    encodedMessage = MultipartEncoder({'roomId': roomid,
                  'text': text, 'parentId': parentid,
                  'files': (plotName, open(plotName, 'rb'),
                  'image/png')})

    r = requests.post('https://webexapis.com/v1/messages', data=encodedMessage,
                    headers={'Authorization': 'Bearer ' + auth_token,
                    'Content-Type': encodedMessage.content_type})

def greet_back(room_id=None):
    return metricsBot.send_message(room_id=room_id, text="Hi, this is the Webex Metrics bot.\nYou can type help to get more info")

def send_choose_project_card(room_id=None):
    message = metricsBot.send_card(card=chooseProjectCard, room_id=room_id)
    message_id = message.json()['id']

    @metricsBot.attachment_response(message_id=message_id)
    def respond_to_card(msg):
        print(msg)
        print(msg['inputs']['choices'])
        metricsBot.send_message(
            room_id= room_id, text = msg['inputs']['choices'] + " has been chosen"
        )
        metricsBot.send_message(
            room_id= room_id, text = "Now you can type \"create graph\" to get the next card."
        )
        metricsBot.delete_message(message_id=message_id)

def send_single_event_card(room_id=None):
    message = metricsBot.send_card(card=eventCard, room_id=room_id)
    message_id = message.json()['id']

    @metricsBot.attachment_response(message_id=message_id)
    def respond_to_card(msg):
        print(msg)
        print(msg['inputs']['error_name1'])
        # Logic to convert card input to json
        encodedMessage = MultipartEncoder({'roomId': room_id,
                      'text': 'example attached',
                      'files': ('plot.png', open('plot.png', 'rb'),
                      'image/png')})

        r = requests.post('https://webexapis.com/v1/messages', data=encodedMessage,
                        headers={'Authorization': 'Bearer ' + auth_token,
                        'Content-Type': encodedMessage.content_type})
        metricsBot.delete_message(message_id=message_id)

def send_config_card(room_id=None):
    message = metricsBot.send_card(card=configCard, room_id=room_id)
    message_id = message.json()['id']

    @metricsBot.attachment_response(message_id=message_id)
    def respond_to_card(msg):
        print(msg)
        metricsBot.send_message(
            room_id=room_id, text="The bot has been configured.\nTo reconfigure, type command \"Configure bot\" again"
        )
        metricsBot.delete_message(message_id=message_id)

def send_two_events_card(room_id=None):
    message = metricsBot.send_card(card=eventCard2, room_id=room_id)
    message_id = message.json()['id']

    @metricsBot.attachment_response(message_id=message_id)
    def respond_to_card(msg):
        print(msg)
        print(msg['inputs']['error_name1'])
        # Logic to convert card input to json
        encodedMessage = MultipartEncoder({'roomId': room_id,
                      'text': 'example attached',
                      'files': ('plot.png', open('plot.png', 'rb'),
                      'image/png')})

        r = requests.post('https://webexapis.com/v1/messages', data=encodedMessage,
                        headers={'Authorization': 'Bearer ' + auth_token,
                        'Content-Type': encodedMessage.content_type})
        metricsBot.delete_message(message_id=message_id)

def send_three_events_card(room_id=None):
    message = metricsBot.send_card(card=eventCard3, room_id=room_id)
    message_id = message.json()['id']

    @metricsBot.attachment_response(message_id=message_id)
    def respond_to_card(msg):
        print(msg)
        print(msg['inputs']['error_name1'])
        # Logic to convert card input to json
        encodedMessage = MultipartEncoder({'roomId': room_id,
                      'text': 'example attached',
                      'files': ('plot.png', open('plot.png', 'rb'),
                      'image/png')})

        r = requests.post('https://webexapis.com/v1/messages', data=encodedMessage,
                        headers={'Authorization': 'Bearer ' + auth_token,
                        'Content-Type': encodedMessage.content_type})
        metricsBot.delete_message(message_id=message_id)
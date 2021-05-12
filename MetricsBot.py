# Bot module

from python_webex.v1.Bot import Bot
from requests_toolbelt.multipart.encoder import MultipartEncoder
import requests
from AmplitudeInteraction import getErrorPlots
import schedule
import json
import time
bot_url = "http://da819a3a90f8.eu.ngrok.io"

keyFile = open(r'./.secret/api_keys.txt','r')
keys = keyFile.read().split('\n')
auth_token = keys[2]
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
def default_response(room_id=None):
    return metricsBot.send_message(room_id=room_id, text="Sorry, could not understand that.\nType help to know about supported commands")


@metricsBot.set_default_file_response()
def respond_file(files = None, room_id = None):
    print("Files: ",files)
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
def plotMessage(roomid, plotName, text, parentid):
    encodedMessage = MultipartEncoder({'roomId': roomid,
                  'text': text, 'parentId': parentid,
                  'files': (plotName, open(plotName, 'rb'),
                  'image/png')})

    r = requests.post('https://webexapis.com/v1/messages', data=encodedMessage,
                    headers={'Authorization': 'Bearer ' + auth_token,
                    'Content-Type': encodedMessage.content_type})

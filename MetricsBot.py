# Bot module

from python_webex.v1.Bot import Bot
from requests_toolbelt.multipart.encoder import MultipartEncoder
import requests
bot_url = "http://36c4b04f0ac0.eu.ngrok.io"

keyFile = open(r'./.secret/api_keys.txt','r')
keys = keyFile.read().split('\n')
auth_token = keys[3]    

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
    name='cards_webhoot', target_url=bot_url+"/attachment-response", resource="attachmentActions", event="created"
)


@metricsBot.on_hears("*")
def default_response(room_id=None):
    return metricsBot.send_message(room_id=room_id, text="Sorry, could not understand that.\nType help to know about supported commands")


@metricsBot.set_default_file_response()
def respond_file(files = None, room_id = None):
    print("Files: ",files)
    response = requests.get(files[0],
                  headers={'Authorization': 'Bearer '+auth_token})
    filename = response.headers['Content-Disposition'].split('"')[1::1][0]
    message = metricsBot.send_message(room_id=room_id, text= "File named " + filename +" received")
    with open(filename, "wb") as newFile:
        newFile.write(response.content)
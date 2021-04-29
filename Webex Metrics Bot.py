from python_webex.v1.Bot import Bot
from python_webex import webhook
import pandas as pd
import requests
import json
from requests.auth import HTTPBasicAuth

keyFile = open(r'./.secret/api_keys.txt','r')
keys = keyFile.read().split('\n')
bot = Bot(keys[2])         # the program will automatically know the bot being referred to y the auth_token

# create a webhook to expose it to the internet
# rememer that url we got from step 2, this is where we use it. In my case it was http://87a942a1.ngrok.io.
# We will be creating a webhook that will be listening when messages are sent
bot.create_webhook(
    name="quickstart_webhook", target_url="http://bb3a8299e77f.ngrok.io", resource="messages", event="created"
)

# we create a function that responds when someone says hi
# the room_id will automatically be filled with the webhook. Do not forget it
@bot.on_hears("hi")
def greet_back(room_id=None):
    return bot.send_message(room_id=room_id, text= "Hi! Will you tell me which error's metrics you would like to monitor? \nJust type the error name and send the message addressed to me!")

# We create a default response in case anyone types anything else that we have not set a response for
# this is done using * [ don't ask me what happend when someone sends '*' as the message, that's on my TODO]
@bot.on_hears("Error ID: *")
def responseToID(room_id=None):
     response = requests.get('https://amplitude.com/api/2/events/segmentation?e={"event_type": "client_ecm_add_account_funnel" }&start=20210421&end=20210428', auth = HTTPBasicAuth('f110e00380d07a5d7d2175674e7f64de', '735a2e6321f2201b15559d75d5451770'))
     response_json = response.json()
     df = pd.DataFrame(response_json['data']['series'], columns = response_json['data']['xValues'])
     return bot.send_message(room_id=room_id, text= df.to_string())


# make the webhook know the bot to be listening for, and we are done
webhook.bot = bot

if __name__ == "__main__":
    webhook.app.run(debug=False)         # don't keep debug=True in production

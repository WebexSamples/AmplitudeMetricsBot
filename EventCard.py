from python_webex.v1.Card import Card
from MetricsBot import metricsBot
from AmplitudeInteraction import getErrorPlot
from requests_toolbelt.multipart.encoder import MultipartEncoder
import requests

keyFile = open(r'./.secret/api_keys.txt','r')
keys = keyFile.read().split('\n')
auth_token = keys[3]    

eventCard = Card()
eventCard.add_text_block(
    text="Webex Metrics Bot", size="Large"
)

eventCard.add_text_block(
    text="Please Enter the required Data", weight="Bolder", size="Medium"
)

eventCard.add_text_block(
    text="Enter the Error Name"
)

eventCard.add_input_text(
    input_id="error_name", input_placeholder="eg: client_ecm_add_account_funnel"
)

eventCard.add_text_block(
    text="Enter the regularity with which you want Updates"
)

eventCard.add_input_text(
    input_id="regularity", input_placeholder="eg: Daily/Weekly/Monthly"
)

eventCard.add_submit_action_btn(
    title="Create request"
)

@metricsBot.listen("create graph")
def send_basic_card(room_id=None):
    message = metricsBot.send_card(card=eventCard, room_id=room_id)
    message_id = message.json()['id']

    @metricsBot.attachment_response(message_id=message_id)
    def respond_to_card(msg):
        print(msg)
        print(msg['inputs']['error_name'])
        df = getErrorPlot(msg['inputs']['error_name'].lower(),msg['inputs']['regularity'].lower())
        print(df)
        # metricsBot.send_message(
        #     room_id=room_id, text=df.to_string()
        # )
        encodedMessage = MultipartEncoder({'roomId': room_id,
                      'text': 'example attached',
                      'files': ('plot.png', open('plot.png', 'rb'),
                      'image/png')})

        r = requests.post('https://webexapis.com/v1/messages', data=encodedMessage,
                        headers={'Authorization': 'Bearer ' + auth_token,
                        'Content-Type': encodedMessage.content_type})
        metricsBot.delete_message(message_id=message_id)

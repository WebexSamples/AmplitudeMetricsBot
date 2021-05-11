from MyCard import MyCard
from python_webex.v1.Card import Card
from MetricsBot import metricsBot
from AmplitudeInteraction import getErrorPlot
from requests_toolbelt.multipart.encoder import MultipartEncoder
import requests

keyFile = open(r'./.secret/api_keys.txt','r')
keys = keyFile.read().split('\n')
auth_token = keys[3]    

eventCard2 = MyCard()

eventCard2.add_text_block(
    text="Webex Metrics Bot", size="Large"
)

eventCard2.add_text_block(
    text="Please Enter the required Data", weight="Bolder", size="Medium"
)

eventCard2.add_text_block(
    text="Enter the First Error Name"
)

eventCard2.add_input_text(
    input_id="error_name1",
    input_placeholder="eg: client_ecm_add_account_funnel",
    input_value="client_ecm_add_account_funnel"
)

eventCard2.add_text_block(
    text="Enter the Second Error Name"
)

eventCard2.add_input_text(
    input_id="error_name2",
    input_placeholder="eg: client_ecm_add_account_funnel",
    input_value="client_ecm_add_account_funnel"
)

eventCard2.add_text_block(
    text="Enter the regularity with which you want Updates"
)

eventCard2.add_input_text(
    input_id="regularity",
    input_placeholder="eg: Daily/Weekly/Monthly",
    input_value="weekly"
)

eventCard2.add_submit_action_btn(
    title="Create request"
)

@metricsBot.listen("two events")
def send_basic_card(room_id=None):
    message = metricsBot.send_card(card=eventCard2, room_id=room_id)
    message_id = message.json()['id']

    @metricsBot.attachment_response(message_id=message_id)
    def respond_to_card(msg):
        print(msg)
        print(msg['inputs']['error_name1'])
        df = getErrorPlot(msg['inputs']['error_name1'].lower(),msg['inputs']['regularity'].lower())
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
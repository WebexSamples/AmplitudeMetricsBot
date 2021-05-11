from MyCard import MyCard
from MetricsBot import metricsBot

chooseProjectCard = MyCard()

chooseProjectCard.add_text_block(
    text="Webex Metrics Bot", size="Large"
)

chooseProjectCard.add_text_block(
    text="Please Choose the Project you want", weight="Bolder", size="Medium"
)

choiceSetData =[{"title": "Spark Test","value": "Spark Test"},{"title": "Spark Production","value": "Spark Production"}]
chooseProjectCard.add_input_choiceset(
    input_id="choices",input_choices=choiceSetData,input_is_multiselect=False 
)

chooseProjectCard.add_submit_action_btn(
    title="Submit"
)

@metricsBot.listen("choose project")
def send_basic_card(room_id=None):
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
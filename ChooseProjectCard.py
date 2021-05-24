from MyCard import MyCard

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
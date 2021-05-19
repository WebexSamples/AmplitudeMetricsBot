from MyCard import MyCard

configCard = MyCard()
configCard.add_text_block(
    text="Webex Metrics Bot", size="Large"
)

configCard.add_text_block(
    text="Please Configure the Bot according to your needs", weight="Bolder", size="Medium"
)

configCard.add_text_block(
    text="Enter the number of errors to be queried (Max: 3)",
    wrap = True
)

configCard.add_input_number(
    input_id="no_of_errors",
    input_value=0
)

configCard.add_input_toggle(
    input_id="alertToggle", input_title= "Keep me updated"
)

configCard.add_text_block(
    text="Choose the alert frequency(If above toggle is On)",
    wrap = True
)

choiceSetData =[{"title": "Daily","value": "daily"},{"title": "Weekly","value": "weekly"}]
configCard.add_input_choiceset(
    input_id="alertFrequency",input_choices=choiceSetData,input_is_multiselect=False 
)

configCard.add_submit_action_btn(
    title="Configure Bot"
)
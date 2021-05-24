from MyCard import MyCard

eventCard = MyCard()

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
    input_id="error_name1",
    input_placeholder="eg: client_ecm_add_account_funnel",
    input_value="client_ecm_add_account_funnel"
)

eventCard.add_text_block(
    text="Enter the regularity with which you want Updates"
)

eventCard.add_input_text(
    input_id="regularity",
    input_placeholder="eg: Daily/Weekly/Monthly",
    input_value="weekly"
)

eventCard.add_submit_action_btn(
    title="Create request"
)
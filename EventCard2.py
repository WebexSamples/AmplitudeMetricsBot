from MyCard import MyCard

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

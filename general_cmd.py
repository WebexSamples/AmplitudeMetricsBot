from MetricsBot import metricsBot


@metricsBot.listen("hi")
def greet_back(room_id=None):
    return metricsBot.send_message(room_id=room_id, text="Hi, this is the Webex Metrics bot.\nYou can type help to get more info")

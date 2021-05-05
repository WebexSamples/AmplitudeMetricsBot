from MetricsBot import metricsBot


@metricsBot.listen("help")
def help_user(room_id=None):
    messageString = """
Help
==========
This is the list of available commands

help - Show this help
hi - Greet the user
create graph - Send the Card to collect graph details
    """
    return metricsBot.send_message(room_id=room_id, text=messageString)

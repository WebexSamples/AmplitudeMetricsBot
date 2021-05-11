from MetricsBot import metricsBot


@metricsBot.listen("help")
def help_user(room_id=None):
    messageString = """
Help
==========
This is the list of available commands

help - Show this help
hi - Greet the user
choose project - Select between the supported Amplitude Projects.
configure bot - Create the configuration the bot will follow
single event - Query for a single Event
two events - Query for 2 Events
three events - Query for 3 events

Or you can directly send a json configured as an attatchment
    """
    return metricsBot.send_message(room_id=room_id, text=messageString)

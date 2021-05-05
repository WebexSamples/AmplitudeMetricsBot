from python_webex import webhook
from MetricsBot import metricsBot

# Import command files
import general_cmd
import help_cmd
import EventCard

webhook.bot = metricsBot

if __name__ == "__main__":
    webhook.app.run(debug=True)

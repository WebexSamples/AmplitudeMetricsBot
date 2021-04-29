import pandas as pd
import requests
import json
from requests.auth import HTTPBasicAuth
from datetime import datetime, timedelta
import matplotlib.pyplot as plt

updateFrequencyEnum = {"daily" : 0, "weekly" : 1, "monthly" : 2}
keyfile = open(r"./.secret/api_keys.txt", "r")
keys = keyfile.read().split('\n')
def getErrorPlot(errorCode, updateFrequency):
    updateFrequency = updateFrequencyEnum[updateFrequency]
    endDate = str(datetime.now().date()).replace('-','')
    if (updateFrequency == 0):
        startDate = endDate
    elif (updateFrequency == 1):
        startDate = str((datetime.now() + timedelta(days=-7)).date()).replace('-','')
    elif (updateFrequency == 2):
        startDate = str((datetime.now() + timedelta(days=-30)).date()).replace('-','')
    HTTPString = 'https://amplitude.com/api/2/events/segmentation?e={"event_type": "' + errorCode + '"}&start=' + startDate + '&end=' + endDate
    print(HTTPString)
    response_json = requests.get(HTTPString, auth = HTTPBasicAuth(keys[0], keys[1])).json()
    df = pd.DataFrame(response_json['data']['series'], columns = response_json['data']['xValues']).transpose().rename(columns = {0: errorCode})
    print(df)

    # Plotting the data with custom specifications
    ax = df.plot(kind='bar')
    plt.title('No. of occurences of ' + errorCode)
    rects = ax.patches

    # Make some labels.
    labels = response_json['data']['series'][0]
    for rect, label in zip(rects, labels):
        height = rect.get_height()
        ax.text(rect.get_x() + rect.get_width() / 2, height + 0.5, label, ha='center', va='bottom')
    plt.show()

getErrorPlot("client_ecm_add_account_funnel", "weekly")

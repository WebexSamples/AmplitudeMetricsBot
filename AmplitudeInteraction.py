import pandas as pd
import requests
import json
from requests.auth import HTTPBasicAuth
from datetime import datetime, timedelta
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import seaborn as sns
import cexprtk
iValues = {"daily" : '1', "weekly" : '7', "monthly" : '30', "hourly" : '-3600000', "realtime" : '-300000'}
measures = {'uniques' : 'uniques', 'event totals' : 'totals', 'active %' : 'pct_dau', 'average' : 'average'}
keyFile = open(r'./.secret/api_keys.txt','r')
operators = ['<=', '>=', '=', '<', '>']
keys = keyFile.read().split('\n')

def getDFList(inputJsonFileName):
    with open(inputJsonFileName) as f:
        inputJson = json.load(f)
    errors = inputJson['body']['events']
    interval = iValues[inputJson['body']['interval']]
    metric = measures[inputJson['body']['measures']]
    dfList = []
    endDate = str(datetime.now().date()).replace('-','')
    if (interval == '-3600000' or interval == '-300000'):
        startDate = endDate
    else:
        endVal = inputJson['body']['interval_range'][-1]
        if (endVal == 'd'):
            startDate = str((datetime.now() + timedelta(-int(inputJson['body']['interval_range'][:-1]) + 1)).date()).replace('-','')
        elif (endVal == 'w'):
            startDate = str((datetime.now() + timedelta(-(int(inputJson['body']['interval_range'][:-1]) * 7) + 1)).date()).replace('-','')
        elif (endVal == 'm'):
            startDate = str((datetime.now() + timedelta(-(int(inputJson['body']['interval_range'][:-1]) * 30) + 1)).date()).replace('-','')
        else:
            startDate = endDate

    for i in range(len(errors)):
        HTTPString = ('https://amplitude.com/api/2/events/segmentation?e=' + str(errors[i]) + '&start=' + startDate + '&end=' + endDate + '&i=' + interval + '&m=' + metric).replace("'", '"')
        response = requests.get(HTTPString, auth = HTTPBasicAuth(keys[0], keys[1]))
        if str(response) != '<Response [200]>':
            return 'API call Failed'
        response_json = response.json()
        tempDF = pd.DataFrame(response_json['data']['series'], columns = response_json['data']['xValues']).transpose()
        if not (tempDF.empty):
            if (response_json['data']['seriesLabels'] != [0]):
                tempDF.columns = [el[1] for el in response_json['data']['seriesLabels']]
            if interval in ['1','7']:
                tempDF = tempDF.rename(index = lambda x: x.split('T')[0])
            else:
                tempDF = tempDF.rename(index = lambda x: x.split('T')[1])
            if not (str(tempDF.columns[0]).isdigit()):
                tempDF = tempDF.rename(columns = lambda x: errors[i]['event_type'] + ', ' + x)
            else:
                tempDF = tempDF.rename(columns = lambda x: errors[i]['event_type'])
            dfList.append(tempDF)
    return dfList

def getErrorPlots(inputJsonFileName):
    with open(inputJsonFileName) as f:
        inputJson = json.load(f)
    plotName = inputJsonFileName[:-5] + 'plot.png'
    chartType = inputJson['body']['chart_type']
    dfList = []
    dfList = getDFList(inputJsonFileName)
    df = pd.DataFrame()
    for i in dfList:
        if df.empty:
            df = i
        else:
            df = df.join(i)

    fig, ax = plt.subplots()
    xlabel = '' if (':' in df.index[0]) else 'Dates'
    plt.style.use('fivethirtyeight')
    csfont = {'fontname':'Futura'}
    palette = ['#540D6E', '#EE4266', '#FFD23F', '#1F271B', '#F0F0F0']
    plt.rcParams["font.family"] = csfont['fontname']
    plt.rcParams['font.size'] = '8'
    # sns.set_style('ticks')
    if chartType in ['bar', 'line']:
        if chartType == 'line':
            ax = df.plot(kind='line', marker='o')
        else:
            ax = df.plot(kind='bar', width=0.75)
            rects = ax.patches
            autolabelbar(rects, ax, False)
    elif chartType == 'stacked bar':
        ax = df.plot.bar(stacked=True, color=palette)
        rects = ax.patches
        autolabelbar(rects, ax, True)
    elif chartType == 'stacked area':
        ax = df.plot.area(alpha=0.5)
    ax.grid(alpha=0.2, b=True, axis='y')
    ax.grid(alpha=0, b=True, axis='x')
    plt.tick_params(left = False, bottom = False)
    sns.despine(left=True, bottom=True)
    ax.figure.autofmt_xdate()
    plt.xlabel(xlabel, **csfont)
    plt.ylabel(inputJson['body']['measures'].title(), **csfont)
    plt.legend(loc='upper center', bbox_to_anchor=(0.5, -0.2),
           fancybox=True, ncol=5)
    plt.title('Plot for ' + inputJsonFileName)
    plt.savefig(plotName, dpi=300, bbox_inches='tight')
    plt.close(fig)
    return plotName

def autolabelbar(rects, ax, stacked=False):
    # Get y-axis height to calculate label position from.
    (y_bottom, y_top) = ax.get_ylim()
    y_height = y_top - y_bottom
    ylabels = list(plt.yticks())[0]
    diff = (ylabels[1] - ylabels[0]) * 0.4
    for rect in rects:
        height = rect.get_height()
        label_position = ((rect.get_y() + height / 2) - 0.35) if stacked else height + (y_height * 0.01)
        if height > diff:
            t = ax.text(rect.get_x() + rect.get_width()/2., label_position,
                str(int(height)),
                ha='center', va='bottom', in_layout=True, alpha=0.7)
            t.set_wrap(True)

def CheckAlertStatus(inputJsonFileName):
    with open(inputJsonFileName) as f:
        inputJson = json.load(f)
    if inputJson['body']['alerts'] == 'f':
        return
    dfList = getDFList(inputJsonFileName)
    valuesDict = {}
    thresholds = inputJson['body']['thresholds']
    df = pd.DataFrame()
    for i in dfList:
        if df.empty:
            df = i
        else:
            df = df.join(i)
    temp = 65
    for i in df.columns:
        valuesDict[chr(temp)] = df[i][-1]
        temp = temp + 1
    for threshold in thresholds:
        for n in range(len(operators)):
            if operators[n] in threshold:
                expr = [ i.strip() for i in threshold.split(operators[n])]
                print(expr, valuesDict, threshold)
                eval = cexprtk.evaluate_expression(expr[0], valuesDict)
                if eval <= int(expr[1]) and n == 0:
                    return (True, threshold)
                elif eval >= int(expr[1]) and n == 1:
                    return (True, threshold)
                elif eval == int(expr[1]) and n == 2:
                    return (True, threshold)
                elif eval < int(expr[1]) and n == 3:
                    return (True, threshold)
                elif eval > int(expr[1]) and n == 4:
                    return (True, threshold)
                break
    return [False]
getErrorPlots('input.Json')

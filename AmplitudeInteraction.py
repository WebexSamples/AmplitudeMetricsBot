import pandas as pd
import requests
import json
from requests.auth import HTTPBasicAuth
from datetime import datetime, timedelta
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
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

    for errorIndex in range(len(errors)):
        HTTPString = ('https://amplitude.com/api/2/events/segmentation?e=' + str(errors[errorIndex]) + '&start=' + startDate + '&end=' + endDate + '&i=' + interval + '&m=' + metric).replace("'", '"')
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
                tempDF = tempDF.rename(columns = lambda x: errors[errorIndex]['event_type'] + ', ' + x)
            else:
                tempDF = tempDF.rename(columns = lambda x: errors[errorIndex]['event_type'])
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
    if dfList == 'API call Failed':
        return 'API call Failed'
    for dataframe in dfList:
        if df.empty:
            df = dataframe
        else:
            df = df.join(dataframe)

    fig, ax = plt.subplots()
    xlabel = '' if (':' in df.index[0]) else 'Dates'
    plt.style.use('fivethirtyeight')
    csfont = {'fontname':'Futura'}
    palette = ['#e6194b', '#3cb44b', '#ffe119', '#4363d8', '#f58231', '#911eb4', '#46f0f0', '#f032e6', '#bcf60c', '#fabebe', '#008080', '#e6beff', '#9a6324', '#fffac8', '#800000', '#aaffc3', '#808000', '#ffd8b1', '#808080', '#f0f0f0']
    plt.rcParams["font.family"] = csfont['fontname']
    plt.rcParams['font.size'] = '8'
    # sns.set_style('ticks')
    if chartType in ['bar', 'line']:
        if chartType == 'line':
            ax = df.plot.line(marker='o', color=palette, linewidth=1, markersize=1)
        else:
            ax = df.plot.bar(color=palette)
            rects = ax.patches
            if len(rects) <= 30:
                autolabelbar(rects, ax, False)
    elif chartType == 'stacked bar':
        ax = df.plot.bar(stacked=True, color=palette)
        rects = ax.patches
        if len(df.index) <= 20:
            autolabelbar(rects, ax, True)
    elif chartType == 'stacked area':
        ax = df.plot.area(alpha=0.5, color=palette)
    if plt.xticks()[0][-1] > 19 and chartType not in ['stacked area', 'line']:
        xticksList = []
        for tick in range(0, int(plt.xticks()[0][-1]) + 1):
            if tick % int(len(plt.xticks()[0]) / 7) == 0:
                xticksList.append(df.index[tick])
            else:
                xticksList.append('')
        plt.xticks(np.arange(len(xticksList)), xticksList)
    ax.grid(alpha=0, b=True, axis='x')
    plt.tick_params(left = False, bottom = False)
    sns.despine(left=True, bottom=True)
    ax.figure.autofmt_xdate()
    plt.xlabel(xlabel, **csfont)
    plt.ylabel(inputJson['body']['measures'].title(), **csfont)
    plt.legend(loc='upper center', bbox_to_anchor=(0.5, -0.2),
           fancybox=True, ncol=3)
    plt.title('')
    plt.savefig(plotName, dpi=600, bbox_inches='tight')
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
        label_position = ((rect.get_y() + height / 2) - (y_height * 0.01)) if stacked else height + (y_height * 0.01)
        if height:
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
    thresholdsTriggered = []
    if dfList == 'API call Failed':
        return 'API call Failed'
    for dataframe in dfList:
        if df.empty:
            df = dataframe
        else:
            df = df.join(dataframe)
    ascii = 65
    for i in df.columns:
        valuesDict[chr(temp)] = df[i][-1]
        ascii = ascii + 1
    for threshold in thresholds:
        for operatorIndex in range(len(operators)):
            if operators[operatorIndex] in threshold:
                expr = [ i.strip() for i in threshold.split(operators[operatorIndex])]
                eval = cexprtk.evaluate_expression(expr[0], valuesDict)
                print(eval)
                if eval <= int(expr[1]) and operatorIndex == 0:
                    thresholdsTriggered.append((threshold, eval))
                elif eval >= int(expr[1]) and operatorIndex == 1:
                    thresholdsTriggered.append((threshold, eval))
                elif eval == int(expr[1]) and operatorIndex == 2:
                    thresholdsTriggered.append((threshold, eval))
                elif eval < int(expr[1]) and operatorIndex == 3:
                    thresholdsTriggered.append((threshold, eval))
                elif eval > int(expr[1]) and operatorIndex == 4:
                    thresholdsTriggered.append((threshold, eval))
                break
    return thresholdsTriggered

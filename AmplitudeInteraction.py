import requests, json, matplotlib, cexprtk, asyncio
import pandas as pd
from requests.auth import HTTPBasicAuth
from datetime import datetime, timedelta
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import seaborn as sns
from threading import Thread
from concurrent.futures import ThreadPoolExecutor

iValues = {"daily" : '1', "weekly" : '7', "monthly" : '30', "hourly" : '-3600000', "realtime" : '-300000'}
measures = {'uniques' : 'uniques', 'event totals' : 'totals', 'active %' : 'pct_dau', 'average' : 'average'}
dfList = []
keyFile = open(r'./.secret/api_keys.txt','r')
themeFile = open(r'./themeConfig.json','r')
themeJson = json.load(themeFile)
themeFile.close()
operators = ['<=', '>=', '=', '<', '>']
keys = keyFile.read().split('\n')
jsonPlotJobs = []

def apiCall(inputJsonFileName, HTTPString, errorString):
    with open(inputJsonFileName) as f:
        inputJson = json.load(f)
    interval = iValues[inputJson['body']['interval']]
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
            tempDF = tempDF.rename(columns = lambda x: errorString['event_type'] + ', ' + x)
        else:
            tempDF = tempDF.rename(columns = lambda x: errorString['event_type'])
        dfList.append(tempDF)
        return tempDF

async def getDFListAsynchronously(inputJsonFileName):
    global dfList
    with open(inputJsonFileName) as f:
        inputJson = json.load(f)
        f.close()
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
    if inputJson['body']['between_dates'] != '' and not(inputJson['body']['repeat']) and not(inputJson['body']['alerts']):
        (startDate, endDate) = [date.strip() for date in inputJson['body']['between_dates'].split('-')]

    with ThreadPoolExecutor(max_workers=10) as executor:
        with requests.Session() as session:
            loop = asyncio.get_event_loop()
            tasks = []
            for i in range(len(errors)):
                HTTPString = ('https://amplitude.com/api/2/events/segmentation?e=' + str(errors[i]) + '&start=' + startDate + '&end=' + endDate + '&i=' + interval + '&m=' + metric).replace("'", '"')
                tasks.append(loop.run_in_executor(
                    executor,
                    apiCall,
                    *(inputJsonFileName, HTTPString, errors[i])
                ))
            for response in await asyncio.gather(*tasks):
                pass

def getErrorPlots(inputJsonFileName):
    with open(inputJsonFileName) as f:
        inputJson = json.load(f)
        f.close()
    plotName = inputJsonFileName[:-5] + 'plot.png'
    chartType = inputJson['body']['chart_type']
    errorNames = [event['event_type'] for event in inputJson['body']['events']]
    loop = asyncio.get_event_loop()
    future = asyncio.ensure_future(getDFListAsynchronously("input.json"))
    loop.run_until_complete(future)
    tempDF = pd.DataFrame()
    df = pd.DataFrame()
    if dfList == 'API call Failed':
        return 'API call Failed'
    for dataframe in dfList:
        if tempDF.empty:
            tempDF = dataframe
        else:
            tempDF = tempDF.join(dataframe)
    for error in errorNames:
        df[error] = tempDF[error]
    fig, ax = plt.subplots()
    xlabel = 'Hours' if (':' in df.index[0]) else 'Dates'
    plt.style.use(themeJson['body']['matplotlib_style'])
    csfont = {'fontname': themeJson['body']['figure_font_name']}
    palette = themeJson['body']['plot_color_palette']
    plt.rcParams["font.family"] = csfont['fontname']
    plt.rcParams['font.size'] = themeJson['body']['figure_font_size']
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
    plt.title(inputJson['body']['plot_title'])
    plt.savefig(plotName, dpi= int(themeJson['body']['plot_dpi']), bbox_inches='tight')
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
    if inputJson['body']['alerts'] == False:
        return
    loop = asyncio.get_event_loop()
    future = asyncio.ensure_future(getDFListAsynchronously("input.json"))
    loop.run_until_complete(future)
    valuesDict = {}
    thresholds = inputJson['body']['thresholds']
    errorNames = [event['event_type'] for event in inputJson['body']['events']]
    df = pd.DataFrame()
    tempDF = pd.DataFrame()
    thresholdsTriggered = []
    if dfList == 'API call Failed':
        return 'API call Failed'
    for dataframe in dfList:
        if tempDF.empty:
            tempDF = dataframe
        else:
            tempDF = tempDF.join(dataframe)
    for error in errorNames:
        df[error] = tempDF[error]

    ascii = 65
    for column in df.columns:
        valuesDict[chr(ascii)] = df[column][-1]
        ascii = ascii + 1
    for threshold in thresholds:
        for operatorIndex in range(len(operators)):
            if operators[operatorIndex] in threshold:
                expr = [ i.strip() for i in threshold.split(operators[operatorIndex])]
                eval = cexprtk.evaluate_expression(expr[0], valuesDict)

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

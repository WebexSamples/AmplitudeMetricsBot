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
with open(r'./.secret/api_keys.txt','r') as keyFile:
    keys = keyFile.read().split('\n')
    keyFile.close()
with open(r'./themeConfig.json','r') as themeFile:
    themeJson = json.load(themeFile)
    themeFile.close()

def apiCall(inputJson, HTTPString, errorString, eventNo, formula=''):
    global dfList
    interval = iValues[inputJson['body']['interval']]
    response = requests.get(HTTPString, auth = HTTPBasicAuth(keys[0], keys[1]))
    if str(response) != '<Response [200]>':
        dfList.append('API call Failed')
        return
    response_json = response.json()
    if 'error' in response_json:
        dfList.append('API call Failed')
        return
    tempDF = pd.DataFrame(response_json['data']['series'], columns = response_json['data']['xValues']).transpose()
    if not (tempDF.empty):
        if (response_json['data']['seriesLabels'] != [0] and response_json['data']['seriesLabels'][0] != ''):
            tempDF.columns = [el[1] for el in response_json['data']['seriesLabels']]
        if interval in ['1','7','30']:
            tempDF = tempDF.rename(index = lambda x: x.split('T')[0])
        else:
            tempDF = tempDF.rename(index = lambda x: x.split('T')[1])
        if formula == '':
            if not (str(tempDF.columns[0]).isdigit()):
                tempDF = tempDF.rename(columns = lambda x: errorString['event_type'] + ', ' + x)
            else:
                tempDF = tempDF.rename(columns = lambda x: errorString['event_type'])
            tempDF = tempDF.rename(columns = lambda x: '(' + chr(eventNo + 65) + ') ' + x)
        elif len(tempDF.columns) != 1:
            if not (str(tempDF.columns[0]).isdigit()):
                tempDF.columns = [el for el in response_json['data']['seriesLabels']]
            tempDF = tempDF.rename(columns = lambda x: formula + '(' + chr(eventNo + 65) + ') ' + x)
        elif 'PERCENTILE' in formula:
            tempDF = tempDF.rename(columns = lambda x: formula.split()[0] + '(' + chr(eventNo + 65) + '), ' + formula.split()[-1])
        else:
            tempDF = tempDF.rename(columns = lambda x: formula + '(' + chr(eventNo + 65) + ')')
        if ':' in tempDF.index[0] and inputJson['body']['interval_range'][-1] == 'h':
            if inputJson['body']['interval'].lower() == 'hourly':
                tempDF = tempDF.tail(int(inputJson['body']['interval_range'][:-1]))
            elif inputJson['body']['interval'].lower() == 'realtime':
                tempDF = tempDF.tail(int(inputJson['body']['interval_range'][:-1])*12)
        dfList.append(tempDF)

async def getDFListAsynchronously(inputJson, parameter_plot = 'events'):
    global dfList
    errors = inputJson['body']['events']
    interval = iValues[inputJson['body']['interval']]
    metric = measures[inputJson['body']['measures']] if parameter_plot == 'events' else 'formula'
    eventMetricList = [[] for i in range(26)]
    dfList = []
    eventNo = 0
    endDate = str(datetime.now().date()).replace('-','')
    if (interval == '-3600000' or interval == '-300000'):
        startDate = str((datetime.now() - timedelta(2)).date()).replace('-','')
    elif 'interval_range' in inputJson['body']:
        endVal = inputJson['body']['interval_range'][-1]
        if (endVal == 'd'):
            startDate = str((datetime.now() + timedelta(-int(inputJson['body']['interval_range'][:-1]) + 1)).date()).replace('-','')
        elif (endVal == 'w'):
            startDate = str((datetime.now() + timedelta(-(int(inputJson['body']['interval_range'][:-1]) * 7) + 1)).date()).replace('-','')
        elif (endVal == 'm'):
            startDate = str((datetime.now() + timedelta(-(int(inputJson['body']['interval_range'][:-1]) * 30))).date()).replace('-','')
        else:
            startDate = endDate
    if 'between_dates' in inputJson['body'] and not(inputJson['body']['repeat']) and not(inputJson['body']['alerts']):
        (startDate, endDate) = [date.strip() for date in inputJson['body']['between_dates'].split('-')]

    with ThreadPoolExecutor(max_workers=5) as executor:
        with requests.Session() as session:
            loop = asyncio.get_event_loop()
            tasks = []
            if parameter_plot == 'events':
                for i in range(len(errors)):
                    HTTPString = ('https://amplitude.com/api/2/events/segmentation?e=' + str(errors[i]) + '&start=' + startDate + '&end=' + endDate + '&i=' + interval + '&m=' + metric).replace("'", '"')
                    tasks.append(loop.run_in_executor(
                        executor,
                        apiCall,
                        *(inputJson, HTTPString, errors[i], eventNo)
                    ))
                    eventNo = eventNo + 1
            else:
                eventMetricList = getEventMetricsList(inputJson)
                for index in range(len(errors)):
                    for metricsFormula in eventMetricList[index]:
                        formula = metricsFormula + '(A)' if ' ' not in metricsFormula else metricsFormula.split()[0] + '(A, ' + metricsFormula.split()[-1] + ')'
                        HTTPString = ('https://amplitude.com/api/2/events/segmentation?e=' + str(errors[index]) + '&start=' + startDate + '&end=' + endDate + '&i=' + interval + '&m=' + metric + '&formula=' + formula).replace("'", '"')
                        tasks.append(loop.run_in_executor(
                            executor,
                            apiCall,
                            *(inputJson, HTTPString, errors[index], eventNo, metricsFormula)
                        ))
                    eventNo = eventNo + 1
            for response in await asyncio.gather(*tasks):
                pass

def getErrorPlots(inputJsonFileName):
    with open(inputJsonFileName) as f:
        inputJson = json.load(f)
        f.close()
    plotName = inputJsonFileName[:-5] + 'plot.png'
    chartType = inputJson['body']['chart_type']
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    if 'formulas' in inputJson['body'] and inputJson['body']['measures'].lower() == 'formula':
        future = asyncio.ensure_future(getDFListAsynchronously(inputJson, parameter_plot = 'formula'))
    else:
        future = asyncio.ensure_future(getDFListAsynchronously(inputJson, parameter_plot = 'events'))
    loop.run_until_complete(future)
    df = pd.DataFrame()
    for dataframe in dfList:
        if type(dataframe) == type('string'):
            return 'API call Failed'
        if df.empty:
            df = dataframe
        else:
            df = df.join(dataframe)
    if 'formulas' in inputJson['body']:
        df = formulaEvaluator(df, inputJson['body']['formulas'])
    else:
        df = df.reindex(sorted(df.columns), axis=1)
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
    if 'formulas' in inputJson['body']:
        plt.ylabel(inputJson['body']['plot_title'].title(), **csfont)
    else:
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
        if int(height):
            t = ax.text(rect.get_x() + rect.get_width()/2., label_position,
                str(int(height)),
                ha='center', va='bottom', in_layout=True, alpha=0.7)
            t.set_wrap(True)

def CheckAlertStatus(inputJsonFileName):
    with open(inputJsonFileName) as f:
        inputJson = json.load(f)
    if inputJson['body']['alerts'] == False:
        return
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    future = asyncio.ensure_future(getDFListAsynchronously(inputJson))
    loop.run_until_complete(future)
    valuesDict = {}
    thresholds = inputJson['body']['thresholds']
    df = pd.DataFrame()
    operators = ['<=', '>=', '=', '<', '>']
    thresholdsTriggered = []
    for dataframe in dfList:
        if type(dataframe) == type('string'):
            return 'API call Failed'
        if df.empty:
            df = dataframe
        else:
            df = df.join(dataframe)
    df = df.reindex(sorted(df.columns), axis=1)
    for column in df.columns:
        valuesDict[column[1]] = df[column][-1]
    for threshold in thresholds:
        for operatorIndex in range(len(operators)):
            if operators[operatorIndex] in threshold:
                expr = [ i.strip() for i in threshold.split(operators[operatorIndex])]
                eval = cexprtk.evaluate_expression(expr[0], valuesDict)
                if str(eval) == 'nan' or str(eval) == 'inf':
                    eval = 0
                if eval <= float(expr[1]) and operatorIndex == 0:
                    thresholdsTriggered.append((threshold, eval))
                elif eval >= float(expr[1]) and operatorIndex == 1:
                    thresholdsTriggered.append((threshold, eval))
                elif eval == float(expr[1]) and operatorIndex == 2:
                    thresholdsTriggered.append((threshold, eval))
                elif eval < float(expr[1]) and operatorIndex == 3:
                    thresholdsTriggered.append((threshold, eval))
                elif eval > float(expr[1]) and operatorIndex == 4:
                    thresholdsTriggered.append((threshold, eval))
                break
    return thresholdsTriggered

def getEventMetricsList(inputJson):
    metricsList = ['ACTIVE', 'AVG', 'TOTALS', 'UNIQUES', 'HIST', 'FREQPERCENTILE', 'PERCENTILE', 'PROPSUM', 'PROPAVG', 'PROPHIST', 'PROPCOUNT', 'PROPCOUNTAVG', 'REVENUETOTAL', 'ARPAU']
    eventMetricList = [[] for i in range(26)]
    formulas = inputJson['body']['formulas']
    for formula in formulas:
        for metric in metricsList:
            metricIndexes = [i for i in range(len(formula)) if formula.startswith(metric, i)]
            for index in metricIndexes:
                if formula[index + len(metric)] == '(' and formula[index - 1] not in 'PTQ':
                    metricErrorAlpha = formula[index + len(metric) + 1]
                    if formula[index:index+len(metric)] in "FREQPERCENTILE":
                        metricErrorValue = formula[index + len(metric) + 3 : index + len(metric) + 3 + formula[index + len(metric) + 3:].find(')')]
                        metric = metric + ' ' + metricErrorValue
                    if metric not in eventMetricList[ord(metricErrorAlpha) - 65]:
                        eventMetricList[ord(metricErrorAlpha) - 65].append(metric)
    return eventMetricList
def formulaEvaluator(df, formulas):
    metricsList = ['ACTIVE', 'AVG', 'TOTALS', 'UNIQUES', 'HIST', 'FREQPERCENTILE', 'PERCENTILE', 'PROPSUM', 'PROPAVG', 'PROPHIST', 'PROPCOUNT', 'PROPCOUNTAVG', 'REVENUETOTAL', 'ARPAU']
    evaluatedDF = pd.DataFrame()
    valuesDict = {}
    formulaNo = 1
    for formula in formulas:
        tempFormula = formula
        evaluatedValuesList = []
        for index in range(len(df.index)):
            ascii = 65
            for column in df.columns:
                if ' ' not in column:
                    valuesDict[chr(ascii)] = df[column].to_list()[index]
                    formula = formula.replace(str(column), chr(ascii), -1)
                ascii = ascii + 1
            try:
                eval = cexprtk.evaluate_expression(formula, valuesDict)
            except:
                eval = "nan"
            if str(eval) != 'nan' and str(eval) != 'inf':
                evaluatedValuesList.append(eval)
            else:
                evaluatedValuesList.append(0)
        evaluatedDF['Formula ' + str(formulaNo)] = evaluatedValuesList
        formulaNo = formulaNo + 1
    evaluatedDF.index = df.index
    return evaluatedDF

def appendPlotJob(inputJsonFileName):
    with open('JobQueue.txt', 'a') as queueFile:
        queueFile.write(inputJsonFileName + '\n')
        queueFile.close()

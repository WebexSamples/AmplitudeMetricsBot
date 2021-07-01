# Bot module

from python_webex.v1.Bot import Bot
from requests_toolbelt.multipart.encoder import MultipartEncoder
import requests
from AmplitudeInteraction import CheckAlertStatus, appendPlotJob
import json
import time
from datetime import datetime,timedelta
import pymongo
import os.path
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.jobstores.mongodb import MongoDBJobStore
from apscheduler.executors.pool import ThreadPoolExecutor
import atexit
from bson.objectid import ObjectId

from ChooseProjectCard import chooseProjectCard
from ConfigCard import configCard
from EventCard import eventCard
from EventCard2 import eventCard2
from EventCard3 import eventCard3

bot_url = "http://c87ffde0ea45.eu.ngrok.io"

with open(r'./.secret/api_keys.txt','r') as keyFile:
    keys = keyFile.read().split('\n')
    auth_token = keys[2]
    dbPass = keys[4]

client = pymongo.MongoClient("mongodb+srv://mukuagar:" + dbPass + "@metricsbotcluster.hpx9t.mongodb.net/test?retryWrites=true&w=majority")

db = client.test

jobstores = {
    'default': MongoDBJobStore(database = "test", collection = "jobs", client= client)
}
executors = {
    'default': ThreadPoolExecutor(5)
}
job_defaults = {
    'coalesce': False,
    'max_instances': 3
}
sched = BackgroundScheduler(jobstores=jobstores, executors= executors, job_defaults= job_defaults)
sched.start()
atexit.register(lambda: sched.shutdown())

class MetricsBotClass(Bot):
    def permute(self, input_string):
        if not input_string:
            yield ""
        else:
            first = input_string[:1]
            if first.lower() == first.upper():
                for sub_casing in self.permute(input_string[1:]):
                    yield first + sub_casing
            else:
                for sub_casing in self.permute(input_string[1:]):
                    yield first.lower() + sub_casing
                    yield first.upper() + sub_casing

    def listen(self, message_text):
        all_permutation = list(self.permute(message_text))

        def on_hears_decorator(f):
            for p in all_permutation:
                Bot.on_hears(self, p)(f)
        return on_hears_decorator


metricsBot = MetricsBotClass()
metricsBot.create_webhook(
    name="message_webhook", target_url=bot_url, resource="messages", event="created"
)
metricsBot.create_webhook(
    name='cards_webhook', target_url=bot_url+"/attachment-response", resource="attachmentActions", event="created"
)


@metricsBot.on_hears("*")
def default_response(room_id=None, message = None):
    print("The Message is :", message['text'].replace('TestBot', '').strip())
    messageText = message['text'].replace('TestBot', '').strip().lower()
    if messageText == 'help':
        return help_user(room_id=room_id)
    elif messageText == "sample":
        return send_sample_json(room_id = room_id)
    elif messageText == "choose project":
        return send_choose_project_card(room_id=room_id)
    elif messageText == "configure bot":
        return send_config_card(room_id=room_id)
    elif messageText == "single event":
        return send_single_event_card(room_id=room_id)
    elif messageText == "two events":
        return send_two_events_card(room_id=room_id)
    elif messageText == "three events":
        return send_three_events_card(room_id=room_id)
    elif "cancel" in messageText:
        return cancel_job(messageText, room_id= room_id, message=message)
    elif messageText == "request access for all":
        return request_access_all(room_id = room_id, message = message)
    elif "request access for" in messageText:
        return request_access(senderMessage = messageText, room_id = room_id, message = message)
    elif "add user" in messageText:
        return add_person(messageText.split()[-1].strip(), room_id = room_id, message = message, isAdmin = False)
    elif "add admin" in messageText:
        return add_person(messageText.split()[-1].strip(), room_id = room_id, message = message, isAdmin = True)
    elif messageText == "add all":
        return add_all(room_id= room_id,message = message)
    elif "remove user" in messageText:
        return remove_person(messageText, room_id= room_id, message= message)
    else:
        return metricsBot.send_message(room_id=room_id, text="Sorry, could not understand that.\nType help to know about supported commands")


@metricsBot.set_default_file_response()
def respond_file(files = None, room_id = None, message = None):
    respond_to_file(files=files, room_id=room_id,message=message)


@metricsBot.set_file_action(message_text="*")
def respond_file_spaces(files = None, room_id = None, message = None):
    respond_to_file(files=files, room_id= room_id, message= message)


# Helper Functions

def respond_to_file(files= None, room_id= None, message = None):
    response = requests.get(files[0],
                  headers={'Authorization': 'Bearer '+auth_token})
    if response.headers['Content-Type'].split('/')[-1] != "json":
        metricsBot.send_message(room_id=room_id, text= "Metrics Bot can only support files of json Format")
        return
    filename = response.headers['Content-Disposition'].split('"')[1::1][0]
    messageSent = metricsBot.send_message(room_id=room_id, text= "File named " + filename +" received")
    isValidRoom = checkUsers(room_id)
    if not isValidRoom[0]:
        reply_message(room_id=room_id, message= messageSent.json(), reply='Users mentioned below do not have access to these metrics' + isValidRoom[1])
        requestString = "You can request access by using the command \n\"request acceess for <email>\"\nOR\n\"request access for all\""
        reply_message(room_id=room_id, message= messageSent.json(), reply= requestString)
        return

    reply_message(room_id=room_id, message= messageSent.json(), reply='You will receive response if the Input is correct')

    jsonname = room_id + response.headers['Content-Disposition'].split('"')[1::1][0]
    with open(jsonname, "wb") as newFile:
        newFile.write(response.content)
    appendPlotJob(jsonname)
    flag = 0
    while(flag != 2):
        with open('JobQueue.txt', 'r') as queueFile:
            currentFile = queueFile.readlines()
            if len(currentFile):
                currentFile = currentFile[0].strip()
            else:
                currentFile = ''
            if currentFile == jsonname:
                flag = 1
            if (currentFile != jsonname) and flag == 1:
                flag = 2
            time.sleep(1)
        queueFile.close()
    resultPlot = (jsonname[:-5] + 'plot.png') if isFileNewerThan(str(jsonname[:-5] + 'plot.png'), timedelta(seconds = 30)) else 'API call Failed'

    if resultPlot == 'API call Failed':
        reply_message(room_id=room_id, message= messageSent.json(), reply='API call error occurred, please re-check the input JSON')
    else:
        with open(jsonname) as f:
            inputJson = json.load(f)
        errorstrings = [i for i in inputJson['body']['events']]
        outString = ''
        for i in errorstrings:
            filters = ''
            if 'filters' in i:
                for j in i['filters']:
                    filters = filters + j['subprop_key'] + ' ' + j['subprop_op'] + ' ' + str(j['subprop_value']) + ', '
                filters = filters.rstrip(', ')
            groupby = ''
            if 'group_by' in i:
                for j in i['group_by']:
                    groupby = groupby + j['value'] + ', '
                groupby = groupby.rstrip(', ')
            outString = outString + '-  ' + i['event_type']
            if 'filters' in i:
                outString += '; ' + 'where: ' + filters
            if 'group_by' in i:
                outString += '; ' + 'grouped by: ' + groupby
            outString = outString + '\n'
        textString = "Ola! here's your update for the errors:\n" + outString
        id = room_id
        pid = messageSent.json()['id']
        plotMessage(id, resultPlot, textString, pid)
        if inputJson['body']['repeat'] == True:
            add_to_db(room_id=room_id, inputJson=inputJson, filename= jsonname, messageSender = message['personEmail'], isRepeat= True)
        if inputJson['body']['alerts'] == True and len(inputJson['body']['thresholds']) > 0:
            add_to_db(room_id=room_id, inputJson=inputJson, filename= jsonname, messageSender = message['personEmail'], isRepeat= False)


def help_user(room_id=None):
    messageString = """
Help
==========
This is the list of available commands

help - Show this help
sample - Sends a Sample Json which can be edited and send back to the bot

The json can be configured to make one time request or set up alerts on a regular basis or even send an alert when certain error thresholds are met.
    """
    return metricsBot.send_message(room_id=room_id, text=messageString)

def plotMessage(roomid, plotName, text, parentid):
    encodedMessage = MultipartEncoder({'roomId': roomid,
                  'text': text, 'parentId': parentid,
                  'files': (plotName, open(plotName, 'rb'),
                  'image/png')})

    r = requests.post('https://webexapis.com/v1/messages', data=encodedMessage,
                    headers={'Authorization': 'Bearer ' + auth_token,
                    'Content-Type': encodedMessage.content_type})

def checkUsers(room_id):
    memberURL = "https://webexapis.com/v1/memberships?roomId="
    response = requests.get(memberURL + room_id,
                headers={'Authorization': 'Bearer '+auth_token})
    itemList = response.json()['items']
    userString = ""
    userArray = []
    isValid = True
    for item in itemList:
        if '@webex.bot' in item['personEmail']:
            continue
        if db.users.count_documents({ 'email': item['personEmail']}, limit = 1) == 0:
            userString += '\n' + item['personEmail']
            userArray.append(item['personEmail'])
            isValid = False
    return (isValid, userString, userArray)


def send_choose_project_card(room_id=None):
    message = metricsBot.send_card(card=chooseProjectCard, room_id=room_id)
    message_id = message.json()['id']

    @metricsBot.attachment_response(message_id=message_id)
    def respond_to_card(msg):
        print(msg)
        print(msg['inputs']['choices'])
        metricsBot.send_message(
            room_id= room_id, text = msg['inputs']['choices'] + " has been chosen"
        )
        metricsBot.send_message(
            room_id= room_id, text = "Now you can type \"create graph\" to get the next card."
        )
        metricsBot.delete_message(message_id=message_id)

def send_single_event_card(room_id=None):
    message = metricsBot.send_card(card=eventCard, room_id=room_id)
    message_id = message.json()['id']

    @metricsBot.attachment_response(message_id=message_id)
    def respond_to_card(msg):
        print(msg)
        print(msg['inputs']['error_name1'])
        # Logic to convert card input to json
        encodedMessage = MultipartEncoder({'roomId': room_id,
                      'text': 'example attached',
                      'files': ('plot.png', open('plot.png', 'rb'),
                      'image/png')})

        r = requests.post('https://webexapis.com/v1/messages', data=encodedMessage,
                        headers={'Authorization': 'Bearer ' + auth_token,
                        'Content-Type': encodedMessage.content_type})
        metricsBot.delete_message(message_id=message_id)

def send_config_card(room_id=None):
    message = metricsBot.send_card(card=configCard, room_id=room_id)
    message_id = message.json()['id']

    @metricsBot.attachment_response(message_id=message_id)
    def respond_to_card(msg):
        print(msg)
        metricsBot.send_message(
            room_id=room_id, text="The bot has been configured.\nTo reconfigure, type command \"Configure bot\" again"
        )
        metricsBot.delete_message(message_id=message_id)

def send_two_events_card(room_id=None):
    message = metricsBot.send_card(card=eventCard2, room_id=room_id)
    message_id = message.json()['id']

    @metricsBot.attachment_response(message_id=message_id)
    def respond_to_card(msg):
        print(msg)
        print(msg['inputs']['error_name1'])
        # Logic to convert card input to json
        encodedMessage = MultipartEncoder({'roomId': room_id,
                      'text': 'example attached',
                      'files': ('plot.png', open('plot.png', 'rb'),
                      'image/png')})

        r = requests.post('https://webexapis.com/v1/messages', data=encodedMessage,
                        headers={'Authorization': 'Bearer ' + auth_token,
                        'Content-Type': encodedMessage.content_type})
        metricsBot.delete_message(message_id=message_id)

def send_three_events_card(room_id=None):
    message = metricsBot.send_card(card=eventCard3, room_id=room_id)
    message_id = message.json()['id']

    @metricsBot.attachment_response(message_id=message_id)
    def respond_to_card(msg):
        print(msg)
        print(msg['inputs']['error_name1'])
        # Logic to convert card input to json
        encodedMessage = MultipartEncoder({'roomId': room_id,
                      'text': 'example attached',
                      'files': ('plot.png', open('plot.png', 'rb'),
                      'image/png')})

        r = requests.post('https://webexapis.com/v1/messages', data=encodedMessage,
                        headers={'Authorization': 'Bearer ' + auth_token,
                        'Content-Type': encodedMessage.content_type})
        metricsBot.delete_message(message_id=message_id)

def repeat_response(filename=None, room_id = None, objectId = None):
    message = metricsBot.send_message(room_id=room_id, text= "Here is your scheduled update")
    isValidRoom = checkUsers(room_id)
    if not isValidRoom[0]:
        reply_message(room_id=room_id, message= message.json(), reply='Users mentioned below do not have access to these metrics' + isValidRoom[1])
        requestString = "You can request access by using the command \n\"request acceess for <email>\"\nOR\n\"request access for all\""
        reply_message(room_id=room_id, message= message.json(), reply= requestString)
        query = db.things.find_one({"_id": ObjectId(objectId)}, {"jobID": 1})
        print("Query: \n",query['jobID'])
        reply_message(room_id=room_id, message=message.json(), reply= 'To stop futher Updates, Please Type \n"Cancel ' + query['jobID'] + '"')
        return

    reply_message(room_id=room_id, message= message.json(), reply='You will receive response if the Input is correct')

    appendPlotJob(filename)
    flag = 0
    while(flag != 2):
        with open('JobQueue.txt', 'r') as queueFile:
            currentFile = queueFile.readlines()
            if len(currentFile):
                currentFile = currentFile[0].strip()
            else:
                currentFile = ''
            if currentFile == filename:
                flag = 1
            if (currentFile != filename) and flag == 1:
                flag = 2
            time.sleep(1)
        queueFile.close()
    resultPlot = (filename[:-5] + 'plot.png') if isFileNewerThan(str(filename[:-5] + 'plot.png'), timedelta(seconds = 30)) else 'API call Failed'

    if resultPlot == 'API call Failed':
        reply_message(room_id=room_id, message= message.json(), reply='API call error occurred, please re-check the input JSON')
    else:
        with open(filename) as f:
            inputJson = json.load(f)
        errorstrings = [i for i in inputJson['body']['events']]
        outString = ''
        for i in errorstrings:
            filters = ''
            if 'filters' in i:
                for j in i['filters']:
                    filters = filters + j['subprop_key'] + ' ' + j['subprop_op'] + ' ' + str(j['subprop_value']) + ', '
                filters = filters.rstrip(', ')
            groupby = ''
            if 'group_by' in i:
                for j in i['group_by']:
                    groupby = groupby + j['value'] + ', '
                groupby = groupby.rstrip(', ')
            outString = outString + '-  ' + i['event_type']
            if 'filters' in i:
                outString += '; ' + 'where: ' + filters
            if 'group_by' in i:
                outString += '; ' + 'grouped by: ' + groupby
            outString = outString + '\n'
        textString = "Ola! here's your update for the errors:\n" + outString
        id = room_id
        pid = message.json()['id']
        plotMessage(id, resultPlot, textString, pid)
        query = db.things.find_one({"_id": ObjectId(objectId)}, {"jobID": 1})
        print("Query: \n",query['jobID'])
        reply_message(room_id=room_id, message=message.json(), reply= 'To stop futher Updates, Please Type \n"Cancel ' + query['jobID'] + '"')

def add_to_db(room_id=None, inputJson = None, filename = None, messageSender = None, isRepeat = None):
    dataDict = {"roomID": room_id, "inputJson": inputJson}
    result = db.things.insert_one(dataDict)
    if isRepeat:
        response = call_repeat_scheduler(objectId= result.inserted_id, filename = filename, messageSender = messageSender)
        if response == 0:
            metricsBot.send_message(room_id=room_id, text = "Json contains errors in repeat_interval field")
    else:
        response = call_alert_scheduler(objectId= result.inserted_id, filename = filename, messageSender = messageSender, inputJson = inputJson)

def call_repeat_scheduler(objectId: None, filename = None, messageSender = None):
    print("Object is: ",objectId)
    query = db.things.find_one({"_id": ObjectId(objectId)})
    print("The query is: \n",query['inputJson'])
    interval = query['inputJson']['body']['repeat_interval'].lower()
    try:
        jobID = sched.add_job(repeat_response,CronTrigger.from_crontab(interval, timezone='UTC') ,args=(filename,query['roomID'], objectId), misfire_grace_time= 300, jitter = 100)
    except ValueError:
        return 0
    db.things.update({"_id": ObjectId(objectId)}, {"$set": {"jobID": jobID.id}})
    db.jobs.update({'_id': jobID.id}, {"$set": {"jobOwner": messageSender}})
    return jobID

def cancel_job(jobDetails: None, room_id= None, message = None):
    jobID = jobDetails.split()[-1].strip()
    jobDoc = db.jobs.find_one({'_id': jobID})
    if jobDoc == None:
        metricsBot.send_message(room_id=room_id, text="Check the Job ID entered")
        return
    if jobDoc['jobOwner'] == message['personEmail']:
        db.jobs.delete_one({"_id": jobID})
        metricsBot.send_message(room_id=room_id, text=" You will receive no furter updates regarding Job " + jobID)
    else:
        metricsBot.send_message(room_id=room_id, text="Only "+ jobDoc['jobOwner'] + " is allowed to remove job " + jobID)


def reply_message(room_id = None, message= None, reply = None):
    encodedMessage = MultipartEncoder({'roomId': room_id,
                        'text': reply,
                        'parentId':message['id']})
    response = requests.post('https://webexapis.com/v1/messages', data=encodedMessage,
                        headers={'Authorization': 'Bearer ' + auth_token,
                        'Content-Type': encodedMessage.content_type})
    return response

def call_alert_scheduler(objectId: None, filename = None, messageSender = None, inputJson = None):
    query = db.things.find_one({"_id": ObjectId(objectId)})
    interval = "*/1 * * * *"
    try:
        jobID = sched.add_job(alert_response,CronTrigger.from_crontab(interval, timezone='UTC') ,args=(filename,query['roomID'], objectId, inputJson), misfire_grace_time= 180, jitter = 60)
    except ValueError:
        return 0
    db.things.update({"_id": ObjectId(objectId)}, {"$set": {"jobID": jobID.id}})
    db.jobs.update({'_id': jobID.id}, {"$set": {"jobOwner": messageSender}})
    return jobID

def alert_response(filename = None, room_id = None, objectId = None, inputJson = None):
    responses = CheckAlertStatus(filename)
    if len(responses) > 0:
        isValidRoom = checkUsers(room_id)
        if not isValidRoom[0]:
            myMessage = metricsBot.send_message(room_id= room_id, text='Users mentioned below do not have access to metrics' + isValidRoom[1])
            requestString = "You can request access by using the command \n\"request acceess for <email>\"\nOR\n\"request access for all\""
            reply_message(room_id=room_id, message= myMessage.json(), reply= requestString)
            query = db.things.find_one({"_id": ObjectId(objectId)}, {"jobID": 1})
            print("Query: \n",query['jobID'])
            reply_message(room_id=room_id, message=myMessage.json(), reply= 'To stop futher Updates, Please Type \n"Cancel ' + query['jobID'] + '"')
            return
        messageThread = send_markdown(room_id= room_id, markdown_text = "# Alert")
        for response in responses:
            thresholdString = ""
            for char in response[0]:
                char = char.upper()
                if ord(char) >=65 and ord(char) <= 90:
                    thresholdString += inputJson['body']['events'][ord(char) - 65]['event_type']
                else:
                    thresholdString += char.upper()
            print("Threshold \""+ thresholdString + "\" was crossed with value " + str(response[1]))
            reply_message(room_id=room_id,message= messageThread.json(), reply ="Threshold "+ thresholdString + " was crossed with value " + str(response[1]))

        appendPlotJob(filename)
        flag = 0
        while(flag != 2):
            with open('JobQueue.txt', 'r') as queueFile:
                currentFile = queueFile.readlines()
                if len(currentFile):
                    currentFile = currentFile[0].strip()
                else:
                    currentFile = ''
                if currentFile == filename:
                    flag = 1
                if (currentFile != filename) and flag == 1:
                    flag = 2
                time.sleep(1)
            queueFile.close()
        resultPlot = (filename[:-5] + 'plot.png') if isFileNewerThan(str(filename[:-5] + 'plot.png'), timedelta(seconds = 30)) else 'API call Failed'

        if resultPlot == 'API call Failed':
            reply_message(room_id=room_id, message= messageSent.json(), reply='API call error occurred, please re-check the input JSON')
        else:
            reply_message(room_id=room_id,message=messageThread.json(), reply ="Here is the graph again!")
            errorstrings = [i for i in inputJson['body']['events']]
            outString = ''
            for i in errorstrings:
                filters = ''
                if 'filters' in i:
                    for j in i['filters']:
                        filters = filters + j['subprop_key'] + ' ' + j['subprop_op'] + ' ' + str(j['subprop_value']) + ', '
                    filters = filters.rstrip(', ')
                groupby = ''
                if 'group_by' in i:
                    for j in i['group_by']:
                        groupby = groupby + j['value'] + ', '
                    groupby = groupby.rstrip(', ')
                outString = outString + '-  ' + i['event_type']
                if 'filters' in i:
                    outString += '; ' + 'where: ' + filters
                if 'group_by' in i:
                    outString += '; ' + 'grouped by: ' + groupby
                outString = outString + '\n'
            textString = "Ola! here's your update for the errors:\n" + outString
            plotMessage(roomid = room_id, plotName= resultPlot, text= textString, parentid= messageThread.json()['id'])
            query = db.things.find_one({"_id": ObjectId(objectId)}, {"jobID": 1})
            print("Query: \n",query['jobID'])
            reply_message(room_id=room_id, message=messageThread.json(), reply= 'To stop futher Updates, Please Type \n"Cancel ' + query['jobID'] + '"')


def send_markdown(room_id= None, markdown_text = None):
    encodedMessage = MultipartEncoder({'roomId': room_id,
                    'markdown': markdown_text})
    response = requests.post('https://webexapis.com/v1/messages', data=encodedMessage,
                    headers={'Authorization': 'Bearer ' + auth_token,
                    'Content-Type': encodedMessage.content_type})
    return response

def send_sample_json(room_id= None):
    isValidRoom = checkUsers(room_id)
    if not isValidRoom[0]:
        myMessage = metricsBot.send_message(room_id= room_id, text='Users mentioned below do not have access to the sample' + isValidRoom[1])
        requestString = "You can request access by using the command \n\"request acceess for <email>\"\nOR\n\"request access for all\""
        reply_message(room_id=room_id, message= myMessage.json(), reply= requestString)
        return
    encodedMessage = MultipartEncoder({'roomId': room_id,
                      'text': 'Sample attached',
                      'files': ('sample.json', open('sample.json', 'rb'),
                      'file/json')})
    response = requests.post('https://webexapis.com/v1/messages', data=encodedMessage,
                        headers={'Authorization': 'Bearer ' + auth_token,
                        'Content-Type': encodedMessage.content_type})
    return response

def add_person(new_user = None, room_id= None, message = None,replyToMessage= None, isAdmin = None):
    if replyToMessage == None:
        replyToMessage = message
    if db.users.count_documents({ 'email': message['personEmail'], 'isAdmin': True }, limit = 1) != 0:
        if db.users.count_documents({ 'email': new_user}, limit = 1) != 0:
            if isAdmin == True:
                db.users.update_one({'email': new_user}, {"$set": {'isAdmin': True}})
                reply_message(room_id=room_id, message= replyToMessage, reply="The user "+ new_user + " has been granted admin privilidges")
            else:
                reply_message(room_id=room_id, message= replyToMessage, reply="The user "+ new_user + " already has access to the bot commands")
        else:
            if new_user[-10:] != '@cisco.com':
                reply_message(room_id=room_id, message= replyToMessage, reply= new_user + " was not added as only Cisco domain users can be added.")
                return
            db.users.insert_one({'email': new_user, 'isAdmin': isAdmin})
            reply_message(room_id=room_id, message= replyToMessage, reply="The user "+ new_user + " has been added")
    else:
        reply_message(room_id=room_id, message= replyToMessage, reply="You do not have permission to add users")

def remove_person(textMessage, room_id= None, message = None):
    remove_user = textMessage.split()[-1].strip()
    if db.users.count_documents({ 'email': message['personEmail'], 'isAdmin': True }, limit = 1) != 0:
        if db.users.count_documents({ 'email': remove_user}, limit = 1) != 0:
            if db.users.find_one({'email':remove_user})['isAdmin'] == True:
                reply_message(room_id=room_id, message= message, reply="The user "+ remove_user + " cannot be removed as they are admins")
            else:
                db.users.delete_one({"email": remove_user})
                reply_message(room_id=room_id, message= message, reply="The user "+ remove_user + " has been removed")
        else:
            reply_message(room_id=room_id, message=message, reply="The user does not have access to the bot")
    else:
        reply_message(room_id=room_id, message= message, reply="You do not have permission to remove users")

def request_access(senderMessage = None, room_id = None, message = None):
    new_user = senderMessage.split()[-1].strip()
    if db.users.count_documents({ 'email': new_user}, limit = 1) != 0:
            reply_message(room_id=room_id, message= message, reply="The user "+ new_user + " already has access to the bot commands")
    else:
        send_admins_request(userArray=[new_user],userString=new_user, messageSender= message['personEmail'])
        reply_message(room_id=room_id, message= message, reply='A message has been sent to the bot Admins')

def request_access_all(room_id = None, message = None):
    _,invalidUserString,invalidUsers = checkUsers(room_id=room_id)
    if invalidUserString == '':
        reply_message(room_id=room_id, message= message, reply='All users in this space have bot access')
    else:
        send_admins_request(userArray=invalidUsers,userString=invalidUserString, messageSender= message['personEmail'])
        reply_message(room_id=room_id, message= message, reply='A message has been sent to the bot Admins')

def send_admins_request(userArray= None,userString = None, messageSender= None):
    adminList = db.users.find({'isAdmin': True})
    for admin in adminList:
        send_message_to_email(email=admin['email'], message= "The following users request access to metrics bot "+ userString)
        print("Admin:",admin)

def add_all(room_id=None, message = None):
    if db.users.count_documents({ 'email': message['personEmail'], 'isAdmin': True }, limit = 1) == 0:
        reply_message(room_id=room_id, message= message, reply="You do not have permission to add users")
        return
    if 'parentId' in message:
        parentMessage = metricsBot.get_message_details(message_id=message['parentId']).json()
        print(parentMessage['text'].splitlines()[1:])
        userlist = parentMessage['text'].splitlines()[1:]
        for user in userlist:
            add_person(new_user= user, room_id=room_id, message=message,replyToMessage=parentMessage, isAdmin=False)
    else:
        print("Add from space")
        _,_,invalidUsers = checkUsers(room_id=room_id)
        for user in invalidUsers:
            add_person(new_user= user, room_id=room_id, message=message, isAdmin=False)

def send_message_to_email(email= None, message = None):
    encodedMessage = MultipartEncoder({'toPersonEmail': email,
                      'text': message})
    response = requests.post('https://webexapis.com/v1/messages', data=encodedMessage,
                        headers={'Authorization': 'Bearer ' + auth_token,
                        'Content-Type': encodedMessage.content_type})
def isFileNewerThan(file, delta):
    cutoff = datetime.utcnow() - delta
    mtime = datetime.utcfromtimestamp(os.path.getmtime(file))
    if mtime > cutoff:
        return True
    return False

import AmplitudeInteraction as ai
import time

while True:
    with open('JobQueue.txt', 'r') as queueFile:
        queue = queueFile.readlines()
        queueFile.close()
    print(queue)
    if(len(queue)):
        if queue[0].strip() != '':
            plot = ai.getErrorPlots(queue[0].strip())
            if (plot == 'API call Failed'):
                print(queue[0].strip() + ' Plot FAILED!')
            else:
                print(plot + ' Plotted!')
        with open('JobQueue.txt', 'w') as queueFile:
            for name in queue[1:]:
                queueFile.write(name)
            queueFile.close()
    time.sleep(1)

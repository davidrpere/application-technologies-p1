import time
import utils
import os
import json
from copy import copy


def main():
    print('Hello world. This is the listener app.')
    # Now we must import the sqs queue manager and start listening to the Inbox queue.
    messaging_interface = utils.SqsMessagingInterface('EchoSystem')
    storing_interface = utils.S3StoringInterface()
    messaging_interface.daemon = True
    messaging_interface.start()
    # messaging_interface.join()
    storing_interface.daemon = True
    storing_interface.start()
    # storing_interface.join()

    while not messaging_interface._inbox_ready \
            or not messaging_interface._outbox_ready \
            or not storing_interface._storage_ready:
        time.sleep(1)

    clients = messaging_interface._clients.copy()

    while True:
        time.sleep(0.3)
        for query in messaging_interface._queries:
            if query.query_type == utils.QueryFlag.Remove_Files:
                print('Listener must remove file ', query.query_param)
                storing_interface.remove_file(query.query_param)
                try:
                    os.remove('/tmp/' + query.query_param)
                except FileNotFoundError:
                    print('Asked to remove a file which isn\'t on this machine')
            elif query.query_type == utils.QueryFlag.Update_Files:
                print('Listener must update file ', query.query_param)
                print(messaging_interface._messages[query.client_id])
                local_file = open('/tmp/' + query.query_param, 'a')
                local_file.write(json.dumps(messaging_interface._messages[query.client_id]))
                messaging_interface._messages.pop(query.client_id)
                local_file.close()
                storing_interface.upload_file('/tmp/' + query.query_param)
            elif query.query_type == utils.QueryFlag.Create_Files:
                print('Listener must create file ', query.query_param)
                if not storing_interface._check_file_exists(query.query_param):
                    open('/tmp/' + query.query_param, 'a').close()
                    storing_interface.upload_file('/tmp/' + query.query_param)
            messaging_interface._queries.remove(query)


main()

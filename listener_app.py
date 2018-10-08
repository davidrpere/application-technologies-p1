import time
import utils
import os
import json
import listener_interface


def main():
    print('Hello world. This is the listener app.')
    # Now we must import the sqs queue manager and start listening to the Inbox queue.
    messaging_interface = listener_interface.SqsListenerInterface()
    storing_interface = listener_interface.S3StoringInterface()
    messaging_interface.daemon = True
    messaging_interface.start()
    storing_interface.daemon = True
    storing_interface.start()

    while not messaging_interface.inbox_ready \
            or not messaging_interface.outbox_ready \
            or not storing_interface._storage_ready:
        time.sleep(1)

    while True:
        time.sleep(0.3)
        for query in messaging_interface._queries:
            if query.query_type == utils.QueryFlag.Remove_Files:
                storing_interface.remove_file(query.query_param)
                try:
                    os.remove('/tmp/' + query.query_param)
                except FileNotFoundError:
                    print('Asked to remove a file which isn\'t on this machine')
            elif query.query_type == utils.QueryFlag.Update_Files:
                storing_interface.upload_file_from_dict(query, messaging_interface._messages)
                messaging_interface._messages.pop(query.client_id)
            elif query.query_type == utils.QueryFlag.Create_Files:
                init_msg = ['Started session']
                init_msg_dict = {query.client_id: init_msg}
                storing_interface.upload_file_from_dict(query, init_msg_dict)
            elif query.query_type == utils.QueryFlag.Download_Files:
                print('Client asked to retrieve messages.')
                if storing_interface._check_file_exists(query.query_param):
                    url = storing_interface.get_file_url(query.query_param)
                    if url is not None:
                        messaging_interface.send_message(url, 'download-reply', query.client_id)
            messaging_interface._queries.remove(query)


main()

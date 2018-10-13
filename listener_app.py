import time
import utils
import os
import listener_interface, aws_wrapper
import logging


def main():
    logging.getLogger().setLevel(logging.INFO)
    sqs_manager = aws_wrapper.SqsManager()
    messaging_interface = listener_interface.SqsListenerInterface(sqs_manager)
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
            if query.query_type == utils.Command.REMOVE_CLIENT:
                storing_interface.remove_file(query.query_param)
                try:
                    os.remove('/tmp/' + query.query_param)
                except FileNotFoundError:
                    logging.info('Asked to remove a file which isn\'t on this machine')
            elif query.query_type == utils.Command.BEGIN_ECHO:
                messaging_interface._messages[query.client_id] = ['--Echo began--']
            elif query.query_type == utils.Command.CLIENT_END:
                storing_interface.upload_file_from_dict(query, messaging_interface._messages)
                messaging_interface._messages.pop(query.client_id)
            elif query.query_type == utils.Command.NEW_CLIENT:
                init_msg = [utils.Constants.HELLO_BODY.value]
                init_msg_dict = {query.client_id: init_msg}
                storing_interface.upload_file_from_dict(query, init_msg_dict)
            elif query.query_type == utils.Command.DOWNLOAD_REQUEST:
                logging.info('Client asked to retrieve messages.')
                if storing_interface._check_file_exists(query.query_param):
                    url = storing_interface.get_file_url(query.query_param)
                    if url is not None:
                        messaging_interface.send_message(url, utils.Command.DOWNLOAD_REPLY, query.client_id)
            elif query.query_type == utils.Command.DOWNLOAD_URL_REQUEST:
                logging.info('Client is updating its URL.')
                if storing_interface._check_file_exists(query.query_param):
                    url = storing_interface.get_file_url(query.query_param)
                    if url is not None:
                        messaging_interface.send_message(url, utils.Command.DOWNLOAD_URL_REPLY, query.client_id)
            messaging_interface._queries.remove(query)


main()

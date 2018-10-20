import aws_wrapper
import random
import time
import os
import json
import logging
from threading import Thread
from typing import Dict
from utils import Query, Command, Constants


class SqsListenerInterface(Thread):
    """ Class for interfacing with the SQS Queues in a simple way, server oriented, abstracting from the lower level
    operation.

    Parameters such as inbox and outbox queue names are hardcoded and extracted from Constants class.
    Boolean parameters are used to set if queues are ready to use.
    A dict of clients is kept in memory as long as a client is being served, and a dict of messages is also kept,
    containing messages for each client.
    """
    inbox_queue_name = Constants.INBOX_QUEUE_NAME.value
    inbox_ready = False
    outbox_queue_name = Constants.OUTBOX_QUEUE_NAME.value
    outbox_ready = False
    _clients: Dict[int, str] = {}
    _messages: Dict = {}

    def __init__(self, sqs_manager):
        """ Instantiates an SQS Listener Interface.

        Random ID is generated on each instantiation, so each instance is a EchoSystem Listener.
        :param sqs_manager: SQS manager previously instantiated to bind to our interface.
        """
        logging.info('Initialized listener interface.')
        Thread.__init__(self)
        self._identity = random.getrandbits(32)
        self._sqs_manager = sqs_manager
        self._sqs_manager.bind_to(self.received_message)
        self._queries = []

    def run(self):
        """ Run method for the listener interface.

        This will wait for the queues to be ready, set their boolean flags to true and then long-poll messages from
        Inbox queue and sleep 2 seconds between services, so we don't overkill CPU nor SQS queries.
        :return:
        """
        logging.info('Initialized listener interface run method.')
        if not self._sqs_manager._check_sqs_queues(self.inbox_queue_name):
            self._sqs_manager.create_queue(self.inbox_queue_name)
        if not self._sqs_manager._check_sqs_queues(self.outbox_queue_name):
            self._sqs_manager.create_queue(self.outbox_queue_name)
        self._sqs_manager._wait_for_queue_confirmation(self.inbox_queue_name)
        self.inbox_ready = True
        self._sqs_manager._wait_for_queue_confirmation(self.outbox_queue_name)
        self.outbox_ready = True

        while True:
            self.receive_message()
            time.sleep(2)

    def received_message(self, message):
        """ Callback method for received messages.

        Implements the behaviour of the listeners. First, we extract important values from the message, such as the
        Attributes dict, client id, command and filename, if proceeds.
        If the client is not in our list of clients, we don't process the message if it's an echo request (client is in
        the middle of a chat) message. Otherwise, we fulfill the client query, polling a new query so the listener which
        implements our interface can act in consequence, and remove the message from the queue.
        :param message: Received message.
        """
        attributes = message['MessageAttributes']
        client_id = attributes['Author']['StringValue']
        command = attributes['Command']['StringValue']
        filename = client_id + '.json'
        if client_id not in self._clients.keys():
            logging.info('Detected command ' + command + ' from client ' + client_id)
            if command == Command.ECHO_REQUEST.value or command == Command.CLIENT_END.value:
                self._sqs_manager.change_visibility_timeout(self._sqs_manager.get_queue_url(self.inbox_queue_name),
                                                            message)
            else:
                if command == Command.NEW_CLIENT.value:
                    self._queries.append(Query(client_id, filename, Command.NEW_CLIENT))
                elif command == Command.BEGIN_ECHO.value:
                    self._queries.append(Query(client_id, filename, Command.BEGIN_ECHO))
                elif command == Command.REMOVE_CLIENT.value:
                    self._queries.append(Query(client_id, filename, Command.REMOVE_CLIENT))
                elif command == Command.DOWNLOAD_REQUEST.value:
                    self._queries.append(Query(client_id, filename, Command.DOWNLOAD_REQUEST))
                elif command == Command.DOWNLOAD_URL_REQUEST.value:
                    self._queries.append(Query(client_id, filename, Command.DOWNLOAD_URL_REQUEST))
                self._sqs_manager.delete_message(message,
                                                 self._sqs_manager.get_queue_url(self.inbox_queue_name))
        elif client_id in self._clients.keys():
            message_body = message['Body']
            if command == Command.CLIENT_END.value:
                self._queries.append(Query(client_id, filename, Command.CLIENT_END))
                messages = ''
                for each_message in self._messages[client_id]:
                    messages += each_message + ', '
                logging.info('Client ' + client_id + 'left echo-chat. Messages to be updated to S3: ' + messages)
            elif command == Command.ECHO_REQUEST.value:
                logging.info('Echoing : ' + message_body)
                logging.info('Echoing a message with command : ' + command)
                self.send_message(message_body, 'echo', client_id)
            else:
                logging.warning('Unexpected command. Client ' + str(client_id) + ' is in client list, cmd: ' + command)

            if client_id in self._messages:
                self._messages[client_id].append(message_body)
            else:
                conversation = []
                conversation.append(message_body)
                self._messages[client_id] = conversation

            self._sqs_manager.delete_message(message, self._sqs_manager.get_queue_url(self.inbox_queue_name))

    def send_message(self, message, command, addressee=None):
        """ Sends a message, with a given content, command and (optional) addressee.

        :param message: Message content.
        :param command: Message command.
        :param addressee: Message addressee.
        """
        self._sqs_manager.send_message(self._sqs_manager.get_queue_url(self.outbox_queue_name), self._identity,
                                       message,
                                       addressee, command)

    def receive_message(self):
        """ Receives messages with addressee EchoSystem.
        """
        self._sqs_manager.receive_message(self._sqs_manager.get_queue_url(self.inbox_queue_name), 'EchoSystem')


class S3StoringInterface(Thread):
    """ Class for interfacing with the S3 service in a simple way, abstracting from the lower level operation.

    Bucket name parameter is picked from Constants class.
    A boolean is kept in memory for indicating when the bucket is ready.
    """
    _storage_ready = False
    bucket_name = Constants.BUCKET_NAME.value

    def __init__(self):
        """ Instantiates an S3 Storing Interface.

        Instantiates internally an S3Manager object.
        """
        Thread.__init__(self)
        self._s3_manager = aws_wrapper.S3Manager()

    def run(self):
        """ Runs forever, keeping the thread alive.

        First, waits for the s3 bucket to be ready. If it doesn't exist yet, it creates it, and then waits until it's
        ready. After that, it sleeps forever.
        Sleep time between loops is 500 milliseconds.
        """
        if not self._check_s3_bucket(self.bucket_name):
            self._s3_manager.create_bucket(self.bucket_name)
        self._wait_for_bucket_confirmation(self.bucket_name)
        self._storage_ready = True

        while True:
            time.sleep(0.5)

    def get_file_url(self, file_name):
        """ Gets the url for a given file in s3.

        The method queries S3 to generate a public URL for the given object.
        :param file_name: File name of the file to generate the URL for ('Key' in AWS s3)
        :return: URL if file exists, None otherwise.
        """
        for file in self._s3_manager.files:
            if file == file_name:
                struct = {'Key': file_name, 'filename': file_name}
                url = self._s3_manager.generate_url(struct)
                return url
        return None

    def upload_file_from_dict(self, query, messages):
        """ Uploads a file to S3 from a dict containing messages.

        This method creates a local file, if it doesn't exist, for holding the data. After that, S3 bucket is queried
        for the file, downloading it to the local file (Always overwriting). After the file is correctly overwritten,
        messages dict is appended to the content of the file and uploaded again to S3.
        :param query: Query parameters, holding data from the user.
        :param messages: Messages dict to be appended.
        """
        local_file_path = '/tmp/' + query.query_param
        dict_of_strings = {}
        if os.path.isfile(local_file_path):
            local_file = open(local_file_path, 'r')
        else:
            local_file = open(local_file_path, 'w+')
        if self._check_file_exists(query.query_param):
            self.download_file(query.query_param, os.path.abspath(local_file_path))
            local_file = open(local_file_path, 'r')
            file_data_json = json.loads(local_file.read())
            if query.client_id in file_data_json:
                old_json_content = file_data_json[query.client_id]
                try:
                    old_json_content.append(messages[query.client_id])
                    dict_of_strings[query.client_id] = old_json_content
                except KeyError:
                    logging.info('No new messages.')
                local_file.close()
                local_file = open(local_file_path, 'w')
            else:
                local_file.close()
                local_file = open(local_file_path, 'w')
                dict_of_strings[query.client_id] = messages[query.client_id]
        else:
            dict_of_strings[query.client_id] = messages[query.client_id]
        local_file.write(json.dumps(dict_of_strings))
        local_file.close()
        self.upload_file(local_file_path)
        # os.remove(local_file_path)

    def upload_file(self, filename, bucket=None):
        """ Uploads a file to S3 from local storage.

        :param filename: Local filesystem file path.
        :param bucket: Bucket name. Default is the one the class instance is holding.
        """
        if bucket is None:
            bucket = self.bucket_name
        file_name_r = os.path.basename(filename)
        self._s3_manager._resource.meta.client.upload_file(filename, bucket, file_name_r)

    def download_file(self, filename, local_path, bucket=None):
        """ Downloads a file form S3 to local storage.

        :param filename: File name (In S3)
        :param local_path: Local filesystem file path.
        :param bucket: Bucket name. Default is the one the class instance is holding.
        """
        if bucket is None:
            bucket = self.bucket_name
        self._s3_manager._resource.Bucket(bucket).download_file(filename, local_path)

    def remove_file(self, filename, bucket=None):
        """ Removes a file from S3.

        :param filename: Name of the file to be removed.
        :param bucket: Bucket name. Default is the one the class instance is holding.
        """
        if bucket is None:
            bucket = self.bucket_name
        response = self._s3_manager._client.delete_object(
            Bucket=bucket,
            Key=filename,
        )

    def _wait_for_bucket_confirmation(self, bucket=None):
        """ Waits for a bucket to exist.

        This method actively queries S3 for the list of buckets.
        Warning: This method will hang forever if the bucket does not exist or hasn't been queried to be created.
        :param bucket: Bucket name.
        """
        if bucket is None:
            bucket = self.bucket_name
        while True:
            for given_bucket in self._s3_manager.buckets:
                if bucket in given_bucket:
                    return True
            time.sleep(1)

    def _check_file_exists(self, file_name):
        """ Checks if a file exists.

        This method actively queries the list of objects in the bucket.
        :param file_name: File name.
        :return: True if exists, false otherwise.
        """
        for file in self._s3_manager.files:
            if file_name == file:
                return True
        return False

    def _check_s3_bucket(self, bucket_name):
        """ Checks if a bucket exists.

        This method actively queries the list of buckets to S3.
        :param bucket_name: Bucket name.
        :return: True if exists, false otherwise.
        """
        for bucket in self._s3_manager.buckets:
            if bucket_name in bucket:
                return True
        return False

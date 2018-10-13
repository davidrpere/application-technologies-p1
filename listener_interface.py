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
    inbox_queue_name = Constants.INBOX_QUEUE_NAME.value
    inbox_ready = False
    outbox_queue_name = Constants.OUTBOX_QUEUE_NAME.value
    outbox_ready = False
    _clients: Dict[int, str] = {}
    _messages: Dict = {}

    def __init__(self, sqs_manager):
        logging.info('Initialized listener interface.')
        Thread.__init__(self)
        self._identity = random.getrandbits(32)
        self._sqs_manager = sqs_manager
        self._sqs_manager.bind_to(self.received_message)
        self._queries = []


    def run(self):
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
            time.sleep(0.05)

    def received_message(self, message):
        attributes = message['MessageAttributes']
        client_id = attributes['Author']['StringValue']
        command = attributes['Command']['StringValue']
        filename = client_id + '.json'
        if client_id not in self._clients.keys():
            logging.info('Detected command ' + command + ' from client ' + client_id)
            if command == Command.ECHO_REQUEST.value:
                self._sqs_manager.change_visibility_timeout(self._sqs_manager.get_queue_url(self.inbox_queue_name),
                                                            message)
            else:
                if command == Command.NEW_CLIENT.value:
                    self._queries.append(Query(client_id, filename, Command.NEW_CLIENT))
                elif command == Command.BEGIN_ECHO.value:
                    self._clients[client_id] = filename
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
                logging.info('Client ' + client_id + ' left echo-chat.')
                self._queries.append(Query(client_id, filename, Command.CLIENT_END))
                messages = ''
                for each_message in self._messages[client_id]:
                    messages += each_message + ', '
                logging.info('Messages to be updated to S3: ' + messages)
                self._clients.pop(client_id)
            elif command == Command.DOWNLOAD_URL_REQUEST.value:
                logging.info('Client ' + client_id + ' queried a download link.')
                logging.info('TODO : Remember to remove auto update of s3 link.')
                self._sqs_manager.change_visibility_timeout(self._sqs_manager.get_queue_url(self.inbox_queue_name),
                                                            message, 5)
            else:
                logging.info('Echoing : ' + message_body)
                logging.info('Echoing a message with command : ' + command)
                self.send_message(message_body, 'echo', client_id)

            if client_id in self._messages:
                self._messages[client_id].append(message_body)
            else:
                conversation = []
                conversation.append(message_body)
                self._messages[client_id] = conversation
            self._sqs_manager.delete_message(message, self._sqs_manager.get_queue_url(self.inbox_queue_name))

    def send_message(self, message, command, addressee=None):
        self._sqs_manager.send_message(self._sqs_manager.get_queue_url(self.outbox_queue_name), self._identity,
                                       message,
                                       addressee, command)

    def receive_message(self):
        self._sqs_manager.receive_message(self._sqs_manager.get_queue_url(self.inbox_queue_name), 'EchoSystem')


class S3StoringInterface(Thread):
    _storage_ready = False
    bucket_name = Constants.BUCKET_NAME.value

    def __init__(self):
        Thread.__init__(self)
        self._s3_manager = aws_wrapper.S3Manager()

    def run(self):
        if not self._check_s3_bucket(self.bucket_name):
            self._s3_manager.create_bucket(self.bucket_name)
        self._wait_for_bucket_confirmation(self.bucket_name)
        self._storage_ready = True

        while True:
            time.sleep(0.5)

    def get_file_url(self, file_name):
        for file in self._s3_manager.files:
            if file == file_name:
                struct = {'Key': file_name, 'filename': file_name}
                url = self._s3_manager.generate_url(struct)
                return url
        return None

    def upload_file_from_dict(self, query, messages):
        local_file_path = '/tmp/' + query.query_param
        dict_of_strings = {}
        if os.path.isfile(local_file_path):
            local_file = open(local_file_path, 'r')
        else:
            local_file = open(local_file_path, 'w')
        if self._check_file_exists(query.query_param):
            self.download_file(query.query_param, os.path.abspath(local_file_path))
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

    def upload_file(self, filename, bucket=None):
        if bucket is None:
            bucket = self.bucket_name
        file_name_r = os.path.basename(filename)
        self._s3_manager._resource.meta.client.upload_file(filename, bucket, file_name_r)

    def download_file(self, filename, local_path, bucket=None):
        if bucket is None:
            bucket = self.bucket_name
        self._s3_manager._resource.Bucket(bucket).download_file(filename, local_path)

    def remove_file(self, filename, bucket=None):
        if bucket is None:
            bucket = self.bucket_name
        response = self._s3_manager._client.delete_object(
            Bucket=bucket,
            Key=filename,
        )

    def _wait_for_bucket_confirmation(self, bucket=None):
        if bucket is None:
            bucket = self.bucket_name
        while True:
            for given_bucket in self._s3_manager.buckets:
                if bucket in given_bucket:
                    return True
            time.sleep(1)

    def _check_file_exists(self, file_name):
        for file in self._s3_manager.files:
            if file_name == file:
                return True
        return False

    def _check_s3_bucket(self, bucket_name):
        for bucket in self._s3_manager.buckets:
            if bucket_name in bucket:
                return True
        return False

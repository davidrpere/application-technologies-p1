import aws_wrapper
import random
from threading import Thread
from typing import Dict
from utils import Query, QueryFlag
import time
import os
import json


class SqsListenerInterface(Thread):
    inbox_queue_name = 'Inbox'
    inbox_ready = False
    outbox_queue_name = 'Outbox'
    outbox_ready = False
    _clients: Dict[int, str] = {}
    _messages: Dict = {}

    def __init__(self):
        Thread.__init__(self)
        self._identity = random.getrandbits(32)
        self._sqs_manager = aws_wrapper.SqsManager()
        self._queries = []

    def run(self):
        # TODO Get these parameters from configuration file.
        if not self._sqs_manager._check_sqs_queues(self.inbox_queue_name):
            self._sqs_manager.create_queue(self.inbox_queue_name)
        if not self._sqs_manager._check_sqs_queues(self.outbox_queue_name):
            self._sqs_manager.create_queue(self.outbox_queue_name)
        self._sqs_manager._wait_for_queue_confirmation(self.inbox_queue_name)
        self.inbox_ready = True
        self._sqs_manager._wait_for_queue_confirmation(self.outbox_queue_name)
        self.outbox_ready = True

        while True:
            received_messages = self.receive_message()
            if received_messages:
                for received_message in received_messages:
                    self._process_message_content(received_message)

    def _process_message_content(self, received_message):
        attributes = received_message['MessageAttributes']
        client_id = attributes['Author']['StringValue']
        command = attributes['Command']['StringValue']
        filename = client_id + '.json'
        if command == 'new-client':
            print('Detected new client.')
            self._clients[client_id] = filename
            self._queries.append(Query(client_id, filename, QueryFlag.Create_Files))
            self._sqs_manager.delete_message(received_message, self._sqs_manager.get_queue_url(self.inbox_queue_name))
        elif client_id in self._clients.keys():
            if command == 'client-end':
                print('Client left the chat, but not the session.')
                self._queries.append(Query(client_id, filename, QueryFlag.Update_Files))
                print(self._messages)
            elif command == 'client-left':
                print('Client closed the connection.')
                self._queries.append(Query(client_id, filename, QueryFlag.Remove_Files))
            elif command == 'download-query':
                print('Client queried conversations.')
                self._queries.append(Query(client_id, filename, QueryFlag.Download_Files))
            else:
                print('Echoing : ', received_message['Body'])
                self.send_message(received_message['Body'], 'echo', received_message['MessageAttributes']['Author'])
            author = attributes['Author']['StringValue']
            if author in self._messages:
                self._messages[author].append(received_message['Body'])
            else:
                conversation = []
                conversation.append(received_message['Body'])
                self._messages[author] = conversation
            self._sqs_manager.delete_message(received_message, self._sqs_manager.get_queue_url(self.inbox_queue_name))
        else:
            self._sqs_manager.change_visibility_timeout(self._sqs_manager.get_queue_url(self.inbox_queue_name),
                                                        received_message)

    def send_message(self, message, command, addressee=None):
        self._sqs_manager._send_message(self._sqs_manager.get_queue_url(self.outbox_queue_name), self._identity,
                                        message,
                                        addressee, command)

    def receive_message(self):
        return self._sqs_manager._receive_message(self._sqs_manager.get_queue_url(self.inbox_queue_name), 'EchoSystem')


class S3StoringInterface(Thread):
    _storage_ready = False
    bucket_name = 'ta-assignment-1'

    def __init__(self):
        Thread.__init__(self)
        self._s3_manager = aws_wrapper.S3Manager()

    def run(self):
        # TODO Get these parameters from configuration file.
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
                old_json_content.append(messages[query.client_id])
                dict_of_strings[query.client_id] = old_json_content
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
        print('Asked to download a file.')
        self._s3_manager._resource.Bucket(bucket).download_file(filename, local_path)

    def remove_file(self, filename, bucket=None):
        if bucket is None:
            bucket = self.bucket_name
        print('Asked to remove a file.')
        response = self._s3_manager._client.delete_object(
            Bucket=bucket,
            Key=filename,
        )
        print(response)

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

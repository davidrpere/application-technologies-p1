import time
from typing import Dict, Any
import aws_wrapper
import random
from threading import Thread
import os
from enum import Enum


class S3StoringInterface(Thread):
    _storage_ready = False

    def __init__(self):
        print('Hello, S3 storing interface')
        Thread.__init__(self)
        self._s3_manager = aws_wrapper.S3Manager()

    def run(self):
        # TODO Get these parameters from configuration file.
        print('S3 interface run method.')
        if not self._check_s3_bucket('ta-assignment-1'):
            self._s3_manager.create_bucket('ta-assignment-1')
        self._wait_for_bucket_confirmation('ta-assignment-1')
        self._storage_ready = True

        while True:
            time.sleep(5)

    def upload_file(self, filename, bucket='ta-assignment-1'):
        print('Asked to upload a file.')
        file_name_r = os.path.basename(filename)
        self._s3_manager._resource.meta.client.upload_file(filename, bucket, file_name_r)

    def download_file(self, filename, local_path, bucket='ta-assignment-1'):
        print('Asked to download a file.')
        self._s3_manager._resource.Bucket(bucket).download_file(filename, local_path)

    def remove_file(self, filename, bucket='ta-assignment-1'):
        print('Asked to remove a file.')
        response = self._s3_manager._client.delete_object(
            Bucket=bucket,
            Key=filename,
        )
        print(response)

    def _wait_for_bucket_confirmation(self, bucket_name):
        while True:
            for bucket in self._s3_manager.buckets:
                if bucket_name in bucket:
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


class SqsMessagingInterface(Thread):
    _outbox_ready = False
    _inbox_ready = False
    _clients: Dict[int, str] = {}
    _messages: Dict = {}

    def __init__(self, role):
        print('Hello, Messaging interface')
        Thread.__init__(self)
        self._identity = random.getrandbits(32)
        self._sqs_manager = aws_wrapper.SqsManager()
        self._role = role
        if self._role == 'EchoSystem':
            self._queries = []
        
    def run(self):
        # TODO Get these parameters from configuration file.
        if not self._sqs_manager._check_sqs_queues('Inbox'):
            self._sqs_manager.create_queue('Inbox')
        if not self._sqs_manager._check_sqs_queues('Outbox'):
            self._sqs_manager.create_queue('Outbox')
        self._sqs_manager._wait_for_queue_confirmation('Inbox')
        self._inbox_ready = True
        self._sqs_manager._wait_for_queue_confirmation('Outbox')
        self._outbox_ready = True

        if self._role == 'Client':
            self._begin_connection()

        while True:
            received_messages = self.receive_message()
            if received_messages:
                for received_message in received_messages:
                    if self._role == 'EchoSystem':
                        self._process_message_content(received_message)
                    elif self._role == 'Client':
                        print('\nEcho says... >>', received_message['Body'])

    def _begin_connection(self):
        print('Starting connection from messaging interface...')
        self._sqs_manager._send_message(self._sqs_manager.get_queue_url('Inbox'), self._identity, self._identity,
                                        'EchoSystem', 'new-client')

    def end_connection(self):
        print('Ending connection from messaging interface...')
        self._sqs_manager._send_message(self._sqs_manager.get_queue_url('Inbox'), self._identity, self._identity,
                                        'EchoSystem', 'client-left')

    def _process_message_content(self, received_message):
        # TODO fix
        # print(received_message)
        # print(received_message['MessageAttributes']['Command'])
        attributes = received_message['MessageAttributes']
        client_id = attributes['Author']['StringValue']
        filename = client_id + '.json'
        if received_message['MessageAttributes']['Command']['StringValue'] == 'new-client':
            print('Detected new client.')
            self._clients[client_id] = filename
            self._queries.append(Query(client_id, filename, QueryFlag.Create_Files))
        elif received_message['MessageAttributes']['Command']['StringValue'] == 'client-end':
            # TODO save chat to S3
            print('Client left the chat, but not the session.')
            self._queries.append(Query(client_id, filename, QueryFlag.Update_Files))
            print(self._messages)
        elif received_message['MessageAttributes']['Command']['StringValue'] == 'client-left':
            # TODO delete file from S3
            print('Client closed the connection.')
            self._queries.append(Query(client_id, filename, QueryFlag.Remove_Files))
        else:
            print('Echoing : ', received_message['Body'])
            self.send_message(received_message['Body'], received_message['MessageAttributes']['Author'])
        author = attributes['Author']['StringValue']
        if author in self._messages:
            self._messages[author].append(received_message['Body'])
        else:
            conversation = []
            conversation.append(received_message['Body'])
            self._messages[author] = conversation

    def send_message(self, message, addressee=None):
        if self._role == 'EchoSystem':
            self._sqs_manager._send_message(self._sqs_manager.get_queue_url('Outbox'), self._identity, message,
                                            addressee)
        elif self._role == 'Client':
            if message == 'END':
                self._sqs_manager._send_message(self._sqs_manager.get_queue_url('Inbox'), self._identity, message,
                                                'EchoSystem', 'client-end')
            else:
                self._sqs_manager._send_message(self._sqs_manager.get_queue_url('Inbox'), self._identity, message,
                                                'EchoSystem')

    def receive_message(self):
        if self._role == 'EchoSystem':
            return self._sqs_manager._receive_message(self._sqs_manager.get_queue_url('Inbox'), 'EchoSystem')
        elif self._role == 'Client':
            return self._sqs_manager._receive_message(self._sqs_manager.get_queue_url('Outbox'), self._identity)


class QueryFlag(Enum):
    Download_Files = 8
    Remove_Files = 4
    Create_Files = 2
    Update_Files = 1


class Query:

    def __init__(self, client, filename, query_type):
        self.client_id = client
        self.query_type = QueryFlag(query_type)
        self.query_param = filename
        

class MessageAttributes(object):
    # TODO left on purpose. Might want to overload more parameters in the future.
    def __init__(self, author, addressee, cmd=None):
        self._message_attributes = {
            'Author': {
                'DataType': 'String',
                'StringValue': str(author)
            },
            'Addressee': {
                'DataType': 'String',
                'StringValue': str(addressee)
            },
            'Command': {
                'DataType': 'String',
                'StringValue': str(cmd)
            }
        }


class BucketAttributes(object):
    _acl = 'public-read-write'
    _bucket = 'ta-assignment-1'
    _location_constraint = {'LocationConstraint': 'eu-west-3'}
    _grant_full_control = 'yes'
    _grant_read = 'yes'
    _grant_read_acp = 'yes'
    _grant_write = 'yes'
    _grant_write_acp = 'yes'

    def __init__(self, acl=None, bucket=None, location_constraint=None, grant_full_control=None,
                 grant_read=None, grant_read_acp=None, grant_write=None, grant_write_acp=None):
        if acl is not None:
            self._acl = acl
        if bucket is not None:
            self._bucket = bucket
        if location_constraint is not None:
            self._location_constraint = location_constraint
        if grant_full_control is not None:
            self._grant_full_control = grant_full_control
        if grant_read is not None:
            self._grant_read = grant_read
        if grant_read_acp is not None:
            self._grant_read_acp = grant_read_acp
        if grant_write is not None:
            self._grant_write = grant_write
        if grant_write_acp is not None:
            self._grant_write_acp = grant_write_acp

    def get_dictionary(self):
        default_params = {
            'ACL': self._acl,
            'Bucket': self._bucket,
            'CreateBucketConfiguration': {
                self._location_constraint
            },
            'GrantFullControl': self._grant_full_control,
            'GrantRead': self._grant_read,
            'GrantReadACP': self._grant_read_acp,
            'GrantWrite': self._grant_write,
            'GrantWriteACP': self._grant_write_acp
        }
        return default_params


class QueueAttributes(object):
    _delay_seconds = '0'
    _message_retention_period = '345600'
    _maximum_message_size = '262144'
    _receive_message_wait_time_seconds = '0'
    _visibility_timeout = '0'

    def __init__(self, delay_seconds=None, message_retention_period=None, maximum_message_size=None,
                 receive_message_wait_time_seconds=None, visibility_timeout=None):
        if delay_seconds is not None:
            self._delay_seconds = delay_seconds
        if message_retention_period is not None:
            self._message_retention_period = message_retention_period
        if maximum_message_size is not None:
            self._maximum_message_size = maximum_message_size
        if receive_message_wait_time_seconds is not None:
            self._receive_message_wait_time_seconds = receive_message_wait_time_seconds
        if visibility_timeout is not None:
            self._visibility_timeout = visibility_timeout

    def get_dictionary(self):
        default_params = {'DelaySeconds': self._delay_seconds,
                          'MaximumMessageSize': self._maximum_message_size,
                          'MessageRetentionPeriod': self._message_retention_period,
                          'ReceiveMessageWaitTimeSeconds': self._receive_message_wait_time_seconds,
                          'VisibilityTimeout': self._visibility_timeout}
        return default_params


def main():
    print('Performing unit test for utils.py')
    s3_storing_interface = S3StoringInterface()
    # response = s3_storing_interface._check_file_exists('test-file')
    # print(response)
    # for keys in response['Contents']:
    #     print(keys)
    #     print('---')

    if s3_storing_interface._check_file_exists('gracias_jeff.txt') is True:
        s3_storing_interface._s3_manager.remove_file('gracias_jeff.txt')
    else:
        s3_storing_interface._s3_manager.upload_file('/home/drodriguez/Desktop/gracias_jeff.txt')
    print(s3_storing_interface._check_file_exists('gracias_tim.txt'))
    s3_storing_interface._s3_manager.download_file('gracias_tim.txt', '/home/drodriguez/Desktop/gracias_jonny.txt')
    print(s3_storing_interface._check_file_exists('gracias_marques.txt'))


if __name__ == '__main__':
    main()

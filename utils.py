import time
from typing import Dict, Any

import aws_wrapper
import random
from threading import Thread
import os

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

    def __init__(self, role):
        print('Hello, Messaging interface')
        Thread.__init__(self)
        self._identity = random.getrandbits(32)
        self._sqs_manager = aws_wrapper.SqsManager()
        self._role = role

    def run(self):
        # TODO Get these parameters from configuration file.
        if not self._check_sqs_queues('Inbox'):
            self._sqs_manager.create_queue('Inbox')
        if not self._check_sqs_queues('Outbox'):
            self._sqs_manager.create_queue('Outbox')
        self._wait_for_queue_confirmation('Inbox')
        self._inbox_ready = True
        self._wait_for_queue_confirmation('Outbox')
        self._outbox_ready = True

        if self._role == 'Client':
            self._sqs_manager._send_message(self._sqs_manager.get_queue_url('Inbox'), self._identity, self._identity,
                                            'EchoSystem', 'new-client')

        while True:
            received_messages = self.receive_message()
            if received_messages:
                for received_message in received_messages:
                    if self._role == 'EchoSystem':
                        print('Echoing : ', received_message['Body'])
                        self._process_message_content(received_message)
                    elif self._role == 'Client':
                        print('\nEcho says... >>', received_message['Body'])

    def _process_message_content(self, received_message):
        # TODO fix
        print(received_message)
        print(received_message['MessageAttributes']['Command'])
        attributes = received_message['MessageAttributes']
        if received_message['MessageAttributes']['Command']['StringValue'] == 'new-client':
            print('Detected new client.')
            self._clients[attributes['Author']['StringValue']] = attributes['Author']['StringValue'] + '.yaml'
            # TODO guardamos este pequeño DICT en disco en S3.

        else:
            self.send_message(received_message['Body'], received_message['MessageAttributes']['Author'])

    def send_message(self, message, addressee=None):
        if self._role == 'EchoSystem':
            self._sqs_manager._send_message(self._sqs_manager.get_queue_url('Outbox'), self._identity, message,
                                            addressee)
        elif self._role == 'Client':
            self._sqs_manager._send_message(self._sqs_manager.get_queue_url('Inbox'), self._identity, message,
                                            'EchoSystem')

    def receive_message(self):
        if self._role == 'EchoSystem':
            return self._sqs_manager._receive_message(self._sqs_manager.get_queue_url('Inbox'), 'EchoSystem')
        elif self._role == 'Client':
            return self._sqs_manager._receive_message(self._sqs_manager.get_queue_url('Outbox'), self._identity)

    def _wait_for_queue_confirmation(self, queue_name):
        while True:
            for queue in self._sqs_manager.queues:
                if queue_name in queue:
                    return True
            time.sleep(1)

    def _check_sqs_queues(self, queue_name):
        for queue in self._sqs_manager.queues:
            if queue_name in queue:
                return True
        return False


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

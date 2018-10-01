import time
import aws_wrapper
import random
from threading import Thread


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

    def _check_s3_bucket(self, bucket_name):
        for bucket in self._s3_manager.buckets:
            if bucket_name in bucket:
                return True
        return False


class SqsMessagingInterface(Thread):
    _outbox_ready = False
    _inbox_ready = False
    _conversations = []

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

        while True:
            received_messages = self.receive_message()
            if received_messages:
                for received_message in received_messages:
                    if self._role == 'EchoSystem':
                        print('Echoing : ', received_message['Body'])
                        self._process_message_content(received_message)
                        self.send_message(received_message['Body'], received_message['Author'])
                    elif self._role == 'Client':
                        print('\nEcho says... >>', received_message['Body'])


    def _process_message_content(self, received_message):
        if received_message['Command'] == 'NEW_USER':
            self._conversations.append()

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
    def __init__(self, author, addressee):
        self._message_attributes = {
            'Author': {
                'DataType': 'String',
                'StringValue': str(author)
            },
            'Addressee': {
                'DataType': 'String',
                'StringValue': str(addressee)
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

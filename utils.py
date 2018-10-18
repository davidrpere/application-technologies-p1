import os
import time
import aws_wrapper
import logging
import botocore
from enum import Enum
from threading import Thread


class S3StoringInterface(Thread):
    """Class for interfacing the interaction with Amazon Simple Storage Service.

    Default bucket name is hardcoded.
    """
    _storage_ready = False
    BUCKET_NAME = 'ta-assignment-1'

    def __init__(self, bucket_name):
        """Instantiates a S3 Storing interface object.
        """
        if bucket_name is not None:
            self.BUCKET_NAME = bucket_name
        Thread.__init__(self)
        self._s3_manager = aws_wrapper.S3Manager()

    def run(self):
        """Checks for the configured bucket to exist and runs forever doing nothing.
        """
        if not self._check_s3_bucket(self.BUCKET_NAME):
            self._s3_manager.create_bucket(self.BUCKET_NAME)
        self._wait_for_bucket_confirmation(self.BUCKET_NAME)
        self._storage_ready = True

        while True:
            time.sleep(5)

    def upload_file(self, filename, bucket=None):
        """Uploads the specified local file to the default S3 bucket.

        If desired, another bucket can be specified.
        """
        if bucket is None:
            bucket = self.BUCKET_NAME
        file_name_r = os.path.basename(filename)
        self._s3_manager._resource.meta.client.upload_file(filename, bucket, file_name_r)

    def download_file(self, filename, local_path, bucket=None):
        """Downloads the specified file from the default S3 bucket to the local path.

        If desired, another bucket can be specified.
        """
        if bucket is None:
            bucket = self.BUCKET_NAME
        try:
            self._s3_manager._resource.Bucket(bucket).download_file(filename, local_path)
        except botocore.exceptions.ClientError as e:
            if e.response['Error']['Code'] == "404":
                logging.info('Tried to download file ' + filename + ' from bucket ' + bucket + ', file does not exist.')
            else:
                raise

    def remove_file(self, filename, bucket=None):
        """Removes the specified file from the default bucket. If it doesn't exist, it does nothing.

        If desired, another bucket can be specified.
        """
        if bucket is None:
            bucket = self.BUCKET_NAME
        response = self._s3_manager._client.delete_object(
            Bucket=bucket,
            Key=filename,
        )
        logging.info('Tried to delete file ' + filename + ' from bucket ' + bucket + ', response: ' + response)

    def _wait_for_bucket_confirmation(self, bucket_name):
        """Waits until the specified bucket exists.

        This method effectively queries the S3 bucket list.
        """
        while True:
            for bucket in self._s3_manager.buckets:
                if bucket_name in bucket:
                    return True
            time.sleep(1)

    def _check_file_exists(self, file_name):
        """Returns true if the specified file exists, false otherwise.

        This method effectively queries the S3 keys list.
        """
        for file in self._s3_manager.files:
            if file_name == file:
                return True
        return False

    def _check_s3_bucket(self, bucket_name):
        """Returns true if the specified bucket exists, false otherwhise.

        This method effectively queries the S3 bucket list.
        """
        for bucket in self._s3_manager.buckets:
            if bucket_name in bucket:
                return True
        return False


class Constants(Enum):
    """Class holding the default values for the EchoSystem.
    """
    INBOX_QUEUE_NAME = 'Inbox'
    OUTBOX_QUEUE_NAME = 'Outbox'
    ECHOSYSTEM_ID = 'EchoSystem'
    HELLO_BODY = 'Started session.'
    BUCKET_NAME = 'ta-assignment-1'
    REGION = 'eu-west-3'

    def __str__(self):
        """Returns the string value of the member variable.
        """
        return str(self.value)


class Command(Enum):
    """Class holding the default values for the EchoSystem commands.
    """
    BEGIN_ECHO = 'begin-chat'
    ECHO_REPLY = 'echo'
    ECHO_REQUEST = 'echo-request'
    DOWNLOAD_REQUEST = 'download-query'
    DOWNLOAD_REPLY = 'download-reply'
    DOWNLOAD_URL_REQUEST = 'download-url-query'
    DOWNLOAD_URL_REPLY = 'download-url-reply'
    REMOVE_CLIENT = 'client-left'
    NEW_CLIENT = 'new-client'
    CLIENT_END = 'client-end'

    def __str__(self):
        """Returns the string value of the member variable.
        """
        return str(self.value)


class Query:
    """Class representing a Query, issued from interfaces to client applications.
    """

    def __init__(self, client, filename, command_type):
        """Instantiates the Query element, specified by the client, filename and command type.
        """
        self.client_id = client
        self.query_type = Command(command_type)
        self.query_param = filename
        

class MessageAttributes(object):
    """Class holding the default message attributes composition.
    """
    def __init__(self, author, addressee, cmd=None):
        """Instantiates a 'MessageAttributes' element for a SQS Message with the specified parameters.

        Command is empty by default.
        """
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
    """Class holding the default attributes for creating a bucket.

    Values are hardcoded for our purpose.
    """
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
        """Instantiates attributes for a S3 Bucket.

        If any value is not specified, default value is used.
        """
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
        """Returns the dictionary element for the bucket element.
        """
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
    """Class holding the attributes for a SQS Queue.

    Default values are hardcoded for our purpose.
    """
    _delay_seconds = '0'
    _message_retention_period = '345600'
    _maximum_message_size = '262144'
    _receive_message_wait_time_seconds = '20'
    _visibility_timeout = '0'

    def __init__(self, delay_seconds=None, message_retention_period=None, maximum_message_size=None,
                 receive_message_wait_time_seconds=None, visibility_timeout=None):
        """Instantiates attributes for a SQS Queue.

        If any value is not specified, default value is used.
        """
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
        """Returns the dictionary element for the queue element.
        """
        default_params = {'DelaySeconds': self._delay_seconds,
                          'MaximumMessageSize': self._maximum_message_size,
                          'MessageRetentionPeriod': self._message_retention_period,
                          'ReceiveMessageWaitTimeSeconds': self._receive_message_wait_time_seconds,
                          'VisibilityTimeout': self._visibility_timeout}
        return default_params


def main():
    """Mock main method for testing the behaviour of the class implementation.
    """
    print('Performing unit test for utils.py')
    s3_storing_interface = S3StoringInterface()

    if s3_storing_interface._check_file_exists('gracias_jeff.txt') is True:
        s3_storing_interface._s3_manager.remove_file('gracias_jeff.txt')
    else:
        s3_storing_interface._s3_manager.upload_file('/home/drodriguez/Desktop/gracias_jeff.txt')
    print(s3_storing_interface._check_file_exists('gracias_tim.txt'))
    s3_storing_interface._s3_manager.download_file('gracias_tim.txt', '/home/drodriguez/Desktop/gracias_jonny.txt')
    print(s3_storing_interface._check_file_exists('gracias_marques.txt'))


if __name__ == '__main__':
    main()

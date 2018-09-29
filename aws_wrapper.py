import time
import boto3
import utils


class AwsWrapper(object):
    def __init__(self, boto3Type):
        self._session = boto3.session.Session()
        self._client = self._session.client(boto3Type)
        self._resource = self._session.resource(boto3Type)


class Ec2Manager(AwsWrapper):
    def __init__(self):
        print('Hello, ec2 manager')
        AwsWrapper.__init__(self, 'ec2')


class S3Manager(AwsWrapper):
    def __init__(self):
        print('Hello, s3 manager')
        AwsWrapper.__init__(self, 's3')
        self.buckets = self._client.list_buckets()

    def create_bucket(self, bucket_name):
        self._client.create_bucket(Bucket=bucket_name)

    def remove_bucket(self, bucket_name):
        if bucket_name in self._buckets:
            bucket = self._resource.Bucket(bucket_name)
            for key in bucket.objects.all():
                key.delete()
            bucket.delete()
            return True
        else:
            return False

    def buckets_to_array(self):
        return [bucket for bucket in (self.buckets or [])]

    @property
    def buckets(self):
        self.buckets = self._client.list_buckets()
        return self._buckets

    @buckets.setter
    def buckets(self, value):
        try:
            self._buckets = [bucket['Name'] for bucket in value['Buckets']]
        except KeyError:
            self._buckets = []


class SqsManager(AwsWrapper):
    def __init__(self):
        print('Hello, sqs manager')
        # utils.check_global_variables()
        AwsWrapper.__init__(self, 'sqs')
        self.queues = self._client.list_queues()

    def create_queue(self, queue_name, queue_attributes=None):
        if not queue_attributes:
            dictionary_attributes = QueueAttributes().get_dictionary()
            request_params = {
                'QueueName': queue_name,
                'Attributes': dictionary_attributes
            }
            queue = self._client.create_queue(**request_params)
            print('Created queue: ', queue)
        else:
            dictionary_attributes = queue_attributes.get_dictionary()
            self._client.create_queue(queue_name, dictionary_attributes)
        self.queues = self._client.list_queues()

    def remove_queue(self, queue_url):
        if queue_url in self._queues:
            response = self._client.delete_queue(
                QueueUrl=queue_url
            )
            return True
        else:
            return False

    def queues_to_array(self):
        return [queue for queue in (self.queues or [])]

    @property
    def queues(self):
        self.queues = self._client.list_queues()
        return self._queues

    @queues.setter
    def queues(self, value):
        try:
            self._queues = value['QueueUrls']
        except KeyError:
            self._queues = []


class QueueAttributes(object):
    _delay_seconds = '0'
    _message_retention_period = '345600'
    _maximum_message_size = '262144'
    _receive_message_wait_time_seconds = '0'
    _visibility_timeout = '12'

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


def test_sqs():
    print('Main test unit for the sqs-manager.')
    print('Testing class instantiation.')
    manager = SqsManager()  # role

    print(manager.queues_to_array())

    time.sleep(5)

    print('testing queue creation')
    manager.create_queue('Inbox')
    manager.create_queue('Outbox')

    time.sleep(60)
    print(manager.queues_to_array())

    queues = manager.queues_to_array()
    if queues:
        for queue in queues:
            manager.remove_queue(queue)

    time.sleep(5)
    print(manager.queues_to_array())


def test_s3():
    print('Main test unit for the s3-manager')
    # TODO implement s3 unit tests.


def main():
    print('Performing unit tests for Amazon Web Services Wrappers.')
    test_sqs()
    test_s3()


if __name__ == '__main__':
    main()
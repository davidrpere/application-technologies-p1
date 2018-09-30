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

    def upload_file(self, filename):
        print('Asked to upload a file.')

    def download_file(self, filename):
        print('Asked to download a file.')


    def create_bucket(self, bucket_name):
        # parameters = utils.BucketAttributes(None, 'ta-assignment-p1').get_dictionary()
        self._client.create_bucket(
            ACL='public-read-write',
            Bucket=bucket_name,
            CreateBucketConfiguration={
                'LocationConstraint': 'eu-west-3'
            }
        )
        # self._client.create_bucket(parameters)
        # self._client.create_bucket(Bucket=bucket_name)

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
        AwsWrapper.__init__(self, 'sqs')
        self.queues = self._client.list_queues()

    def _send_message(self, queue, author, message_body, addressee=None):
        attributes = utils.MessageAttributes(author, addressee)._message_attributes
        response = self._client.send_message(
            QueueUrl=queue,
            DelaySeconds=0,
            MessageAttributes=attributes,
            MessageBody=(
                message_body
            )
        )

    def _receive_message(self, queue, addressee=None):
        response = self._client.receive_message(
            QueueUrl=queue,
            MaxNumberOfMessages=1,
            MessageAttributeNames=[
                'All'
            ],
            VisibilityTimeout=0,
            WaitTimeSeconds=0
        )
        messages = []
        try:
            for message in response['Messages']:
                message_addressee = message['MessageAttributes']['Addressee']['StringValue']
                message_author = message['MessageAttributes']['Author']['StringValue']
                message_body = message['Body']
                if str(addressee) in message_addressee:
                    compound = {'Author': message_author, 'Addressee': message_addressee, 'Body': message_body}
                    messages.append(compound)
                    self._client.delete_message(
                        QueueUrl=queue,
                        ReceiptHandle=message['ReceiptHandle']
                    )
        except KeyError:
            time.sleep(0.1)
        return messages

    def create_queue(self, queue_name, queue_attributes=None):
        if not queue_attributes:
            dictionary_attributes = utils.QueueAttributes().get_dictionary()
            request_params = {
                'QueueName': queue_name,
                'Attributes': dictionary_attributes
            }
            queue_created = False
            while not queue_created:
                try:
                    queue = self._client.create_queue(**request_params)
                    queue_created = True
                except self._client.exceptions.QueueDeletedRecently:
                    print('Can\'t create queue yet. AWS won\'t let create it.')
                    time.sleep(10)
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

    def get_queue_url(self, substring):
        for queue in self.queues:
            if substring in queue:
                return queue
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

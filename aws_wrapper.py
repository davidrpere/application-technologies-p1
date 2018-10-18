import time
import boto3
import utils
import logging


class AwsWrapper(object):
    """Class for instantiating an AWS Wrapper.

    Type of resource must be specified. If not supported, raises ValueError.
    """

    def __init__(self, boto3type):
        if boto3type is not 'ec2' and not 's3' and not 'sqs':
            logging.error('Resource type not supported.')
            raise ValueError
        else:
            self._session = boto3.session.Session()
            self._client = self._session.client(boto3type)
            self._resource = self._session.resource(boto3type)


class Ec2Manager(AwsWrapper):
    """Class for instantiating an EC2 wrapper manager.
    """
    def __init__(self):
        """Instantiates parent class as ec2 resource.
        """
        AwsWrapper.__init__(self, 'ec2')


class S3Manager(AwsWrapper):
    """Class for instantiating an S3 wrapper manager.
    """
    def __init__(self):
        """Instantiates parent class as s3 resource and lists the available buckets.
        """
        AwsWrapper.__init__(self, 's3')
        self.buckets = self._client.list_buckets()

    def generate_url(self, file):
        """Generates a public download url for the specified file.
        """
        return self._client.generate_presigned_url(
            "get_object",
            Params={
                "Bucket": utils.Constants.BUCKET_NAME.value,
                "Key": file["Key"],
                "ResponseContentDisposition": "attachment; filename=" + file["filename"]
            })

    def create_bucket(self, bucket_name):
        """Creates an S3 bucket with the specified name.

        Region availability is picked from utils.Constants.REGION
        :param bucket_name: Name of the bucket to be created.
        :return: Empty.
        """
        self._client.create_bucket(
            ACL='public-read-write',
            Bucket=bucket_name,
            CreateBucketConfiguration={
                'LocationConstraint': utils.Constants.REGION.value
            }
        )

    def remove_bucket(self, bucket_name):
        """Removes a bucket from S3.

        :param bucket_name: Name of the bucket to be removed.
        :return: True on success, false if bucket is not listed.
        """
        if bucket_name in self._buckets:
            bucket = self._resource.Bucket(bucket_name)
            for key in bucket.objects.all():
                key.delete()
            bucket.delete()
            return True
        else:
            return False

    def buckets_to_array(self):
        """ Returns bucket list as an array.

        :return: Bucket list as an array.
        """
        return [bucket for bucket in (self.buckets or [])]

    def list_files(self):
        """ Lists files in the bucket specified in utils.Constants.BUCKET_NAME

        :return: List of files (Keys).
        """
        return self._client.list_objects(
            Bucket=utils.Constants.BUCKET_NAME.value
        )

    @property
    def files(self):
        """ Property corresponding to the actual files in the bucket specified in utils.Constants.BUCKET_NAME

        File list is queried and assigned to property files.
        :return: Private variable _files.
        """
        self.files = self._client.list_objects(
            Bucket=utils.Constants.BUCKET_NAME.value
        )
        return self._files

    @files.setter
    def files(self, value):
        """ Property setter for the files.

        Parses the AWS response and keeps the 'Key' parameter for each element.
        :param value: AWS response from list_objects
        :return: Array holding file names.
        """
        try:
            self._files = [entry['Key'] for entry in value['Contents']]
        except KeyError:
            self._files = []

    @property
    def buckets(self):
        """ Property corresponding to the actual buckets in the account and availability region specified.

        Bucket list is queried and assigned to the property buckets.
        :return: Private variable _buckets.
        """
        self.buckets = self._client.list_buckets()
        return self._buckets

    @buckets.setter
    def buckets(self, value):
        """ Property setter for the buckets.

        :param value: AWS response to list_buckets.
        :return: Array holding the property 'Name' of every bucket.
        """
        try:
            self._buckets = [bucket['Name'] for bucket in value['Buckets']]
        except KeyError:
            self._buckets = []


class SqsManager(AwsWrapper):
    """ Class for instantiating an SQS wrapper manager.
    """
    def __init__(self):
        """Instantiates parent class as a sqs resource and lists the available queues.
        """
        AwsWrapper.__init__(self, 'sqs')
        self.queues = self._client.list_queues()
        self._observers = []

    def bind_to(self, callback):
        """Binds the parameter function as a callback for the _observers variable.

        For more information on this, check the "Observer design pattern" for programming.
        :param callback: Function to bind as a callback.
        """
        self._observers.append(callback)

    def send_message(self, queue, author, message_body, addressee=None, cmd=None):
        """ Sends a message to an SQS queue.

        :param queue: Queue to send the message to.
        :param author: Author for the MessageAttributes parameters dict.
        :param message_body: Message body.
        :param addressee: Addressee to send the message to.
        :param cmd: Command, if it's a protocol message.
        """
        attributes = utils.MessageAttributes(author, addressee, cmd)._message_attributes
        response = self._client.send_message(
            QueueUrl=queue,
            DelaySeconds=0,
            MessageAttributes=attributes,
            MessageBody=(
                str(message_body)
            )
        )
        logging.debug(response)

    def receive_message(self, queue, addressee=None):
        """ Polls the queue for messages.

        Long polling is enabled, meaning that if there are no messages, return time is 10s.
        If messages are found for the specified addressee, callback functions are called for
        every observer specified by method bind_to(), and the message element is sent.

        If any message is found for any other addresse, it's put back in the queue inmediately.
        If KeyError is raised when polling messages, we return.
        :param queue: Queue to poll.
        :param addressee: Addressee to filter messages.
        """
        response = self._client.receive_message(
            QueueUrl=queue,
            MaxNumberOfMessages=10,
            AttributeNames=[
                'All'
            ],
            MessageAttributeNames=[
                'All'
            ],
            VisibilityTimeout=10,
            WaitTimeSeconds=20
        )
        try:
            sorted_messages = sorted(response['Messages'], key=lambda k: k['Attributes']['SentTimestamp'])
            for message in sorted_messages:
                message_addressee = message['MessageAttributes']['Addressee']['StringValue']
                logging.info('Message Timestamp is ' + message['Attributes']['SentTimestamp'])
                if str(addressee) in message_addressee:
                    for callback in self._observers:
                        callback(message)
                else:
                    self.change_visibility_timeout(queue, message)
        except KeyError:
            time.sleep(0.1)

    def change_visibility_timeout(self, queue_url, message, visibility_timeout=0):
        """ Changes the visibility timeout for a message.

        Useful if we want to put back in the queue a message with an specific timeout. Default is 0.
        :param queue_url: Queue to put the message back in.
        :param message: Message element. ReceiptHandle is used.
        :param visibility_timeout: Visibility timeout. Default is 0.
        """
        self._client.change_message_visibility(
            QueueUrl=queue_url,
            ReceiptHandle=message['ReceiptHandle'],
            VisibilityTimeout=visibility_timeout
        )

    def delete_message(self, message, queue_url):
        """ Removes a message from the queue.

        :param message: Message to be removed. ReceiptHandle is used.
        :param queue_url: Queue to remove the message from.
        """
        self._client.delete_message(
            QueueUrl=queue_url,
            ReceiptHandle=message['ReceiptHandle']
        )

    def create_queue(self, queue_name, queue_attributes=None):
        """ Creates a SQS Queue.

        If the queue can't be created immediately because it has been deleted recently, we sleep for
        10 seconds and try again. If any other exception is raised, it's not handled.
        We'll wait until queue is created.
        List of queues is updated at the end.
        :param queue_name: Name for the queue.
        :param queue_attributes: Attributes for the queue. If not specified, defaults are used
        from utils class.
        """
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
                    logging.info('Can\'t create queue yet. AWS won\'t let create it.')
                    time.sleep(10)
            logging.info('Created queue: ')
            for keys, values in queue.items():
                logging.info(keys)
                logging.info(values)
        else:
            dictionary_attributes = queue_attributes.get_dictionary()
            self._client.create_queue(queue_name, dictionary_attributes)
        self.queues = self._client.list_queues()

    def remove_queue(self, queue_url):
        """ Removes a SQS Queue.

        :param queue_url: URL of the queue to be removed.
        :return: True on success, false otherwise.
        """
        if queue_url in self._queues:
            response = self._client.delete_queue(
                QueueUrl=queue_url
            )
            return True
        else:
            return False

    def get_queue_url(self, substring):
        """ Get the url for a queue.

        :param substring: String included on the name of the queue to remove.
        :return: True on success, false otherwise.
        """
        for queue in self.queues:
            if substring in queue:
                return queue
        else:
            return False

    def _check_sqs_queues(self, queue_name):
        """ Checks if a queue exists.

        :param queue_name: Name of the queue to check.
        :return: True if exists, false otherwise.
        """
        for queue in self.queues:
            if queue_name in queue:
                return True
        return False

    def _wait_for_queue_confirmation(self, queue_name):
        """ Waits for a queue to exist.

        Warning: If the queue hasn't been issued to be created, this will never return.
        :param queue_name: Name of the queue to wait for.
        """
        while True:
            for queue in self.queues:
                if queue_name in queue:
                    return True
            time.sleep(1)

    def queues_to_array(self):
        """ Returns queue list as an array.

        :return: Queue list as an array.
        """
        return [queue for queue in (self.queues or [])]

    @property
    def queues(self):
        """ Property corresponding to the actual existing queues.

        Queue list is queried and assigned to property queues.
        :return: Private variable _queues.
        """
        self.queues = self._client.list_queues()
        return self._queues

    @queues.setter
    def queues(self, value):
        """ Property setter for the queues.

        Parses the AWS response and keeps the 'QueueUrls' parameter for each element.
        :param value: AWS response from list_queues.
        :return: Array holding queue urls.
        """
        try:
            self._queues = value['QueueUrls']
        except KeyError:
            self._queues = []


def test_sqs():
    """ Mock method for testing Queue creation and deletion by the wrapper.
    """
    print('Main test unit for the sqs-manager.')
    print('Testing class instantiation.')
    manager = SqsManager()  # role

    print(manager.queues_to_array())

    time.sleep(5)

    print('testing queue creation')
    manager.create_queue(utils.Constants.INBOX_QUEUE_NAME.value)
    manager.create_queue(utils.Constants.OUTBOX_QUEUE_NAME.value)

    time.sleep(60)
    print(manager.queues_to_array())

    queues = manager.queues_to_array()
    if queues:
        for queue in queues:
            manager.remove_queue(queue)

    time.sleep(5)
    print(manager.queues_to_array())


def main():
    """ Mock main method for testing elements in aws_wrapper.
    """
    print('Performing unit tests for Amazon Web Services Wrappers.')
    test_sqs()


if __name__ == '__main__':
    main()

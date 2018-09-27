import boto3
import utils


class SqsManager(object):

    def __init__(self, role=None):
        print("Hello, sqs manager")
        if not role:
            raise ValueError("Role must be provided.")
        # utils.check_global_variables()
        self._session = boto3.session.Session()
        self._client = self._session.client('sqs')
        self._resource = self._session.resource('sqs')

        self._queues = self._client.list_queues()

    def create_queue(self, queue_name, queue_attributes=None):
        if not queue_attributes:
            # instantiate standard queue attributes
            # dictionary_attributes = QueueAttributes().get_dictionary()
            # self._client.create_queue(queue_name, dictionary_attributes)
            queue = self._client.create_queue(
                QueueName='sqs-handwritten-example-number-two',
                Attributes={
                    'VisibilityTimeout': '12'  # 10 minutes
                }
            )
        else:
            dictionary_attributes = queue_attributes.get_dictionary()
            self._client.create_queue(queue_name, dictionary_attributes)
        self.list_queues()

    def list_queues(self):
        self._queues = self._client.list_queues()
        return self._queues


class QueueAttributes(object):
    _delay_seconds = 0
    _message_retention_period = 345600
    _maximum_message_size = 262144
    _receive_message_wait_time_seconds = 0
    _visibility_timeout = 12

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
        dict = {"DelaySeconds": self._delay_seconds,
                "MaximumMessageSize": self._maximum_message_size,
                "MessageRetentionPeriod": self._message_retention_period,
                "ReceiveMessageWaitTimeSeconds": self._receive_message_wait_time_seconds,
                "VisibilityTimeout": self._visibility_timeout}
        return dict


def main():
    print("Main test unit for the sqs-manager.")
    print("Testing class instantiation.")
    manager = SqsManager("test")
    print("Testing to retrieve queue list.")
    if not manager._queues:
        print("No queues.")
    else:
        for queue in manager._queues.get('QueueUrls'):
            print(queue)
    print("Testing queue creation")
    manager.create_queue("sqs-manager test queue")
    print("Printing queue list again", manager._queues.get('QueueUrls'))


if __name__ == "__main__":
    main()

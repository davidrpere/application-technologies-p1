import random
from aws_wrapper import SqsManager, S3Manager, AwsWrapper
import urllib.request, json
import time
from threading import Thread
from utils import Command, Constants


class SqsClientInterface(Thread):
    inbox_queue_name = Constants.INBOX_QUEUE_NAME.value
    inbox_ready = False
    outbox_queue_name = Constants.OUTBOX_QUEUE_NAME.value
    outbox_ready = False
    s3_link = None
    responses = []

    def __init__(self, sqs_manager):
        Thread.__init__(self)
        self._identity = random.getrandbits(32)
        self._sqs_manager = sqs_manager
        self._sqs_manager.bind_to(self.received_message)

    def received_message(self, message):
        # print('received message callback')
        command = message['MessageAttributes']['Command']['StringValue']
        if command == Command.ECHO_REPLY.value:
            print('Echo says : ' + message['Body'])
        elif command == Command.DOWNLOAD_REPLY.value:
            with urllib.request.urlopen(message['Body']) as url:
                data = json.loads(url.read().decode())
                print(data)
        elif command == Command.DOWNLOAD_URL_REPLY.value:
            self.s3_link = message['Body']
        self._sqs_manager.delete_message(message, self._sqs_manager.get_queue_url(self.outbox_queue_name))

    def run(self):
        if not self._sqs_manager._check_sqs_queues(self.inbox_queue_name):
            self._sqs_manager.create_queue(self.inbox_queue_name)
        if not self._sqs_manager._check_sqs_queues(self.outbox_queue_name):
            self._sqs_manager.create_queue(self.outbox_queue_name)
        self._sqs_manager._wait_for_queue_confirmation(self.inbox_queue_name)
        self.inbox_ready = True
        self._sqs_manager._wait_for_queue_confirmation(self.outbox_queue_name)
        self.outbox_ready = True

        self._begin_connection()

        while True:
            self.receive_message()
            time.sleep(2)

    def retrieve_messages(self):
        self._sqs_manager.send_message(self._sqs_manager.get_queue_url(self.inbox_queue_name), self._identity,
                                       self._identity,
                                       Constants.ECHOSYSTEM_ID, Command.DOWNLOAD_REQUEST.value)

    def receive_message(self):
        self._sqs_manager.receive_message(self._sqs_manager.get_queue_url(self.outbox_queue_name),
                                          self._identity)

    def send_message(self, message):
        if message == 'END':
            self._sqs_manager.send_message(self._sqs_manager.get_queue_url(self.inbox_queue_name), self._identity,
                                           message,
                                           Constants.ECHOSYSTEM_ID, Command.CLIENT_END.value)
            # self.upload_s3()
        else:
            self._sqs_manager.send_message(self._sqs_manager.get_queue_url(self.inbox_queue_name), self._identity,
                                           message,
                                           Constants.ECHOSYSTEM_ID, Command.ECHO_REQUEST.value)

    def upload_s3(self):
        self._sqs_manager.send_message(self._sqs_manager.get_queue_url(self.inbox_queue_name), self._identity,
                                       self._identity,
                                       Constants.ECHOSYSTEM_ID, Command.DOWNLOAD_URL_REQUEST.value)

    def begin_chat(self):
        self._sqs_manager.send_message(self._sqs_manager.get_queue_url(self.inbox_queue_name), self._identity,
                                       self._identity,
                                       Constants.ECHOSYSTEM_ID, Command.BEGIN_ECHO.value)
        time.sleep(1)

    def _begin_connection(self):
        self._sqs_manager.send_message(self._sqs_manager.get_queue_url(self.inbox_queue_name), self._identity,
                                       self._identity,
                                       Constants.ECHOSYSTEM_ID, Command.NEW_CLIENT.value)

    def end_connection(self):
        self._sqs_manager.send_message(self._sqs_manager.get_queue_url(self.inbox_queue_name), self._identity,
                                       self._identity,
                                       Constants.ECHOSYSTEM_ID, Command.REMOVE_CLIENT.value)

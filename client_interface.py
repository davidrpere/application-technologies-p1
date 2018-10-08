import random
import aws_wrapper
import urllib.request, json
from threading import Thread


class SqsClientInterface(Thread):
    inbox_queue_name = 'Inbox'
    inbox_ready = False
    outbox_queue_name = 'Outbox'
    outbox_ready = False

    def __init__(self):
        Thread.__init__(self)
        self._identity = random.getrandbits(32)
        self._sqs_manager = aws_wrapper.SqsManager()

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
            received_messages = self.receive_message()
            if received_messages:
                for received_message in received_messages:
                    command = received_message['MessageAttributes']['Command']['StringValue']
                    if command == 'echo':
                        print('Echo says: ', received_message['Body'])
                    elif command == 'download-reply':
                        with urllib.request.urlopen(received_message['Body']) as url:
                            data = json.loads(url.read().decode())
                            print(data)
                    self._sqs_manager.delete_message(received_message,
                                                     self._sqs_manager.get_queue_url(self.outbox_queue_name))

    def retrieve_messages(self):
        self._sqs_manager._send_message(self._sqs_manager.get_queue_url(self.inbox_queue_name), self._identity,
                                        self._identity,
                                        'EchoSystem', 'download-query')

    def receive_message(self):
        return self._sqs_manager._receive_message(self._sqs_manager.get_queue_url(self.outbox_queue_name),
                                                  self._identity)

    def send_message(self, message):
        if message == 'END':
            self._sqs_manager._send_message(self._sqs_manager.get_queue_url(self.inbox_queue_name), self._identity,
                                            message,
                                            'EchoSystem', 'client-end')
        else:
            self._sqs_manager._send_message(self._sqs_manager.get_queue_url(self.inbox_queue_name), self._identity,
                                            message,
                                            'EchoSystem')

    def _begin_connection(self):
        self._sqs_manager._send_message(self._sqs_manager.get_queue_url(self.inbox_queue_name), self._identity,
                                        self._identity,
                                        'EchoSystem', 'new-client')

    def end_connection(self):
        self._sqs_manager._send_message(self._sqs_manager.get_queue_url(self.inbox_queue_name), self._identity,
                                        self._identity,
                                        'EchoSystem', 'client-left')

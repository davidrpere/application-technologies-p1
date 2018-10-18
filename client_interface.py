import logging
import random
import urllib.request, json
import time
from threading import Thread
from utils import Command, Constants


class SqsClientInterface(Thread):
    """ CLass for interfacing with the SQS Queues in a simple way, client oriented, abstracting from the lower leve
    operation.

    Parameters such as inbox and outbox queue names are hardcoded and extracted from Constants class.
    Boolean parameters are used to set if queues are ready to use.
    """
    inbox_queue_name = Constants.INBOX_QUEUE_NAME.value
    inbox_ready = False
    outbox_queue_name = Constants.OUTBOX_QUEUE_NAME.value
    outbox_ready = False
    s3_link = None
    responses = []

    def __init__(self, sqs_manager):
        """ Instantiates an SQS Listener Interface.

        Random ID is generated on each instantation, so each instante is an (almost) unique.
        :param sqs_manager: SQS manager previously instiated to bind to our interface.
        """
        logging.info('Initialized client interface.')
        Thread.__init__(self)
        self._identity = random.getrandbits(32)
        self._sqs_manager = sqs_manager
        self._sqs_manager.bind_to(self.received_message)

    def received_message(self, message):
        """ Callback method for received messages.

        Implements the behaviour of the client. First, we extract the command from the received message. After that, we
        evaluate which kind of command it is and act in consequence.
        Behaviour is implemented on this method as it's preferred for keeping the messaging async with the activity of
        the client app.
        After performing our task, the message is deleted from the queue.
        :param message: Received message.
        """
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
        """ Run method for the client interface.

        This will wait for the queues to be ready, set their boolean flags to true and then long-poll messages from
        Inbox queue and sleep 2 seconds between services, so we don't overkill CPU nor SQS queries.
        :return:
        """
        logging.info('Initialized client interface run method.')
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
        """ Retrieves messages from S3.

        The method sends a petition to SQS querying the URL of the S3 file.
        The received reply will be managed asynchronously.
        """
        self._sqs_manager.send_message(self._sqs_manager.get_queue_url(self.inbox_queue_name), self._identity,
                                       self._identity,
                                       Constants.ECHOSYSTEM_ID, Command.DOWNLOAD_REQUEST.value)

    def receive_message(self):
        """ Receives messages with addressee self identity.
        """
        self._sqs_manager.receive_message(self._sqs_manager.get_queue_url(self.outbox_queue_name),
                                          self._identity)

    def send_message(self, message):
        """ Sends a message, with a given content.

        If the message is 'END', a different command will be issued.
        :param message: Message body.
        """
        if message == 'END':
            self._sqs_manager.send_message(self._sqs_manager.get_queue_url(self.inbox_queue_name), self._identity,
                                           message,
                                           Constants.ECHOSYSTEM_ID, Command.CLIENT_END.value)
        else:
            self._sqs_manager.send_message(self._sqs_manager.get_queue_url(self.inbox_queue_name), self._identity,
                                           message,
                                           Constants.ECHOSYSTEM_ID, Command.ECHO_REQUEST.value)

    def upload_s3(self):
        """ Queries a listener to upload to AWS S3 messages and sending an url.
        """
        self._sqs_manager.send_message(self._sqs_manager.get_queue_url(self.inbox_queue_name), self._identity,
                                       self._identity,
                                       Constants.ECHOSYSTEM_ID, Command.DOWNLOAD_URL_REQUEST.value)

    def begin_chat(self):
        """ Sends a message asking for a listener to echo chat.
        """
        self._sqs_manager.send_message(self._sqs_manager.get_queue_url(self.inbox_queue_name), self._identity,
                                       self._identity,
                                       Constants.ECHOSYSTEM_ID, Command.BEGIN_ECHO.value)
        time.sleep(1)

    def _begin_connection(self):
        """ Sends a message asking to be registered in the system.
        """
        self._sqs_manager.send_message(self._sqs_manager.get_queue_url(self.inbox_queue_name), self._identity,
                                       self._identity,
                                       Constants.ECHOSYSTEM_ID, Command.NEW_CLIENT.value)

    def end_connection(self):
        """ Sends a message telling we're leaving the system.
        """
        self._sqs_manager.send_message(self._sqs_manager.get_queue_url(self.inbox_queue_name), self._identity,
                                       self._identity,
                                       Constants.ECHOSYSTEM_ID, Command.REMOVE_CLIENT.value)

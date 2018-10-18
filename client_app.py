import time
import logging
import signal, sys
import client_interface, aws_wrapper


def main():
    """ Client app. Implements, by using the client interface, the basic behaviour of the client console app.
    """

    def handler(signum, frame):
        """ Catches signals from the system to close the program.

        Sends end connection command to listeners before leaving.
        """
        logging.error('Catch signal, terminating.')
        global_messaging_interface.end_connection()
        sys.exit()

    signal.signal(signal.SIGILL, handler)
    signal.signal(signal.SIGABRT, handler)
    signal.signal(signal.SIGINT, handler)
    signal.signal(signal.SIGTERM, handler)

    sqs_manager = aws_wrapper.SqsManager()
    messaging_interface = client_interface.SqsClientInterface(sqs_manager)
    messaging_interface.daemon = True
    messaging_interface.start()

    global_messaging_interface = messaging_interface

    while not messaging_interface.inbox_ready \
            or not messaging_interface.outbox_ready:
        time.sleep(1)

    choice = '0'
    while choice != 'q':
        print('Main menu of the client app. You have two choices:')
        print('Choose 1 for sending EchoApp messages.')
        print('Choose 2 for retrieving EchoApp messages.')
        print('Choose q for closing the client.')

        choice = input('Please make a choice: ')

        if choice == 'q':
            print('Closing...')
            messaging_interface.end_connection()
            exit()
        elif choice == '1':
            print('Chosen option: Sending EchoApp messages.')
            send_messages(messaging_interface)
        elif choice == '2':
            print('Chosen option: Retrieve messages.')
            retrieve_messages(messaging_interface)
        else:
            print('Please, choose a valid option.')


def send_messages(messaging_interface):
    """ EchoApp subroutine.

    Sends begin chat command and waits for user input. Sends messages as user presses ENTER key.
    Doesn't allow empty messages. Exits on user typing "END".
    :param messaging_interface: Messaging interface.
    """
    print('This is the echo message app.')
    messaging_interface.begin_chat()
    while not messaging_interface.inbox_ready or not messaging_interface.outbox_ready:
        time.sleep(1)

    while True:
        time.sleep(0.1)
        input_msg = input('')
        if not input_msg:
            print('Message body can\'t be empty.')
            continue
        messaging_interface.send_message(input_msg)
        if input_msg == 'END':
            print('\n')
            break


def retrieve_messages(messaging_interface):
    """ SearchingApp subroutine.

    Queries asynchronously messages from S3 via SQS message. Output is printed when received.
    :param messaging_interface: Messaging interface.
    """
    print('Querying messages to the service. Please stand-by.')
    messaging_interface.retrieve_messages()
    time.sleep(5)


main()

import utils
import time
import json
import client_interface, aws_wrapper


def main():
    sqs_manager = aws_wrapper.SqsManager()
    messaging_interface = client_interface.SqsClientInterface(sqs_manager)
    messaging_interface.daemon = True
    messaging_interface.start()

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
            # TODO cleanup
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


# def custom_callback(message):
#     print('Custom callback')

def send_messages(messaging_interface):
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
    print('Querying messages to the service. Please stand-by.')
    messaging_interface.retrieve_messages()
    time.sleep(5)


main()

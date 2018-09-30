import utils
import time

def main():
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
            exit()
        elif choice == '1':
            print('Chosen option: Sending EchoApp messages.')
            send_messages()
        elif choice == '2':
            print('Chosen option: Retrieve messages.')
            retrieve_messages()
        else:
            print('Please, choose a valid option.')


def send_messages():
    print('This is the echo message app.')
    messaging_interface = utils.SqsMessagingInterface('Client')
    messaging_interface.daemon = True
    messaging_interface.start()
    while not messaging_interface._inbox_ready or not messaging_interface._outbox_ready:
        time.sleep(1)

    while True:
        # time.sleep(0.1)
        input_msg = input('>> ')
        messaging_interface.send_message(input_msg, 'EchoSystem')
        if input_msg == 'END':
            print('\n')
            break

def retrieve_messages():
    print('This is the message retrieval app.')


main()

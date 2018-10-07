import utils
import time
import json

def main():
    messaging_interface = utils.SqsMessagingInterface('Client')
    messaging_interface.daemon = True
    messaging_interface.start()
    storing_interface = utils.S3StoringInterface()
    storing_interface.daemon = True
    storing_interface.start()

    while not messaging_interface._inbox_ready \
            or not messaging_interface._outbox_ready \
            or not storing_interface._storage_ready:
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
            retrieve_messages(storing_interface, messaging_interface._identity)
        else:
            print('Please, choose a valid option.')


def send_messages(messaging_interface):
    print('This is the echo message app.')
    while not messaging_interface._inbox_ready or not messaging_interface._outbox_ready:
        time.sleep(1)

    while True:
        # time.sleep(0.1)
        input_msg = input('>> ')
        if not input_msg:
            print('Message body can\'t be empty.')
            continue
        messaging_interface.send_message(input_msg, 'EchoSystem')
        if input_msg == 'END':
            print('\n')
            break


def retrieve_messages(storing_interface, identity):
    print('This is the message retrieval app.')
    print('Storage is ready. Querying all the messages from S3 bucket...')
    storing_interface.download_file(str(identity) + '.json', '/tmp/' + str(identity) + '.json')
    with open('/tmp/' + str(identity) + '.json') as json_data:
        d = json.load(json_data)
        print(d)


main()

import time
import utils


def main():
    print('Hello world. This is the listener app.')
    # Now we must import the sqs queue manager and start listening to the Inbox queue.
    messaging_interface = utils.SqsMessagingInterface('EchoSystem')
    storing_interface = utils.S3StoringInterface()
    messaging_interface.daemon = True
    messaging_interface.start()
    # messaging_interface.join()
    storing_interface.daemon = True
    storing_interface.start()
    # storing_interface.join()

    while not messaging_interface._inbox_ready \
            or not messaging_interface._outbox_ready \
            or not storing_interface._storage_ready:
        time.sleep(1)

    while True:
        time.sleep(0.3)


main()

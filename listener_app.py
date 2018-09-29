import time
import aws_wrapper


def main():
    print('Hello world. This is the listener app.')
    # Now we must import the sqs queue manager and start listening to the Inbox queue.
    messaging_interface = aws_wrapper.SqsMessagingInterface('EchoSystem')

    messaging_interface.start()
    messaging_interface.join()

    while not messaging_interface._inbox_ready or not messaging_interface._outbox_ready:
        time.sleep(1)

    print('Messaging interface says that outbox is ', messaging_interface._outbox_ready)
    print('Messaging interface says that inbox is ', messaging_interface._inbox_ready)
    # Queues successfully detected. Now go on to listening to one.

    messaging_interface._test_thread_death()
    messaging_interface.send_message('does not matter')
    time.sleep(10)
    messaging_interface.receive_message()


main()

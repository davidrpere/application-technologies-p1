import boto3

def main():
    choice = "0"
    while choice == "0":
        print("Main menu of the client app. You have two choices:")
        print("Choose 1 for sending EchoApp messages.")
        print("Choose 2 for retrieving EchoApp messages.")
        print("Choose q for closing the client.")

        choice = input("Please make a choice: ")

        if choice == "q":
            # cleanup
            print("Closing...")
            exit()
        elif choice == "1":
            print("Chosen option: Sending EchoApp messages.")
            send_messages()
        elif choice == "2":
            print("Chosen option: Retrieve messages.")
            retrieve_messages()
        else:
            print("Please, choose a valid option.")

def send_messages():
    print("This is the echo message app.")
    # try to start scs queue
    # confirm correct startup
    # notify and wait for user input
    # send user input.
    # if user input is END, go back to main menu.

def retrieve_messages():
    print("This is the message retrieval app.")
    # try to start scs queue (?)
    # confirm correct startup
    # notify and wait for user input
    # send user input.
    # wait for reply.
    # show information.
    # ask if you want to continue or not.
    # if user input is END, go back to main menu.

def init_scs_queue():
    # Get the service resource
    sqs = boto3.resource('sqs')

    # Create the queue. This returns an SQS.Queue instance
    queue = sqs.create_queue(QueueName='test', Attributes={'DelaySeconds': '5'})
    response = client.create_queue(
        QueueName='string',
        Attributes={
            'string': 'string'
        }
    )

    # You can now access identifiers and attributes
    print(queue.url)
    print(queue.attributes.get('DelaySeconds'))

main()

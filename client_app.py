import boto3

# Get the service resource
sqs = boto3.resource('sqs')

for queue in sqs.queues.all():
    print(queue.url)
    print("This is one print")

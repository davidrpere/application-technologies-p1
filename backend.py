import boto3


class backend:

    def __init__(self):
        print("Hello world")

    def iniatilze_sqs(self):
        self.sqs_client = boto3.client('sqs')

    def initialize_s3(self):
        self.s3_client = boto3.client('s3')

    def initialize_ec2(self):
        self.ec2_client = boto3.client('ec2')

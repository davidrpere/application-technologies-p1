import time
import aws_wrapper


class Backend:

    def __init__(self):
        print("Instantiated backend class.")
        self._sqs_manager = self._iniatilze_sqs()
        self._ec2_manager = self._initialize_ec2()
        self._s3_manager = self._initialize_s3()

    def create_bucket(self, bucket_name):
        self._s3_manager.create_bucket(bucket_name)

    def create_queue(self, queue_name):
        self._sqs_manager.create_queue(queue_name)

    def remove_queue(self, queue_url):
        self._sqs_manager.remove_queue(queue_url)

    def list_buckets(self):
        print(self._s3_manager.buckets_to_array())

    def list_queues(self):
        print(self._sqs_manager.queues_to_array())

    def _iniatilze_sqs(self):
        return aws_wrapper.SqsManager()

    def _initialize_s3(self):
        return aws_wrapper.S3Manager()

    def _initialize_ec2(self):
        return aws_wrapper.Ec2Manager()


def main():
    print('Backend main unit test')
    backend = Backend()
    backend.list_queues()
    backend.list_buckets()


if __name__ == '__main__':
    main()

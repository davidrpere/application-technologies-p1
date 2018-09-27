import os
import boto3


def check_global_variables():
    if (not os.environ.get('AWS_ACCOUNT_ID', None) and
            not (boto3.Session().get_credentials().method in ['iam-role', 'assume-role'])):
        raise EnvironmentError('Environment variable `AWS_ACCOUNT_ID` not set and no role found.')

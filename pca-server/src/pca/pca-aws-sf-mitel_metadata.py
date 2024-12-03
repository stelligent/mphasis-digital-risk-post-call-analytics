"""
This python function is part of the main processing workflow.  This performs any specific processing
required to handle Mitel Metadata files.

Copyright MPhasis.com, Inc. or its affiliates. All Rights Reserved.
SPDX-License-Identifier: Apache-2.0
"""

import json
import boto3
import tempfile
from time import sleep
import uuid
import os

import pcaconfiguration as cf

cf.loadConfiguration()

def verify_s3_obj_exists(s3, bucket, key, wait_seconds=120, check_interval=20):
    attempts = int(wait_seconds / check_interval)
    i = attempts
    while i > 0:
        try:
            s3.head_object(Bucket=bucket, Key=key)
            print(f"Object \'{key}\' found in {attempts - i + 1} attempt(s). ")
            return
        except Exception as e:
            print(f"Object {key} not found.  will retry {i} more times.")
        sleep(check_interval)
        i -= 1
    raise Exception(f"FATAL: Object \'{key}\' NOT FOUND after {attempts + 1} attempt(s) in {wait_seconds} seconds. ")

def get_file(s3, bucket, key, key_filename):
    dl_file_path = f"{tempfile.gettempdir()}/{key_filename}"
    s3.download_file(bucket, key, dl_file_path)
    return dl_file_path

def write_dict_to_s3(s3, obj, bucket, key):
    s3.put_object(
        Body=json.dumps(obj),
        Bucket=bucket,
        Key=key
    )

def lambda_handler(event, context):
    """
    Lambda function entrypoint
    """
    # collect args for this invocation
    functionConfig = {}
    functionConfig['metadata_bucket'] = cf.appConfig[cf.CONF_S3BUCKET_INPUT]
    functionConfig['metadata_file'] = f"{event['key'][:-3]}json"
    functionConfig['interim_results_bucket'] = cf.appConfig[cf.CONF_S3BUCKET_OUTPUT]
    functionConfig['interim_results_file'] = event['interimResultsFile']

    s3 = boto3.client("s3")

    verify_s3_obj_exists(
        s3,
        functionConfig['metadata_bucket'],
        f"{functionConfig['metadata_file']}"
    )

    metadata_file = get_file(
        s3,
        functionConfig['metadata_bucket'],
        f"{functionConfig['metadata_file']}",
        f"{uuid.uuid1()}.json"
    )
    with open(metadata_file, 'r') as file:
        metadata = json.load(file)
    os.remove(metadata_file)

    interrim_results_file = get_file(
        s3,
        functionConfig['interim_results_bucket'],
        f"{functionConfig['interim_results_file']}",
        f"{uuid.uuid1()}.json"
    )
    with open(interrim_results_file, 'r') as file:
        interrim_results = json.load(file)
    os.remove(interrim_results_file)

    interrim_results['MitelMetadata'] = metadata
    del metadata

    write_dict_to_s3(
        s3,
        interrim_results,
        functionConfig['interim_results_bucket'],
        functionConfig['interim_results_file']
    )

    print(json.dumps(functionConfig))
    print("Done")

    return event

if __name__ == "__main__":
    lambda_handler(None, None)


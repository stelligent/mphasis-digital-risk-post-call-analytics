"""
This python function is triggered when a new audio file is dropped into the S3 preload bucket.
It parse and process the call metata file(s), converts to json, rename files, and copies them
into the PCA input bucket for ingetation.

Copyright MPhasis.com, Inc. or its affiliates. All Rights Reserved.
SPDX-License-Identifier: Apache-2.0
"""
import json
import urllib.parse
import boto3
import pcaconfiguration as cf
import os
import re
import tempfile
import xml.etree.ElementTree as ET
from time import sleep
from xmljson import parker
import datetime
from zoneinfo import ZoneInfo


# Load our configuration
cf.loadConfiguration()

CONF_PRELOAD_OBJECT_KEY_REGEX = cf.appConfig[cf.CONF_PRELOAD_OBJECT_KEY_REGEX]
key_check_pattern = re.compile(CONF_PRELOAD_OBJECT_KEY_REGEX)

CONF_S3BUCKET_INPUT = cf.appConfig[cf.CONF_S3BUCKET_INPUT]
CONF_PREFIX_RAW_AUDIO = cf.appConfig[cf.CONF_PREFIX_RAW_AUDIO]

def convert_iso_utc_to_tz(iso_string, format_string="%Y-%m-%d %H:%M:%S %Z", timezone="America/New_York", default_value="Unknown"):
    try:
        tz = ZoneInfo(timezone)
        dt = datetime.datetime.fromisoformat(iso_string.replace('Z', '+00:00'))
        # dt=dt.replace(tzinfo=datetime.timezone.utc) #Convert it to an aware datetime object in UTC time.
        dt=dt.astimezone(tz) #Convert it to your local timezone (still aware)
        return dt.strftime(format_string)
    except Exception as e:
        print(str(e))
        return default_value

def persist_as_json(xml_data, json_file_path):
    with open(json_file_path, 'w') as f:
        json.dump(xml_data, f)

def get_call_guid(xml_data):
    return xml_data.find("./id").text

def get_agent_name(xml_data):
    first_emp = xml_data.find(".//employee[lastName!='Voicemail']")

    if first_emp is None:
        agent_name = "Agent"
    else:
        first_name = first_emp.find("./firstName")
        last_name = first_emp.find("./lastName")
        if first_name is None and last_name is None:
            agent_name = "Agent"
        else:
            first_name = first_name.text if first_name is not None else ""
            last_name = last_name.text if last_name is not None else ""
            agent_name = f"{first_name} {last_name}"

    return agent_name

def get_node_text(xml_data, xpath, default):
    find_node = xml_data.find(xpath)
    if find_node is None:
        return_text = "Unknown"
    else:
        return_text = find_node.text
    return return_text

def get_agent_extension(xml_data):
    first_emp = xml_data.find(".//employee[lastName!='Voicemail']")
    if first_emp is None:
        agent_extension = "Unknown"
    else:
        agent_extension = get_node_text(first_emp, "./phoneNumber", "Unknown")
    return agent_extension

def get_call_direction(xml_data):
    return get_node_text(xml_data, "./direction", "Unknown")

def get_call_starttime(xml_data):
    utc_starttime = get_node_text(xml_data, "./starttime", "Unknown")
    return convert_iso_utc_to_tz(utc_starttime)

def get_call_endtime(xml_data):
    utc_endtime = get_node_text(xml_data, "./endtime", "Unknown")
    return convert_iso_utc_to_tz(utc_endtime)

def get_caller_number(xml_data):
    return get_node_text(xml_data, "./callerNumber", "Unknown")

def get_organization(xml_data):
    org_param_node = xml_data.find(".//conversationParameters[name='Organization']")
    if org_param_node is None:
        org_name = "Unknown"
    else:
        org_name = get_node_text(org_param_node, "./parameterValue", "Unknown")
    return org_name

def get_base_filename(call_guid, agent_name, agent_extension, caller_number, organization):
    pattern = re.compile('[\W_]+')
    agent_name = pattern.sub('', agent_name)
    organization = pattern.sub('', organization)
    return f"Mitel_GUID_{call_guid}_AGENT_{agent_name}-x{agent_extension}_CUSTOMER_{caller_number}_ORG_{organization}_orig"

def get_audio_filename(call_guid, agent_name, agent_extension, caller_number, organization, extension):
    return f"{get_base_filename(call_guid, agent_name, agent_extension, caller_number, organization)}.{extension}"

def get_json_metadata_filename(call_guid, agent_name, agent_extension, caller_number, organization):
    return f"{get_base_filename(call_guid, agent_name, agent_extension, caller_number, organization)}.json"

def get_xml_metadata_filename(call_guid, agent_name, agent_extension, caller_number, organization):
    return f"{get_base_filename(call_guid, agent_name, agent_extension, caller_number, organization)}.xml"

def add_node_with_value(parent_node, new_node_name, new_node_value):
    new_node = ET.SubElement(parent_node, new_node_name)
    new_node.text = new_node_value

def inject_call_summary(
        root,
        call_guid,
        agent_name,
        agent_extension,
        call_direction,
        caller_number,
        organization,
        start_time,
        end_time
        # audio_filename,
        # json_filename,
        # xml_filename
    ):
    summary_node = ET.SubElement(root, "callSummary")
    add_node_with_value(summary_node, "callGuid", call_guid)
    add_node_with_value(summary_node, "agentName", agent_name)
    add_node_with_value(summary_node, "agentExtension", agent_extension)
    add_node_with_value(summary_node, "callDirection", call_direction)
    add_node_with_value(summary_node, "callerNumber", caller_number)
    add_node_with_value(summary_node, "organization", organization)
    add_node_with_value(summary_node, "startTime", start_time)
    add_node_with_value(summary_node, "endTime", end_time)
    # add_node_with_value(summary_node, "audioFilename", audio_filename)
    # add_node_with_value(summary_node, "jsonFilename", json_filename)
    # add_node_with_value(summary_node, "xmlFilename", xml_filename)
    return


# original_audio_filename = f"{xml_file_path[:-3]}wav"
# if not os.path.isfile(original_audio_filename):
#     raise Exception(f"FATAL: Required audio file [{original_audio_filename}] not found")


def process_file(xml_file_path):

    tree = ET.parse(xml_file_path)
    root = tree.getroot()

    agent_name = get_agent_name(root)
    agent_extension = get_agent_extension(root)
    call_guid = get_call_guid(root)
    call_direction = get_call_direction(root)
    caller_number = get_caller_number(root)
    organization = get_organization(root)
    start_time = get_call_starttime(root)
    end_time = get_call_endtime(root)

    print(f"Call GUID: {call_guid}")
    print(f"Agent: {agent_name}")
    print(f"Agent Extension: {agent_extension}")
    print(f"Call Direction: {call_direction}")
    print(f"Caller Number: {caller_number}")
    print(f"Organization: {organization}")
    print(f"Call Start Time: {start_time}")
    print(f"Call End Time: {end_time}")

    audio_filename = get_audio_filename(call_guid, agent_name, agent_extension, caller_number, organization, "wav")
    json_filename = get_json_metadata_filename(call_guid, agent_name, agent_extension, caller_number, organization)
    xml_filename = get_xml_metadata_filename(call_guid, agent_name, agent_extension, caller_number, organization)

    inject_call_summary(
        root,
        call_guid,
        agent_name,
        agent_extension,
        call_direction,
        caller_number,
        organization,
        start_time,
        end_time
        # json_filename,
        # audio_filename,
        # xml_filename
    )

    print(f"Audio Filename: {audio_filename}")
    print(f"JSON Filename: {json_filename}")
    print(f"XML Filename: {xml_filename}")

    persist_as_json(parker.data(root, preserve_root=True), f"{tempfile.tempdir}/{json_filename}")
    tree.write(f"{tempfile.tempdir}/{xml_filename}")

    return {
        'audio_filename': audio_filename,
        'json_filename': json_filename,
        'xml_filename': xml_filename,
        'local_path': tempfile.tempdir
    }

def get_file(s3, bucket, key, key_filename):
    xml_file_path = f"{tempfile.gettempdir()}/{key_filename}"
    s3.download_file(bucket, key, xml_file_path)
    return xml_file_path

def verify_s3_obj_exists(s3, bucket, key, wait_seconds=120, check_interval=20):
    attempts = int(wait_seconds / check_interval)
    i = attempts
    while i > 0:
        try:
            s3.head_object(Bucket=bucket, Key=key)
            print(f"wav file \'{key}\' found in {attempts - i + 1} attempt(s). ")
            return
        except Exception as e:
            print(f"wav file not found.  will retry {i} more times.")
        sleep(check_interval)
        i -= 1
    raise Exception(f"FATAL: wav file \'{key}\' NOT FOUND after {attempts + 1} attempt(s) in {wait_seconds} seconds. ")

def push_files(s3, source_bucket, wav_key, file_names):

    s3.upload_file(
        f"{file_names['local_path']}{os.path.sep}{file_names['json_filename']}",
        CONF_S3BUCKET_INPUT,
        f"{CONF_PREFIX_RAW_AUDIO}/{file_names['json_filename']}"
    )

    s3.upload_file(
        f"{file_names['local_path']}{os.path.sep}{file_names['xml_filename']}",
        CONF_S3BUCKET_INPUT,
        f"{CONF_PREFIX_RAW_AUDIO}/{file_names['xml_filename']}"
    )

    s3.copy(
        {
            "Bucket": source_bucket,
            "Key": wav_key
        },
        CONF_S3BUCKET_INPUT,
        f"{CONF_PREFIX_RAW_AUDIO}/{file_names['xml_filename']}"
    )



def lambda_handler(event, context):

    file_names = {}

    # Get handles to the object from the event
    s3 = boto3.client("s3")
    bucket = event['Records'][0]['s3']['bucket']['name']
    key = urllib.parse.unquote_plus(event['Records'][0]['s3']['object']['key'], encoding='utf-8')
    wav_key = f"{key[:-3]}wav"

    # Check if there's actually a file and that this wasn't just a folder creation event
    key_filename = key.split("/")[-1]
    if len(key_filename) == 0:
        # Just a folder, no object - silently quit
        final_message = f"Folder creation event at \'{key}\', no object to process"
    elif not bool(key_check_pattern.search(key_filename)):
        final_message = f"Object key \'{key}\' does not match CONF_PRELOAD_OBJECT_KEY_REGEX \'{CONF_PRELOAD_OBJECT_KEY_REGEX}\'. Skipping."
    else:
        # Validate that the object exists
        try:
            s3.head_object(Bucket=bucket, Key=key)
        except Exception as e:
            print(e)
            raise Exception(
                'Error getting object {} from bucket {}. Make sure it exists and your bucket is in the same region as this function.'.format(
                    key, bucket))

        # Verify corresponding audio file exits
        try:
            verify_s3_obj_exists(s3, bucket, wav_key)
        except Exception as e:
            print(e)
            raise Exception(
                'Audio missing.  Error getting object {} from bucket {}. Make sure it exists!'.format(
                    key, bucket))

        xml_file_path = get_file(s3, bucket, key, key_filename)
        print(f"Input File Path: {xml_file_path}")

        file_names = process_file(xml_file_path)
        print(json.dumps(file_names, indent=2))

        push_files(s3, bucket, wav_key, file_names)

        final_message = f"s3://{bucket}/{key} pushed to {CONF_S3BUCKET_INPUT}/{CONF_PREFIX_RAW_AUDIO}\'."

    print(json.dumps(event,indent=2))
    print(f"bucket: {bucket}")
    print(f"key:    {key}")
    print(final_message)

    return {
        'statusCode': 200,
        'body': final_message,
        'bucket': bucket,
        'key': key,
        'file_names': file_names
    }


import json
import boto3
import os
import urllib.parse
from botocore.exceptions import ClientError
import csv
from time import sleep


def lambda_handler(event, context):
    # TODO implement
    if event:
        bucket = event['Records'][0]['s3']['bucket']['name']
        key = urllib.parse.unquote_plus(event['Records'][0]['s3']['object']['key'], encoding='utf-8')
        pushKeys(bucket,key)
    
def pushKeys(bucket,key):
    s3_client=boto3.client('s3')
    ssm=boto3.client('ssm')
    ec2=boto3.client('ec2')
    User_List = getObject(bucket,key,s3_client)
    
    for row in User_List:
        
        try:
            response = ssm.send_command(
                InstanceIds=[row['InstanceId']],
                DocumentName="AWS-RunRemoteScript",
                Parameters={
                        "sourceType":["S3"],"sourceInfo":["{\"path\":\"https://s3.amazonaws.com/ici-taniumreports/sendKey.sh\"}"],
                        "commandLine":["sendKey.sh"]
                        #"commands": ["#!/bin/bash/","sudo su - 'row['Name']'","echo 'row['Key']  > .ssh/authorized_keys"]
                    }, 
                OutputS3BucketName='ici-logreport',
                        #OutputS3KeyPrefix='Logs',
                )
        except ClientError as e:
            print(e,row['InstanceId'])
            continue
        command_id = response["Command"]["CommandId"]
        sleep(5)
            
                # fetching command output
        output = ssm.get_command_invocation(CommandId=command_id, InstanceId=row['InstanceId'])
        print(output)
        
                    
def getObject(bucket,key,client):
    try:
        response = client.get_object(Bucket=bucket, Key=key)
        file_content = response["Body"].read().decode('utf-8').splitlines()
        reader = csv.DictReader(file_content)
        UserList = []
        for row in reader:
            UserList.append(row)
        print(UserList)
        return UserList
    
    except Exception as e:
        print(e)
        raise e
    

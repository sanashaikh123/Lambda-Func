import json
import boto3
from botocore.exceptions import ClientError
import csv
from time import sleep
import os
import datetime
import pandas as pd

def lambda_handler(event, context):
    # TODO implement
    if event:
        createAccount()
    else:
        createAccount()
        
    
def createAccount():
    ssm = boto3.client("ssm")
    s3 = boto3.client("s3")
    ec2 = boto3.client("ec2")
    user_List = getObject(s3)
    
    #print(user_List[0]["Owner"])
    
        
    try:
        response = ec2.describe_instances(
            Filters=[
                {
                    'Name': 'tag:'+"Owner",
                    'Values': [user_List[0]["Owner"]]
                }
            ]
        )
            
        instancelist = []
        for reservation in (response["Reservations"]):
            for instance in reservation["Instances"]:
                if instance["State"]["Name"] == "running"  :
                    response = ssm.describe_instance_information(
                
                                Filters=[
                                    {
                                        'Key': 'InstanceIds',
                                        'Values': [
                                            instance["InstanceId"]
                                        ]
                                    },
                                ],
                                
                            )
                    instancelist.append(instance["InstanceId"])
                    print(instance["InstanceId"])
                    
                    if response['InstanceInformationList'][0]['PlatformType'] == 'Linux':
                    
                        #print(response['InstanceInformationList'][0]['PlatformType'])
                        callScript(ssm,instance["InstanceId"])
                            
                    else:
                        
                        continue
                    
    except ClientError as e:
        print(e)
    
        
def getObject(client):
    try:
        response = client.get_object(Bucket="ici-logreport", Key="Onboarding_Template.csv")
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


        
def callScript(ssm,insatnceID):
    response = ssm.send_command(
        InstanceIds=[insatnceID,''],
        DocumentName="AWS-RunRemoteScript",
        Parameters={
            "sourceType":["S3"],"sourceInfo":["{\"path\":\"https://s3.amazonaws.com/ici-taniumreports/createAccount.sh\"}"],
            "commandLine":["createAccount.sh"]
            }, 
        OutputS3BucketName='ici-logreport',
        #OutputS3KeyPrefix='Logs',
        )
                
                # fetching command id for the output
    command_id = response["Command"]["CommandId"]
    sleep(5)
        
                # fetching command output
    output = ssm.get_command_invocation(CommandId=command_id, InstanceId=insatnceID)
    print(output)

import json
import boto3
import urllib.parse
from botocore.exceptions import ClientError
import csv
from time import sleep
import os
import pandas as pd
import datetime

def lambda_handler(event, context):
    # TODO implement
    s3_client=boto3.client('s3')
    ssm_client=boto3.client('ssm')
    if event:
        splunkUpgrade(s3_client,ssm_client)
    else:
        splunkUpgrade(s3_client,ssm_client)
       
    converttoCSV()
    putObeject(s3_client)


def splunkUpgrade(s3,ssm):
    Instance_List = []
    client=boto3.client('ec2')
    response = client.describe_instances()
    for i in response["Reservations"]:
        for instance in i["Instances"]:
            if instance["State"]["Name"] == "running"  :
                Instance_List.append(instance["InstanceId"])
    print(Instance_List)
    
    for instance in Instance_List:
        try :
            response = ssm.describe_instance_information(
                
                Filters=[
                    {
                        'Key': 'InstanceIds',
                        'Values': [
                            instance
                        ]
                    },
                ],
            
            )
            Platform=response['InstanceInformationList'][0]['PlatformType']
            if response['InstanceInformationList'][0]['PlatformType'] == 'Linux':
                print(response['InstanceInformationList'][0]['PlatformType'],instance)
                
                try:
                    response = ssm.send_command(
                        InstanceIds=[instance],
                        DocumentName="AWS-RunRemoteScript",
                        Parameters={
                        "sourceType":["S3"],"sourceInfo":["{\"path\":\"https://s3.amazonaws.com/ici-taniumreports/Splunk_upgrade.sh\"}"],
                        "commandLine":["Splunk_upgrade.sh"]
                        #"commands": ["ls"]
                        }, 
                        OutputS3BucketName=os.environ['SSMLogOutput'],
                        #OutputS3KeyPrefix='Logs',
                        )
                except ClientError as e:
                    print(e,instance)
                    
                    continue
                command_id = response["Command"]["CommandId"]
                sleep(5)
            
                # fetching command output
                output = ssm.get_command_invocation(CommandId=command_id, InstanceId=instance)
                print(output)
                logtoExcel(instance,command_id,Platform)
                
            else:
                print("Inside else part")
                print(response['InstanceInformationList'][0]['PlatformType'],instance)
                
                
                try:
                    response = ssm.send_command(
                        InstanceIds=[instance],
                        DocumentName="AWS-RunRemoteScript",
                        Parameters={
                        "sourceType":["S3"],"sourceInfo":["{\"path\":\"https://s3.amazonaws.com/ici-taniumreports/Splunk_upgrade.ps1\"}"],
                        "commandLine":["Splunk_upgrade.ps1"]
                        #"commands": ["ls"]
                        }, 
                        OutputS3BucketName=os.environ['SSMLogOutput'],
                        #OutputS3KeyPrefix='Logs',
                        )
                except ClientError as e:
                    print(e,instance)
                    
                    continue
                
                
                command_id = response["Command"]["CommandId"]
                sleep(5)
            
                # fetching command output
                output = ssm.get_command_invocation(CommandId=command_id, InstanceId=instance)
                print(output)
                logtoExcel(instance,command_id,Platform)
                
        except IndexError as e:
            print(e,instance)
            instance = ',' + instance
            date=',' + datetime.datetime.now().strftime('%m/%d/%Y%H:%M:%S')
            line=['Either SSM Agent is not installed or in not running state']
            line.extend((date,instance))
            with open('/tmp/output1.txt','a+') as output:
                output.seek(0)
                data = output.read(100)
                if len(data) > 0:
                    output.write("\n")
                            
                    output.writelines(line)
                    #output.seek(0)
                    print(output.read())
            continue       
       
def logtoExcel(instance,command_id,Platform):
    global file_content
    global response
    s3 = boto3.client('s3')
    if Platform == 'Linux':
        key = "Logs/{}/{}/awsrunShellScript/runShellScript/stdout".format(command_id,instance)
        #key="Logs/f3983a09-3bea-44bb-ab08-30ab1efa20ac/i-00f8a04d1022e9f9a/awsrunShellScript/runShellScript/stdout"
        print(key)
        var = datetime.datetime.now()
        
        date = ',' + var.strftime('%m/%d/%Y%H:%M:%S')
        insID = ',' + instance
        
        try:
            sleep(30)
            response = s3.get_object(Bucket=os.environ['Log_Bucket'], Key=key)
        except ClientError as e:
            
            if response['ResponseMetadata']['HTTPStatusCode'] != 200:
                return logtoExcel(instance,command_id,Platform)
    else:
        key = "Logs/{}/{}/awsrunPowerShellScript/runPowerShellScript/stdout".format(command_id,instance)
        
        print(key)
        var = datetime.datetime.now()
        
        date = ',' + var.strftime('%m/%d/%Y%H:%M:%S')
        insID = ',' + instance
        
        try:
            sleep(30)
            response = s3.get_object(Bucket=os.environ['Log_Bucket'], Key=key)
        except ClientError as e:
            
            if response['ResponseMetadata']['HTTPStatusCode'] != 200:
                return logtoExcel(instance,command_id,Platform)
        
    file_content = response["Body"].read().decode('utf-8').splitlines()
    print(file_content)
    file_content.extend((date,insID))
    print(file_content)
        
    with open('/tmp/output1.txt','a+') as output:
        output.seek(0)
        data = output.read(100)
        if len(data) > 0:
            output.write("\n")
            
        output.writelines(file_content)
        #output.seek(0)
        print(output.read())

def converttoCSV():
    try:
        read_file = pd.read_csv ('/tmp/output1.txt',header=None)
        read_file.columns = ['Status','Date','InstanceId']
        read_file.to_csv ('/tmp/UpgradeStatus.csv', index=None)
    except ClientError as e:
        print(e)
        
def putObeject(client):
    
    try:
        s3 = boto3.resource('s3')
        s3.meta.client.upload_file('/tmp/UpgradeStatus.csv', 'ici-logreport', 'UpgradeStatus.csv')
    except ClientError as e:
        print(e)
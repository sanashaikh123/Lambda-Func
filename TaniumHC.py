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
    print("Received event: " + json.dumps(event, sort_keys=True))
    s3_client=boto3.client('s3')
    ssm_client=boto3.client('ssm')
    
    if event:
        bucket = event['Records'][0]['s3']['bucket']['name']
        key = urllib.parse.unquote_plus(event['Records'][0]['s3']['object']['key'], encoding='utf-8')
        
        getStatus(bucket,key)
        
    else:
            #yet to implement
        getSplunkHC(event,s3,ssm_client)
    
    convertToCSV()
    putObeject(s3_client)
    deleteObject(bucket,key,s3_client)
        
    
def getStatus(bucket,key):
    s3_client=boto3.client('s3')
    ssm=boto3.client('ssm')
    ec2=boto3.client('ec2')
    Instance_List = getObject(bucket,key,s3_client)
           
    for row in Instance_List:
        response = ec2.describe_instance_status(
            InstanceIds=[row['Instanceid']],
            IncludeAllInstances=True
        )
        
        if response['InstanceStatuses'][0]['InstanceState']['Name'] == 'running':
            if row['Application'] == "Tanium":
                
                response = ssm.send_command(
                InstanceIds=[row['Instanceid']],
                DocumentName="AWS-RunRemoteScript",
                Parameters={
                    "sourceType":["S3"],"sourceInfo":["{\"path\":\"https://s3.amazonaws.com/ici-taniumreports/TaniumHC.sh\"}"],
                    "commandLine":["TaniumHC.sh"]
                }, 
                OutputS3BucketName=os.environ['SSMLogOutput'],
                #OutputS3KeyPrefix='Logs',
                )
                
                # fetching command id for the output
                command_id = response["Command"]["CommandId"]
                sleep(5)
        
                # fetching command output
                output = ssm.get_command_invocation(CommandId=command_id, InstanceId=row['Instanceid'])
                print(output)
                logConversion(row['Instanceid'],command_id,row['Application'])
            
            elif row['Application'] == "Qaulys":
                response = ssm.send_command(
                InstanceIds=[row['Instanceid']],
                DocumentName="AWS-RunRemoteScript",
                Parameters={
                    "sourceType":["S3"],"sourceInfo":["{\"path\":\"https://s3.amazonaws.com/ici-taniumreports/Qaulys.sh\"}"],
                    "commandLine":["Qaulys.sh"]
                }, 
                OutputS3BucketName=os.environ['SSMLogOutput'],
                #OutputS3KeyPrefix='Logs',
                )
                
                # fetching command id for the output
                command_id = response["Command"]["CommandId"]
                sleep(5)
        
                # fetching command output
                output = ssm.get_command_invocation(CommandId=command_id, InstanceId=row['Instanceid'])
                print(output)
                logConversion(row['Instanceid'],command_id,row['Application'])
                
            else:
                response = ssm.send_command(
                InstanceIds=[row['Instanceid']],
                DocumentName="AWS-RunRemoteScript",
                Parameters={
                    "sourceType":["S3"],"sourceInfo":["{\"path\":\"https://s3.amazonaws.com/ici-taniumreports/Splunk.sh\"}"],
                    "commandLine":["Splunk.sh"]
                }, 
                OutputS3BucketName=os.environ['SSMLogOutput'],
                #OutputS3KeyPrefix='Logs',
                )
                
                # fetching command id for the output
                command_id = response["Command"]["CommandId"]
                sleep(5)
        
                # fetching command output
                output = ssm.get_command_invocation(CommandId=command_id, InstanceId=row['Instanceid'])
                print(output)
                logConversion(row['Instanceid'],command_id,row['Application'])
            
        else:
            instid=',' + row['Instanceid']
            appl=',' + row['Application']
            date=',' + datetime.datetime.now().strftime('%m/%d/%Y%H:%M:%S')
            line=['An instance is not in a valid state to reach',',NA',',NA',',NA',',NA',',NA',',NA',',NA',',']
            line.extend((date,instid,appl))
            with open('/tmp/output1.txt','a+') as output:
                output.seek(0)
                data = output.read(100)
                if len(data) > 0:
                    output.write("\n")
                    
                output.writelines(line)
                #output.seek(0)
                print(output.read())
            
        
def logConversion(instanceid,command_id,application):
    global file_content
    s3 = boto3.client('s3')
    
    #bucket = "ici-logreport"
    key = "Logs/{}/{}/awsrunShellScript/runShellScript/stdout".format(command_id,instanceid)
    #key="Logs/f3983a09-3bea-44bb-ab08-30ab1efa20ac/i-00f8a04d1022e9f9a/awsrunShellScript/runShellScript/stdout"
    print(key)
    var = datetime.datetime.now()
    
    date = ',' + var.strftime('%m/%d/%Y%H:%M:%S')
    insID = ',' + instanceid
    app = ',' + application
    sleep(35)
    response = s3.get_object(Bucket=os.environ['Log_Bucket'], Key=key)
    if response['ResponseMetadata']['HTTPStatusCode'] != 200:
        return logConversion(instanceid,command_id,application)
    else:
        try:
            file_content = response["Body"].read().decode('utf-8').splitlines()
            file_content.extend((date,insID,app))
            print(file_content)
            
        except ClientError as e:
            print(e)
        
        
    with open('/tmp/output1.txt','a+') as output:
        output.seek(0)
        data = output.read(100)
        if len(data) > 0:
            output.write("\n")
            
        output.writelines(file_content)
        #output.seek(0)
        print(output.read())
        
    '''
    a = os.listdir('/tmp')
    for x in a:
        print(x)
    '''
    return
        
def getObject(bucket,key,client):
    try:
        response = client.get_object(Bucket=bucket, Key=key)
        file_content = response["Body"].read().decode('utf-8').splitlines()
        reader = csv.DictReader(file_content)
        InstanceId = []
        for row in reader:
            InstanceId.append(row)
        print(InstanceId)
        return InstanceId
    
    except Exception as e:
        print(e)
        raise e

def putObeject(client):
    
    try:
        s3 = boto3.resource('s3')
        s3.meta.client.upload_file('/tmp/stdout.csv', 'ici-logreport', 'stdout.csv')
    except ClientError as e:
        print(e)

def convertToCSV():
    try:
        read_file = pd.read_csv ('/tmp/output1.txt',header=None)
        read_file.columns = ['Service','Config/auditd.conf File','Input.conf','Output.conf','Port 443','Port 80','Port 9997','Certification Files','000* Directories','Date','InstanceId','Application']
        read_file.to_csv ('/tmp/stdout.csv', index=None)
    except ClientError as e:
        print(e)
        
def deleteObject(bucket,key,s3):
    try:
        response = s3.delete_object(
        Bucket=bucket,
        Key=key,
        )
        
    except ClientError as e:
        print(e)
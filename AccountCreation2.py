import json
import json
import boto3
from botocore.exceptions import ClientError
import csv
from time import sleep
import os
import datetime



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
    for row in user_List:
        '''
        response = ssm.describe_instance_information(
                
                    Filters=[
                        {
                            'Key': 'InstanceIds',
                            'Values': [
                                        row["InstanceId"]
                                    ]
                        },
                    ],
                                
            )
        if response['InstanceInformationList'][0]['PlatformType'] == 'Linux':
            
            with open('/tmp/output1.txt','w+') as output:
                output.seek(0)
                #data = output.read(100)
                #if len(data) > 0:
                #   output.write("\n")
                output.writelines(row['User Id'])
                output.seek(0)
                print(output.read())
                putObject(s3)
            '''
        callScript(ssm)
        #else:
         #   continue
        #TODO implement 

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

def putObject(client):
    
    try:
        s3 = boto3.resource('s3')
        s3.meta.client.upload_file('/tmp/output1.txt', 'ici-logreport', 'user.txt')
    except ClientError as e:
        print(e)
        
def callScript(ssm):
    response = ssm.send_command(
        InstanceIds=[''],
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
    #output = ssm.get_command_invocation(CommandId=command_id, InstanceId=os.environ['InstanceID'])
    #print(output)
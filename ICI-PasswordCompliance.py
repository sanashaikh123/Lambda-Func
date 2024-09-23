from __future__ import print_function
import boto3
from botocore.exceptions import ClientError
import os
import json
import csv
from time import sleep
import datetime
import dateutil.parser
import sys
from datetime import timedelta

# These should be passed in via Lambda Environment Variables
try: 
    BLACKHOLE_GROUPNAME = os.environ['BLACKHOLE_GROUPNAME']
    ACTION_TOPIC_ARN = os.environ['ACTION_TOPIC_ARN']
    GRACE_PERIOD = int(os.environ['GRACE_PERIOD'])
    DISABLE_USERS = os.environ['DISABLE_USERS']
    SEND_EMAIL = os.environ['SEND_EMAIL']
    FROM_ADDRESS = os.environ['FROM_ADDRESS']
    EXPLANATION_FOOTER = os.environ['EXPLANATION_FOOTER']
    EXPLANATION_HEADER = os.environ['EXPLANATION_HEADER']
except KeyError as e:
    print("Key Error: " + e.message)
    sys.exit(1)

print("Loading function")

if DISABLE_USERS == "true":
    expired_message = "\nYour Password is {} days post expiration. Your permissions have been revoked.\n Kindly contact to AWS admins to activate your account. "
    #print(expired_message)
    key_expired_message = "\n{} AccessKey ID {} is {} days post expiration. It has been deactivated.Please find new keys.\n New_Access_Key : {} \n New_Secret_key : {} \n Kindly distribute it across your application & reach out to AWS admins in-case of any issues."
else:    
    expired_message = "\nYour Password is {} days post expiration. You must change your password or risk losing access. "
    #print(expired_message)
    key_expired_message = "\n\{} AccessKey ID {} is {} days post expiration. You must rotate this key or it will be deactivated. "


# Define a Global String to be the report output sent to ACTION_TOPIC_ARN
ACTION_SUMMARY = ""
REPORT_SUMMARY = ""
Key_Rotate_Message= ""

key_warn_message = "\n {} AccessKey ID {} is {} days from expiration. The key is going to be rotating on the last day. "
password_warn_message = "\nYour Password will expire in {} days.Kindly reset your password before last date or risk losing access."

email_subject = "Credential Expiration Notice From AWS Account: {}"

def lambda_handler(event, context):
    print("Received event: " + json.dumps(event, sort_keys=True))
    iam_client = boto3.client('iam')

    try: 
        if event['source'] == "aws.iam" : 
            print("source is aws iam")
            process_IAMEvent(event, context, iam_client)
        else:
            process_UsersCron(iam_client)
    except KeyError as e:
        # Probably called as a test event with out a source. This is what we want to do here. 
        print("error")
        process_UsersCron(iam_client)
    return 

def process_UsersCron(iam_client): 
    global ACTION_SUMMARY # This is what we send to the admins
    global REPORT_SUMMARY
    max_age = get_max_password_age(iam_client)
    account_name = iam_client.list_account_aliases()['AccountAliases'][0]
    #print(account_name)
    credential_report = get_credential_report(iam_client)

    # Iterate over the credential report, use the report to determine password expiration
    # Then query for access keys, and use the key creation data to determine key expiration
    for row in credential_report:
        global message
        global message1
        global expiryDays
        global keyDays
        expiryDays = None
        keyDays = None
 
        message1 = "" #this is what we send to service account owner
        message = "" # This is what we send to the user
        UsersToSendMail = ['' ]
        ExemptedKeys = ['']
        MailSendingDays = [15,10,5,0,-2]
        if row['password_enabled'] != "true":  
                # Process their Access Keys
            try:
                response = iam_client.list_access_keys( UserName=row['user'] )
                for key in response['AccessKeyMetadata'] :
                    if ((key['Status'] == "Inactive") or (row['user'] in ExemptedKeys)) : continue
                    
                    key_expires = days_till_expire(key['CreateDate'], max_age)
                    keyDays = key_expires
                    checkKey_Status("apiGatewayAuth" , iam_client)
                    rotate_key("","apiGatewayAuth" , iam_client)
                    message = message + key_expired_message.format(row['user'], key['AccessKeyId'], key_expires * -1,New_Access_Key,New_Secret_key) + "\n"
                    if key_expires <=0 :
                       
                        #rotate_key(key['AccessKeyId'], row['user'], iam_client) 
                        rotate_key("","apiGatewayAuth" , iam_client)
                        message = message + key_expired_message.format(row['user'], key['AccessKeyId'], key_expires * -1,New_Access_Key,New_Secret_key) + "\n" 
                        #print(message)
                        REPORT_SUMMARY = REPORT_SUMMARY + "\n {}'s Key {} expired {} days ago.Hence it has been rotated. ".format(row['user'], key['AccessKeyId'], key_expires * -1 )
                    elif key_expires <= GRACE_PERIOD:
                        message1 = message1 + key_warn_message.format(row['user'], key['AccessKeyId'], key_expires)
                        #print(message1)
                        REPORT_SUMMARY = REPORT_SUMMARY + "\n {}'s Key {} will expire {} days from now ".format(row['user'], key['AccessKeyId'], key_expires)
            except ClientError as e:
                continue
        

        # elif  is_user_expired(row['user'],row['password_enabled']) == 0:
        #     # Process their password
            
        #     password_expires = days_till_expire(row['password_last_changed'], max_age)
        #     expiryDays = password_expires
            
        #     if password_expires == 0 :
                
        #         REPORT_SUMMARY = REPORT_SUMMARY + "\n{}'s Password expired {} days ago".format(row['user'], password_expires)
        #         message = message + password_warn_message + "\n" + "Please note this is the last reminder post that your account get disabled".format(password_expires)
                
        #     elif password_expires <= -2 :
        #         disable_user(row['user'],iam_client)
        #         add_user_to_blackhole(row['user'], iam_client)
        #         REPORT_SUMMARY = REPORT_SUMMARY + "\n{}'s Password expired {} days ago".format(row['user'], password_expires * -1)
        #         message = message + expired_message.format(password_expires * -1)
                
                    
        #     elif password_expires <= GRACE_PERIOD :
                
        #         message = message + password_warn_message.format(password_expires)
        #         REPORT_SUMMARY = REPORT_SUMMARY + "\n{}'s Password Will expire in {} days".format(row['user'], password_expires)
                #print(REPORT_SUMMARY)
                #print(message)

              
        if (( expiryDays in MailSendingDays ) or (keyDays in MailSendingDays)): 
            
            if message != "": 
                client = boto3.client('iam')
                response = client.list_user_tags(
                    UserName=(row['user'])
                
                )['Tags']
                #print(response['Value'])
                #print(response)
                for tag in response:
                    #print(tag['Key'])
                    if tag['Key']=='email':
                        #print(tag['Key'],tag['Value'])
                        email_user(tag['Value'],message,account_name)
                        #email_user(response['Value'],message,account_na
                    else:
                        continue
                
            if message1 !="":
                for user in UsersToSendMail:
                    email_ServiceAccount(user,message1,account_name)
        
    # All Done. Send a summary to the ACTION_TOPIC_ARN, and print one out for the Lambda Logs
    print("Action Summary:" + ACTION_SUMMARY)
    if ACTION_SUMMARY != "": send_summary()
    if REPORT_SUMMARY != "": email_user(FROM_ADDRESS, REPORT_SUMMARY, account_name )
    return

def get_credential_report(iam_client):
    resp1 = iam_client.generate_credential_report()
    if resp1['State'] == 'COMPLETE' :
        try: 
            response = iam_client.get_credential_report()
            
            credential_report_csv = response['Content']
            #print(type(credential_report_csv))
            
            # print(credential_report_csv)
            credential_report_csv1 = credential_report_csv.decode('utf-8').splitlines()
            reader = csv.DictReader(credential_report_csv1)
            # print(reader.fieldnames)
            credential_report = []
            for row in reader:
                credential_report.append(row)
                #print(credential_report)
            return(credential_report)
        except ClientError as e:
            print("Unknown error getting Report: " + e)
    else:
        sleep(2)
        return get_credential_report(iam_client)
        
def is_user_expired(username,password_enabled):
    client = boto3.client('iam')
    
    try:
        response = client.list_groups_for_user(UserName=username)
        #print(response)
    except ClientError as e:
        return 1

    for group in response['Groups'] :
        if ((group['GroupName'] == BLACKHOLE_GROUPNAME) and (password_enabled == "false")):
            return 1
        elif ((group['GroupName'] == BLACKHOLE_GROUPNAME) and (password_enabled == "true")): 
            remove_user_from_blackhole(username,client)
            return 0
        
    return 0

def days_till_expire(last_changed, max_age):
    # Ok - So last_changed can either be a string to parse or already a datetime object.
    # Handle these accordingly
    if type(last_changed) is str:
        last_changed_date=dateutil.parser.parse(last_changed).date()
        
    elif type(last_changed) is datetime.datetime:
        last_changed_date=last_changed.date()
        
    else:
        # print("last_changed", last_changed)
        # print(type(last_changed))
        return -99999
    expires = (last_changed_date + datetime.timedelta(max_age)) - datetime.date.today()
    
    return(expires.days)


def get_max_password_age(iam_client):
    try: 
        response = iam_client.get_account_password_policy()
      
        return response['PasswordPolicy']['MaxPasswordAge']
    except ClientError as e:
        print("Unexpected error in get_max_password_age: %s" +e.message ) 
        

    
def email_user(email, message, account_name):
   
    global ACTION_SUMMARY # This is what we send to the admins
    if SEND_EMAIL != "True": return # Abort if we're not supposed to send email
    if message == "": return # Don't send an empty message
    client = boto3.client('ses')
    
    user = email.split('@') 
    
    body = EXPLANATION_HEADER + " "+ user[0] + "\n" + message + "\n\n" + EXPLANATION_FOOTER
    try: 
        response = client.send_email(
            Source=FROM_ADDRESS,
            Destination={ 'ToAddresses': [ email ] },
            Message={
                'Subject': { 'Data': email_subject.format(account_name) },
                'Body': { 'Text': { 'Data': body } }
            }
        )
        ACTION_SUMMARY = ACTION_SUMMARY  + "\n Email Sent to {}".format(email)
        return 
    
 
    except ClientError as e:
        print("Failed to send message to {}: {}".format(email, e))
        ACTION_SUMMARY = ACTION_SUMMARY + "\n ERROR: Message to {} was rejected: {}".format(email, e)
        
def email_ServiceAccount(email, message, account_name):
   
    global ACTION_SUMMARY # This is what we send to the admins
    if SEND_EMAIL != "True": return # Abort if we're not supposed to send email
    if message == "": return # Don't send an empty message
    client = boto3.client('ses')
    
      
    body = EXPLANATION_HEADER + " " +"Admins" + "\n" + message + "\n\n" + EXPLANATION_FOOTER
    try: 
        response = client.send_email(
            Source=FROM_ADDRESS,
            Destination={ 'ToAddresses': [ email ] },
            Message={
                'Subject': { 'Data': email_subject.format(account_name) },
                'Body': { 'Text': { 'Data': body } }
            }
        )
        ACTION_SUMMARY = ACTION_SUMMARY + "\n Email Sent to {}".format(email)
        return 
    
 
    except ClientError as e:
        print("Failed to send message to {}: {}".format(email, e))
        ACTION_SUMMARY = ACTION_SUMMARY + "\nERROR: Message to {} was rejected: {}".format(email, e)
    
def rotate_key(AccessKeyId, UserName, iam_client):
    print("inside rotate")
    if DISABLE_USERS != "true": return
    global ACTION_SUMMARY
    global Key_Rotate_Message
    global New_Access_Key
    global New_Secret_key
    
    
    try:
        response = iam_client.create_access_key(
        UserName=UserName
        )
        New_Access_Key = response['AccessKey']['AccessKeyId']
        New_Secret_key = response['AccessKey']['SecretAccessKey']
        CreateDate = response['AccessKey']['CreateDate']
        
        response = iam_client.update_access_key(
            UserName=UserName,
            AccessKeyId=AccessKeyId,
            Status='Inactive'
        )
        
        #print(Key_Rotate_Message)
        ACTION_SUMMARY = ACTION_SUMMARY + "\n AccessKeyId {} for user {} has been rotated & user has been informed".format(AccessKeyId, UserName)
        
            
        if response['ResponseMetadata']['HTTPStatusCode'] != 200:
            handle_error("Adding User to Blackhole Group", username, response['ResponseMetadata'])
        else: 
            return 0
        
    except ClientError as e:
        print(e)
        #         #print("User can have a maximum of two access keys (active or inactive) at a time.Please delete either of the keys.")
        # #ACTION_SUMMARY = ACTION_SUMMARY + "\n User can have a maximum of two access keys (active or inactive) at a time.Deleting inactive key."
        # res = iam_client.list_access_keys(UserName=UserName)['AccessKeyMetadata']
        # print("response",res)
        
        # for res in res:
            
        #     if res['Status'] == 'Inactive':
                    
        #         response = iam_client.delete_access_key(
        #         AccessKeyId=res['AccessKeyId'],
        #         UserName=UserName
        #         )
            
        #     else res['Status'] == 'Active':
        #         response = iam_client.delete_access_key(
        #         AccessKeyId=res['AccessKeyId'],
        #         UserName=UserName
        #         )
                 
        
        
        
        
def checkKey_Status(UserName,iam_client):
    print("inside checkKey_Status")
    global ACTION_SUMMARY
    ACTION_SUMMARY = ACTION_SUMMARY + "\n User can have a maximum of two access keys (active or inactive) at a time.Deleting inactive key."
    res = iam_client.list_access_keys(UserName=UserName)['AccessKeyMetadata']
    print("response",res)
    active_keys = []
        
    for res in res:
        
        if res['Status'] == 'Inactive':
                    
            response = iam_client.delete_access_key(
            AccessKeyId=res['AccessKeyId'],
            UserName=UserName
            )
            
        elif res['Status'] == 'Active':
            active_keys.append(res['AccessKeyId'])
            
    print("active_keys....",active_keys,active_keys[1])
    response = iam_client.delete_access_key(
    AccessKeyId=active_keys[1],
    UserName=UserName
    )
            
    
    

def handle_error(action, username, ResponseMetadata):
    raise Exception("ERROR" + action + " User: " + username + " Details: " + ResponseMetadata)
    

# if called by an IAM Event, do stuff. Not yet implemented
def process_IAMEvent(event, context, iam_client):

    api_call = event['detail']['eventName']
    if api_call == "CreateLoginProfile" :
        process_CreateLoginProfile(event,context)
        return 0
    elif api_call == "EnableMFADevice" :
        process_EnableMFADevice(event,context)
        return 0
    elif api_call == "DeactivateMFADevice" :
        process_DeactivateMFADevice(event,context)
        return 0
    else:
        raise Exception("Invalid API Call: " + api_call)
        
# Send the Summary of actions taken to the SNS topic
def send_summary():
    global ACTION_SUMMARY
    client = boto3.client('sns')

    message = "The following Actions were taken by the Expire Users Script at {}: ".format( datetime.datetime.now() ) + ACTION_SUMMARY

    response = client.publish(
        TopicArn=ACTION_TOPIC_ARN,
        Message=message,
        Subject="Expire Users Report for {}".format(datetime.date.today())
    )

def disable_user(username, iam_client):
    if DISABLE_USERS != "true": return
    global ACTION_SUMMARY
    
    ACTION_SUMMARY = ACTION_SUMMARY + "\n User account {} has been disabled \n".format(username)
    try :
        response = iam_client.delete_login_profile(
        UserName=username
        )
    
        if response['ResponseMetadata']['HTTPStatusCode'] != 200:
            handle_error("Deleting login profile ", username, response['ResponseMetadata'])
        else: 
            return 0
            
    except ClientError as e:
        ACTION_SUMMARY = ACTION_SUMMARY + "\n Unable to disable User account {}:{}.\n".format(username,e)
        
# Add the user to the group that only allows them to reset their password
def add_user_to_blackhole(username, iam_client):
    if DISABLE_USERS != "true": return
    global ACTION_SUMMARY
    ACTION_SUMMARY = ACTION_SUMMARY + "\n Added {} to Blackhole Group".format(username)
    response = iam_client.add_user_to_group(
        GroupName=os.environ['BLACKHOLE_GROUPNAME'],
        UserName=username
    )
    if response['ResponseMetadata']['HTTPStatusCode'] != 200:
        handle_error("Disabling User Account", username, response['ResponseMetadata'])
    else: 
        return 0
        
#  would remove the user from the blackhole group once they did change their password
def remove_user_from_blackhole(username, iam_client):
    global ACTION_SUMMARY
    response = iam_client.remove_user_from_group(
        GroupName=os.environ['BLACKHOLE_GROUPNAME'],
        UserName=username
    )
    if response['ResponseMetadata']['HTTPStatusCode'] != 200:
        handle_error("Removing User from Blackhole Group", username, response['ResponseMetadata'])
    else: 
        ACTION_SUMMARY = ACTION_SUMMARY + "\n User {} account has been reactivated and removed from the expired group. \n".format(username)
        return 0

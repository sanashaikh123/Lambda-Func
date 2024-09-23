import json
import boto3
import dateutil.parser
import datetime
from datetime import datetime,timedelta
import sys
from botocore.exceptions import ClientError
import os
from time import sleep

global body_html
global past
global now
body_html = " "
now = datetime.utcnow() 
past = now - timedelta(weeks=1)

def lambda_handler(event, context):
    if event:
        fetchReport()
    else:
        fetchReport()
        
def fetchReport():
    owner = ['']
    owners_email = {"" }
    
    client = boto3.client('cloudwatch')
    ec2 = boto3.client('ec2')
    for owner in owner:
        global body_html
        instancelist = []
        taglist = {}
        body_html =  " "
        
        response = ec2.describe_instances(
                    Filters=[
                    {
                        'Name': 'tag:'+"Owner",
                        'Values': [owner]
                    }
                ]
            
            
            )
        if owner in owners_email :
            email = owners_email[owner]
            
        for reservation in (response["Reservations"]):
            
            for instance in reservation["Instances"]:
                if instance["State"]["Name"] == "running"  :
                    
                    instancelist.append(instance["InstanceId"])
                
                for tags in instance["Tags"]:
                    if tags["Key"] == "Name":
                        taglist[instance["InstanceId"]] = tags['Value']

            volumeID = (instance['BlockDeviceMappings'][0]['Ebs']['VolumeId'])
    
        for instance in instancelist:
            response1 = client.get_metric_statistics(
                Namespace='AWS/EC2',
                MetricName='CPUUtilization',
                Dimensions=[
                    {
                        'Name': 'InstanceId',
                        'Value': instance
                    },
                            ],
                    StartTime=past ,
                    EndTime=now,
                    Period=10800,
                    Statistics=[
                            'Average',
                    ],
                            
                    Unit='Percent'
                )
            CPU =[]
            for cpu in response1['Datapoints']:
                if 'Average' in cpu:
                    CPU.append(cpu['Average'])
                                    
                    Sum = sum(CPU)
                    Avg = (Sum/len(CPU))
                  
                        #print(instance["InstanceId"] , Avg)
                
            if instance in taglist :
                tag = taglist[instance]
                
            balance = getBurstBalance(volumeID)
            stealTime = getCPUStealTime(instance)
                        #print("stealTime",stealTime)
                            
            utilization = getDiskUtilization(instance)
                    #print("utilization",utilization)
            htmlBody(instance,Avg,utilization,balance,stealTime,tag)
                
        
        sendMail(email)  
    
def htmlBody(InstId,CPU,disk,balance,stealTime,tag):
    
    global body1
    global body2
    global body_html
    
    body1 = """<html>
    
        <head></head>
        <style>
            table, th, td {
                  border: 1px solid white;
                  border-collapse: collapse;
                  width:1000px;
                  background-color: #E3BDF5 
                }
            th {
                padding:0em 0em .5em;
                text-align:center
                border-bottom:1px dotted #FFF;
                font-size:95%
                   ;
                }
            td  {
                padding:0em 0em .5em;font-size:81%;
                }
            
           
        </style>
        
        <body>
          <p>Hi<br>You are receiving this mail because you are the owner of the below mentioned resources.<br>This is to bring your attention to the weekly utilization of your resources.
            Kindly have a look at highlighted underutilized resources and do let us know if any one of them are acceptable to decommission.</p>
          <table>
            
            <tr>
                <th>Instance Name</th>
                <th>Instance Id</th>
                <th>CPU Utilization</th>
                <th>Disk Utilization</th>
                <th>Burst Balance</th>
                <th>CPU Steal Time</th>
            </tr>
            """
    if CPU <= 15 :
        if disk >=75 :
            if ((balance == 'NA') or (balance <=15)):
                if stealTime >=10:
  
                    body_html = body_html + """
                        <tr>
                            <td >{}</td>
                            <td >{}</td>
                            <td style="background-color:#F9DC0A" > {}</td>
                            <td style="background-color:#BA033D">{}</td>
                            <td style="background-color:#BA033D">{}</td>
                            <td style="background-color:#BA033D">{}</td>
                         </tr>""".format(tag,InstId,CPU,disk,balance,stealTime)
                else:
                    
                    body_html = body_html + """
                        <tr>
                            <td >{}</td>
                            <td >{}</td>
                            <td style="background-color:#F9DC0A" > {}</td>
                            <td style="background-color:#BA033D">{}</td>
                            <td style="background-color:#BA033D">{}</td>
                            <td >{}</td>
                         </tr>""".format(tag,InstId,CPU,disk,balance,stealTime)
                    
            else:
                if stealTime >=10:
                    body_html = body_html + """
                    <tr>
                        <td >{}</td>
                        <td >{}</td>
                        <td style="background-color:#F9DC0A" > {}</td>
                        <td style="background-color:#BA033D">{}</td>
                        <td >{}</td>
                        <td style="background-color:#BA033D">{}</td>
                     </tr>""".format(tag,InstId,CPU,disk,balance,stealTime)
                else:

                    body_html = body_html + """
                        <tr>
                            <td >{}</td>
                            <td >{}</td>
                            <td style="background-color:#F9DC0A" > {}</td>
                            <td style="background-color:#BA033D">{}</td>
                            <td >{}</td>
                            <td >{}</td>
                         </tr>""".format(tag,InstId,CPU,disk,balance,stealTime)
        elif ((balance == 'NA') or (balance <= 15)) :
            if stealTime >=10:
                
                body_html = body_html + """
                    <tr>
                        <td >{}</td>
                        <td >{}</td>
                        <td style="background-color:#F9DC0A"> {}</td>
                        <td >{}</td>
                        <td style="background-color:#BA033D">{}</td>
                        <td style="background-color:#BA033D">{}</td>
                    </tr>""".format(tag,InstId,CPU,disk,balance,stealTime)
            else :
                body_html = body_html + """
                    <tr>
                        <td >{}</td>
                        <td >{}</td>
                        <td style="background-color:#F9DC0A"> {}</td>
                        <td >{}</td>
                        <td style="background-color:#BA033D">{}</td>
                        <td >{}</td>
                    </tr>""".format(tag,InstId,CPU,disk,balance,stealTime)
                
        else :
            body_html = body_html + """
                <tr>
                    <td >{}</td>
                    <td >{}</td>
                    <td style="background-color:#F9DC0A"> {}</td>
                    <td >{}</td>
                    <td >{}</td>
                    <td >{}</td>
                </tr>""".format(tag,InstId,CPU,disk,balance,stealTime)
            
    elif disk >= 75 :
        if ((balance == 'NA') or (balance <=15)) :
            if stealTime >=10:
                body_html = body_html + """
                    <tr>
                        <td >{}</td>
                        <td >{}</td>
                        <td > {}</td>
                        <td style="background-color:#BA033D">{}</td>
                        <td style="background-color:#BA033D">{}</td>
                        <td style="background-color:#BA033D">{}</td>
                    </tr>""".format(tag,InstId,CPU,disk,balance,stealTime)
            else:
                body_html = body_html + """
                    <tr>
                        <td >{}</td>
                        <td >{}</td>
                        <td > {}</td>
                        <td style="background-color:#BA033D">{}</td>
                        <td style="background-color:#BA033D">{}</td>
                        <td >{}</td>
                    </tr>""".format(tag,InstId,CPU,disk,balance,stealTime)
                
        else:
            body_html = body_html + """
                    <tr>
                        <td >{}</td>
                        <td >{}</td>
                        <td > {}</td>
                        <td style="background-color:#BA033D">{}</td>
                        <td > {}</td>
                        <td > {}</td>
                </tr>""".format(tag,InstId,CPU,disk,balance,stealTime)
    elif ((balance == 'NA') or (balance <=15)) :
        if stealTime >=10:
            body_html = body_html + """
                    <tr>
                        <td >{}</td>
                        <td >{}</td>
                        <td > {}</td>
                        <td > {}</td>
                        <td style="background-color:#BA033D">{}</td>
                        <td style="background-color:#BA033D">{}</td>
                    </tr>""".format(tag,InstId,CPU,disk,balance,stealTime)
        else:
            body_html = body_html + """
                    <tr>
                        <td >{}</td>
                        <td >{}</td>
                        <td > {}</td>
                        <td > {}</td>
                        <td style="background-color:#BA033D">{}</td>
                        <td >{}</td>
                    </tr>""".format(tag,InstId,CPU,disk,balance,stealTime)
            
    elif stealTime >=10:
        body_html = body_html + """
                <tr>
                    <td >{}</td>
                    <td >{}</td>
                    <td > {}</td>
                    <td > {}</td>
                    <td > {}</td>
                    <td style="background-color:#BA033D">{}</td>
                    
                </tr>""".format(tag,InstId,CPU,disk,balance,stealTime)
        
        
    else :
        body_html = body_html + """
                <tr>
                    <td >{}</td>
                    <td >{}</td>
                    <td > {}</td>
                    <td>{}</td>
                    <td > {}</td>
                    <td > {}</td>
                </tr>""".format(tag,InstId,CPU,disk,balance,stealTime)

    body2 = """</body>
        </html>
               """  
    print(body_html)           
def sendMail(email):
    global body_html
        
    SENDER = "Weekly Summary<awscompliancealert@gmail.com>"
    #RECIPIENT = ""
    
    #CC = ""
    
    SUBJECT = "AWS Resource Utilization Weekly Report - {}".format(datetime.today())
        
    # The character encoding for the email.
    CHARSET = "UTF-8"
    
    CC = ""
    CC1 = ""
    client = boto3.client('ses')
    try:
    #Provide the contents of the email.
        response = client.send_email(
            Destination={
                'ToAddresses': [
                    email
                ],
                'CcAddresses':[CC,CC1]
                
            },
            Message={
                'Body': {
                    'Html': {
                        'Charset': CHARSET,
                        'Data': body1 + body_html + body2,
                    },
                },
                'Subject': {
                    'Charset': CHARSET,
                    'Data': SUBJECT,
                },
            },
            Source=SENDER,
        )
    # Display an error if something goes wrong.	
    except ClientError as e:
        print(e.response['Error']['Message'])
    else:
        print("Email sent! Message ID:")
     
    
def getDiskUtilization(InstId):
    Avg1 = 0
    client = boto3.client('cloudwatch')
    if InstId == 'i-0103b937c1c8f8fa7':
        response = client.get_metric_statistics(
            Namespace='CWAgent',
            MetricName='disk_used_percent',
              
            Dimensions=[
                {
                    'Name': 'InstanceId',
                    'Value': InstId
                },
                {
                    'Name': 'fstype',
                    'Value': 'ext4'
                },
                {
                    'Name': 'path',
                    'Value': '/'
                },
                
            ],
            StartTime=past,
            EndTime=now,
            Period=10800,
            Statistics=[
                'Average',
            ],
        )
        
    else :
        response = client.get_metric_statistics(
            Namespace='CWAgent',
            MetricName='disk_used_percent',
              
            Dimensions=[
                {
                    'Name': 'InstanceId',
                    'Value': InstId
                },
                {
                    'Name': 'fstype',
                    'Value': 'xfs'
                },
                {
                    'Name': 'path',
                    'Value': '/'
                },
                
            ],
            StartTime=past,
            EndTime=now,
            Period=10800,
            Statistics=[
                'Average',
            ],
        )
    Disk =[]
    for disk in response['Datapoints']:
        if 'Average' in disk:
            Disk.append(disk['Average'])
                                
        Sum = sum(Disk)
        Avg1 = (Sum/len(Disk))
                                        
    return Avg1
def getBurstBalance(vid):
    global past
    global now
    Avg1 = 0
    volume_type =  ['gp3','io1','io2','standard','sc1','st1']
    
   
    client = boto3.client('cloudwatch')
    ec2 = boto3.client('ec2')
    response = ec2.describe_volumes(
        VolumeIds=[vid,],
    )
    for vol in response['Volumes']:
        
        if ( vol['VolumeType']) in volume_type:
            return 'NA'
        else:
    
            response = client.get_metric_statistics(
                Namespace='AWS/EBS',
                MetricName='BurstBalance',
                Dimensions=[
                    {
                        'Name': 'VolumeId',
                        'Value': vid
                    },
                ],
                StartTime=past,
                EndTime=now,
                Period=10800,
                Statistics=[
                    'Average',
                ],
                
                Unit='Percent'
            )
            Burst =[]
            for burst in response['Datapoints']:
                if 'Average' in burst:
                    Burst.append(burst['Average'])
                                    
                Sum = sum(Burst)
                Avg1 = (Sum/len(Burst))
                                        
            return Avg1

def getCPUStealTime(InstId):
    Avg1 = 0
    client = boto3.client('cloudwatch')
    response = client.get_metric_statistics(
        Namespace='CWAgent',
        MetricName='cpu_usage_steal',
        Dimensions=[
            {
                'Name': 'InstanceId',
                'Value': InstId
            },
            {
                'Name': 'cpu',
                'Value': 'cpu-total'
            }
        ],
        StartTime=past,
        EndTime=now,
        Period=10800,
        Statistics=[
            'Average',
        ],
        
        Unit='Percent'
    )
    
    Time =[]
    for time in response['Datapoints']:
        if 'Average' in time:
            Time.append(time['Average'])
                                
        Sum = sum(Time)
        Avg1 = (Sum/len(Time))
                                        
    return Avg1
    
    
    
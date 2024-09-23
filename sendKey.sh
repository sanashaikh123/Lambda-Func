#!/bin/bash
aws s3 cp "s3://ici-logreport/NewUser_Details.csv" /opt
printf '%s\n\n' "$(sed '1d' /opt/NewUser_Details.csv)" > /opt/NewUser.csv
sed -i 's///g' /opt/NewUser.csv
insID=`(curl http://169.254.169.254/latest/meta-data/instance-id)` 2>/dev/null
while IFS="," read -r Name Key InstanceId
do
        if [[ $insID = $InstanceId ]]; then

#                sudo su - $Name
                echo $Key > /home/$Name/.ssh/authorized_keys
        else
                continue
        fi
done < "/opt/NewUser.csv"
#rm -rf /opt/NewUser.csv /opt/NewUser_Details.csv


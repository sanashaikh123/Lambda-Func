#!/bin/bash
aws s3 cp s3://ici-logreport/UserToDelete.csv /opt
aws s3 cp s3://ici-taniumreports/User_Inventory.csv /opt
insID=`(curl http://169.254.169.254/latest/meta-data/instance-id)` 2>/dev/null
printf '%s\n\n' "$(sed '1d' /opt/UserToDelete.csv)" > /opt/NewUser.csv
sed -i 's///g' /opt/NewUser.csv 
sed -i '/^[[:space:]]*$/d' /opt/NewUser.csv

while IFS="," read -r user Owner Key 
do

	if grep -q $user "/etc/passwd"  ;then
                        userdel -r $user 2>/dev/null
			sed -i "/$user/"d "/opt/User_Inventory.csv"
        else
		continue

         fi

done < "/opt/NewUser.csv" 
aws s3 cp /opt/User_Inventory.csv s3://ici-taniumreports
rm -rf /opt/NewUser.csv /opt/UserToDelete.csv  /opt/User_Inventory.csv

#!/bin/bash
aws s3 cp s3://ici-logreport/Onboarding_Template.csv /opt
aws s3 cp s3://ici-taniumreports/User_Inventory.csv /opt
insID=`(curl http://169.254.169.254/latest/meta-data/instance-id)` 2>/dev/null
printf '%s\n\n' "$(sed '1d' /opt/Onboarding_Template.csv)" > /opt/NewUser.csv
sed -i 's/
//g' /opt/NewUser.csv 
sed -i '/^[[:space:]]*$/d' /opt/NewUser.csv


while IFS="," read -r user Owner Key 
do

	if grep -q $user "/etc/passwd"  ;then
                        continue
        else
                        if grep -q mywizardusers /etc/group;then


                                useradd -m $user  -s /bin/bash
                                mkdir /home/$user/.ssh/
                                touch /home/$user/.ssh/authorized_keys
					  chown -R $user:$user /home/$user
                                chmod 700 /home/$user/.ssh
                                chmod 600 /home/$user/.ssh/authorized_keys
                                echo $Key > /home/$user/.ssh/authorized_keys
                                usermod -aG mywizardusers $user
                        else
                                groupadd mywizardusers
                                useradd -m $user -s /bin/bash
                                mkdir /home/$user/.ssh/
                                touch /home/$user/.ssh/authorized_keys
				        chown -R $user:$user /home/$user
                                chmod 700 /home/$user/.ssh
                                chmod 600 /home/$user/.ssh/authorized_keys
                                echo $Key > /home/$user/.ssh/authorized_keys
                                usermod -aG mywizardusers $user
                        fi
                        if grep -q $user /etc/passwd ;then
                                 echo "$user,$insID" >> /opt/User_Inventory.csv
                        fi

         fi

done < "/opt/NewUser.csv" 
aws s3 cp /opt/User_Inventory.csv s3://ici-taniumreports
rm -rf /opt/NewUser.csv /opt/Onboarding_Template.csv /opt/User_Inventory.csv

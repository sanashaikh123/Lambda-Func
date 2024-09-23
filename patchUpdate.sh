if egrep -q '^(NAME="Ubuntu")' /etc/os-release; then
	aws s3 cp s3://ici-logreport/Updates.csv /opt
	printf '%s\n\n' "$(sed '1d' /opt/Updates.csv)" > /opt/UpdateList.csv
	sed -i 's/^M//g' /opt/UpdateList.csv
	sed -i '/^[[:space:]]*$/d' /opt/UpdateList.csv
	while IFS="," read -r list commands
		do
			echo $list
			apt-get install -y $list
			apt-get upgrade -y
		done < /opt/UpdateList.csv
else
	aws s3 cp s3://ici-logreport/Updates.csv /opt
        printf '%s\n\n' "$(sed '1d' /opt/Updates.csv)" > /opt/UpdateList.csv
        sed -i 's/^M//g' /opt/UpdateList.csv
        sed -i '/^[[:space:]]*$/d' /opt/UpdateList.csv
        while IFS="," read -r list
                do
			echo $list
			yum clean all
                        yum install -y install $list
                        yum update -y
			yum-complete-transaction
                done < /opt/UpdateList.csv


fi
rm -rf  /opt/UpdateList.csv /opt/Updates.csv

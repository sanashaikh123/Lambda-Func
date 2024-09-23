#!/bin/bash
if egrep -q '^(NAME="Ubuntu")' /etc/os-release; then
	disk=`(df -h /dev/root |awk '{ print $5 }'|sed '/Use/d')`
	echo "$disk"
else
	disk=`(df -h /dev/nvme0n1p1 |awk '{ print $5 }'|sed '/Use/d')`
	echo "$disk"

fi

#!/bin/bash

# This foreman-hook adds the Comment from the Satellite Host object to the VM object in vCenter
#
# Requires jq () in order to pick out the sub elements from the host object passed from Satellite
#
# Calls on /usr/local/bin/

host_obj=$(cat -)
#logger "hook: ${host_obj}"
echo  ${host_obj}

hostname=$(echo ${host_obj} | jq '.host.name' | tr -d \"  )
comment=$(echo ${host_obj} | jq '.host.comment' | tr -d \" )
compute_resource_name=$(echo ${host_obj} | jq '.host.compute_resource_name' | tr -d \")

logger "Hook: Updating ${hostname} with new Comment:"
echo "Hostname ${hostname}"
comment="${comment}    url: https://satellite.example.com/hosts/${hostname}"
logger "Hook: ${comment}"
echo "Comment ${comment}"

vcenter_url=""
case "$compute_resource_name" in
        vcenter01)
                vcenter_url="vcenter01.example.com"
                ;;
 
esac

# Remove domain as vCenter doesn't see this
#hostname=$(echo ${hostname} | cut -d'.' -f1)


/usr/local/bin/add_description_to_vsphere_vm.py --hostname "${hostname}" --vcenter "${vcenter_url}" --comment "${comment}"
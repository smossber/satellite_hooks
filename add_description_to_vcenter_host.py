#!/usr/bin/env python
#-*- coding: utf-8 -*-
"""
This script is used by foreman-hook 02-add-description-to-vcenter.sh


This script is a rework of the following pyvmomi community sample:
https://github.com/vmware/pyvmomi-community-samples/blob/master/samples/change_vm_vif.py

The wait_for_tasks() function is copied from here:
https://github.com/vmware/pyvmomi-community-samples/blob/master/samples/tools/tasks.py

The function is put directly in this script to remove dependencies from the tools directory.

"""

import atexit
from pyVmomi import vim
from pyVmomi import vmodl
from pyVim import connect
import argparse
import sys
import syslog
import json
import codecs

parser = argparse.ArgumentParser(description='vcenter-change-host-vlan.py')
parser.add_argument('--hostname', required=True, help='The name of the host you want to modify')
parser.add_argument('--comment', required=True, help='The comment/description you want to add to the host')
parser.add_argument('--vcenter', required=True, help='The vCenter the host is in')

args = parser.parse_args()

hostname = args.hostname
comment = args.comment
vcenter = args.vcenter

# Insert address and credentials for the vCenter your VM exist in
username = ""
password = ""
port = 443

# You can remove these if you don't want to clutter syslog
syslog.syslog("hook:: vcenter-change-host-vlan.py")
syslog.syslog("hook: updating VM " + hostname + " with Annotation: " + comment)
#syslog.syslog("DEBUG: target VLAN: " + target_vlan)
syslog.syslog("hook: on vCenter: " + vcenter)

def get_obj(content, vimtype, name):
    """
     Get the vsphere object associated with a given text name
    """
    obj = None
    container = content.viewManager.CreateContainerView(content.rootFolder,
                                                        vimtype, True)

    for view in container.view:
        if view.name == name:
            obj = view
            break

    if obj is None:
        print "ERROR: Couldn't find VM object named " + hostname + " in vCenter " + vcenter
        syslog.syslog(syslog.LOG_ERR, "ERROR: Couldn't find VM object named " + hostname + " in vCenter " + vcenter)
        sys.exit(1)
    else:
        return obj

def wait_for_tasks(service_instance, tasks):
    """Given the service instance si and tasks, it returns after all the
   tasks are complete
   """
    property_collector = service_instance.content.propertyCollector
    task_list = [str(task) for task in tasks]
    # Create filter
    obj_specs = [vmodl.query.PropertyCollector.ObjectSpec(obj=task)
                 for task in tasks]
    property_spec = vmodl.query.PropertyCollector.PropertySpec(type=vim.Task,
                                                               pathSet=[],
                                                               all=True)
    filter_spec = vmodl.query.PropertyCollector.FilterSpec()
    filter_spec.objectSet = obj_specs
    filter_spec.propSet = [property_spec]
    pcfilter = property_collector.CreateFilter(filter_spec, True)
    try:
        version, state = None, None
        # Loop looking for updates till the state moves to a completed state.
        while len(task_list):
            update = property_collector.WaitForUpdates(version)
            for filter_set in update.filterSet:
                for obj_set in filter_set.objectSet:
                    task = obj_set.obj
                    for change in obj_set.changeSet:
                        if change.name == 'info':
                            state = change.val.state
                        elif change.name == 'info.state':
                            state = change.val
                        else:
                            continue

                        if not str(task) in task_list:
                            continue

                        if state == vim.TaskInfo.State.success:
                            # Remove task from taskList
                            task_list.remove(str(task))
                        elif state == vim.TaskInfo.State.error:
                            raise task.info.error
            # Move to next version
            version = update.version
    finally:
        if pcfilter:
            pcfilter.Destroy()



# Start program
if __name__ == "__main__":
        try:
                service_instance = connect.SmartConnect(host=vcenter, user=username, pwd=password, port=port)
        except vim.fault.InvalidLogin:
                print "Invalid credentials for " + vcenter + ". Exiting.."
                syslog.syslog(syslog.LOG_ERR, "ERROR: Invalid credentials for vCenter " + vcenter)
                sys.exit(1)
        atexit.register(connect.Disconnect, service_instance)
        content = service_instance.RetrieveContent()
        vm = get_obj(content, [vim.VirtualMachine], hostname)

        # Fetch the spec object
        spec = vim.vm.ConfigSpec()
        # Set annotations (Notes) to input comment
        # ignore stuff we can't decode
        spec.annotation = comment.decode("utf-8","ignore")

        # start the reconfiguration
        task = vm.ReconfigVM_Task(spec)
        wait_for_tasks(service_instance, [task])
        print("Done setting values.")
        syslog.syslog("hook: Updated Annotations successfully")
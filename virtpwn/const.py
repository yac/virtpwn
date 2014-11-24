MACHINE_CONF_FN = 'machine.yml'
MACHINES_CONF_FN = 'machines.yml'
CONF_FNS = [MACHINES_CONF_FN, MACHINE_CONF_FN]

DATA_FN = '.virtpwn'

VMS_NOT_CREATED, VMS_POWEROFF, VMS_RUNNING, VMS_RESPONDING = range(4)
VMS_DESC = [
    "not created",
    "powered off",
    "running",
    "responding"
]

VMINIT_FAIL = 'fail'
VMINIT_DONE = 'done'

VM_MNT = 'mnt'

WAIT_START = 300

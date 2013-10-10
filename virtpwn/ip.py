import cmd
import exception
import log
from log import term

from lxml import etree

def _get_instance_ip(mac):
    errors = []
    # 1. get IP from DHCP leases
    try:
        cmd_str = 'grep -i "%s" /var/lib/libvirt/dnsmasq/*.leases' % mac
        lease = cmd.run_or_die(cmd_str).rstrip()
        ip = lease.split(" ")[2]
        log.verbose("Got IP from DHCP leases.")
        return ip
    except Exception as e:
        errors.append(('DHCP leases', str(e)))

    # 2. get IP from ARP table
    try:
        arp_stdout = cmd.run_or_die('arp -n')
        for line in arp_stdout.splitlines()[1:]:
            parts = line.split()
            if parts[2] == mac:
                log.verbose("Got IP from ARP cache.")
                return parts[0]
    except Exception as e:
        errors.append(('ARP cache', str(e)))
    else:
        errors.append(('ARP cache', 'MAC not found'))

    errsum = "\n".join(map(lambda e: " * %s" % ": ".join(e), errors))
    desc = 'Failed to obtain IP address from following sources:\n%s' % errsum
    log.verbose(desc)
    return None


def get_instance_ip(name):
    """
    Return instance IP address.
    """
    out = cmd.virsh_or_die("dumpxml %s" % name)
    domxml = etree.fromstring(out)
    mac_path = "devices/interface/mac"
    # Filters could be added here if needed a la
    # mac_path = "devices/interface[@type='bridge']/mac"
    mac = domxml.find(mac_path).attrib["address"].lower().strip()
    return _get_instance_ip(mac)

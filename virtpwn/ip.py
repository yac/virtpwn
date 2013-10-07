import cmd
import exception
import log
from log import term

from lxml import etree

def _get_instance_ip_lease(mac):
    # network name - use default for now
    net = 'default'
    cmd_str = ('grep -i "%(mac)s" '
               '/var/lib/libvirt/dnsmasq/%(net)s.leases'
               % {'mac': mac, 'net': net})
    lease = cmd.run_or_die(cmd_str).rstrip()
    ip = lease.split(" ")[2]
    return ip

def get_instance_ip(name):
    """
    Return instance IP address.
    """
    out = cmd.virsh_or_die("dumpxml %s" % name)
    domxml = etree.fromstring(out)
    mac_path = "devices/interface/mac"
    # mac_path = "devices/interface[@type='bridge']/mac"
    mac = domxml.find(mac_path).attrib["address"].lower().strip()

    ip = None
    # So far, only method is from DHCP lease, but in future other methods
    # such as qemu guest daemon or sniffing can be added.
    try:
        ip = _get_instance_ip_lease(mac)
    except exception.CommandFailed, ex:
        log.verbose('Failed to get instance IP address from DHCP leases:')
        cmd.log_cmd_fail(ex, fail_log_fun=log.verbose,
                            out_log_fun=log.verbose)
    except Exception, ex:
        log.verbose('Failed to get instance IP address from DHCP leases: %s' % ex)
    return ip

import virtpwn.cmd as cmd
import virtpwn.exception as exception
import virtpwn.log as log

def provision(pwn, tasks):
    prov = pwn.conf['provision']
    try:
        fabfile = prov['fabfile']
    except KeyError:
        raise exception.MissingRequiredConfigOption(option='provision/fabfile')
    ip = pwn.ip()
    if not ip:
        raise exception.Bug("Failed to determine IP address, can't provision.")
    log.info("Provisioning %s using Fabric..." % ip)
    cmd_seq = ['fab', '-f', fabfile, '-H', ip, '-u', 'root'] + tasks
    cmd.run_interactive(cmd_seq)

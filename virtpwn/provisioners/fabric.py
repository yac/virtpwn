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
    user = 'root'
    log.info("Provisioning %s using Fabric..." % ip)
    cmd_str = 'fab -f "%(fabfile)s" -H "%(host)s" -u "%(user)s" %(tasks)s' % {
                  'fabfile': fabfile,
                  'host': ip,
                  'user': user,
                  'tasks': " ".join(tasks)
              }
    cmd.run_or_die(cmd_str, stdout=True, stderr=True)

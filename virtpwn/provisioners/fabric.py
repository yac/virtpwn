import virtpwn.cmd as cmd
import virtpwn.exception as exception
import virtpwn.log as log
import virtpwn.fabric

def parse_tasks(tasks):
    def parse_task(task):
        if isinstance(task, dict):
            if len(task) != 1:
                raise exception.InvalidTask(task=task)
            for t, tt in task.items():
                return "%s:%s" % (t, tt)
        return task
    return map(parse_task, tasks)

def provision(pwn, conf, tasks=None):
    if not tasks:
        try:
            tasks = conf.get('tasks')
        except AttributeError:
            reason = "incorrect provisioning configuration"
            raise exception.InvalidConfig(reason=reason)
    if not tasks:
        msg = "No provisioning tasks specified."
        raise exception.MissingRequiredConfigOption(message=msg)
    if 'fabfile' in conf:
        fabfile = conf['fabfile']
    else:
        fabfile = virtpwn.fabric.BASE_FABFILE
        log.verbose('No fabfile specified, using builin: %s' % fabfile)
    ip = pwn.get_ip(wait=0, fatal=True)
    pwn.ensure_ssh()
    log.info("Provisioning %s using Fabric..." % ip)
    ftasks = parse_tasks(tasks)
    cmd_str = 'fab -f "%(fabfile)s" -H "%(host)s" -u "%(user)s" %(tasks)s' % {
                  'fabfile': fabfile,
                  'host': ip,
                  'user': pwn.vm_user,
                  'tasks': " ".join(ftasks)
              }
    cmd.run_or_die(cmd_str, stdout=True, stderr=True)

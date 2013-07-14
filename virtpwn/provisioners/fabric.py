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

def tasks_magic(tasks, pwn):
    """
    Magically preproccess tasks.

    Provide additional information from pwn manager in order to reduce
    redundancy in machine config file.
    """
    def replace(old, new):
        if old in tasks:
            log.verbose("Magically modifying task '%s' to '%s'" % (old,new))
            i = tasks.index(old)
            tasks[i] = new
    replace('hostname', 'hostname:%s' % pwn.vm_id)
    replace('add_admin_user', 'add_admin_user:%s' % pwn.vm_user)

def provision(pwn, conf, tasks=None, user=None):
    if not tasks:
        try:
            tasks = conf.get('tasks')
        except AttributeError:
            print tasks
            reason = "incorrect provisioning configuration"
            raise exception.InvalidConfig(reason=reason)
    if not tasks:
        msg = "No provisioning tasks specified."
        raise exception.MissingRequiredConfigOption(message=msg)
    ip = pwn.get_ip(wait=0, fatal=True)
    pwn.ensure_ssh()
    if 'fabfile' in conf:
        fabfile = conf['fabfile']
        magic = False
    else:
        fabfile = virtpwn.fabric.BASE_FABFILE
        magic = True
        log.verbose('No fabfile specified, using builin: %s' % fabfile)
    if magic:
        tasks_magic(tasks, pwn)
    if 'user' in conf:
        # user setting in conf overrides passed user
        user = conf['user']
    elif not user:
        user = pwn.vm_user
    log.info("Provisioning %s using Fabric as %s..." % (ip, user))
    ftasks = parse_tasks(tasks)
    cmd_str = 'fab -f "%(fabfile)s" -H "%(host)s" -u "%(user)s" %(tasks)s' % {
                  'fabfile': fabfile,
                  'host': ip,
                  'user': user,
                  'tasks': " ".join(ftasks)
              }
    cmd.run_or_die(cmd_str, stdout=True, stderr=True)

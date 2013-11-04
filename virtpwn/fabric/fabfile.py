from fabric.api import run, local, env, settings
from fabric.utils import warn
import re


DEFAULT_PASSWORD = 'secret'


def ensure_ssh_known_host(user=None):
    if not user:
        user = env.user
    local("ssh -o StrictHostKeyChecking=no -o PasswordAuthentication=no"
            " '%s@%s' exit 2> /dev/null ; :" % (user, env.host))

def ssh_copy_id(password=DEFAULT_PASSWORD, user=None):
    if not user:
        user = env.user
    ensure_ssh_known_host(user)
    local("sshpass -p '%s' ssh-copy-id '%s@%s'" % (password, user, env.host))

def update_hosts(name, old_name=None):
    if not old_name:
        old_name = run("hostname")
    hosts = run("cat /etc/hosts")
    m = re.search("^127\.0\.0\.1\s.*$", hosts, flags=re.M)
    if not m:
        run("echo '127.0.0.1    %s' >> /etc/hosts" % name)
        return
    line = m.group(0)
    if re.search('\s%s[\s$]' % name, line):
        return
    if old_name and old_name != name and old_name != 'localhost' \
       and re.search("\s%s[\s$]" % old_name, line):
        # replace old hostname with new one
        run("sed -i -r 's/(\s)%s(\s|$)/\1%s\2/g' /etc/hosts" % (old_name, name))
    else:
        # append new hostname
        run("sed -i -r '/^127\.0\.0\.1|::1/s#$# %s#' /etc/hosts" % name)

def hostname(name):
    update_hosts(name)
    run("echo '%s' > /etc/hostname" % name)
    run("hostname '%s'" % name)

def ensure_confline(line, rex, fn):
    if run("grep -qE '%s' '%s' ; echo -n $?" % (rex, fn)) == '0':
        run("sed -ir 's/%s/%s/' '%s'" % (rex, line, fn))
    else:
        run("echo '%s' >> '%s'" % (line, fn))

def admin_sudo_nopass():
    ensure_confline('%wheel	ALL=(ALL)	NOPASSWD: ALL', '^%wheel[[:space:]].*',
                    '/etc/sudoers')

def add_admin_user(user, password=DEFAULT_PASSWORD):
    run("test '%s' != root" % user)
    if run("id -u '%s' > /dev/null ; echo -n $?" % user) != '0':
        run("useradd -m '%s'" % (user))
    run("usermod -a -G wheel '%s'" % (user))
    run("echo '%s:%s' | chpasswd" % (user, password))
    ssh_copy_id(password, user=user)
    admin_sudo_nopass()

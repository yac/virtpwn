from fabric.api import run, local, env, settings


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

def hostname(name):
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
    run("test '%s' != root")
    if run("id -u '%s' > /dev/null ; echo -n $?" % user) != '0':
        run("useradd -m -G wheel '%s'" % (user))
        run("echo '%s:%s' | chpasswd" % (user, password))
    ssh_copy_id(password, user=user)
    admin_sudo_nopass()

from fabric.api import run, local, env

def ssh_copy_id(password, user='root'):
    local("sshpass -p '%s' ssh-copy-id '%s@%s'" % (password, user, env.host))

def hello():
    run('date > /tmp/virtpwn.was.here')

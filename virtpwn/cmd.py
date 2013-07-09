import exception
import log
from log import term

import subprocess
import sys

def log_cmd_fail(ex, fail_log_fun=log.warning, out_log_fun=log.info):
    fail_str = term.red('command failed:')
    fail_log_fun('%s %s' % (fail_str, ex.cmd))
    if ex.out:
        out_log_fun(term.bold("stdout:"))
        out_log_fun(ex.out)
    if ex.err:
        out_log_fun(term.yellow("stderr:"))
        out_log_fun(ex.err)

def run(cmd):
    log.command('$ %s' % cmd)
    prc = subprocess.Popen(cmd, shell=True,
                           stdout=subprocess.PIPE,
                           stderr=subprocess.PIPE)
    out, err = prc.communicate()
    errcode = prc.returncode
    return (errcode, out.rstrip(), err.rstrip())

def run_or_die(cmd):
    ret, out, err = run(cmd)
    if ret != 0:
        raise exception.CommandFailed(cmd=cmd, ret=ret, out=out, err=err)
    return out

def virsh(cmd):
    return run('virsh %s' % cmd)

def virsh_or_die(cmd):
    return run_or_die('virsh %s' % cmd)

def run_interactive(cmd):
    try:
        p = subprocess.Popen(cmd, shell=False, stdin=sys.stdin, stdout=sys.stdout)
        p.communicate()
    except KeyboardInterrupt:
        pass

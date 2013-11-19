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

def run(cmd, stdout=False, stderr=False):
    log.command('$ %s' % cmd)
    if stdout:
        sout = sys.stdout
    else:
        sout = subprocess.PIPE
    if stderr:
        serr = sys.stderr
    else:
        serr = subprocess.PIPE
    prc = subprocess.Popen(cmd, shell=True, stdout=sout, stderr=serr)
    out, err = prc.communicate()
    errcode = prc.returncode
    if out:
        out = out.rstrip()
    if err:
        err = err.rstrip()
    return (errcode, out, err)

def run_or_die(cmd, stdout=False, stderr=False):
    ret, out, err = run(cmd, stdout=stdout, stderr=stderr)
    if ret != 0:
        raise exception.CommandFailed(cmd=cmd, ret=ret, out=out, err=err)
    return out

def run_in_background(cmd):
    log.command('$ %s &' % cmd)
    prc = subprocess.Popen(cmd, shell=True)
    return prc.pid

def virsh(cmd):
    return run('virsh %s' % cmd)

def virsh_or_die(cmd):
    return run_or_die('virsh %s' % cmd)

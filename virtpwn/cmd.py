import subprocess
import exception
import log
from log import term

def run(cmd):
    prc = subprocess.Popen(cmd, shell=True,
                           stdout=subprocess.PIPE,
                           stderr=subprocess.PIPE)
    out, err = prc.communicate()
    errcode = prc.returncode
    return (errcode, out.rstrip(), err.rstrip())

def run_or_die(cmd):
    log.info("$ %s" % cmd)
    #ret, out, err = run(cmd)
    ret, out, err = 0, "", ""
    if ret != 0:
        log.warning("$ %s" % cmd)
        log.warning("returned %d" % ret)
        if out:
            log.info(term.bold("stdout:"))
            log.info(out)
        if err:
            log.info(term.red("stderr:"))
            log.info(err)
        raise exception.CommandFailed(cmd=cmd)

def virsh(cmd):
    return run("virsh %s" % cmd)

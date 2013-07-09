# -*- encoding: utf-8 -*-

import argh
import cmd
import core
import exception
import log
from log import term

from argh import arg, aliases


@arg('-n', '--no-provision', help="disable provisioning")
@aliases('start')
def up(no_provision=False):
    """
    Ready and start the machine.
    """
    pwn = core.get_pwn_manager()
    pwn.do_up(provision=not no_provision)


@arg('-f', '--force', help="force shutdown")
@aliases('stop', 'halt', 'poweroff')
def down(force=False):
    """
    Poweroff the machine.
    """
    pwn = core.get_pwn_manager()
    pwn.do_down(force=force)


@aliases('status', 'state')
def info():
    """
    Show the machine information.
    """
    pwn = core.get_pwn_manager()
    pwn.do_info()


@aliases('pwn', 'destroy', 'rm')
def delete():
    """
    Delete the machine.
    """
    pwn = core.get_pwn_manager()
    msg = "Do you want to %s machine %s? [Yn] " % (
        term.red("DELETE"), term.bold(pwn.name))
    cfrm = raw_input(msg)
    if cfrm == '' or cfrm.lower() == 'y':
        pwn.do_delete()
    else:
        print "Aborted."


def ssh():
    """
    Connect to machine IP using ssh.
    """
    pwn = core.get_pwn_manager()
    pwn.do_ssh()


@arg('tasks', nargs='*')
def provision(tasks):
    """
    Provision the machine.
    """
    pwn = core.get_pwn_manager()
    pwn.do_provision(tasks=tasks)


def parse_global_args(args):
    if args.verbose >= 2:
        log.log.setLevel(log.DEBUG)
    elif args.verbose >= 1:
        log.log.setLevel(log.VERBOSE)
    if args.show_commands or args.verbose > 0:
        # enable command logging as well
        log.log_commands = True

def main():
    parser = argh.ArghParser()
    commands = [up, down, delete, info, ssh, provision]
    parser.add_commands(commands)
    parser.add_argument('-c', '--show-commands', action='store_true',
                        help="display virsh/shell commands used")
    parser.add_argument('-v', '--verbose', action='count',
                        help="increase output verbosity", default=0)
    try:
        parser.dispatch(pre_call=parse_global_args)
    except exception.CommandFailed, ex:
        cmd.log_cmd_fail(ex)
    except exception.ProjectConfigNotFound, ex:
        log.info(ex)

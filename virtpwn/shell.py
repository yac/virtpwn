# -*- encoding: utf-8 -*-

import argh
import cmd
import core
import exception
import log
import sys
from log import term

from argh import arg, aliases
from argh.assembling import SUPPORTS_ALIASES
from argh.constants import ATTR_ALIASES


@arg('-n', '--no-provision', help="disable provisioning")
@aliases('start', 'run')
def up(no_provision=False):
    """
    Ready and start the machine.
    """
    pwn = core.get_pwn_manager()
    pwn.do_up(provision=not no_provision)


@arg('-f', '--force', help="force shutdown")
@aliases('stop', 'halt', 'die', 'poweroff')
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

@arg('-f', '--force', help="force shutdown")
@aliases('pwn', 'destroy', 'rm')
def delete(force=False):
    """
    Delete the machine.
    """
    confirm = not force
    pwn = core.get_pwn_manager()
    pwn.do_delete(confirm=confirm)


def ssh():
    """
    Connect to machine IP using ssh.
    """
    pwn = core.get_pwn_manager()
    pwn.do_ssh()


def view():
    """
    Display the graphical console with virt-viewer.
    """
    pwn = core.get_pwn_manager()
    pwn.do_view()



@arg('src', nargs='?', help="machine directory to mount")
@arg('dst', nargs='?', help="host mount point")
def mount(src=None, dst=None):
    """
    Mount the machine directory.
    """
    pwn = core.get_pwn_manager()
    pwn.do_mount(src, dst)


@arg('dst', nargs='?', help="host mount point")
@arg('-c', '--clean-only', help="clean invalid mounts only")
def umount(dst=None, clean_only=False):
    """
    Unmount the machine director{ies,y}.
    """
    pwn = core.get_pwn_manager()
    pwn.do_umount(dst, clean_only=clean_only)


@arg('-i', '--init', help="run initial setup")
@arg('tasks', nargs='*', help="specify provisioning tasks")
@aliases('prv', 'fab')
def provision(tasks, init=False):
    """
    Provision the machine.
    """
    pwn = core.get_pwn_manager()
    pwn.do_provision(tasks=tasks, init=init)


COMMANDS = [up, down, delete, info, ssh, view, provision, mount, umount]


def translate_alias(command):
    for c in COMMANDS:
        if hasattr(c, ATTR_ALIASES):
            aliases = getattr(c, ATTR_ALIASES)
            for alias in aliases:
                if alias == command:
                    return c.__name__
    return command

def process_argv():
    argv = sys.argv[1:]
    if not SUPPORTS_ALIASES:
        # do aliasing ourselves if argparse doesn't support it
        for i, arg in enumerate(argv):
            if arg[0] != '-':
                argv[i] = translate_alias(arg)
                break
    return argv


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
    parser.add_commands(COMMANDS)
    parser.add_argument('-c', '--show-commands', action='store_true',
                        help="display virsh/shell commands used")
    parser.add_argument('-v', '--verbose', action='count',
                        help="increase output verbosity", default=0)
    try:
        argh.dispatch(parser, argv=process_argv(), pre_call=parse_global_args)
    except exception.CommandFailed, ex:
        cmd.log_cmd_fail(ex)
    except exception.ProjectConfigNotFound, ex:
        log.info(ex)

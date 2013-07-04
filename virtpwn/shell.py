# -*- encoding: utf-8 -*-

import core
import argh
from argh import arg, aliases
import log

@arg('-n', '--no-provision', help="disable provisioning")
def up(no_provision=False):
    """
    Ready and start the machine.
    """
    pwn = core.get_pwn_manager()
    pwn.do_up(provision=not no_provision)


@arg('-f', '--force', help="force shutdown")
@aliases('down', 'stop', 'poweroff')
def halt(force=False):
    """
    Poweroff the machine.
    """
    pwn = core.get_pwn_manager()
    pwn.do_halt(force=force)


def status():
    """
    Show the machine status.
    """
    pwn = core.get_pwn_manager()
    pwn.do_status()


def parse_global_args(args):
    if args.verbose >= 2:
        log.log.setLevel(log.DEBUG)
    elif args.verbose >= 1:
        log.log.setLevel(log.VERBOSE)

def main():
    parser = argh.ArghParser()
    parser.add_commands([up, halt, status])
    parser.add_argument('-v', '--verbose', action='count',
                        help="increase output verbosity", default=0)
    parser.dispatch(pre_call=parse_global_args)

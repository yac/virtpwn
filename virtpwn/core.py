# -*- encoding: utf-8 -*-

from cmd import run, virsh
import const
import exception
import cmd
import log
from log import term

import logging
import os.path
import time
import yaml


VERSION = '0.0.1'



def find_project(path=None):
    """
    Search for poject config files in specified/current directory and its
    parents.

    Return (project_path, project_config) tuple if found, otherwise
    raise ProjectConfigNotFound.
    """
    if not path:
        path = '.'
    spath = os.path.abspath(path).split(os.sep)
    while spath:
        apath = os.sep.join(spath)
        for conf_fn in const.CONF_FNS:
            conf_path = os.path.join(apath, conf_fn)
            if os.path.isfile(conf_path):
                return (apath, conf_fn)
        spath.pop()
    raise exception.ProjectConfigNotFound()


def get_pwn_manager(path=None):
    """
    Return pwn project manager which provides unified control interface.
    """
    path, conf_fn = find_project(path)
    if conf_fn is const.MACHINE_CONF_FN:
        return MachinePwnManager(path, conf_fn)
    else:
        # TODO: const.MACHINES_CONF_FN
        # multiple machine config file shall be supported
        raise NotImplemented(
                  "Multiple machine config (%s) not implemented yet." % \
                  conf_fn)


class MachinePwnManager(object):
    def __init__(self, path=None, conf_fn=None):
        self.data = {}
        self.conf = {}
        if path and conf_fn:
            self.load(path, conf_fn)
        else:
            self.path = path
            self.conf_fn = conf_fn

    def abs_conf_fn(self):
        return os.path.join(self.path, self.conf_fn)

    def abs_data_fn(self):
        return os.path.join(self.path, const.DATA_FN)

    def _load_conf(self):
        abs_conf_fn = self.abs_conf_fn()
        log.verbose("Machine config: %s" % abs_conf_fn)
        conf_file = file(abs_conf_fn, 'r')
        self.conf = yaml.load(conf_file)
        log.debug(" -> %s" % self.conf)

    def _check_state(self):
        log.debug("Checking machine state...")
        self.id = None
        if 'vm_id' in self.data:
            self.id = self.data['vm_id']
            # TODO: actually check
            self.state = const.VMS_POWEROFF
        else:
            self.state = const.VMS_NOT_CREATED

    def _load_data(self):
        abs_data_fn = self.abs_data_fn()
        if not os.path.isfile(abs_data_fn):
            log.verbose("No machine data: %s" % abs_data_fn)
            return
        data_file = file(abs_data_fn, 'r')
        log.verbose("Machine data: %s" % abs_data_fn)
        self.data = yaml.load(data_file)
        log.debug(" -> %s" % self.data)

    def load(self, path, conf_fn):
        self.path = path
        self.conf_fn = conf_fn
        self.name = self.path.split(os.sep)[-1]
        log.verbose("Loading machine %s" % term.bold(self.name))
        self._load_conf()
        self._load_data()
        self._check_state()

    def _save_data(self):
        abs_data_fn = self.abs_data_fn()
        data_file = file(abs_data_fn, 'w')
        log.verbose("Updating machine data: %s" % abs_data_fn)
        yaml.dump(self.data, data_file)

    def _get_base(self):
        base = self.conf.get('base')
        if not base:
            raise MissingRequiredConfigOption(option='base')
        return base

    def _generate_id(self, base):
        stamp = int(time.time())
        self.id = "%s_%s_%d" % (self.name, base, stamp)

    def vm_create(self):
        log.verbose("Creating new %s VM.")
        assert(self.id is None)
        base = self._get_base()
        self._generate_id(base)
        log.debug("New VM ID: %s" % self.id)
        cmdstr = 'sudo virt-clone -o "%s" -n "%s" --auto-clone' % \
                 (base, self.id)
        cmd.run_or_die(cmdstr)
        self.data['vm_id'] = self.id
        self._save_data()

    def vm_start(self):
        log.verbose("Starting %s VM: %s", term.bold(self.name), self.id)

    def do_up(self, provision=True):
        log.verbose("Bringing %s up." % term.bold(self.name))
        if self.state == const.VMS_NOT_CREATED:
            self.vm_create()
        if self.state < const.VMS_RUNNING:
            self.vm_start()
        else:
            log.info("%s already running.", term.bold(self.name))


    def do_halt(self, force=False):
        print "bringing machine(s) DOWN"
        print "forced: %s" % force

    def do_status(self):
        log.info("%s VM %s." % (term.bold(self.name),
                                     const.VMS_DESC[self.state]))
        if self.state >= const.VMS_POWEROFF:
            log.info("VM ID: %s" % term.bold(self.id))


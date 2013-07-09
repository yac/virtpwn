# -*- encoding: utf-8 -*-

from cmd import run, virsh
import cmd
import const
import exception
import ip
import log
from log import term
import provision

import logging
import hashlib
import os.path
import time
import yaml


VERSION = '0.1'


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
        self.vm_id = None
        self.conf = {}
        self._ip = None
        if path and conf_fn:
            self.load(path, conf_fn)
        else:
            self.path = path
            self.conf_fn = conf_fn

    @property
    def name_pp(self):
        return term.bold(self.name)

    @property
    def state_pp(self):
        if self.state >= const.VMS_RUNNING:
            tfun = term.green
        else:
            tfun = term.yellow
        return tfun(const.VMS_DESC[self.state])

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

    def _load_data(self):
        abs_data_fn = self.abs_data_fn()
        if not os.path.isfile(abs_data_fn):
            log.verbose("No machine data: %s" % abs_data_fn)
            return
        data_file = file(abs_data_fn, 'r')
        log.verbose("Machine data: %s" % abs_data_fn)
        data = yaml.load(data_file)
        self.vm_id = data.get('vm_id')
        log.debug(" -> %s" % data)

    def _check_state(self):
        log.debug("Checking machine state...")
        if self.vm_id:
            ret, out, err = virsh('domstate "%s"' % self.vm_id)
            if ret != 0:
                log.verbose("No VM found for saved data. Cleaning.")
                self._remove_vm_data()
                self.state = const.VMS_NOT_CREATED
            else:
                if out == 'shut off':
                    self.state = const.VMS_POWEROFF
                elif out == 'running':
                    self.state = const.VMS_RUNNING
                else:
                    raise exception.VirshParseError(out=out)
        else:
            self.state = const.VMS_NOT_CREATED
        log.debug("%s seems to be %s." % (self.name_pp, self.state_pp))

    def load(self, path, conf_fn):
        self.path = path
        self.conf_fn = conf_fn
        self.name = self.path.split(os.sep)[-1]
        log.verbose("Loading %s:" % self.name_pp)
        self._load_conf()
        self._load_data()
        self._check_state()

    def _save_data(self):
        data = {}
        if self.vm_id:
            data['vm_id'] = self.vm_id
        if data:
            abs_data_fn = self.abs_data_fn()
            log.verbose("Updating machine data: %s" % abs_data_fn)
            data_file = file(abs_data_fn, 'w')
            yaml.dump(data, data_file)

    def _remove_vm_data(self):
        self.vm_id = None
        # Currently, data contain only VM data, so just delete the data file.
        abs_data_fn = self.abs_data_fn()
        if os.path.isfile(abs_data_fn):
            os.remove(abs_data_fn)

    def _get_base(self):
        base = self.conf.get('base')
        if not base:
            raise MissingRequiredConfigOption(option='base')
        return base

    def _generate_id(self, base):
        stamp = int(time.time())
        hstamp = hashlib.sha1(str(stamp)).hexdigest()[0:4]
        self.vm_id = "%s_%s_%s" % (self.name, base, hstamp)

    def ip(self, wait=30, log_fun=log.info):
        assert(self.vm_id is not None)
        if self._ip:
            return self._ip
        self._ip = ip.get_instance_ip(self.vm_id)
        if not self._ip and wait:
            log_fun("Waiting for IP address for next %d s" % wait)
            log_fun("TODO: wait")
        return self._ip

    def vm_create(self):
        assert(self.vm_id is None)
        log.verbose("Creating new %s VM.")
        base = self._get_base()
        self._generate_id(base)
        log.debug("New VM ID: %s" % self.vm_id)
        cmdstr = 'sudo virt-clone -o "%s" -n "%s" --auto-clone' % \
                 (base, self.vm_id)
        cmd.run_or_die(cmdstr)
        self._save_data()
        self._check_state()
        if self.state != const.VMS_POWEROFF:
            print self.state
            raise exception.Bug("New VM cloned but in wrong state.")

    def vm_start(self):
        assert(self.state == const.VMS_POWEROFF)
        assert(self.vm_id is not None)
        log.verbose("Starting %s VM: %s", self.name_pp, self.vm_id)
        cmd.virsh_or_die('start "%s"' % self.vm_id)

    def vm_stop(self, force=False):
        assert(self.state >= const.VMS_RUNNING)
        assert(self.vm_id is not None)
        cmd_str = 'destroy "%s"' % self.vm_id
        if not force:
            cmd_str += ' --graceful'
        cmd.virsh_or_die(cmd_str)

    def vm_destroy(self):
        assert(self.vm_id is not None)
        cmd_str = 'undefine "%s" --remove-all-storage' % self.vm_id
        cmd.virsh_or_die(cmd_str)

    def vm_provision(self, tasks=None):
        ip = self.ip()
        assert(ip)
        prov = self.conf.get('provision')
        if not prov:
            raise exception.MissingRequiredConfigOption(option='provision')
        if not tasks:
            tasks = prov.get('tasks')
            if not tasks:
                msg = "No provisioning tasks specified."
                raise exception.MissingRequiredConfigOption(message=msg)
        provision.provision(self, tasks)

    def do_up(self, provision=True):
        if self.state == const.VMS_NOT_CREATED:
            log.info("Creating new %s...", self.name_pp)
            self.vm_create()
        if self.state < const.VMS_RUNNING:
            log.info("Starting %s...", self.name_pp)
            self.vm_start()
            if provision:
                self.vm_provision()
        else:
            log.info("%s is already running.", self.name_pp)

    def do_down(self, force=False):
        if self.state == const.VMS_NOT_CREATED:
            log.info("%s isn't created.", self.name_pp)
        elif self.state < const.VMS_RUNNING:
            log.info("%s isn't running.", self.name_pp)
        else:
            log.info("Stopping %s..." % self.name_pp)
            self.vm_stop(force)

    def do_delete(self):
        if self.state == const.VMS_NOT_CREATED:
            log.info("%s isn't created.", self.name_pp)
            return
        if self.state >= const.VMS_RUNNING:
            log.info("Force stopping %s..." % self.name_pp)
            self.vm_stop(force=True)
        log.info("Deleting %s..." % self.name_pp)
        self.vm_destroy()

    def do_info(self):
        log.info("%s is %s." % (self.name_pp, self.state_pp))
        if self.state >= const.VMS_POWEROFF:
            log.info("")
            log.info("virt domain: %s" % self.vm_id)
        if self.state >= const.VMS_RUNNING:
            ip = self.ip()
            if ip:
                log.info("IP address: %s" % ip)
            else:
                log.info("IP address can't be determined.")

    def do_ssh(self, wait=30):
        if self.state < const.VMS_RUNNING:
            self.do_up()
        ip = self.ip(wait=wait)
        if not ip:
            log.info("Failed to determine IP address, can't SSH.")
        # TODO: configurable
        user = 'root'
        cmd_seq = ['/usr/bin/ssh', '%s@%s' % (user, ip)]
        cmd.run_interactive(cmd_seq)

    def do_provision(self, tasks=None, wait=30):
        if self.state < const.VMS_RUNNING:
            self.do_up(provision=False)
        ip = self.ip(wait=wait)
        if not ip:
            log.info("Failed to determine IP address, can't provision.")
            return
        self.vm_provision(tasks)

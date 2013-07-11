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
import os
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
        log.debug(" -> %s" % data)
        self.vm_id = data.get('vm_id')
        self.vm_init = data.get('vm_init')
        self.vm_mnt = data.get('vm_mnt', {})

    def _save_data(self):
        data = {}
        if self.vm_id:
            data['vm_id'] = self.vm_id
        if self.vm_init:
            data['vm_init'] = self.vm_init
        if self.vm_mnt:
            data['vm_mnt'] = self.vm_mnt
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
        # TODO: do a mounts cleanup here or elsewhere

    def load(self, path, conf_fn):
        self.path = path
        self.conf_fn = conf_fn
        self.name = self.path.split(os.sep)[-1]
        # config
        self.vm_id = None
        # TODO: configurable
        self.vm_user = 'root'
        self.vm_init = None
        self.vm_mnt = {}
        log.verbose("Loading %s:" % self.name_pp)
        self._load_conf()
        self._load_data()
        self._check_state()

    def _proj_path(self, *path):
        return os.path.join(self.path, *path)

    def _get_base(self):
        base = self.conf.get('base')
        if not base:
            raise MissingRequiredConfigOption(option='base')
        return base

    def _get_domains(self):
        doms_str = cmd.virsh_or_die('list --all --name')
        doms = doms_str.strip().split("\n")
        return doms

    def _generate_id(self, base):
        assert(self.name)
        doms = self._get_domains()
        new_id = self.name
        pfix = 0
        while new_id in doms:
            pfix += 1
            new_id = "%s_%d" % (self.name, pfix)
        if pfix > 0:
            log.verbose("%s domain exists, using %s" % (self.name, new_id))
        self.vm_id = new_id
        return self.vm_id

    def get_ip(self, wait=30, fatal=False, log_fun=log.info):
        assert(self.vm_id is not None)
        if self._ip:
            return self._ip
        self._ip = ip.get_instance_ip(self.vm_id)
        if not self._ip and wait:
            log_fun("Waiting for IP address for next %d s..." % wait)
            for i in range(0, wait):
                time.sleep(1)
                self._ip = ip.get_instance_ip(self.vm_id)
                if self._ip:
                    break
        if fatal and not self._ip:
            raise UnknownGuestAddress(machine=self.name)
        return self._ip

    def get_ssh_host(self):
        ip = self.get_ip(wait=0, fatal=True)
        return "%s@%s" % (self.vm_user, ip)

    def check_ssh(self):
        """
        Return True if SSH port is open.
        """
        ip = self.get_ip(wait=0)
        if not ip:
            return False
        port = 22
        # TODO: nc may be unavailable
        ret, _, _ = run(": | nc '%s' %d" % (ip, port))
        return (ret == 0)

    def ensure_ssh(self, wait=30, log_fun=log.info):
        assert(self.state >= const.VMS_RUNNING)
        self.get_ip()
        if self.check_ssh():
            return
        log_fun("Waiting for SSH connection for next %d s..." % wait)
        for i in range(0, wait):
            time.sleep(1)
            if self.check_ssh():
                return
        raise SshConnectionError(machine=self.name)

    def vm_create(self):
        assert(self.vm_id is None)
        log.verbose("Creating new %s VM.")
        base = self._get_base()
        self._generate_id(base)
        log.debug("New VM ID: %s" % self.vm_id)
        cmdstr = 'sudo virt-clone -o "%s" -n "%s" --auto-clone' % \
                 (base, self.vm_id)
        cmd.run_or_die(cmdstr, stdout=True)
        self._save_data()
        self._check_state()
        if self.state != const.VMS_POWEROFF:
            raise exception.Bug("New VM cloned but in wrong state.")

    def vm_start(self):
        assert(self.state == const.VMS_POWEROFF)
        assert(self.vm_id is not None)
        log.verbose("Starting %s VM: %s", self.name_pp, self.vm_id)
        cmd.virsh_or_die('start "%s"' % self.vm_id)

    def vm_stop(self, force=False):
        assert(self.state >= const.VMS_RUNNING)
        assert(self.vm_id is not None)
        self.vm_umount()
        cmd_str = 'destroy "%s"' % self.vm_id
        if not force:
            cmd_str += ' --graceful'
        cmd.virsh_or_die(cmd_str)

    def vm_destroy(self):
        assert(self.vm_id is not None)
        cmd_str = 'undefine "%s" --remove-all-storage' % self.vm_id
        cmd.virsh_or_die(cmd_str)

    def vm_initial_setup(self, tasks=None):
        log.info("Running initial setup for %s:" % self.name_pp)
        ip = self.get_ip(fatal=True)
        init_conf = self.conf.get('init')
        # hostname magic
        _tasks = init_conf['tasks']
        if 'hostname' in _tasks:
            i = _tasks.index('hostname')
            _tasks[i] = 'hostname:%s' % self.vm_id
        try:
            provision.provision(self, init_conf, tasks)
        except Exception, e:
            self.vm_init = const.VMINIT_FAIL
            self._save_data()
            raise e
        self.vm_init = const.VMINIT_DONE
        self._save_data()

    def vm_provision(self, tasks=None):
        ip = self.get_ip(fatal=True)
        prov_conf = self.conf.get('provision')
        if not prov_conf:
            raise exception.MissingRequiredConfigOption(option='provision')
        provision.provision(self, prov_conf, tasks)

    def vm_umount(self, dst=None):
        assert(self.state >= const.VMS_RUNNING)
        if dst:
            if dst not in self.vm_mnt:
                log.info("%s is not mounted." % dst)
                return
            umnts = [dst]
        else:
            umnts = self.vm_mnt.keys()
        for udst in umnts:
            log.info("Unmounting: %s (%s)"
                     % (udst, self.vm_mnt[udst]['src']))
            cmd.run_or_die("fusermount -u '%s'" % udst)
            self.vm_mnt.pop(udst)
            self._save_data()
            abs_dst = self._proj_path(udst)
            try:
                os.rmdir(abs_dst)
            except Exception, e:
                log.info("Can't remove mount point %s" % abs_dst)

    def do_up(self, provision=True):
        if self.state == const.VMS_NOT_CREATED:
            log.info("Creating new %s...", self.name_pp)
            self.vm_create()
        if self.state < const.VMS_RUNNING:
            log.info("Starting %s...", self.name_pp)
            self.vm_start()
            self._check_state()
            if provision and not self.vm_init:
                self.vm_initial_setup()
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
            log.info('')
            log.info("virt domain: %s" % self.vm_id)
        if self.vm_init:
            if self.vm_init == const.VMINIT_DONE:
                init_str = term.green('done')
            elif self.vm_init == const.VMINIT_FAIL:
                init_str = term.yellow('failed')
            log.info("initial setup: %s" % init_str)
        if self.state >= const.VMS_RUNNING:
            log.info('')
            ip = self.get_ip(wait=0)
            if ip:
                log.info("IP address: %s" % term.bold(ip))
                if self.check_ssh():
                    ssh_str = term.green('open')
                else:
                    ssh_str = term.yellow('closed')
                log.info("SSH port: %s" % ssh_str)
            else:
                log.info("IP address can't be determined.")
        if self.vm_mnt:
            log.info('')
            log.info(term.bold("Mounts:"))
            for dst, mnt in self.vm_mnt.items():
                log.info("%s -> %s" % (mnt['src'], dst))

    def do_ssh(self, wait=30):
        if self.state < const.VMS_RUNNING:
            self.do_up()
            self._check_state()
        self.ensure_ssh()
        host = self.get_ssh_host()
        cmd_seq = "ssh '%s'" % host
        cmd.run(cmd_seq, stdout=True, stderr=True)

    def do_provision(self, tasks=None, init=False):
        if self.state < const.VMS_RUNNING:
            self.do_up(provision=False)
        ip = self.get_ip(fatal=True)
        if init:
            self.vm_initial_setup(tasks)
        else:
            self.vm_provision(tasks)

    def do_mount(self, src=None, dst=None):
        if self.state < const.VMS_RUNNING:
            self.do_up()
        if not src:
            src = '/'
        if not dst:
            dst = const.VM_MNT
        abs_dst = self._proj_path(dst)
        if dst in self.vm_mnt:
            emnt = self.vm_mnt[dst]
            log.info("Already mounted using %s:" % emnt['type'])
            log.info("    mount point: %s" % dst)
            log.info("    %s dir: %s" % (self.name_pp, emnt['src']))
            return
        log.info("Mounting %s:%s to %s using sshfs..."
                 % (self.get_ip(), src, dst))
        self.ensure_ssh()
        host = self.get_ssh_host()
        if not os.path.isdir(abs_dst):
            os.makedirs(abs_dst)
        cmd_str = "sshfs '%(host)s:%(src)s' '%(dst)s'" % {
            'host': host,
            'src': src,
            'dst': dst
        }
        cmd.run_or_die(cmd_str)
        self.vm_mnt[dst] = {'type': 'sshfs', 'src': src}
        self._save_data()

    def do_umount(self, dst=None):
        if self.state < const.VMS_RUNNING:
            log.info("%s not running, nothing to unmount." % self.name_pp)
            return
        if not self.vm_mnt:
            log. info("Nothing is mounted.")
            return
        self.vm_umount(dst)

# -*- encoding: utf-8 -*-

from cmd import run, virsh
import cmd
import const
import collections
import exception
import ip
import log
from log import term
import provision
import re

import logging
import os
import os.path
import time
import yaml


VERSION = '0.1'


def find_project(path=None):
    """
    Search for project config files in specified/current directory and its
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

    def _conf_get_required(self, opt):
        if opt not in self.conf:
            raise MissingRequiredConfigOption(option=opt)
        return self.conf[opt]

    def _load_conf(self):
        abs_conf_fn = self.abs_conf_fn()
        log.verbose("Machine config: %s" % abs_conf_fn)
        conf_file = file(abs_conf_fn, 'r')
        self.conf = yaml.load(conf_file)
        log.debug(" -> %s" % self.conf)

        self.base = self._conf_get_required('base')
        self.vm_user = self.conf.get('user', 'root')
        self.mounts = self.conf.get('mount', [])

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
        self.vm_user = 'root'
        self.vm_init = None
        self.vm_mnt = {}
        log.verbose("Loading %s:" % self.name_pp)
        self._load_conf()
        self._load_data()
        self._check_state()

    def _proj_path(self, *path):
        return os.path.join(self.path, *path)

    def _get_domains(self):
        doms_str = cmd.virsh_or_die('list --all --name')
        doms = doms_str.strip().split("\n")
        return doms

    def _generate_id(self):
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

    def get_ip(self, wait=const.WAIT_START, fatal=False):
        assert(self.vm_id is not None)
        if self._ip:
            return self._ip
        self._ip = ip.get_instance_ip(self.vm_id)
        if not self._ip and wait:
            log.info("Waiting for IP address for next %d s..." % wait)
            for i in range(0, wait):
                time.sleep(1)
                self._ip = ip.get_instance_ip(self.vm_id)
                if self._ip:
                    break
        if fatal and not self._ip:
            raise exception.UnknownGuestAddress(machine=self.name)
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

    def ensure_ssh(self, wait=const.WAIT_START):
        assert(self.state >= const.VMS_RUNNING)
        self.get_ip()
        if self.check_ssh():
            return
        log.info("Waiting for SSH connection for next %d s..." % wait)
        for i in range(0, wait):
            time.sleep(1)
            if self.check_ssh():
                return
        raise exception.SshConnectionError(machine=self.name)

    def vm_create(self):
        assert(self.vm_id is None)
        log.info("Creating new %s VM based on %s..." % (self.name_pp,
                                                       term.bold(self.base)))
        self._generate_id()
        log.debug("New VM ID: %s" % self.vm_id)
        cmdstr = 'virt-clone -o "%s" -n "%s" --auto-clone' % \
                 (self.base, self.vm_id)
        cmd.run_or_die(cmdstr, stdout=True)
        self._save_data()
        self._check_state()
        if self.state != const.VMS_POWEROFF:
            raise exception.Bug("New VM cloned but in wrong state.")

    def vm_start(self):
        assert(self.state == const.VMS_POWEROFF)
        assert(self.vm_id is not None)
        if self.vm_id == self.name:
            msg = "Starting %s VM..." % self.name_pp
        else:
            msg = "Starting %s VM, virt domain %s..." % (self.name_pp,
                                                         term.bold(self.vm_id))
        log.info(msg)
        cmd.virsh_or_die('start "%s"' % self.vm_id)
        self.vm_clean_mounts()

    def vm_stop(self, force=False):
        assert(self.state >= const.VMS_RUNNING)
        assert(self.vm_id is not None)
        if force:
            msg = "Force stopping %s VM..." % self.name_pp
        else:
            msg = "Stopping %s VM..." % self.name_pp
        log.info(msg)
        try:
            self.vm_umount()
        except Exception as ex:
            if not force:
                raise
        cmd_str = 'destroy "%s"' % self.vm_id
        if not force:
            cmd_str += ' --graceful'
        cmd.virsh_or_die(cmd_str)

    def vm_destroy(self):
        assert(self.vm_id is not None)
        log.info("Deleting %s VM..." % self.name_pp)
        cmd_str = 'undefine "%s" --remove-all-storage' % self.vm_id
        cmd.virsh_or_die(cmd_str)
        self._remove_vm_data()

    def _get_provision_confs(self, opt):
        opt_multi = '%ss' % opt
        conf = self.conf.get(opt)
        if conf != None:
            confs = [conf]
        else:
            confs = self.conf.get(opt_multi)
            if confs is None:
                confs = []
        return confs

    def vm_initial_setup(self, tasks=None):
        confs = self._get_provision_confs('init')
        if not confs:
            log.info("No initial setup for %s." % self.name_pp)
            return
        log.info("Running initial setup for %s:" % self.name_pp)
        for conf in confs:
            try:
                provision.provision(self, conf, tasks, user='root')
            except Exception, e:
                self.vm_init = const.VMINIT_FAIL
                self._save_data()
                raise e
        self.vm_init = const.VMINIT_DONE
        self._save_data()

    def vm_provision(self, tasks=None):
        confs = self._get_provision_confs('provision')
        # TODO: specified tasks with more provisions
        for conf in confs:
            if tasks:
                try:
                    provision.provision(self, conf, tasks)
                    break
                except Exception as e:
                    pass
            else:
                provision.provision(self, conf, tasks)

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
            abs_udst = self._proj_path(udst)
            cmd.run_or_die("fusermount -u '%s'" % abs_udst)
            self.vm_mnt.pop(udst)
            self._save_data()
            abs_dst = self._proj_path(udst)
            try:
                os.rmdir(abs_dst)
            except Exception, e:
                log.info("Can't remove mount point %s" % abs_dst)

    def vm_clean_mounts(self):
        if not self.vm_mnt:
            return
        log.info("Cleaning invalid mounts...")
        dsts = self.vm_mnt.keys()
        for dst in dsts:
            abs_dst = self._proj_path(dst)
            cmd_str = "mount | grep '%s'" % abs_dst
            ret, _, _ = cmd.run(cmd_str)
            if ret != 0:
                log.info("%s doesn't seem to be mounted, cleaning."
                         % dst)
                self.vm_mnt.pop(dst)
                self._save_data()
                try:
                    os.rmdir(abs_dst)
                except Exception, e:
                    log.verbose("Can't remove mount point %s" % abs_dst)

    def do_up(self, provision=True):
        if self.state == const.VMS_NOT_CREATED:
            self.vm_create()
        if self.state < const.VMS_RUNNING:
            self.vm_start()
            self._check_state()
            self.get_ip()
            if provision and not self.vm_init:
                self.vm_initial_setup()
            self.do_mount(auto_only=True)
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
            self.vm_stop(force)

    def do_delete(self, confirm=True):
        if self.state == const.VMS_NOT_CREATED:
            log.info("%s isn't created.", self.name_pp)
            return
        if confirm:
            msg = "Do you want to %s machine %s? [Yn] " % \
                  (term.red("DELETE"), term.bold(self.name))
            cfrm = raw_input(msg)
            if cfrm != '' and cfrm.lower() != 'y':
                log.info("Aborted.")
                return
        if self.state >= const.VMS_RUNNING:
            self.vm_stop(force=True)
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

    def do_ssh(self, wait=const.WAIT_START):
        if self.state < const.VMS_RUNNING:
            self.do_up()
            self._check_state()
        self.ensure_ssh()
        host = self.get_ssh_host()
        cmd_seq = "ssh '%s'" % host
        cmd.run(cmd_seq, stdout=True, stderr=True)

    def do_view(self):
        if self.state < const.VMS_RUNNING:
            self.do_up()
            self._check_state()
        assert(self.state >= const.VMS_RUNNING)
        cmd.run("virt-viewer '%s'" % (self.vm_id))

    def do_provision(self, tasks=None, init=False):
        if self.state < const.VMS_RUNNING:
            self.do_up(provision=False)
        ip = self.get_ip(fatal=True)
        if init:
            self.vm_initial_setup(tasks)
        else:
            self.vm_provision(tasks)

    def vm_mount(self, src, dst=None):
        if not dst:
            dst = os.path.basename(src.rstrip(os.sep))
            if not dst:
                dst = const.VM_MNT
        abs_dst = self._proj_path(dst)
        log.info("Mounting %s:%s to %s using sshfs..."
                 % (self.get_ip(), src, dst))
        if dst in self.vm_mnt:
            emnt = self.vm_mnt[dst]
            log.info("Already mounted using %s:" % emnt['type'])
            log.info("    mount point: %s" % dst)
            log.info("    %s dir: %s" % (self.name_pp, emnt['src']))
            return
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

    def _check_mounts(self):
        if self.mounts and not isinstance(self.mounts, collections.Iterable):
            raise InvalidConfig(
                reason="'mount' isn't iterable. It must be a list of mounts.")
        for mnt in self.mounts:
            if not hasattr(mnt, 'get'): 
                raise InvalidConfig(
                    reason="Mount point must be a dict-like object. (%s)" % mnt)
            if not mnt.get('vm'):
                raise MissingRequiredConfigOption(
                    reason="Mount point doesn't contain VM directory to mount 'vm'. (%s)" % mnt) 

    def do_mount(self, src=None, dst=None, auto_only=False):
        if self.state < const.VMS_RUNNING:
            self.do_up()
        self.vm_clean_mounts()
        if src:
            if dst:
                self.vm_mount(src, dst=dst)
                return
            self._check_mounts()
            def _match_mount(mnt):
                if re.search(src, mnt.get('vm', '')) or \
                   re.search(src, mnt.get('local', '')):
                    return True
                return False
            mounts = [m for m in self.mounts if _match_mount(m)]
            if not mounts:
                self.vm_mount(src)
                return
        elif self.mounts:
            self._check_mounts()
            mounts = self.mounts
        else:
            if auto_only:
                return
            log.info("No mounts configured, mountig /")
            self.vm_mount('/')
            return
        if auto_only:
            mounts = [m for m in mounts if m.get('auto', False)]
            if mounts:
                log.info("Auto mounting...")
        for mnt in mounts:
            self.vm_mount(mnt['vm'], dst=mnt.get('local', None))

    def do_umount(self, dst=None, clean_only=False):
        if clean_only:
            self.vm_clean_mounts()
            return
        if self.state < const.VMS_RUNNING:
            log.info("%s not running, nothing to unmount." % self.name_pp)
            return
        if not self.vm_mnt:
            log.info("Nothing is mounted.")
            return
        self.vm_umount(dst)

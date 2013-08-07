# virtpwn

**virtpwn** is a lightweight yet powerful command line libvirt frontend
inspired by Vagrant. It is essentially a VM manager automating boring tasks
that should be done for you automatically.

**virtpwn** is young and under "heavy" development, so now is great time hack
it up to suit your needs. I'll respond to (reasonable) feature requests and
even hack it for you, feel free to create issues.


## Why use it?

 * Fast and effortless creation, deletion and control of VMs.
 * Each VM is associated with directory of your choice and it's controlled by
   issuing commands in that directory without the need to specify an ID.
 * Detect VM IP and eliminate the need for using it.
 * Provisioning using Fabric. (ready for chef/puppet support)
 * Easily SSH to VM. (`virtpwn ssh`)
 * Easily mount VM filesystem using sshfs. (`virtpwn mount`)
 * Configure your VM using nice YAML config. 
 * `virtpwn` uses virt command line tools and can show you the exact commands
   used (`-c`)
 
Once you have your machine config up, it's a matter of one command to create
new machine, provision it and SSH to it:

    virtpwn ssh

Time to kill the machine and start anew:

    virtpwn delete
    virtpwn up

Updated provisioning scripts, let's test them:

    virtpwn provision

Let's copy some files to the VM:

    virtpwn mount
    cp something mnt/tmp

## Requirements

**virtpwn** requires:

 * python modules:
    * argh
    * blessings
    * lxml
 * virt command line tools:
    * `virsh` libvirt client
    * `virt-clone` 
 * fabric


Install these using your favourite package manager. Something like this might
work on Fedora:

    yum install python-argh python-blessings python-lxml libvirt-client
        virt-install fabric

might do the trick. If some of them aren't packaged, fastest way is to use
`pip` or when everything else fails, `easy_install`. I for one like to have
latest Fabric since my distro ships a terribly old version, so:

    pip install fabric

## QUICKSTART

After you managed to install the above requirements:

    git clone https://github.com/yac/virtpwn.git
    cd virtpwn
    # use develop mode to allow comfortable hacking
    sudo python setup.py develop

Being lazy person, I create a `vm` alias for `virtpwn`:

    # optional
    cd `dirname $(which virtpwn)`
    sudo ln -s virtpwn vm

After that, just create a directory with `machine.yml` config file.

    mkdir foovm
    cd foovm
    cp $VIRTPWN_SOURCE/examples/basic-machine/machine.yml .
    edit machine.yml

Given the base virt domain specified in the config exists and requirements are
met, you're good to go:

    virtpwn up
 
To get all available commands, use

    virtpwn help

Have fun!


## TODO

 * `virtpwn init` to create basic `machine.yml`
 * m0ar documentation!
    * config file and provisioning
    * debugging and such
    * howto get nice base image using Oz
 * make Fabric optional

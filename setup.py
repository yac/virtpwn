#!/usr/bin/env python

import setuptools
from virtpwn.core import VERSION

setuptools.setup(
    name='virtpwn',
    version=VERSION,
    description='lightweight libvirt frontend inspired by vagrant',
    author='Jakub Ruzicka',
    author_email='jruzicka@redhat.com',
    url='http://github.com/yac/virtpwn',
    packages=['virtpwn', 'virtpwn.provisioners', 'virtpwn.fabric'],
    entry_points={
        "console_scripts": ["virtpwn = virtpwn.shell:main"]
    }
    )

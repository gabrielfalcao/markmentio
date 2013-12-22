# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import commands
from datetime import datetime
from os.path import dirname, abspath, join
from fabric.api import run, runs_once, put, sudo

LOCAL_FILE = lambda *path: join(abspath(dirname(__file__)), *path)

SOURCECODE_PATH = LOCAL_FILE('*')

@runs_once
def create():
    dependencies = [
        'git-core',
        'build-essential',
        'python-pip',
        'python-gnupg',
        'supervisor',
        'redis-server',
        'rng-tools',
        'python-dev',
        'libmysqlclient-dev',
        'mysql-client',
        'libxml2-dev',
        'libxslt1-dev',
        'libevent-dev',
        'libev-dev',
        'virtualenvwrapper',
    ]
    sudo("apt-get -q=2 update")
    sudo("apt-get install -q=2 -y aptitude")
    sudo("aptitude install -q=2 -y {0}".format(" ".join(dependencies)))
    sudo('echo "HRNGDEVICE=/dev/urandom" >> /etc/default/rng-tools')
    sudo("dpkg-reconfigure rng-tools")

    sudo("(test -e /srv && rm -rf /srv/)")
    sudo("rm -rf /srv/markment-io")
    sudo("rm -rf /var/log/markment-io")
    sudo("mkdir -p /var/log/markment-io")
    sudo("mkdir -p /srv")
    sudo("chown -R ubuntu.ubuntu /srv")
    sudo("chown -R ubuntu.ubuntu /var/log")
    sudo("chown -R redis.redis /var/log/redis")
    sudo("chown -R ubuntu.ubuntu /etc/supervisor/conf.d")
    sudo("chmod -R 755 /etc/supervisor")


@runs_once
def deploy():
    now = datetime.now()
    release_path = '/srv/markment-io'
    run("test -e /srv/venv || virtualenv --no-site-packages --clear /srv/venv")
    put(LOCAL_FILE('.conf', 'sitecustomize.py.template'), "/srv/venv/lib/python2.7/sitecustomize.py")
    put(LOCAL_FILE('.conf', 'supervisor.http.conf'), "/etc/supervisor/conf.d/markment-io-http.conf")
    put(LOCAL_FILE('.conf', 'supervisor.workers.conf'), "/etc/supervisor/conf.d/markment-io-workers.conf")

    put(LOCAL_FILE('.conf', 'ssh', 'id_rsa*'), "/home/ubuntu/.ssh/")
    sudo('cp -fv /home/ubuntu/.ssh/id_rsa* /root/.ssh/')
    sudo("chmod 600 /home/ubuntu/.ssh/id_rsa*")
    sudo("chmod 600 /root/.ssh/id_rsa*")

    address = 'git@github.com:weedlabs/markmentio.git'
    run("test -e {0} || git clone {1} {0}".format(release_path, address))
    run("cd /srv/markment-io && git fetch --prune")
    run("cd /srv/markment-io && git reset --hard origin/master")
    run("cd /srv/markment-io && git clean -df")
    run("cd /srv/markment-io && git pull")

    run("/srv/venv/bin/pip install -r /srv/markment-io/requirements.txt")
    sudo("service supervisor stop")
    sudo("(ps aux | egrep python | grep -v grep | awk '{ print $2 }' | xargs kill -9 2>&1>/dev/null) 2>&1>/dev/null || echo")
    sudo("service supervisor start")
    sudo("supervisorctl restart all")

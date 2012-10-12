# -*- coding: utf-8 -*-
from fabric.api import *

from flib import *


'''
Do not forget to add new functions into this list
'''
__all__ = ['setup_server']


HOME_DIRECTORY = '/var/www'


def home_rel(path):
    return '{home}/{path}'.format(home=HOME_DIRECTORY, path=path)


def setup_server():
    log(format_header('Starting initial server setup'), MSG_SUCCESS)
    copy_ssh_keys()

    log(format_header('Setting up packages'), MSG_SUCCESS)
    update_repos()
    install_packages([
        'build-essential', 'python-dev', 'python-software-properties',
        'python-pip',
        'git-core', 'nginx', 'uwsgi'
    ])
    log('Installing virtualenvwrapper', MSG_INFO)
    run('pip install virtualenvwrapper')

    log('Setting up generic locale (en_US)', MSG_INFO)
    run('locale-gen en_US')
    run('update-locale LANG=en_US')

    log(format_header('Creating directories and files'), MSG_SUCCESS)

    mkdir(HOME_DIRECTORY)
    mkfile(home_rel('.profile'))
    mkdir(home_rel('projects'))
    mkdir(home_rel('log'))
    mkdir(home_rel('run'))
    mkdir(home_rel('virtualenvs'))
    mkdir(home_rel('log/uwsgi'))

    # setting up virtualenvwrapper
    write_into_file(home_rel('.profile'),
        '''
        export WORKON_HOME=~/virtualenvs
        source /usr/local/bin/virtualenvwrapper.sh
        '''
    )

    log(format_header('Setting up uwsgi'), MSG_SUCCESS)
    mkdir('/etc/uwsgi', user='root')
    mkdir('/etc/uwsgi/apps-enabled', user='root')
    # we need to create this directory manually during uwsgi bugs
    run('mkdir -p /usr/lib/uwsgi/plugins')
    mkfile('/etc/init/uwsgi.conf', user='root')
    # setting up uwsgi
    write_into_file('/etc/init/uwsgi.conf',
        '''
        description "uWSGI Emperor"
        start on runlevel [2345]
        stop on runlevel [06]
        #respawn

        env UWSGI_BIN=/usr/local/bin/uwsgi
        env LOGTO=/var/log/uwsgi/emperor.log

        exec $UWSGI_BIN --master --die-on-term --emperor /etc/uwsgi/apps-enabled --uid www-data --gid www-data --logto $LOGTO
        ''',
    user='root')

    run('/etc/init.d/uwsgi restart')

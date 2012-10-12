# -*- coding: utf-8 -*-
from fabric.api import *
from fabric.contrib.files import exists
from fabric.colors import *


MSG_ERROR = 0
MSG_INFO = 1
MSG_SUCCESS = 2


def log(msg, type):
    if type == MSG_ERROR:
        p_msg = red(msg)
    if type == MSG_INFO:
        p_msg = yellow(msg)
    if type == MSG_SUCCESS:
        p_msg = green(msg)

    print(p_msg)


def format_header(header):
    '''
    I think, this function could be written more cute using format() mini-lang,
    but i have no time to learn it :(
    At least i know about my problems ;)
    '''
    hlen = len(header)
    return '\n{0}\n{1}\n{0}'.format('=' * hlen, header)


def copy_ssh_keys():
    local('ssh-copy-id {0.user}@{0.host_string}'.format(env))
    log('SSH keys copied', MSG_SUCCESS)


def update_repos():
    log('Updating packages list', MSG_INFO)
    run('apt-get update')
    log('Packages list updated', MSG_SUCCESS)


def install_package(package):
    log('Installing package "{0}"'.format(package), MSG_INFO)
    run('apt-get -yq install {0}'.format(package))


def install_packages(packages_list):
    for package in packages_list:
        install_package(package)


def mkdir(path, user='www-data'):
    if not exists(path):
        log('Creating directory {0}'.format(path), MSG_INFO)
        run('mkdir {0}'.format(path))
        log('Changing directory mode', MSG_INFO)
        run('chown {user}:{user} {path}'.format(user=user, path=path))
    else:
        log('Directory "{0}" already exists!'.format(path), MSG_INFO)


def mkfile(path, user='www-data'):
    if not exists(path):
        log('Creating file {0}'.format(path), MSG_INFO)
        run('touch {0}'.format(path))
        log('Changing file mode', MSG_INFO)
        run('chown {user}:{user} {path}'.format(user=user, path=path))
    else:
        log('File "{0}" already exists!'.format(path), MSG_INFO)


def _sudo(command, user):
    with settings(warn_only=True):
        env.sudo_prefix = "sudo -S -i -p '%(sudo_prompt)s'"
        return sudo(command, user=user)


def write_into_file(path, text, user='www-data'):
    if not exists(path):
        log('File does not exists!', MSG_ERROR)
    else:
        # flushing file before writing
        _sudo('echo "" > {path}'.format(path=path), user)
        for line in text.splitlines():
            _sudo('echo {text} >> {path}'.format(text=line, path=path), user)

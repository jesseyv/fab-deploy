# -*- coding: utf-8 -*-
from fabric.api import *

from flib import *
from flib import _sudo


'''
Do not forget to add new functions into this list
'''
__all__ = ['setup_server', 'init_project_deploy']


HOME_DIRECTORY = '/var/www'
PROJECTS_ROOT = '{home}/projects/'.format(home=HOME_DIRECTORY)

DEPLOY_USER = 'www-data'


def home_rel(path):
    return '{home}/{path}'.format(home=HOME_DIRECTORY, path=path)


def get_repo_info():
    '''
    Getting repository address, name, etc
    '''
    repo_info = {}
    repo_info['ssh_url'] = local('git config --get remote.origin.url',
        capture=True)
    repo_info['git_url'] = 'git://{0}'.format(
        repo_info['ssh_url'].split('@')[1].replace(':', '/'))
    repo_info['name'] = local('basename {0} .git'.format(
        repo_info['ssh_url']), capture=True)

    return repo_info
        

def setup_server():
    '''
    Initial server setup proc
    setup_server -H <hostname/IP> -u <user> (usually root)
    '''
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


def restart_proj():
    repo_info = get_repo_info()
    
    with settings(warn_only=True):
        log('Restarting project serving', MSG_SUCCESS)
        run('touch /etc/uwsgi/apps-enabled/{}.ini'.format(repo_info['name']))
        run('service nginx reload')


def enable_proj():
    repo_info = get_repo_info()

    log('Enabling project serving', MSG_SUCCESS)
    run('ln -s -f {0}{1}/uwsgi.ini /etc/uwsgi/apps-enabled/{1}.ini'.format(
        PROJECTS_ROOT, repo_info['name']))
    run('ln -s -f {0}{1}/nginx.conf /etc/nginx/sites-available/{1}'.format(
        PROJECTS_ROOT, repo_info['name']))
    run('ln -s -f /etc/nginx/sites-available/{0} /etc/nginx/sites-enabled/{0}'.format(
        repo_info['name']))
    restart_proj()


def init_project_deploy():
    '''
    Makes remote project initial setup
    init_project_deploy -H <hostname/IP> -u <user> (usually root)
    '''
    copy_ssh_keys()
    with settings(warn_only=True):
        repo_info = get_repo_info()

        with cd(PROJECTS_ROOT):
            if run('test -d {0}'.format(repo_info['name'])).failed:
                log('Cloning project\'s repo', MSG_INFO)
                _sudo('git clone {0}'.format(repo_info['git_url']), DEPLOY_USER)

            with cd(repo_info['name']):
                log('Updating project\'s repo', MSG_SUCCESS)
                _sudo('git reset --hard HEAD; git pull', DEPLOY_USER)
                put('{0}/local_settings.py'.format(repo_info['name']),
                    '{0}{1}'.format(PROJECTS_ROOT, repo_info['name']))
                run('chown {0}:{0} local_settings.py'.format(DEPLOY_USER))
                #put('fixtures', '{0}{1}'.format(PROJECTS_ROOT, repo_info['name']))
                #run('chown -R {0}:{0} fixtures'.format(DEPLOY_USER))
                WORK_HOME = _sudo('echo $WORKON_HOME', DEPLOY_USER)

                if run('test -d {0}/{1}'.format(WORK_HOME, repo_info['name'])).failed:
                    log('Creating virtualenv for project', MSG_SUCCESS)
                    _sudo('mkvirtualenv {}'.format(repo_info['name']), DEPLOY_USER)

                with prefix('workon {}'.format(repo_info['name'])):
                    print(green('Installing required packets'))
                    _sudo('pip install -r requirements.txt', DEPLOY_USER)

                    print(green('Syncing DB'))
                    _sudo('python manage.py syncdb --noinput --migrate', DEPLOY_USER)

                    print(green('Migrating DB'))
                    _sudo('python manage.py migrate --noinput', DEPLOY_USER)

                    print(green('Collecting static'))
                    _sudo('python manage.py collectstatic --noinput', DEPLOY_USER)

    enable_proj()
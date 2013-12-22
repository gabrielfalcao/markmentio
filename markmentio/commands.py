#!/usr/bin/env python
# -*- coding: utf-8; -*-
import sys
import time
import json


from flask.ext.script import Command
from flask.ext.script import Option
from redis import StrictRedis

LOGO = '''
                                            888
                                            888
                                            888
                88888b.d88b.  8888b. 888d888888  888
                888 "888 "88b    "88b888P"  888 .88P
                888  888  888.d888888888    888888K
                888  888  888888  888888    888 "88b
                888  888  888"Y888888888    888  888

                             888         d8b
                             888         Y8P
                             888
88888b.d88b.  .d88b. 88888b. 888888      888 .d88b.
888 "888 "88bd8P  Y8b888 "88b888         888d88""88b
888  888  88888888888888  888888         888888  888
888  888  888Y8b.    888  888Y88b.    d8b888Y88..88P
888  888  888 "Y8888 888  888 "Y888   Y8P888 "Y88P"
'''


class RunWorkers(Command):
    def run(self):
        redis = StrictRedis()
        from markmentio.workers.manager import DocumentationGenerator

        workers = DocumentationGenerator()
        print "Waiting for a build..."

        while workers.are_running():
            next_build_raw = redis.lpop("yipidocs:builds")
            if not next_build_raw:
                time.sleep(3)
                continue

            next_build = json.loads(next_build_raw)

            workers.feed(next_build)
            payload = workers.wait_and_get_work()
            if 'error' in payload:
                print "Failed", payload
                sys.stderr.write(payload['error'])
                continue

            repository = payload['repository']
            owner = repository['owner']['name']
            serialized_payload = json.dumps(payload)
            full_name = "{owner[name]}/{name}".format(**repository)
            redis.hset("markmentio:ready", full_name, serialized_payload)
            redis.rpush("markmentio:notifications", json.dumps({
                'message': 'Documentation ready: {0}'.format(full_name)
            }))
            print "Waiting for a build..."


class EnqueueProject(Command):
    def run(self):
        from markmentio.models import User
        from markmentio import db
        redis = StrictRedis()
        users = User.using(db.engine).all()
        if not users:
            print ("Run the server and log in with github, "
                   "I need a real user token to test this...")

            raise SystemExit(1)
        user = users[0]

        redis.rpush("yipidocs:builds", json.dumps({
            'token': user.github_token,
            'clone_path': '/tmp/YIPIT_DOCS',
            'repository': {
                'name': 'yipit-client',
                'owner': {
                    'name': 'Yipit',
                }
            }
        }))


class Check(Command):
    def run(self):
        from markmentio.app import App
        from markmentio.settings import absurl
        from traceback import format_exc
        app = App.from_env()
        HEALTHCHECK_PATH = "/"
        try:
            print LOGO
            print "SMOKE TESTING APPLICATION"
            app.web.test_client().get(HEALTHCHECK_PATH)
        except Exception as e:
            print "OOPS"
            print "An Exception happened when making a smoke test to \033[1;37m'{0}'\033[0m".format(absurl(HEALTHCHECK_PATH))
            print format_exc(e)
            raise SystemExit(3)

def init_command_manager(manager):
    manager.add_command('enqueue', EnqueueProject())
    manager.add_command('check', Check())
    manager.add_command('workers', RunWorkers())
    return manager

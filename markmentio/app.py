# -*- coding: utf-8 -*-

import os
import sys
import logging
import traceback
import pickle

from datetime import timedelta, datetime
from uuid import uuid4
from redis import StrictRedis
from werkzeug.datastructures import CallbackDict
from flask.sessions import SessionInterface, SessionMixin

from flask import Flask, render_template
from flask.ext.script import Manager
from flask.ext.sqlalchemy import SQLAlchemy
from flask.ext.github import GitHub

from logging import getLogger, StreamHandler
from sqlalchemy import (
    create_engine,
    MetaData,
)

from markmentio.assets import AssetsManager
from markmentio.commands import init_command_manager
from markmentio import views

class PrettyFormatter(logging.Formatter):
    COLORS = {
        'DEBUG': '\033[37m',
        'INFO': '\033[32m',
        'ERROR': '\033[1;31m',
        'WARNING': '\033[32m',
        'CRITICAL': '\033[35m',
        'FATAL': '\033[36m',
    }
    def format(self, record):
        level_name = record.levelname
        try:
            original = logging.Formatter.format(self, record)
        except TypeError:
            original = ":".join([record.msg, str(record.args)])

        color = self.COLORS.get(level_name, '\033[37m')
        time = datetime.now().strftime("\033[37m[%Y-%m-%d %H:%M:%S]\033[0m")
        return "{time} {color}[{level_name}]\033[1;37m {original}\033[0m".format(**locals())




class RedisSession(CallbackDict, SessionMixin):

    def __init__(self, initial=None, sid=None, new=False):
        def on_update(self):
            self.modified = True
        CallbackDict.__init__(self, initial, on_update)
        self.sid = sid
        self.new = new
        self.modified = False


class RedisSessionInterface(SessionInterface):
    serializer = pickle
    session_class = RedisSession

    def __init__(self, redis=None, prefix='session:'):
        if redis is None:
            redis = StrictRedis(db=2)

        self.redis = redis
        self.prefix = prefix

    def generate_sid(self):
        return str(uuid4())

    def get_redis_expiration_time(self, app, session):
        if session.permanent:
            return app.permanent_session_lifetime
        return timedelta(days=1)

    def open_session(self, app, request):
        sid = request.cookies.get(app.session_cookie_name)
        if not sid:
            sid = self.generate_sid()
            return self.session_class(sid=sid, new=True)
        val = self.redis.get(self.prefix + sid)
        if val is not None:
            data = self.serializer.loads(val)
            return self.session_class(data, sid=sid)
        return self.session_class(sid=sid, new=True)

    def save_session(self, app, session, response):
        domain = self.get_cookie_domain(app)
        if not session:
            self.redis.delete(self.prefix + session.sid)
            if session.modified:
                response.delete_cookie(app.session_cookie_name,
                                       domain=domain)
            return
        redis_exp = self.get_redis_expiration_time(app, session)
        cookie_exp = self.get_expiration_time(app, session)
        val = self.serializer.dumps(dict(session))
        self.redis.setex(self.prefix + session.sid, int(redis_exp.total_seconds()), val)
        response.set_cookie(app.session_cookie_name, session.sid,
                            expires=cookie_exp, httponly=True,
                            domain=domain)


class App(object):
    """Manage the main web app and all its subcomponents.

    By subcomponents I mean the database access, the command interface,
    the static assets, etc.
    """
    testing_mode = bool(os.getenv('MARKMENTIO_TESTING_MODE', False))

    def __init__(self, settings_path='markmentio.settings'):
        self.web = Flask(__name__)

        # Preparing session
        self.web.session_interface = RedisSessionInterface()
        # Loading our settings
        self.web.config.from_object(settings_path)

        # Loading our JS/CSS
        self.assets = AssetsManager(self.web)
        self.assets.create_bundles()

        # Setting up our commands
        self.commands = init_command_manager(Manager(self.web))
        self.assets.create_assets_command(self.commands)

        # Setting up our database component
        self.db = SQLAlchemy(self.web)
        metadata = MetaData()

        # Time to register our blueprints
        views.mod.app = self
        views.mod.db = self.db
        views.mod.engine = self.db.engine
        self.web.register_blueprint(views.mod)

        # GitHub
        self.github = GitHub(self.web)
        views.mod.github = self.github

        # Logging
        if not self.testing_mode:
            self.setup_logging(output=sys.stderr, level=logging.DEBUG)


        self.github.access_token_getter(views.get_github_token)
        self.web.route('/.sys/callback')(self.github.authorized_handler(views.github_callback))

        @self.web.errorhandler(500)
        def internal_error(exception):
            self.web.logger.exception(exception)
            tb = traceback.format_exc(exception)
            return render_template('500.html', exception=exception, traceback=tb), 500

    def setup_logging(self, output, level):
        loggers = map(getLogger, [
            'markmentio',
            'markmentio.api',
            'markmentio.views',
            'markmentio:websockets',
            'markmentio:workers',
            'markmentio:workers:downloader',
            'markmentio:workers:static_generator',
        ])
        loggers.append(self.web.logger)
        handler = StreamHandler(output)
        fmt = PrettyFormatter()
        handler.setFormatter(fmt)
        for logger in loggers:
            logger.addHandler(handler)
            logger.setLevel(level)


    @classmethod
    def from_env(cls):
        """Return an instance of `App` fed with settings from the env.
        """
        smodule = os.environ.get(
            'MARKMENTIO_SETTINGS_MODULE',
            'markmentio.settings'
        )
        return cls(smodule)


app = App.from_env()

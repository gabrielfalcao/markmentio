#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from markmentio.app import App
from markmentio import settings
from socketio import socketio_manage
from socketio.server import SocketIOServer

class SocketIOApp(object):
    def __init__(self, app):
        self.app = app

    def __call__(self, environ, start_response):
        from markmentio.websockets import NAMESPACES
        if environ['PATH_INFO'].startswith('/socket.io'):
            socketio_manage(environ, NAMESPACES)
            return

        return self.app.web(environ, start_response)

app = SocketIOApp(App.from_env())

# from OpenSSL import SSL
# context = SSL.Context(SSL.SSLv23_METHOD)
# context.use_privatekey_file(settings.SSL_PRIVATE_KEY_FILE)
# context.use_certificate_file(settings.SSL_CERT_FILE)

#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import unicode_literals
import json
import sys
import logging
import traceback
from pprint import pformat
from threading import RLock, Thread
from redis import StrictRedis

log = logging.getLogger('goloka:workers')


class Heart(object):
    def __init__(self):
        self.lock = RLock()
        self.beat()

    def is_beating(self):
        return self._is_beating

    def stop(self):
        self._is_beating = False
        return self.lock.release()

    def beat(self):
        self.lock.acquire()
        self._is_beating = True


class Worker(Thread):
    def __init__(self, consume_queue, produce_queue):
        super(Worker, self).__init__()
        self.consume_queue = consume_queue
        self.produce_queue = produce_queue
        self.heart = Heart()
        self.daemon = False

    def __str__(self):
        return '<{0}>'.format(self.__class__.__name__)

    def log(self, message, *args, **kw):
        with_redis = kw.get('with_redis', True)
        redis = StrictRedis()
        msg = message % args
        log.info(message, *args)
        if with_redis:
            redis.rpush("markmentio:logs", json.dumps({'message': msg}))

    def consume(self, instructions):
        raise NotImplemented("You must implement the consume method by yourself")

    def produce(self, payload):
        return self.produce_queue.put(payload)

    def before_consume(self):
        self.log("%s is about to consume its queue", self, with_redis=False)

    def after_consume(self, instructions):
        self.log("%s is done", self)

    def do_rollback(self, instructions):
        try:
            self.rollback(instructions)
        except Exception as e:
            error = traceback.format_exc(e)
            self.log(error)

    def run(self):
        while self.heart.is_beating():
            self.before_consume()
            instructions = self.consume_queue.get()
            if not instructions:
                sys.exit(1)
            try:
                self.consume(instructions)
            except Exception as e:
                error = traceback.format_exc(e)
                self.log(error)
                instructions.update({
                    'success': False,
                    'error': error
                })
                self.produce(instructions)
                self.do_rollback(instructions)
                continue

            self.after_consume(instructions)

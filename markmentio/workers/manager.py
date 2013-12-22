#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from Queue import Queue


class Pipeline(object):
    def __init__(self):
        self.running = False
        self.queues = [Queue() for _ in self.steps] + [Queue()]
        self.workers = [self.make_worker(Worker, index) for index, Worker in enumerate(self.steps)]

    def make_worker(self, Worker, index):
        return Worker(self.queues[index], self.queues[index + 1])

    @property
    def input(self):
        return self.queues[0]

    @property
    def output(self):
        return self.queues[-1]

    def start(self):
        self.running = True
        for worker in self.workers:
            worker.start()

    def feed(self, item):
        self.input.put(item)

    def wait_and_get_work(self):
        return self.output.get()

    def are_running(self):
        if self.running:
            return True

        self.start()
        return all([w.is_alive() for w in self.workers])


class DocumentationGenerator(Pipeline):
    from markmentio.workers.downloader import GithubDownloader
    from markmentio.workers.static_generator import StaticGenerator
    steps = [
        GithubDownloader,
        StaticGenerator,
    ]

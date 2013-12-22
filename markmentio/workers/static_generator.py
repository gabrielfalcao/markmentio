#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import os
import sys
import boto
import json

import subprocess
import markment.plugins.autoindex

from tempfile import TemporaryFile

from os.path import dirname, abspath, join, expanduser, exists
from markment.core import Project
from markment.fs import Generator, Node
from markment.ui import Theme, InvalidThemePackage

from boto.s3.key import Key

from markmentio import settings
from markmentio.workers.base import Worker
from markment.plugins import sitemap
from markment.plugins import autoindex


class StaticGenerator(Worker):
    def consume(self, instructions):
        if not instructions['success']:
            return self.produce(instructions)

        potential_path = instructions['destination_path']
        potential_node = Node(potential_path)
        markment_yml_nodes = potential_node.grep('[.]markment.yml')
        if not markment_yml_nodes:
            msg = 'No .markment.yml found in the project {repository[name]}'.format(**instructions)
            payload = {
                'success': False,
                'error': msg
            }
            self.log("Error generating docs: %s", msg)
            return self.produce(payload)

        s3 = boto.connect_s3()

        markment_node = markment_yml_nodes[0].parent
        project = Project.discover(markment_node.path)
        theme_path = project.meta['project'].get('theme')

        if theme_path:
            theme_node = project.node.cd(theme_path)
            theme = Theme.load_from_path(theme_node.path)
            self.log("Using specified theme: %s", theme_path)
        else:
            theme = Theme.load_from_path(settings.DEFAULT_THEME_PATH)
            self.log("Using default theme")

        destination = Generator(project, theme)

        repository = instructions['repository']
        owner = repository['owner']['name']
        name = repository['name']
        static_destination = join(settings.DOCUMENTATION_ROOT, owner, name).format(project.name)
        self.log("Running markment")

        generated = destination.persist(static_destination, gently=True)
        self.log("Markment is done")

        documentation_root_node = Node(settings.DOCUMENTATION_ROOT)
        index = []

        self.log("Preparing markment-io S3 bucket")

        bucket = s3.get_bucket('markment-io')
        config = bucket.configure_website('index.html', 'error.html')

        domain = bucket.get_website_endpoint()

        docs_url = 'http://{0}/{1}/{2}'.format(domain, owner, name)
        bucket_info = {
            'name': bucket.name,
            'domain': domain,
            'url': docs_url
        }

        self.log("Docs will be available under: %s", docs_url)

        for item in generated:
            relative_path = documentation_root_node.relative(item)
            key = Key(bucket)
            key.key = relative_path
            key.set_contents_from_filename(item)
            key.set_acl('public-read')
            index.append(relative_path)
            self.log("%s uploaded to %s/%s", relative_path, docs_url, relative_path)

        payload = {
            'documentation_path': static_destination,
            'repository': repository,
            'index': index,
            'bucket': bucket_info
        }

        self.log("Done generating %s", json.dumps(payload, indent=2))
        self.produce(payload)

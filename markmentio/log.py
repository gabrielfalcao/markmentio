#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import os
import sys
import logging
import couleur
import io


def get_fd():
    if os.getenv("TESTING"):
        return io.open(os.devnull, 'w')
    else:
        return sys.stdout


def get_formatter():
    if couleur.SUPPORTS_ANSI:
        return logging.Formatter('\033[0;37m[%(asctime)s] \033[32m%(levelname)s\033[0m %(message)s')
    else:
        return logging.Formatter('[%(asctime)s] %(levelname)s: %(message)s')


fd = get_fd()
formatter = get_formatter()

handler = logging.StreamHandler(fd)

logger = logging.getLogger('markmentio')
handler.setFormatter(formatter)

logger.setLevel(logging.DEBUG)
logger.addHandler(handler)

#!/usr/bin/env python
# -*- coding: utf-8; -*-
import os
import sys
from os.path import dirname, abspath, join
LOCALFILE = lambda *path: join(abspath(dirname(__file__)), *path)
sys.path.append(LOCALFILE('..'))

from markmentio.app import app

def main():
    try:
        app.commands.run()
    except KeyboardInterrupt:
        print "\rBYE"

if __name__ == "__main__":
    main()

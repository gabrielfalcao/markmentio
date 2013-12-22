# -*- coding: utf-8 -*-
import math
import colorsys
from flask import session, g

from markmentio import settings
from markmentio.log import logger


def user_is_authenticated():
    from markmentio import settings
    from markmentio.models import User
    data = session.get('github_user_data', False)
    if data:
        g.user = User.get_or_create_from_github_user(data)

    return data and data['login']

# -*- coding: utf-8 -*-
import re
import ejson as json
import ejson.serializers
import hashlib
from datetime import datetime
# from werkzeug import generate_password_hash, check_password_hash
import logging

logger = logging.getLogger('markmentio.models')

from markmentio.db import db, metadata, Model, engine
from markmentio import settings


def slugify(string):
    return re.sub(r'\W+', '-', string.lower())


def now():
    return datetime.now()


class User(Model):
    table = db.Table('md_user', metadata,
        db.Column('id', db.Integer, primary_key=True),
        db.Column('github_id', db.Integer, nullable=False, unique=True),
        db.Column('github_token', db.String(256), nullable=True),
        db.Column('gravatar_id', db.String(40), nullable=False, unique=True),
        db.Column('username', db.String(80), nullable=False, unique=True),
        db.Column('md_token', db.String(40), nullable=False, unique=True),
        db.Column('email', db.String(100), nullable=False, unique=True),
        db.Column('created_at', db.DateTime, default=now),
        db.Column('updated_at', db.DateTime, default=now),
    )

    def initialize(self):
        from markmentio.api import GithubUser
        sha = hashlib.sha1()
        sha.update("markmentio:")
        sha.update(self.username)
        self.md_token = sha.hexdigest()
        self.api = GithubUser.from_token(self.github_token)

    def __repr__(self):
        return '<User %r, token=%r>' % (self.username, self.md_token)

    def get_github_url(self):
        return "http://github.com/{0}".format(self.username)

    def list_repositories(self):
        return self.api.get_repositories(self.username)

    @classmethod
    def create_from_github_user(cls, data):
        login = data.get('login')
        fallback_email = "{0}@markment.io".format(login)
        email = data.get('email', fallback_email) or fallback_email

        instance = cls.create(
            username=login,
            github_id=data.get('id'),
            gravatar_id=data.get('gravatar_id'),
            email=email,
            github_token=data.get('github_token')
        )
        logger.info("user %d created: %s", instance.id, instance.email)
        return instance

    @classmethod
    def get_or_create_from_github_user(cls, data):
        login = data.get('login')
        instance = cls.find_one_by(username=login)
        fallback_email = "{0}@markment.io".format(login)

        if not instance:
            instance = cls.create_from_github_user(data)
        else:
            instance.github_token = data.get('github_token')
            instance.email = data.get('email', instance.email)
            instance.save()

        return instance



class Organization(Model):
    table = db.Table('md_organization', metadata,
        db.Column('id', db.Integer, primary_key=True),
        db.Column('owner_id', db.Integer, nullable=False),
        db.Column('name', db.String(80), nullable=False),
        db.Column('email', db.String(100), nullable=False, unique=True),
        db.Column('company', db.UnicodeText, nullable=True),
        db.Column('blog', db.UnicodeText, nullable=True),
        db.Column('avatar_url', db.UnicodeText, nullable=True),
        db.Column('created_at', db.DateTime, default=now),
        db.Column('updated_at', db.DateTime, default=now),
    )


class OrganizationUsers(Model):
    table = db.Table('md_organization_users', metadata,
        db.Column('id', db.Integer, primary_key=True),
        db.Column('user_id', db.Integer, nullable=False),
        db.Column('organization_id', db.Integer, nullable=False),
    )


# {
#   "login": "github",
#   "id": 1,
#   "url": "https://api.github.com/orgs/github",
#   "avatar_url": "https://github.com/images/error/octocat_happy.gif",
#   "name": "github",
#   "company": "GitHub",
#   "blog": "https://github.com/blog",
#   "location": "San Francisco",
#   "email": "octocat@github.com",
#   "public_repos": 2,
#   "public_gists": 1,
#   "followers": 20,
#   "following": 0,
#   "html_url": "https://github.com/octocat",
#   "created_at": "2008-01-14T04:33:35Z",
#   "type": "Organization"
# }

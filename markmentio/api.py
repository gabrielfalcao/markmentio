#!/usr/bin/env python
# -*- coding: utf-8 -*-
import re
import time
import json
import logging
import requests
from datetime import datetime
from redis import StrictRedis
from markmentio.log import logger


class GithubEndpoint(object):
    base_url = u'https://api.github.com'
    TIMEOUT = 60 * 30  # 30 minutes
    def __init__(self, token, public=False):
        self.token = token
        self.redis = StrictRedis(db=1)

        self.public = public
        self.headers = {
            'authorization': 'token {0}'.format(token),
            'User-Agent': 'Yipit/Docs Builder',
        }
        self.log = logging.getLogger('markmentio.api')

    def full_url(self, path):
        url = u"/".join([self.base_url, path.lstrip('/')])
        return url

    def find_cache_object(self, url):
        key = self.key(url)
        data = self.redis.get(key)
        if data:
            self.log.info("GET from CACHE %s at %s", url, str(time.time()))
            return json.loads(data)

    def key(self, url):
        if self.public:
            key = "cache:url:{0}".format(url)
        else:
            key = "cache:token:{1}:url:{0}".format(self.token, url)

        return key

    def create_cache_object(self, response):
        key = self.key(response['url'])
        content = json.dumps(response)
        self.redis.setex(key, self.TIMEOUT, content)

    def get_from_cache(self, path, headers, data=None):
        url = self.full_url(path)
        return self.find_cache_object(url) or {}

    def get_from_web(self, path, headers, data=None):
        url = self.full_url(path)
        data = data or {}

        request = {
            'url': url,
            'data': data,
            'headers': headers,
        }
        response = {}
        error = None
        try:
            self.log.info("GET from WEB %s at %s", url, str(time.time()))
            response = requests.get(**request)
        except Exception as e:
            error = e
            self.log.exception("Error retrieving `%s` with data %s", path, repr(data))
        primitive_response = self.make_primitive_response(url, headers, data, response)

        if str(response.status_code).startswith("2"):
            return primitive_response

        self.log.warning("Failed to retrieve `%s` with data %s", path, json.dumps(primitive_response, indent=2))

    def post(self, path, headers, data=None):
        url = self.full_url(path)
        data = data or {}

        request = {
            'url': url,
            'data': data,
            'headers': headers,
        }
        response = {}
        error = None
        try:
            self.log.info("POST from WEB %s at %s", url, str(time.time()))
            response = requests.post(**request)
        except Exception as e:
            error = e
            self.log.exception("Failed to create `%s` with data %s", path, repr(data))
        primitive_response = self.make_primitive_response(url, headers, data, response)

        if str(response.status_code).startswith("2"):
            return primitive_response

        self.log.warning("Failed to create `%s` with data %s", path, json.dumps(primitive_response, indent=2))

    def make_primitive_response(self, url, headers, data, response):
        return {
            'url': url,
            'request_headers': headers,
            'request_data': data,
            'response_headers': dict(response.headers),
            'error': None,
            'response_data': response.content,
            'cached': False,
            'status_code': response.status_code,
        }

    def retrieve(self, path, data=None, skip_cache=False):
        headers = self.headers
        if skip_cache:
            response = None
        else:
            response = self.get_from_cache(path, headers, data)

        if not response:
            response = self.get_from_web(path, headers, data)
            length = len(response['response_data'])
            if response and length < 1024 * 1024:
                self.create_cache_object(response)
            else:
                self.log.warning("Not caching %s because it is too big: %s", path, length)

        return response

    def create(self, path, data=None):
        return self.post(path, data, self.headers)

    def save(self, path, data=None):
        return self.json(requests.put(
            self.full_url(path),
            headers=self.headers,
        ))


class Resource(object):
    def __init__(self, endpoint):
        self.endpoint = endpoint

    @classmethod
    def from_token(cls, token):
        endpoint = GithubEndpoint(token)
        return cls(endpoint)

    def get_next_path(self, response):
        raw = response['response_headers'].get('link')
        # https://api.github.com/user/54914/repos?sort=pushed&page=2>; rel="next",
        if raw:
            found = re.search(r'https://api.github.com([^;]+); rel="next"', raw)
            if found:
                return found.group(1)

    def get_path_recursively(self, path):
        response = self.endpoint.retrieve(path)
        value = json.loads(response['response_data'])
        next_path = self.get_next_path(response)
        if next_path:
            value += self.get_path_recursively(next_path)

        return value


class GithubUser(Resource):
    def install_ssh_key(self, title, key):
        path = "/user/keys"
        return self.endpoint.create(path, {"title": title, "key": key})

    @classmethod
    def fetch_info(cls, token, skip_cache=False):
        instance = cls.from_token(token)
        response = instance.endpoint.retrieve('/user', skip_cache=skip_cache)
        if not response:
            return {}

        user_info = json.loads(response['response_data'])
        response2 = instance.endpoint.retrieve('/user/orgs', skip_cache=skip_cache)
        if response2:
            orgs = json.loads(response2['response_data'])
            user_info['organizations'] = [o for o in orgs if 'coderwall' not in o['login']]
        else:
            logger.error("Failed to retrieve organizations for %s", str(user_info))
        return user_info

    def get_starred(self, username):
        path = '/users/{0}/starred'.format(username)
        response = self.endpoint.retrieve(path)
        return json.loads(response['response_data'])

    def get_repositories(self, username):
        path = '/users/{0}/repos?sort=pushed'.format(username)
        return self.get_path_recursively(path)


class GithubOrganization(Resource):
    def get_repositories(self, name):
        path = '/orgs/{0}/repos?sort=pushed'.format(name)
        return self.get_path_recursively(path)


class GithubRepository(Resource):
    def get(self, owner, project):
        path = '/repos/{0}/{1}'.format(owner, project)
        response = self.endpoint.retrieve(path)
        return json.loads(response['response_data'])

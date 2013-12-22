#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import time

import json
from flask import (
    Blueprint,
    request,
    session,
    render_template,
    redirect,
    g,
    Response,
    url_for,
)
import traceback
from markmentio import settings
from markmentio.api import (
    GithubUser,
    GithubOrganization,
)
from markmentio.handy.decorators import requires_login
from markmentio.models import User
from markmentio.log import logger
from markmentio import db
from redis import StrictRedis

mod = Blueprint('views', __name__)


def json_response(data, status=200):
    return Response(json.dumps(data), mimetype="text/json", status=int(status))


def error_json_response(message, status=200):
    return json_response({
        'success': False,
        'error': {
            'message': message
        }
    }, status=status)


@mod.before_request
def prepare():
    g.user = None


def add_message(message, error=None):
    if 'messages' not in session:
        session['messages'] = []

    session['messages'].append({
        'text': message,
        'time': time.time(),
        'alert_class': error is None and 'uk-alert-success' or 'uk-alert-danger',
        'error': error,
    })


def full_url_for(*args, **kw):
    return settings.absurl(url_for(*args, **kw))


def ssl_full_url_for(*args, **kw):
    return settings.sslabsurl(url_for(*args, **kw))


@mod.context_processor
def inject_basics():
    return dict(
        settings=settings,
        messages=session.pop('messages', []),
        github_user=session.get('github_user_data', None),
        json=json,
        len=len,
        full_url_for=full_url_for,
        ssl_full_url_for=ssl_full_url_for,
    )


@mod.route("/")
def index():
    if 'github_user_data' in session:
        return redirect(url_for('.dashboard'))

    return render_template('index.html')



@mod.route("/logout")
def logout():
    session.pop('github_user_data', '')
    return redirect('/')


@mod.route("/dashboard")
@requires_login
def dashboard():
    redis = StrictRedis()

    organizations = session['github_user_data']['organizations']
    docs_found = {}
    for name, info in redis.hgetall('markmentio:ready').iteritems():
        docs_found[name] = json.loads(info)

    return render_template('dashboard.html', organizations=organizations, docs_found=docs_found)


@mod.route("/email")
@requires_login
def email():
    return render_template('email/thankyou.html')


@mod.route("/bin/dashboard/repo-list/<owner>.json")
@requires_login
def ajax_dashboard_repo_list(owner):
    token = session['github_token']
    org = GithubOrganization.from_token(token)
    redis = StrictRedis()
    repositories_with_hooks = {}
    try:
        repositories_with_hooks = redis.hgetall("markmentio:hooks")
    except Exception:
        logger.exception("Failed to hgetall markmentio:hooks")

    all_repositories = org.get_repositories(owner)
    tracked_repositories = []
    untracked_repositories = []

    for repo in all_repositories:
        full_name = repo['full_name']
        ready = json.loads(repositories_with_hooks.get(full_name, 'false'))
        repo['ready'] = ready
        repo['not_ready'] = not repo['ready']
        if full_name in repositories_with_hooks:
            tracked_repositories.append(repo)
        else:
            untracked_repositories.append(repo)

    repositories = tracked_repositories + untracked_repositories
    repositories_by_name = dict([(r['full_name'], r) for r in repositories])

    return json_response({
        'repositories': repositories,
        'repositories_by_name': repositories_by_name,
    })


@mod.route("/bin/create/hook.json", methods=["POST"])
@requires_login
def create_hook():
    redis = StrictRedis()
    owner = request.form['repository[owner][login]']
    repository = request.form['repository[name]']
    full_name = request.form['repository[full_name]']
    user_md_token = g.user.md_token
    payload = {
        "full_name": full_name,
        "user_md_token": user_md_token,
        "url": full_url_for(".webhook", owner=owner, repository=repository, md_token=user_md_token),
    }
    redis.hset("markmentio:hooks", full_name, json.dumps(payload))
    return json_response(payload)


@mod.route('/bin/<owner>/<repository>/<md_token>/hook', methods=["POST"])
def webhook(owner, repository, md_token):
    user = User.using(db.engine).find_one_by(md_token=md_token)
    if not user:
        logger.warning("token not found %s for %s/%s", md_token, owner, repository)

        return error_json_response("token not found", 404)
    try:
        instructions = json.loads(request.form['payload'])

        instructions['token'] = user.github_token
        instructions['clone_path'] = '/tmp/YIPIT_DOCS'

        redis = StrictRedis()
        redis.rpush("yipidocs:builds", json.dumps(instructions))
    except Exception as e:
        traceback.print_exc(e)

    return json_response({'cool': True})


@mod.route("/robots.txt")
def robots_txt():
    Disallow = lambda string: 'Disallow: {0}'.format(string)
    return Response("User-agent: *\n{0}\n".format("\n".join([
        Disallow('/bin/*'),
        Disallow('/thank-you'),
    ])))


@mod.route("/500")
def five00():
    return render_template('500.html')


@mod.route("/.healthcheck")
def healthcheck():
    return render_template('healthcheck.html')


@mod.route("/.ok")
def ok():
    return Response('YES\n\r')


@mod.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404


@mod.route('/login')
def login():
    cb = settings.absurl('.sys/callback')
    return mod.github.authorize('user,repo')


def get_github_token(token=None):
    return session.get('github_token', token)  # might bug


def github_callback(token):
    from markmentio.models import User
    next_url = request.args.get('next') or '/'
    if not token:
        logger.error(u'You denied the request to sign in.')
        return redirect(next_url)

    session['github_token'] = token

    github_user_data = GithubUser.fetch_info(token, skip_cache=True)

    github_user_data['github_token'] = token

    g.user = User.get_or_create_from_github_user(github_user_data)
    session['github_user_data'] = github_user_data
    gh_user = GithubUser.from_token(token)
    gh_user.install_ssh_key("markment-io", settings.SSH_PUBLIC_KEY)
    return redirect(next_url)

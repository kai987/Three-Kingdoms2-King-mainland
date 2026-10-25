#!/usr/bin/env python3
"""Resolve an actually deployed Pages SHA using read-only GitHub APIs.

A green verification/Pages workflow with a skipped deploy is not a baseline.
Deployment status, trusted workflow identity and the successful deployment step
must agree. Failure is explicit; callers must use full tests, never HEAD^.
"""
from __future__ import annotations

import argparse
from datetime import datetime
import json
import re
import subprocess
import sys
from urllib.parse import urlsplit

SHA = re.compile(r'[0-9a-f]{40}')
REPOSITORY = re.compile(r'[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+')


class BaselineUnavailable(RuntimeError):
    pass


def gh_api(endpoint):
    try:
        result = subprocess.run(['gh', 'api', '--method', 'GET', endpoint],
                                check=True, capture_output=True, text=True, timeout=30)
        return json.loads(result.stdout)
    except (OSError, subprocess.SubprocessError, ValueError) as error:
        raise BaselineUnavailable('Cannot read trusted GitHub deployment metadata') from error


def _pages(api, endpoint, key=None, max_pages=10):
    rows = []
    for page in range(1, max_pages + 1):
        separator = '&' if '?' in endpoint else '?'
        value = api(f'{endpoint}{separator}per_page=100&page={page}')
        value = value.get(key) if key and isinstance(value, dict) else value
        if not isinstance(value, list):
            raise BaselineUnavailable('Invalid paginated GitHub response')
        rows.extend(value)
        if len(value) < 100:
            return rows
    raise BaselineUnavailable('Deployment history exceeded the bounded lookup; use full tests')


def _run_id(log_url, repository):
    if not isinstance(log_url, str):
        return None
    url = urlsplit(log_url)
    match = re.fullmatch('/' + re.escape(repository) + r'/actions/runs/([1-9][0-9]*)(?:/job/[1-9][0-9]*)?/?', url.path)
    return int(match[1]) if url.scheme == 'https' and url.netloc == 'github.com' and match else None


def resolve_published_base(repository, *, workflow='pages.yml', branch='main',
                           exclude_head=None, api=gh_api, max_pages=3):
    """Return the first verified active Pages deployment, with bounded reads.

    GitHub lists deployments by newest creation and deployment statuses newest
    first. Inspect only the latest status: an old success followed by inactive
    is not the active release. Pending deployments can precede the still-active
    successful deployment; rollback to an older deployment works the same way.
    """
    if (not isinstance(repository, str) or not REPOSITORY.fullmatch(repository)
            or any(part in ('.', '..') for part in repository.split('/'))):
        raise BaselineUnavailable('Expected an owner/repository identity')
    if not isinstance(workflow, str) or not re.fullmatch(r'[A-Za-z0-9_.-]+\.ya?ml', workflow):
        raise BaselineUnavailable('Expected a Pages workflow filename')
    if exclude_head is not None and (not isinstance(exclude_head, str) or not SHA.fullmatch(exclude_head)):
        raise BaselineUnavailable('Expected a complete excluded head SHA')
    if type(max_pages) is not int or not 1 <= max_pages <= 3:
        raise BaselineUnavailable('Pages lookup is limited to three small deployment pages')
    endpoint = f'repos/{repository}'
    requests = 0

    def read(address):
        nonlocal requests
        if requests >= 24:
            raise BaselineUnavailable('Deployment lookup exceeded24 read requests; use full tests')
        requests += 1
        try:
            return api(address)
        except BaselineUnavailable:
            raise
        except (OSError, ValueError, TypeError, KeyError, AttributeError, subprocess.SubprocessError) as error:
            raise BaselineUnavailable('Cannot read trusted GitHub deployment metadata') from error

    run_cache, job_cache = {}, {}
    for page in range(1, max_pages + 1):
        deployments = read(f'{endpoint}/deployments?environment=github-pages&per_page=10&page={page}')
        if not isinstance(deployments, list):
            raise BaselineUnavailable('Invalid paginated GitHub deployments')
        for deployment in deployments:
            if not isinstance(deployment, dict):
                raise BaselineUnavailable('Invalid GitHub deployment')
            sha, ident = deployment.get('sha'), deployment.get('id')
            if (deployment.get('environment') != 'github-pages' or not isinstance(sha, str)
                    or not SHA.fullmatch(sha) or type(ident) is not int or ident < 1 or sha == exclude_head):
                continue
            statuses = read(f'{endpoint}/deployments/{ident}/statuses?per_page=1&page=1')
            if not isinstance(statuses, list):
                raise BaselineUnavailable('Invalid latest deployment status')
            if not statuses:
                continue
            status = statuses[0]
            if not isinstance(status, dict) or status.get('state') != 'success':
                continue
            run_id = _run_id(status.get('log_url'), repository)
            if run_id is None:
                continue
            if run_id not in run_cache:
                run_cache[run_id] = read(f'{endpoint}/actions/runs/{run_id}')
            run = run_cache[run_id]
            run_path = run.get('path') if isinstance(run, dict) else None
            head_repository = run.get('head_repository') if isinstance(run, dict) else None
            if (not isinstance(run, dict) or run.get('head_sha') != sha
                    or run.get('head_branch') != branch
                    or run.get('event') not in ('workflow_run', 'workflow_dispatch')
                    or run.get('status') != 'completed'
                    or not isinstance(run_path, str)
                    or run_path.split('@', 1)[0] != '.github/workflows/' + workflow
                    or not isinstance(head_repository, dict)
                    or not isinstance(head_repository.get('full_name'), str)
                    or head_repository['full_name'].lower() != repository.lower()):
                continue
            attempt = run.get('run_attempt')
            if type(attempt) is not int or attempt < 1:
                continue
            key = run_id, attempt
            if key not in job_cache:
                job_cache[key] = _pages(read, f'{endpoint}/actions/runs/{run_id}/attempts/{attempt}/jobs',
                                       key='jobs', max_pages=2)
            for job in job_cache[key]:
                if (not isinstance(job, dict) or job.get('name') != 'deploy'
                        or job.get('status') != 'completed' or job.get('conclusion') != 'success'
                        or type(job.get('id')) is not int or job['id'] < 1
                        or not isinstance(job.get('steps'), list)
                        or not any(isinstance(step, dict) and step.get('name') == 'Deploy verified artifact'
                                   and step.get('conclusion') == 'success' for step in job['steps'])):
                    continue
                try:
                    timestamp = datetime.fromisoformat(status['created_at'].replace('Z', '+00:00'))
                    if timestamp.tzinfo is None:
                        raise ValueError('Missing timezone')
                except (KeyError, TypeError, ValueError) as error:
                    raise BaselineUnavailable('Invalid successful deployment timestamp') from error
                return dict(sha=sha, run_id=run_id, run_attempt=attempt,
                            job_id=job['id'], deployment_id=ident,
                            status_created_at=status['created_at'], api_requests=requests)
        if len(deployments) < 10:
            break
    raise BaselineUnavailable('No verified active successful Pages deployment is available; use full tests')


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repository', required=True)
    parser.add_argument('--workflow', default='pages.yml')
    parser.add_argument('--branch', default='main')
    parser.add_argument('--head', help='Exclude this complete SHA, if resolving a previous release')
    parser.add_argument('--json', action='store_true', help='Print evidence metadata instead of only the SHA')
    args = parser.parse_args(argv)
    try:
        result = resolve_published_base(args.repository, workflow=args.workflow,
                                        branch=args.branch, exclude_head=args.head)
    except BaselineUnavailable as error:
        print(str(error), file=sys.stderr)
        return 1
    print(json.dumps(result, sort_keys=True) if args.json else result['sha'])
    return 0


if __name__ == '__main__':
    raise SystemExit(main())

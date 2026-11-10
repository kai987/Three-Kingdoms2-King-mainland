#!/usr/bin/env python3
"""Reuse the successful gate of the PR that introduced an exact main tree."""
import argparse
from datetime import datetime
import json
import os
from pathlib import Path
import subprocess

from gate import FLAGS, read_json, validate_plan
from plan import SHA, git, make_plan
from published_base import REPOSITORY, gh_api

SCHEMA = 'tk2-pr-verification-v1'
WORKFLOW = '.github/workflows/remake.yml'
PROOF_KEYS = ('mode', *[key for key in FLAGS if key != 'publish'],
              'groups', 'python_groups', 'scenario_ids', 'removed_scenario_ids')
LOOKUP_ERRORS = (OSError, ValueError, RuntimeError, TypeError, KeyError,
                 AttributeError, subprocess.SubprocessError)


def positive(value):
    return type(value) is int and value > 0


def sha(value):
    return isinstance(value, str) and bool(SHA.fullmatch(value))


def tree(repo, revision):
    if not sha(revision):
        raise ValueError('Invalid commit for tree lookup')
    return git(repo, 'rev-parse', '--verify', revision + '^{tree}').decode().strip()


def timestamp(value):
    return datetime.fromisoformat(value.replace('Z', '+00:00'))


def find(repository, head, event, *, api=gh_api):
    if (not REPOSITORY.fullmatch(repository or '') or not sha(head)
            or event.get('ref') != 'refs/heads/main' or event.get('after') != head
            or event.get('forced') is not False or not sha(event.get('before'))):
        raise ValueError('Expected an ordinary push to main')
    base = event['before']
    endpoint = f'repos/{repository}'
    pulls = api(f'{endpoint}/commits/{head}/pulls?per_page=30')
    matches = [pr for pr in pulls if pr.get('merge_commit_sha') == head and pr.get('merged_at')
               and pr['base']['ref'] == 'main' and pr['base']['repo']['full_name'] == repository
               and pr['head']['repo']['full_name'] == repository]
    if len(matches) != 1:
        raise ValueError('No unique merged pull request from this repository')
    pr = matches[0]
    number, feature = pr['number'], pr['head']['sha']
    if not positive(number) or not sha(feature):
        raise ValueError('Invalid merged pull request identity')
    runs = api(f'{endpoint}/actions/workflows/remake.yml/runs?event=pull_request'
               f'&status=success&head_sha={feature}&per_page=10')['workflow_runs']
    for run in runs:
        if (run.get('event') != 'pull_request' or run.get('status') != 'completed'
                or run.get('conclusion') != 'success' or run.get('path') != WORKFLOW
                or run.get('head_sha') != feature or run.get('head_branch') != pr['head']['ref']
                or run['head_repository']['full_name'] != repository
                or not positive(run.get('id')) or not positive(run.get('run_attempt'))
                or timestamp(run['updated_at']) > timestamp(pr['merged_at'])):
            continue
        jobs = api(f"{endpoint}/actions/runs/{run['id']}/attempts/{run['run_attempt']}/jobs?per_page=100")['jobs']
        if not any(job.get('name') == 'verify / gate' and job.get('status') == 'completed'
                   and job.get('conclusion') == 'success' and job.get('head_sha') == feature
                   and job.get('run_id') == run['id'] and job.get('run_attempt') == run['run_attempt']
                   and any(step.get('name') == 'Upload PR verification receipt' and step.get('conclusion') == 'success'
                           for step in job['steps']) for job in jobs):
            continue
        return dict(repository=repository, number=number, feature=feature, base=base,
                    run_id=run['id'], attempt=run['run_attempt'])
    raise ValueError('No successful verification for the merged PR head')


def receipt(repo, plan, repository, number, feature, run_id, attempt):
    validate_plan(plan)
    if (not plan['web'] or plan['publish'] or not REPOSITORY.fullmatch(repository or '')
            or not all(positive(value) for value in (number, run_id, attempt)) or not sha(feature)):
        raise ValueError('Invalid pull request verification receipt')
    return dict(schema=SCHEMA, repository=repository, number=number, feature=feature,
                run_id=run_id, attempt=attempt, tree=tree(repo, plan['head']), plan=plan)


def verify(repo, plan, candidate, proof, *, api=gh_api):
    if (not plan['publish'] or proof.get('schema') != SCHEMA or any(
            proof.get(key) != candidate[key] for key in
            ('repository', 'number', 'feature', 'run_id', 'attempt'))):
        raise ValueError('PR receipt belongs to a different run, attempt or pull request')
    pr_plan = validate_plan(proof['plan'])
    if pr_plan['publish'] or pr_plan.get('pr_reuse') or any(
            pr_plan.get(key) != plan.get(key) for key in PROOF_KEYS):
        raise ValueError('PR checks do not cover the exact release plan')
    local_tree = tree(repo, plan['head'])
    if proof.get('tree') != local_tree:
        raise ValueError('PR and main source trees differ')
    endpoint = f"repos/{candidate['repository']}"
    tested = api(f"{endpoint}/git/commits/{pr_plan['head']}")
    if (tested['sha'] != pr_plan['head'] or tested['tree']['sha'] != local_tree
            or [parent['sha'] for parent in tested['parents']] != [candidate['base'], candidate['feature']]):
        raise ValueError('The tested merge does not match the PR head and pre-merge main')
    git(repo, 'merge-base', '--is-ancestor', candidate['base'], plan['head'])
    return dict(number=candidate['number'], run_id=candidate['run_id'], attempt=candidate['attempt'],
                head=pr_plan['head'], tree=local_tree)


def write(path, value):
    Path(path).write_text(json.dumps(value, sort_keys=True) + '\n', encoding='utf-8')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=('find', 'receipt', 'decide'))
    parser.add_argument('--plan', required=True)
    parser.add_argument('--candidate')
    parser.add_argument('--proof')
    args = parser.parse_args()
    repo = Path.cwd()
    plan = validate_plan(read_json(args.plan), os.environ['GITHUB_SHA'])
    repository = os.environ['GITHUB_REPOSITORY']
    if args.command == 'receipt':
        event = read_json(os.environ['GITHUB_EVENT_PATH'])
        write(args.proof, receipt(repo, plan, repository, event['number'], event['pull_request']['head']['sha'],
                                  int(os.environ['GITHUB_RUN_ID']), int(os.environ['GITHUB_RUN_ATTEMPT'])))
    elif args.command == 'find':
        if not plan['publish']:
            return
        try:
            event = read_json(os.environ['GITHUB_EVENT_PATH'])
            candidate = find(repository, plan['head'], event)
        except LOOKUP_ERRORS as error:
            print(f'PR verification unavailable: {error}')
            return
        write(args.candidate, candidate)
        with open(os.environ['GITHUB_OUTPUT'], 'a', encoding='utf-8') as output:
            for key in ('run_id', 'attempt'):
                print(f'{key}={candidate[key]}', file=output)
    elif plan['publish']:
        try:
            if not args.proof:
                raise ValueError('Missing verification receipt')
            if Path(args.proof).stat().st_size > 64 * 1024:
                raise ValueError('Oversized verification receipt')
            plan['pr_reuse'] = verify(repo, plan, read_json(args.candidate), read_json(args.proof))
        except LOOKUP_ERRORS as error:
            print(f'Running full verification on main: {error}')
            if not plan['full']:
                plan = make_plan(repo, plan.get('base'), plan['head'], event_name='push',
                                 ref='refs/heads/main', force_full=True)
            plan['reasons'].append('No reusable PR verification receipt; run full checks on main')
        write(args.plan, plan)


if __name__ == '__main__':
    main()

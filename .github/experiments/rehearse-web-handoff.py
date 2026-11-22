"""Replay the proposed main push with the authentic receipt from PR 64."""

import json
import os
from pathlib import Path
import sys

sys.path.insert(0, str(Path.cwd() / 'tools/ci'))
from plan import git
from pr_reuse import find, write
from published_base import gh_api


repository = os.environ['GITHUB_REPOSITORY']
expected_run = int(os.environ['REHEARSAL_PR_RUN'])
repo = Path.cwd()
head = os.environ['TESTED_HEAD']
prefix = f'repos/{repository}'
pr = gh_api(f'{prefix}/pulls/64')
base, feature = pr['base']['sha'], pr['head']['sha']
assert pr['state'] == 'open' and pr['base']['ref'] == 'main'
assert pr['head']['ref'] == 'codex/single-verified-web-artifact'
assert pr['base']['repo']['full_name'] == pr['head']['repo']['full_name'] == repository
assert pr['merge_commit_sha'] == head
assert git(repo, 'rev-list', '--parents', '-n', '1', head).decode().split() == [head, base, feature]
run = gh_api(f'{prefix}/actions/runs/{expected_run}')
simulated = dict(ref='refs/heads/main', before=base, after=head, forced=False)
lookup = f'{prefix}/commits/{head}/pulls?per_page=30'


def api(endpoint):
    if endpoint == lookup:
        # All other metadata, including the successful gate and receipt upload
        # in the real PR workflow attempt, comes directly from GitHub.
        return [dict(pr, merged_at=run['updated_at'], merge_commit_sha=head)]
    return gh_api(endpoint)


candidate = find(repository, head, simulated, api=api)
assert candidate['number'] == 64 and candidate['run_id'] == expected_run
write('build/ci/pr-candidate.json', candidate)
with open(os.environ['GITHUB_OUTPUT'], 'a', encoding='utf-8') as output:
    for key in ('run_id', 'attempt'):
        print(f'{key}={candidate[key]}', file=output)
print(json.dumps(candidate, sort_keys=True))

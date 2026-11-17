"""Accept authentic PR receipts in a rehearsal without merging or deploying."""
from pathlib import Path
import os
import subprocess
import sys
import tempfile

sys.path.insert(0, str(Path.cwd() / 'tools/ci'))
from gate import read_json, validate_plan, verify_jobs
from plan import git, make_plan
from pr_reuse import MAX_RECEIPT_BYTES, find, verify, write
from published_base import gh_api

BASE = 'd304bf7a3b667bf355c9508b2ce77df5ec7f4310'
ROOT = Path.cwd()
REPOSITORY = os.environ['GITHUB_REPOSITORY']
PR_NUMBER = int(os.environ['PR_NUMBER'])
PREFIX = f'repos/{REPOSITORY}'
assert PR_NUMBER > 0
pr = gh_api(f'{PREFIX}/pulls/{PR_NUMBER}')
assert pr['state'] == 'open' and pr['draft'] and not pr['merged']
assert pr['base']['sha'] == BASE and pr['base']['ref'] == 'codex/ci-full-gate-sparse-base'
assert pr['head']['ref'] == 'codex/ci-full-gate-sparse'
assert pr['base']['repo']['full_name'] == pr['head']['repo']['full_name'] == REPOSITORY

head = git(ROOT, 'rev-parse', 'HEAD').decode().strip()
parents = git(ROOT, 'rev-list', '--parents', '-n', '1', head).decode().split()
assert parents == [head, BASE, pr['head']['sha']]
event = {'ref': 'refs/heads/main', 'before': BASE, 'after': head, 'forced': False}
publication_plan = make_plan(ROOT, BASE, head, event_name='push', event=event, force_full=True)
assert publication_plan['mode'] == 'full' and publication_plan['publish']

def check(variant, run_id):
    assert run_id > 0
    run = gh_api(f'{PREFIX}/actions/runs/{run_id}')
    attempt = run['run_attempt']
    assert run['event'] == 'pull_request' and run['conclusion'] == 'success'
    assert run['display_title'] == f'Measure full gate checkout ({variant})'
    # The PR is still open. Provide only the metadata an eventual merge
    # would have added. find() queries real run/attempt/job APIs as usual.
    merged_pr = dict(pr, base=dict(pr['base'], ref='main'),
                     merged_at=run['updated_at'], merge_commit_sha=head)
    lookup = f'{PREFIX}/commits/{head}/pulls?per_page=30'
    requested = []
    def api(endpoint):
        requested.append(endpoint)
        return [merged_pr] if endpoint == lookup else gh_api(endpoint)

    candidate = find(REPOSITORY, head, event, api=api)
    assert candidate['number'] == PR_NUMBER and candidate['run_id'] == run_id
    assert candidate['attempt'] == attempt and candidate['feature'] == pr['head']['sha']
    with tempfile.TemporaryDirectory() as directory:
        subprocess.run(['gh', 'run', 'download', str(run_id), '-R', REPOSITORY, '-n',
                        f'pr-proof-{run_id}-attempt-{attempt}', '-D', directory], check=True)
        receipt_path = Path(directory) / 'receipt.json'
        assert receipt_path.stat().st_size <= MAX_RECEIPT_BYTES
        proof = read_json(receipt_path)
    evidence = verify(ROOT, publication_plan, candidate, proof, api=api)
    assert evidence['head'] == proof['plan']['head']
    assert any(url.startswith(f'{PREFIX}/git/commits/') for url in requested)
    for changed_proof in (dict(proof, tree='0' * 40), dict(proof, run_id=run_id + 1)):
        try:
            verify(ROOT, publication_plan, candidate, changed_proof, api=api)
        except ValueError:
            pass
        else:
            raise AssertionError('Changed receipt was accepted')
    plan = validate_plan(dict(publication_plan, pr_reuse=evidence), head)
    expected_reuse = {name: {'result': 'skipped'} for name in
                      ('docs-check', 'native-rules', 'source-and-browser', 'scoped-tests',
                       'campaign-rules', 'campaign-soak', 'browser-ui', 'resupply-ui')}
    expected_reuse.update(scope={'result': 'success'}, **{'web-build': {'result': 'success'}})
    verify_jobs(plan, expected_reuse)
    write(result / f'{variant}.json', dict(simulated_push=event, actual_pr=PR_NUMBER, receipt=proof,
          verified_reuse=evidence, simulated_api_response=lookup, live_api_endpoints=requested[1:],
          rejected_changed_receipts=2, used_unmodified_production_checks=True))
    print(f'{variant}: accepted actual receipt for run {run_id}, attempt {attempt}, tree {evidence["tree"]}')

result = ROOT / 'build/ci-receipt-rehearsal'
result.mkdir(parents=True)
check('baseline', int(os.environ['BASELINE_RUN']))
check('sparse', int(os.environ['SPARSE_RUN']))

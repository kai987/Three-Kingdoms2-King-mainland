"""Exercise the Pages prepare job against a successful experiment run."""

import json
import os
from pathlib import Path
import re
import subprocess
import sys
from tempfile import TemporaryDirectory
from zipfile import ZipFile

sys.path.insert(0, str(Path.cwd() / 'tools/ci'))
from gate import verify_artifact

SOURCE = '1ddd7ab9bde3815e78e909a2966b688b4618e9c0'
CONTENT = '13e69886886b1738cca93d66f13d9ff66b0578c82f0ea203dd70ca80755bb33f'
BRANCH = 'codex/ci-gate-single-web-artifact'


def require(condition, message):
    if not condition:
        raise ValueError(message)


def api(path):
    return subprocess.check_output(
        ['gh', 'api', f'repos/{os.environ["GITHUB_REPOSITORY"]}/{path}']
    )


def metadata(path):
    return json.loads(api(path))


def main(run_id, variant):
    require(variant in ('baseline', 'single-artifact', 'reuse'), 'Unexpected CI variant')
    repository = os.environ['GITHUB_REPOSITORY']
    run = metadata(f'actions/runs/{run_id}')
    require(
        run['id'] == run_id and run['conclusion'] == 'success'
        and run['event'] == 'workflow_dispatch' and run['head_branch'] == BRANCH
        and run['head_repository']['full_name'] == repository
        and run['head_sha'] == os.environ['GITHUB_SHA']
        and run['path'] == '.github/workflows/remake.yml'
        and run['display_title'] == f'Web artifact experiment ({variant})',
        'Expected a successful CI run for this experiment revision',
    )
    attempt = run['run_attempt']
    endpoint = f'actions/runs/{run_id}'
    jobs = metadata(f'{endpoint}/attempts/{attempt}/jobs?per_page=100')['jobs']
    step = 'Retain the exact tested release' if variant == 'baseline' else 'Upload the verified candidate record'
    require(any(
        j['name'] == 'verify / gate' and j['conclusion'] == 'success'
        and any(s['name'] == step and s['conclusion'] == 'success' for s in j['steps'])
        for j in jobs
    ), 'The successful gate did not issue the expected publication evidence')
    artifacts = metadata(f'{endpoint}/artifacts?per_page=100')['artifacts']

    def unique(name):
        matches = [a for a in artifacts if a['name'] == name and not a['expired']]
        require(len(matches) == 1, f'Expected one live artifact named {name}')
        return matches[0]

    def read_json(name, file):
        artifact = unique(name)
        require(0 < artifact['size_in_bytes'] <= 65536, f'Oversized metadata {name}')
        from io import BytesIO
        with ZipFile(BytesIO(api(f'actions/artifacts/{artifact["id"]}/zip'))) as zip:
            require(zip.namelist() == [file], f'Invalid archive for {name}')
            require(zip.getinfo(file).file_size <= 65536, f'Oversized file in {name}')
            return json.loads(zip.read(file))

    plan = read_json(f'test-plan-{SOURCE}', 'test-plan.json')
    require(plan['schema'] == 'tk2-test-plan-v1' and plan['head'] == SOURCE
            and plan['publish'] is True and plan['docs_only'] is False,
            'CI did not authorize the frozen source for this rehearsal')
    require(bool(plan.get('pr_reuse')) == (variant == 'reuse'), 'Unexpected PR reuse status')
    if variant == 'baseline':
        artifact = unique(f'verified-web-{SOURCE}')
    else:
        proof = read_json(f'verified-candidate-{SOURCE}-attempt-{attempt}', 'verified-candidate.json')
        artifact = unique(f'candidate-web-{SOURCE}-attempt-{attempt}')
        require(proof == {
            'schema': 'tk2-verified-candidate-v1',
            'commit': SOURCE,
            'run_id': run_id,
            'attempt': attempt,
            'artifact_id': artifact['id'],
            'archive_sha256': artifact['digest'].removeprefix('sha256:'),
            'content_sha256': CONTENT,
        }, 'The candidate differs from the record issued by the gate')
        require(not any(a['name'] == f'verified-web-{SOURCE}' for a in artifacts),
                'Optimized CI uploaded a second Web release')

    fresh = metadata(f'actions/artifacts/{artifact["id"]}')
    digest = artifact['digest']
    require(re.fullmatch(r'sha256:[0-9a-f]{64}', digest) and fresh['digest'] == digest
            and fresh['workflow_run']['id'] == run_id and not fresh['expired'],
            'Artifact metadata does not identify the selected CI run')
    with TemporaryDirectory() as temp:
        archive = Path(temp) / 'candidate.zip'
        with archive.open('wb') as out:
            subprocess.run(['gh', 'api', f'repos/{repository}/actions/artifacts/{artifact["id"]}/zip'],
                           stdout=out, check=True)
        subprocess.run(['sha256sum', '-c', '-'], input=f'{digest[7:]}  {archive}\n',
                       text=True, check=True)
        subprocess.run(['unzip', '-q', str(archive), '-d', 'verified-web'], check=True)
    identity = verify_artifact(Path('verified-web'), SOURCE, CONTENT)
    report = {'ci_run': run_id, 'attempt': attempt, 'variant': variant, 'artifact_id': artifact['id'],
              'archive_sha256': digest[7:], 'content_sha256': CONTENT,
              'commit': SOURCE, 'files_checked': len(identity['files']), 'pr_reuse': plan.get('pr_reuse')}
    Path('prepare-evidence.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main(int(sys.argv[1]), sys.argv[2])

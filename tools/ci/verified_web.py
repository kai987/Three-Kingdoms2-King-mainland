"""Publish a verified candidate's identity and retrieve that exact archive for Pages."""

import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import stat
import subprocess
from tempfile import TemporaryDirectory
from zipfile import ZipFile

from gate import SHA, read_json, verify_artifact
from published_base import REPOSITORY, gh_api


SCHEMA = 'tk2-verified-candidate-v1'
DIGEST = re.compile(r'[0-9a-f]{64}')
RECORD_FIELDS = {'schema', 'commit', 'run_id', 'attempt', 'artifact_id',
                 'archive_sha256', 'content_sha256'}


def validate_record(record, *, head, run_id, attempt):
    if (not isinstance(record, dict) or set(record) != RECORD_FIELDS
            or record['schema'] != SCHEMA):
        raise ValueError('Unknown verified candidate record')
    if (not isinstance(record['commit'], str) or not SHA.fullmatch(record['commit'])
            or record['commit'] != head
            or any(type(record[key]) is not int or record[key] < 1
                   for key in ('run_id', 'attempt', 'artifact_id'))
            or (record['run_id'], record['attempt']) != (run_id, attempt)):
        raise ValueError('Verified candidate does not belong to this commit and run attempt')
    if any(not isinstance(record[key], str) or not DIGEST.fullmatch(record[key])
           for key in ('archive_sha256', 'content_sha256')):
        raise ValueError('Verified candidate lacks a valid SHA-256 digest')
    return record


def make_record(root, *, head, run_id, attempt, artifact_id, archive_sha256, content_sha256):
    record = validate_record(
        dict(schema=SCHEMA, commit=head, run_id=run_id, attempt=attempt,
             artifact_id=artifact_id, archive_sha256=archive_sha256, content_sha256=content_sha256),
        head=head, run_id=run_id, attempt=attempt,
    )
    verify_artifact(root, head, content_sha256)
    return record


def verify_metadata(record, artifact):
    if (artifact.get('id') != record['artifact_id']
            or artifact.get('workflow_run', {}).get('id') != record['run_id']
            or artifact.get('name') != f'candidate-web-{record["commit"]}'
            or artifact.get('expired') is not False
            or artifact.get('digest') != 'sha256:' + record['archive_sha256']):
        raise ValueError('GitHub artifact metadata differs from the verified candidate')


def verify_archive(record, archive, root):
    with Path(archive).open('rb') as stream:
        digest = hashlib.file_digest(stream, 'sha256').hexdigest()
    if digest != record['archive_sha256']:
        raise ValueError('Downloaded candidate archive SHA-256 differs from the gate record')
    with ZipFile(archive) as zipped:
        paths = set()
        for member in zipped.infolist():
            name = member.filename.rstrip('/')
            path = PurePosixPath(name)
            if (not path.parts or path.is_absolute() or '..' in path.parts or '\\' in name
                    or path.as_posix() != name or name in paths or stat.S_ISLNK(member.external_attr >> 16)):
                raise ValueError('Unsafe path in the verified candidate archive')
            paths.add(name)
        zipped.extractall(root)
    return verify_artifact(root, record['commit'], record['content_sha256'])


def prepare(record, repository, root):
    if not REPOSITORY.fullmatch(repository):
        raise ValueError('Invalid GitHub repository')
    endpoint = f'repos/{repository}/actions/artifacts/{record["artifact_id"]}'
    verify_metadata(record, gh_api(endpoint))
    with TemporaryDirectory() as directory:
        archive = Path(directory) / 'candidate.zip'
        with archive.open('wb') as stream:
            subprocess.run(['gh', 'api', endpoint + '/zip'], stdout=stream, check=True)
        return verify_archive(record, archive, root)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=('record', 'prepare'))
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--record', type=Path, required=True)
    parser.add_argument('--head', required=True)
    parser.add_argument('--run-id', type=int, required=True)
    parser.add_argument('--attempt', type=int, required=True)
    args = parser.parse_args()
    context = dict(head=args.head, run_id=args.run_id, attempt=args.attempt)
    if args.command == 'record':
        record = make_record(
            args.root, **context, artifact_id=int(os.environ['CANDIDATE_ID']),
            archive_sha256=os.environ['CANDIDATE_ARCHIVE_SHA'],
            content_sha256=os.environ['CONTENT_SHA'],
        )
        args.record.write_text(json.dumps(record, separators=(',', ':')) + '\n', encoding='utf-8')
        print(f'Verified candidate {record["artifact_id"]}, content SHA-256 {record["content_sha256"]}')
    else:
        record = validate_record(read_json(args.record), **context)
        identity = prepare(record, os.environ['GITHUB_REPOSITORY'], args.root)
        print(f'Verified {len(identity["files"])} files from candidate {record["artifact_id"]}, '
              f'content SHA-256 {record["content_sha256"]}')


if __name__ == '__main__':
    main()

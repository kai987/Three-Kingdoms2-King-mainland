"""Verify the parent package and materialize only hash-pinned historical references."""
from argparse import ArgumentParser
from pathlib import Path
from zipfile import ZipFile
import hashlib
import json

def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream,'sha256').hexdigest()


def main():
    parser=ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True,help='Directory with the extracted V2.2.2 manifest')
    parser.add_argument('--previous',type=Path,required=True,help='Original V2.2.1 validation ZIP')
    args=parser.parse_args()
    root=args.output.resolve()
    manifest=json.loads((root/'validation-manifest.json').read_text())
    if sha(args.previous)!=manifest['previous_package']['sha256']:
        raise ValueError('The previous package does not match its pinned SHA-256')
    with ZipFile(args.previous) as prior:
        for name,entry in manifest['referenced_files'].items():
            target=(root/name).resolve()
            if not target.is_relative_to(root):
                raise ValueError(f'Invalid target path {name}')
            data=prior.read(entry['member'])
            if len(data)!=entry['bytes'] or hashlib.sha256(data).hexdigest()!=entry['sha256']:
                raise ValueError(f'Corrupt historical member {entry["member"]}')
            if target.exists() and sha(target)!=entry['sha256']:
                raise ValueError(f'A different file already exists at {target}')
            if not target.exists():
                target.parent.mkdir(parents=True,exist_ok=True)
                with target.open('xb') as stream:
                    stream.write(data)
    print(len(manifest['referenced_files']),'references verified',flush=True)


if __name__=='__main__':
    main()

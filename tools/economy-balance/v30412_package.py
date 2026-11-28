"""Copy inspectable summaries and seal replay evidence into independent ZIP files."""
from argparse import ArgumentParser
import hashlib
from pathlib import Path
import shutil
import zipfile

from common import to_csv


MAX_PART_BYTES = 95_000_000


def checksum(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def bundle(root, archive, phases):
    packets = []
    for phase in phases:
        source = root/phase
        if not source.is_dir():
            raise ValueError(f'Missing requested evidence phase {source}')
        files = [file for file in sorted(source.rglob('*')) if file.is_file()
                 and not file.is_symlink() and file.name != '.DS_Store']
        if not files:
            raise ValueError(f'No evidence present for {phase}')
        parts, current, size = [], [], 0
        for file in files:
            length = file.stat().st_size
            if length > MAX_PART_BYTES:
                raise ValueError(f'Group the provenance for this large source separately: {file}')
            if current and size + length > MAX_PART_BYTES:
                parts.append(current)
                current, size = [], 0
            current.append(file)
            size += length
        if current:
            parts.append(current)
        for number, part in enumerate(parts, 1):
            dest = archive/f'v30412-{phase}-{number:02}.zip'
            manifest = []
            with zipfile.ZipFile(dest, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=6) as packed:
                for file in part:
                    rel = file.relative_to(root).as_posix()
                    manifest.append((rel, checksum(file), file.stat().st_size))
                    packed.write(file, rel)
                packed.writestr('CONTENT_SHA256.txt',
                                '\n'.join(f'{digest}  {rel}' for rel, digest, _ in manifest)+'\n')
            with zipfile.ZipFile(dest) as packed:
                if dest.stat().st_size > 100_000_000 or packed.testzip() is not None:
                    raise ValueError(f'Archive limit or integrity check failed for {dest}')
                for rel, digest, _ in manifest:
                    with packed.open(rel) as stream:
                        if hashlib.file_digest(stream, 'sha256').hexdigest() != digest:
                            raise ValueError(f'Unpacked payload mismatch: {rel}')
            packets.extend(dict(package=dest.name, source=rel, raw_sha256=digest, raw_bytes=length,
                                package_bytes=dest.stat().st_size, package_sha256=checksum(dest))
                           for rel, digest, length in manifest)
    return packets


def main():
    parser = ArgumentParser(description=__doc__)
    parser.add_argument('evidence', type=Path)
    parser.add_argument('summary', type=Path)
    parser.add_argument('destination', type=Path)
    parser.add_argument('--phase', nargs='+', required=True)
    args = parser.parse_args()
    destination = args.destination
    distribution = destination/'summary'
    if not (args.summary/'docs'/'README.md').is_file():
        raise ValueError('Provide the reviewed summary before packaging')
    shutil.copytree(args.summary, distribution, dirs_exist_ok=True)
    packets = destination/'packages'
    packets.mkdir(parents=True, exist_ok=True)
    mapped = bundle(args.evidence, packets, args.phase)
    to_csv(distribution/'sources'/'raw-file-index.csv', mapped)
    members = sorted(path for path in destination.rglob('*') if path.is_file()
                     and path.name not in ('.DS_Store', 'SHA256SUMS.txt'))
    attestation = ''.join(f'{checksum(file)}  {file.relative_to(destination).as_posix()}\n' for file in members)
    (destination/'SHA256SUMS.txt').write_text(attestation, encoding='utf-8')


if __name__ == '__main__':
    main()

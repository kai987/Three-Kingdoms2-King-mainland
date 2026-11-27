"""Recover exact replay inputs from the published evidence and retained archives."""
import argparse
from hashlib import sha256
import json
from pathlib import Path
from zipfile import ZipFile


def digest(data):
    return sha256(data).hexdigest()


def recover(prior, directories, output):
    checks = prior / 'summary/checks'
    index = {}
    for group, filename in (
            ('fixed', 'fixed-capacity-replay-traces.json'),
            ('historical', 'historical-convoy-safety.json'),
            ('performance', 'scheduler-performance-profile.json')):
        payload = json.loads((checks / filename).read_bytes())
        for row in payload if isinstance(payload, list) else payload['results']:
            name = row.get('fixture', row.get('checkpoint'))
            hashed = row.get('fixture_sha256', row.get('checkpoint_sha256', row.get('sha256')))
            key = (group, row.get('label', str(row.get('convoy', name))))
            index[key] = dict(name=name, sha256=hashed, scenario=row.get('scenario'),
                              strategy=row.get('strategy'), seed=row.get('seed'), weather=row.get('weather'))
    source = json.loads((prior / 'summary/sources/checkpoint-sources.json').read_bytes())
    for name, row in source.items():
        index['south', name] = dict(name=name, sha256=row['sha256'], scenario='208-10',
                                    strategy=211, seed=2026)
    inputs = json.loads((checks / 'fixed-replay-inputs.json').read_bytes())
    for name, hashed in inputs['archived_csv'].items():
        index['reference', name] = dict(name=name, sha256=hashed)
    needed = {row['sha256'] for row in index.values()}
    names = {row['name'] for row in index.values()}
    found = {}

    def retain(name, content, container, member=None):
        hashed = digest(content)
        if hashed in needed and hashed not in found:
            found[hashed] = content, dict(container=str(container), member=member)

    packages = []
    for root in directories:
        for path in sorted(root.rglob('*')):
            if not path.is_file():
                continue
            if path.name in names:
                retain(path.name, path.read_bytes(), path)
            elif path.suffix == '.zip':
                packages.append(path)
    for path in sorted(set(packages)):
        with ZipFile(path) as archive:
            for entry in archive.namelist():
                name = Path(entry).name
                if name in names:
                    retain(name, archive.read(entry), path, entry)
    results = []
    for (group, label), row in sorted(index.items()):
        hit = found.get(row['sha256'])
        record = dict(group=group, label=label, **row, restored=hit is not None)
        if hit is not None:
            content, origin = hit
            folder = output / group
            folder.mkdir(parents=True, exist_ok=True)
            file = folder / (label + '.json.gz' if group in ('performance', 'historical') else row['name'])
            file.write_bytes(content)
            record.update(origin, file=str(file.relative_to(output)))
        results.append(record)
    output.mkdir(parents=True, exist_ok=True)
    (output / 'input-manifest.json').write_text(json.dumps(results, indent=2)+'\n', encoding='utf-8')
    return results


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('prior', type=Path)
    parser.add_argument('output', type=Path)
    parser.add_argument('directories', type=Path, nargs='+')
    args = parser.parse_args()
    results = recover(args.prior, args.directories, args.output)
    for row in results:
        print(row['group'], row['label'], row['sha256'], 'verified' if row['restored'] else 'missing')
    return int(not all(row['restored'] for row in results if row['group'] in ('fixed', 'south', 'reference')))


if __name__ == '__main__':
    raise SystemExit(main())

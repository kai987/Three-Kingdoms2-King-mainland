"""Verify delivery identity and military grain ratios without loading the game."""
from argparse import ArgumentParser
from contextlib import ExitStack
import csv
from hashlib import sha256
from io import TextIOWrapper
import json
from pathlib import Path
from zipfile import ZipFile


def checksum(stream):
    digest = sha256()
    while block := stream.read(1024*1024):
        digest.update(block)
    return digest.hexdigest()


def verify_list(root, name='SHA256SUMS.txt'):
    found = 0
    for text in (root/name).read_text(encoding='utf-8').splitlines():
        expected, path = text.split('  ', 1)
        with (root/path).open('rb') as stream:
            assert checksum(stream) == expected, path
        found += 1
    return found


def checks(archive):
    summary_count = verify_list(archive/'summary')
    archive_count = verify_list(archive/'archives')
    index = json.loads((archive/'archives/archive-index.json').read_text(encoding='utf-8'))
    with (archive/'summary/data/scenario-scores.csv').open(encoding='utf-8', newline='') as stream:
        scores = list(csv.DictReader(stream))
    runs = json.loads((archive/'summary/data/simulation-manifest.json').read_text(encoding='utf-8'))
    baseline = json.loads((archive/'summary/sources/baseline.json').read_text(encoding='utf-8'))
    identity = ('wave', 'scenario', 'seed', 'strategy', 'variant')
    identity_of = lambda row: tuple(str(row[key]) for key in identity)
    records = {identity_of(row):row for row in runs}
    members = 0
    with ExitStack() as stack:
        content = {}
        for row in index['archives']:
            path = archive/'archives'/row['name']
            package = stack.enter_context(ZipFile(path))
            assert package.testzip() is None
            assert json.loads(package.read('FILE-MANIFEST.json')) == row['files']
            for member in row['files']:
                location = member['file']
                with package.open(location) as stream:
                    assert checksum(stream) == member['sha256'], (path.name, location)
                assert package.getinfo(location).file_size == member['bytes']
                assert location not in content, location
                content[location] = (package, member['sha256'])
                members += 1
        comparisons = (
            ('unpaid_city_turns', 'unpaid_city_turns'), ('rations_missing', 'rations_missing'),
            ('battles', 'battles'), ('convoy_dispatched', 'convoy_dispatched'),
            ('final_grain', 'grain_stock'), ('final_population', 'population'))
        for row in scores:
            request = int(row['requested_grain'])
            for value, amount in (('timely_grain_rate', 'timely_received_grain'),
                                  ('original_deadline_grain_rate', 'timely_at_original_deadline')):
                if request:
                    assert abs(float(row[value])-100*int(row[amount])/request) < 1e-9, row
                else:
                    assert row[value] == 'null', row
            case = records[identity_of(row)]
            assert case['source'] == index['engine_source'], case
            assert case['scenario_sha256'] == baseline['scenario_sha256'][case['scenario']], case
            assert case['map_sha256'] == baseline['map_sha256'], case
            assert case['engine_worktree_diff_sha256'] == sha256(b'').hexdigest(), case
            for name in ('monthly', 'factions', 'cities'):
                location = f"observed/{case['output']}/{case['scenario']}/{name}.csv"
                package, verified = content[location]
                assert verified == case['table_sha256'][name], location
                if name == 'monthly':
                    with TextIOWrapper(package.open(location), encoding='utf-8', newline='') as stream:
                        latest = list(csv.DictReader(stream))[-1]
                    assert latest['elapsed_months'] == row['full_months'], location
                    for score, raw in comparisons:
                        assert int(row[score]) == int(latest[raw]), (location, score)
    return dict(summary_files=summary_count, indexed_archive_files=archive_count, checked_members=members,
                scored_campaigns=len(scores), raw_macroeconomic_checks=len(comparisons)*len(scores),
                engine_source=index['engine_source'])


if __name__=='__main__':
    parser = ArgumentParser(description=__doc__)
    parser.add_argument('archive', type=Path, help='Directory containing summary/ and archives/')
    args = parser.parse_args()
    print(json.dumps(checks(args.archive), ensure_ascii=False))

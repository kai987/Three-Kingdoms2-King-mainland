"""Shared file and scenario access for the read-only balance exports."""
import csv
import hashlib
import json
from collections import Counter
from itertools import chain
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'source'))

from remake.campaign import Campaign, Catalog
from remake.march_core import backend_status

CATALOG_INDEX = ROOT / 'game/data/campaigns/index.json'
RUNTIME_PATHS = ('source/remake', 'crates/march-core/src', 'game/config',
                 'game/data/campaigns', 'game/app.js', 'game/battle*', 'game/events.js',
                 'game/facilities.js', 'game/city-development.js', 'game/locales', 'game/browser-engine-worker.js', 'game/march-worker.js', 'game/wasm/manifest.json')


def git(*args):
    return subprocess.check_output(['git', '-C', str(ROOT), *args])


def catalog_paths():
    index = json.loads(CATALOG_INDEX.read_text(encoding='utf-8'))
    return [ROOT / 'game/data' / entry for entry in index['catalogs']]


def catalogs():
    return [Catalog(path) for path in catalog_paths()]


class HeadlessCampaign(Campaign):
    """Keep the command transaction and validation, skip the unrelated UI view."""

    def view(self):
        return {}


def open_game(catalog, seed, *, faction='observer'):
    game = HeadlessCampaign(catalog, record_journal=False)
    game.command('new', dict(faction=faction, seed=seed, difficulty='normal'), 0)
    return game


def to_csv(path, rows):
    rows = iter(rows)
    first = next(rows, None)
    if first is None:
        raise ValueError(f'No data for {path}')
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('w', encoding='utf-8', newline='') as handle:
        writer = csv.DictWriter(handle, fieldnames=list(first), lineterminator='\n')
        writer.writeheader()
        for row in chain((first,), rows):
            writer.writerow({key: _csv_cell(value) for key, value in row.items()})


def _csv_cell(value):
    if value is None:
        return 'null'
    if isinstance(value, (list, dict, bool)):
        return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'))
    return value


def to_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + '\n',
                    encoding='utf-8')


def sha256(raw):
    return hashlib.sha256(raw).hexdigest()


def provenance(catalog_rows, args):
    changed = git('diff', '--name-only', 'HEAD', '--', *RUNTIME_PATHS).decode().splitlines()
    added = git('ls-files', '--others', '--exclude-standard', '--', *RUNTIME_PATHS).decode().splitlines()
    paths = sorted(set(changed + added))
    return dict(
        git_sha=git('rev-parse', 'HEAD').decode().strip(),
        git_branch=git('rev-parse', '--abbrev-ref', 'HEAD').decode().strip(),
        extraction_date=args.date,
        opening_seed=args.seed,
        opening_seat='observer',
        opening_difficulty='normal',
        backend=backend_status(),
        runtime_worktree_diff_sha256=sha256(git('diff', '--binary', 'HEAD', '--', *RUNTIME_PATHS)),
        runtime_worktree_files={path: sha256((ROOT / path).read_bytes()) if (ROOT / path).is_file() else None
                                for path in paths},
        catalogs=[dict(scenario_id=c.data['id'], catalog_sha256=c.sha256,
                       active_cities=len(c.data['active_cities'])) for c in catalog_rows],
        requested=dict(sections=list(args.sections), scenario=args.scenario,
                       battle_replicates=args.battle_replicates),
    )


def null_counts(rows):
    return dict(sorted(Counter(key for row in rows for key, value in row.items() if value is None).items()))

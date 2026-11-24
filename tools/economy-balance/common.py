"""Shared file and scenario access for the read-only balance exports."""
import csv
import hashlib
import json
import os
from itertools import chain
from pathlib import Path
import subprocess
import sys

TOOL_ROOT = Path(__file__).resolve().parents[2]
ROOT = Path(os.environ.get('TK2_OBSERVER_RUNTIME_ROOT', TOOL_ROOT)).resolve()
sys.path.insert(0, str(ROOT / 'source'))

from remake.campaign import Campaign, Catalog

CATALOG_INDEX = ROOT / 'game/data/campaigns/index.json'


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

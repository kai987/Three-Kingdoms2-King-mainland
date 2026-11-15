"""Stage valid field contacts that reach a branch in one real soldier step."""
from itertools import product
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / 'tests'), str(ROOT / 'source')]
from browser_soldier_fixture import contact_fixture, _save
from remake.campaign import Campaign, Catalog


def fixture(branch, original):
    game = Campaign(Catalog(ROOT / 'game/data/campaigns/208-10.json'))
    game.load_save(original, game.revision)
    battle = game.state.battle
    row = battle['extended']['siege']
    assert row['mode'] == 'field'
    generals = {piece['side']: piece for piece in row['units'] if piece['kind'] == 'general'}
    locations = ((0, 5), (15, 9)) if branch == 'ended' else ((4, 5), (5, 5))
    for piece, (x, y) in zip(generals.values(), locations):
        piece.update(x=x, y=y)
    other_cells = iter(product(range(9, 15), range(5)))
    for piece in row['units']:
        if piece['kind'] != 'general':
            piece['x'], piece['y'] = next(other_cells)

    assert battle['attacker'] == game.state.player
    row['piece_orders']['attackers'] = {
        piece['id']: ('retreat' if branch == 'ended' else 'advance')
        if piece['kind'] == 'general' else 'wait'
        for piece in row['units'] if piece['side'] == 'attackers'
    }
    case = _save(game)['save']
    game.command('siege_orders', dict(battle_id=battle['id'], piece_orders=row['piece_orders']['attackers']), game.revision)
    game.command('siege_step', dict(battle_id=battle['id']), game.revision)
    ext = game.state.battle['extended']
    if branch == 'ended':
        assert ext.get('siege') is None and not ext['duel']
    else:
        assert ext['siege']['round'] == row['round'] and ext['duel']['round'] == 1
    return {'before': case, 'expected': game.export_save()}


original = contact_fixture()['save']
print(json.dumps({branch: fixture(branch, original) for branch in ('ended', 'duel')}, ensure_ascii=False))

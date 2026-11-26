"""Replay Chibi campaign convoy 1706 without altering a strategic decision."""
from argparse import ArgumentParser
from pathlib import Path
from unittest.mock import patch
import csv
import gzip
import json

from common import ROOT, TOOL_ROOT, to_json
from observe import RecordedCampaign, run_scenario
from observer_telemetry import config
from v222_experiments import Recorder
from v222_reproduce import record
from remake import logistics, market_pricing, transport_emergency, winter_weather

SCENARIO, SEED, CONVOY = '208-10', 2026, 1706
TICKS = {6180, 6190, 6200, 6210, 6220, 6230, 6240, 6970}


def audit(output):
    replay=json.loads((output/'convoy-1706.json').read_text())
    terminal=replay['terminal']
    folder=output/SCENARIO
    with gzip.open(folder/'transport-progress-daily.csv.gz','rt',encoding='utf-8') as stream:
        reached=next(row for row in csv.DictReader(stream) if row['convoy']==str(CONVOY)
                     and row['node']=='hanzhong' and row['tick']=='6225')
    with (folder/'emergency-transport-decisions.csv').open(encoding='utf-8') as stream:
        decision=next(row for row in csv.DictReader(stream) if row['convoy_id']==str(CONVOY)
                      and row['tick']=='6230')
    assert (reached['rations_after'],decision['current_rations'],decision['emergency_route_budget'],
            decision['emergency_target'],decision['decision'])==('124','124','1091','jiameng','no_feasible_exit')
    assert terminal['initial_escort']==terminal['escort_hunger_loss']==2102
    assert terminal['current_escort']==0 and terminal['actual_terminal_tick']==6970
    assert terminal['terminal_status']=='returned_home'
    snap=replay['snapshots']
    assert next(row for row in snap if row['tick']==6230)['expected_city']!='liu_zhang'
    before=next(row['convoy'] for row in snap if row['tick']==6200)
    alternate=next(row for row in before['possible_nodes'] if row['city']=='badong')
    assert before['bag']==1392 and alternate['covered'] and alternate['receiving_blocker'] is None
    to_json(output/'regression-check.json',dict(verified=True,same_case=True,reached=reached,
        decision=decision,terminal=terminal,owners={row['tick']:row['expected_city'] for row in snap},
        departure_alternative=alternate,loss='all_original_escorts',original_escorts_survived=False))


def main():
    cli = ArgumentParser(description=__doc__)
    cli.add_argument('--output', required=True, type=Path)
    cli.add_argument('--audit-existing',action='store_true')
    args = cli.parse_args()
    output = args.output
    if args.audit_existing:
        audit(output)
        return
    snapshots = []
    original = RecordedCampaign.command

    def command(game, *values, **kwargs):
        view = original(game, *values, **kwargs)
        state = game.state
        tick = (state.turn - 1)*10
        if tick in TICKS:
            row = next((row for row in logistics._pool(state)['convoys'] if row['id'] == CONVOY), None)
            facts = dict(tick=tick, expected_city=state.cities['hanzhong'].owner, convoy=None)
            if row is not None:
                if (row['source'], row['original_target']) != ('hanzhong', 'xincheng'):
                    raise ValueError('Convoy identity differs from the archived run')
                facts['convoy'] = record(game,state,row)
            snapshots.append(facts)
            to_json(output/'node-decisions.json', snapshots)
        return view

    output.mkdir(parents=True, exist_ok=True)
    settings = config(TOOL_ROOT/'tools/economy-balance/observer-config.json')
    with patch.object(RecordedCampaign,'command',command), Recorder(output/SCENARIO) as observer:
        with market_pricing.experiment(0), transport_emergency.experiment(3), winter_weather.experiment(
                5,adjustments=winter_weather.CORRECTIONS,detailed=True,observe=observer):
            run = run_scenario(SCENARIO,SEED,233,output,'G4al',settings)
    terminal = observer.convoys.get(CONVOY)
    if run['outcome'] != 'complete' or terminal is None:
        raise ValueError(f'Missing historical convoy replay: {run.get("failure")}')
    to_json(output/'convoy-1706.json',dict(runtime=str(ROOT),seed=SEED,scenario=SCENARIO,
        strategy=212,market=0,weather=221,emergency=222,head=run['head'],
        terminal=terminal,snapshots=snapshots))
    audit(output)


if __name__=='__main__':
    main()

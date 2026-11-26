"""Replay Chibi campaign convoy 1706 without altering a strategic decision."""
from argparse import ArgumentParser
from pathlib import Path
from unittest.mock import patch

from common import ROOT, TOOL_ROOT, to_json
from observe import RecordedCampaign, run_scenario
from observer_telemetry import config
from v222_experiments import Recorder
from v222_reproduce import record
from remake import logistics, market_pricing, transport_emergency, winter_weather

SCENARIO, SEED, CONVOY = '208-10', 2026, 1706
TICKS = {6180, 6190, 6200, 6210, 6220, 6230, 6240, 6970}


def main():
    cli = ArgumentParser(description=__doc__)
    cli.add_argument('--output', required=True, type=Path)
    args = cli.parse_args()
    output = args.output
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


if __name__=='__main__':
    main()

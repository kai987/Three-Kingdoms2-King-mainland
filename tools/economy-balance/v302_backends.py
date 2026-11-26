"""Compare actual seeded V3.0.2 observer state across both route backends."""
from argparse import ArgumentParser
from hashlib import sha256
import json

from common import ROOT, Catalog, HeadlessCampaign
from remake import logistics_strategy, march_core, strategic_granary


def replay(backend, scenario, turns, version):
    catalog = Catalog(ROOT/'game/data/campaigns'/f'{scenario}.json')
    game = HeadlessCampaign(catalog,record_journal=False)
    switches = dict(proactive=True,winter=True,relay=True)
    if version == 3021:
        switches.update(coordination=True,return_safety=True)
    with march_core.using_backend(backend), logistics_strategy.experiment(4,army=True,recovery=True), \
         strategic_granary.experiment(version=version,**switches):
        game.command('new',dict(faction='observer', seed=2026, weather_rules_version=221,
                                 transport_emergency_rules_version=222,regional_market_rules_version=301),0)
        checks=[]
        for _ in range(turns):
            game.command('observe_turn',{},game.revision)
            payload=json.dumps(game.export_save(),ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()
            checks.append(sha256(payload).hexdigest())
        return checks, game.state.rng.draws, game.state.turn, game.state.extension['strategic_granary']['next_id']-1


def main():
    parser=ArgumentParser(description=__doc__)
    parser.add_argument('--scenario',default='184-02')
    parser.add_argument('--turns',type=int,default=18)
    parser.add_argument('--version',type=int,choices=(302,3021),default=302)
    args=parser.parse_args()
    python= replay('python',args.scenario,args.turns,args.version)
    rust= replay('rust',args.scenario,args.turns,args.version)
    print(json.dumps(dict(scenario=args.scenario,turns=args.turns,version=args.version,capture=python,exact=python==rust)))
    if python!=rust:
        print(json.dumps(dict(rust=rust)))
    return int(python!=rust)


if __name__=='__main__':
    raise SystemExit(main())

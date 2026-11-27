"""Replay authentic saves and verify cross-backend compatibility with V2.3.1."""
from argparse import ArgumentParser
from contextlib import ExitStack
from pathlib import Path
import json

from common import Catalog, HeadlessCampaign, ROOT, git, sha256, to_json
from remake import winter_agriculture, winter_forecast as forecast, winter_weather as weather
from remake.campaign import digest
from v23_compat import probe, roundtrip
from v3021_checkpoints import configure


def run_candidate(output, transfers=None):
    game=HeadlessCampaign(Catalog(ROOT/'game/data/campaigns/208-10.json'),record_journal=False)
    phases={'winter':(1,11),'spring':(4,11),'frozen':(6,1),'harvest':(9,21)}
    proofs={}
    with ExitStack() as stack:
        configure(stack,211,221)
        stack.enter_context(weather.experiment(5,adjustments=weather.CORRECTIONS))
        if transfers:
            selection=sorted(transfers.glob('*-compact.json'))
            assert len(selection)==len(phases)
            for checkpoint in selection:
                phase=checkpoint.name.removesuffix('-compact.json')
                for form in ('compact','plain'):
                    path=transfers/f'{phase}-{form}.json'
                    payload=json.loads(path.read_text())
                    game.load_save(payload,game.revision)
                    assert game.export_save(compact=form=='compact')==payload
                    roundtrip(game,payload)
                proofs[phase]=exercise_checkpoint(game)
        else:
            game.command('new',dict(faction='observer',seed=2026,weather_rules_version=23,
                                   weather_forecast_version=231),0)
            while len(proofs)<len(phases):
                state=game.state
                assert state.turn<=37
                for phase,day in phases.items():
                    if (state.month,state.day)!=day or phase in proofs:
                        continue
                    for form in ('plain','compact'):
                        payload=game.export_save(compact=form=='compact')
                        roundtrip(game,payload)
                        to_json(output.parent/'saves'/f'{phase}-{form}.json',payload)
                    proofs[phase]=exercise_checkpoint(game)
                game.command('observe_turn',{},game.revision)
    to_json(output,dict(source=git('rev-parse','HEAD').decode().strip(),phases=proofs))


def exercise_checkpoint(game):
    before=game.to_dict()
    assert before['extension'][forecast.FIELD]==231
    winter=before['extension'][weather.POOL]
    agriculture=winter_agriculture.summary(game.state,'liaodong')
    prediction=forecast.snowpack_risk(game.state,'liaodong',days=10)
    clone=HeadlessCampaign(game.catalog,record_journal=False)
    clone.load_save(game.export_save(compact=True),0)
    clone.command('observe_turn',{},clone.revision)
    after=clone.to_dict()
    return dict(date=[game.state.year,game.state.month,game.state.day],before=digest(before),
                after=digest(after),rng=after['rng'],snow=winter['regions']['liaodong']['depth'],
                multiplier=agriculture['multiplier'],finalized=agriculture['finalized'],
                visible_risk=prediction)


def finish(output, baseline):
    def read(folder,name):
        return json.loads((folder/(name+'.json')).read_text(encoding='utf-8'))
    old=read(baseline,'legacy-v23-rust')
    new=read(output,'legacy-v231-rust')
    assert old['states']==new['states']
    assert old['history']==new['history']
    old23=read(baseline,'candidate-rust')
    new23=read(output,'disabled-v231-rust')
    assert old23['states']==new23['states']
    for key in ('archived-latest',):
        assert read(baseline,key)['history']==read(output,key)['history']
    phases=read(output,'candidate-python')['phases']
    for label in ('candidate-rust','candidate-rust-reads-python','candidate-python-reads-rust'):
        assert read(output,label)['phases']==phases,label
    original=read(baseline,'compatibility')
    to_json(output/'compatibility.json',dict(source=new['source'],original=old['source'],
        no_weather_22_221_checkpoints=sum(len(row['states']) for row in new['states']),
        unchanged_v23_checkpoints=sum(len(row['states']) for row in new23['states']),
        save_formats=['plain','compact'],cross_backend_phases=phases,
        historic_replayed=original['historic_replayed'],historic_quoted=original['historic_unverified'],
        historical_artifacts=[*new['history'],*read(output,'archived-latest')['history']],
        verified_file_sha256={path.name:sha256(path.read_bytes()) for path in output.glob('*.json')
                             if path.name!='compatibility.json'}))


if __name__=='__main__':
    parser=ArgumentParser(description=__doc__)
    commands=parser.add_subparsers(dest='mode',required=True)
    one=commands.add_parser('candidate')
    one.add_argument('output',type=Path)
    one.add_argument('--transfers',type=Path)
    two=commands.add_parser('finish')
    two.add_argument('output',type=Path)
    two.add_argument('baseline',type=Path)
    three=commands.add_parser('original')
    three.add_argument('output',type=Path)
    three.add_argument('regime',choices=('legacy','candidate','archives'))
    three.add_argument('artifacts',nargs='*',type=Path)
    args=parser.parse_args()
    if args.mode=='candidate':
        run_candidate(args.output,args.transfers)
    elif args.mode=='finish':
        finish(args.output,args.baseline)
    else:
        probe(args.output,args.regime,args.artifacts)

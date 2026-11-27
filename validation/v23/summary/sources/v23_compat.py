"""Compare legacy weather and real archived checkpoints with the pre-V2.3 engine."""
from argparse import ArgumentParser
from concurrent.futures import ThreadPoolExecutor
from contextlib import ExitStack
import gzip
import json
import os
from pathlib import Path
import subprocess
import sys

IDS = {2,45,77,126,1685,1706,1723,1860,1902,2095,2170,1228,219,3634}


def verify_archive(game, payload, artifact):
    from common import HeadlessCampaign, sha256
    from remake.campaign import digest, verified_save_content
    original = verified_save_content(payload)['state']
    known = sorted({row['id'] for row in original['extension']['logistics']['convoys']} & IDS)
    trial = HeadlessCampaign(game.catalog, record_journal=False)
    proof = dict(file=artifact.name, sha256=sha256(artifact.read_bytes()), present=known)
    try:
        trial.load_save(payload, 0)
    except Exception as error:
        proof.update(outcome='rejected', error=type(error).__name__, message=str(error),
                     reason=str(error.__cause__) if error.__cause__ else None)
        return proof
    assert trial.to_dict()['rng']==original['rng']
    clocks = []
    for _ in range(4):
        normalized = trial.export_save(compact=True)
        roundtrip(trial, normalized)
        clocks.append(dict(turn=trial.state.turn, sha256=normalized['checksum'],
                           domain_sha256=digest(trial.to_dict()), rng=trial.to_dict()['rng']))
        state = trial.state
        if state.player != 'observer' or state.phase == 'finished':
            break
        trial.command('observe_turn',{},trial.revision)
    proof.update(outcome='replayed', trace=clocks)
    return proof


def roundtrip(game, payload):
    from common import HeadlessCampaign
    clone = HeadlessCampaign(game.catalog,record_journal=False)
    clone.load_save(payload,0)
    assert clone.to_dict()==game.to_dict()
    assert clone.export_save(compact=payload['version']==3)==payload


def replay_one(scenario, version, seed, turns):
    from common import ROOT, Catalog, HeadlessCampaign
    from remake import winter_weather as weather
    from remake.campaign import digest
    from v3021_checkpoints import configure
    game=HeadlessCampaign(Catalog(ROOT/f'game/data/campaigns/{scenario}.json'),record_journal=False)
    physical=[]
    trace=[]
    safe_dates=[]
    with ExitStack() as stack:
        configure(stack,211,221 if version else 0)
        stack.enter_context(weather.experiment(5 if version else 0,
            adjustments=weather.CORRECTIONS if version else 0,
            observe=lambda kind,row: physical.append((kind,row)) if kind in ('region','ice') else None))
        game.command('new',dict(faction='observer',seed=seed,weather_rules_version=version),0)
        for _ in range(turns+1):
            state=game.state
            saved=game.export_save(compact=True)
            domain = game.to_dict()
            trace.append(dict(turn=state.turn, sha256=saved['checksum'],
                              domain_sha256=digest(domain), rng=domain['rng']))
            if (state.day==1 and state.month in (1,4,6,9,10)) or state.turn==1:
                roundtrip(game,saved)
                roundtrip(game,game.export_save())
                safe_dates.append([state.year,state.month,state.day])
            if len(trace)>turns or state.phase=='finished':
                break
            game.command('observe_turn',{},game.revision)
    return dict(scenario=scenario, version=version, seed=seed, states=trace,
                weather_daily_frames=len(physical), weather_sha256=digest(physical), roundtrip_dates=safe_dates)


def probe(output, regime, artifacts):
    from common import ROOT, Catalog, HeadlessCampaign, git, to_json
    from remake.campaign import verified_save_content
    from v3021_checkpoints import configure
    if regime=='archives':
        cases=[]
    elif regime=='candidate':
        cases=[('208-10',23,2026,36)]
    else:
        cases=[(scenario,version,2026,9) for scenario in ('184-02','208-10') for version in (0,22,221)]
    states=[replay_one(*case) for case in cases]
    history=[]
    for artifact in artifacts:
        with gzip.open(artifact,'rt',encoding='utf-8') as stream:
            data=json.load(stream)
        payload=data.get('save',data)
        scenario=payload['scenario'].removeprefix('mainland')
        game=HeadlessCampaign(Catalog(ROOT/f'game/data/campaigns/{scenario}.json'),record_journal=False)
        raw=verified_save_content(payload)['state']['extension']
        strategy=data.get('strategy',raw.get('ai_logistics_strategy_version',211))
        weather=data.get('weather',raw.get('weather_rules_version',0))
        with ExitStack() as stack:
            configure(stack,strategy,weather)
            result=verify_archive(game,payload,artifact)
        history.append(result)
    to_json(output,dict(source=git('rev-parse','HEAD').decode().strip(), states=states, history=history))


def compare_proofs(output):
    from common import to_json
    def read(name):
        return json.loads((output/f'{name}.json').read_text(encoding='utf-8'))

    main, legacy, native, python = (read(name) for name in (
        'legacy-main-rust', 'legacy-v23-rust', 'candidate-rust', 'candidate-python'))
    assert main['states']==legacy['states'], 'Version 0, 22 or 221 diverged from the original runtime'
    assert main['history']==legacy['history'], 'An archive replay diverged from the original runtime'
    def domain(proof):
        # Compact saves compress JSON in insertion order. Compare authoritative
        # content independently of the order used to assemble the dictionaries.
        return [dict(row, states=[{k:v for k,v in frame.items() if k!='sha256'}
                                  for frame in row['states']]) for row in proof['states']]

    assert domain(native)==domain(python), 'V2.3 Python and Rust domain states diverged'
    history=legacy['history']
    if (output/'archived-latest.json').is_file():
        original, updated = read('archived-baseline'), read('archived-latest')
        assert original['source']==main['source'] and updated['source']==legacy['source']
        assert original['history']==updated['history'], 'Supplemental archive replay diverged'
        history=[*history,*updated['history']]
    replayed = {i for item in history if item['outcome']=='replayed' for i in item['present']}
    to_json(output/'compatibility.json',dict(
        baseline=main['source'],source=legacy['source'],python_hash_seed=0,
        legacy_checkpoints=sum(len(row['states']) for row in legacy['states']),
        legacy_frames=sum(row['weather_daily_frames'] for row in legacy['states']),
        candidate_checkpoints=sum(len(row['states']) for row in native['states']),
        candidate_compact_identical=sum(p['sha256']==r['sha256']
            for p,r in zip(python['states'][0]['states'],native['states'][0]['states'])),
        candidate_roundtrip_dates=native['states'][0]['roundtrip_dates'],
        historic_replayed=sorted(replayed), historic_unverified=sorted(IDS-replayed),
        historical_artifacts=history))
    print((output/'compatibility.json').read_text(encoding='utf-8'))


def cross_save(output, transfer, mode):
    """Exchange a real V2.3 campaign checkpoint between backend processes."""
    from common import Catalog, HeadlessCampaign, ROOT, to_json
    from remake import winter_weather as weather
    from remake.campaign import digest
    from v3021_checkpoints import configure
    game = HeadlessCampaign(Catalog(ROOT/'game/data/campaigns/208-10.json'), record_journal=False)
    with ExitStack() as stack:
        configure(stack, 211, 221)
        stack.enter_context(weather.experiment(5, adjustments=weather.CORRECTIONS))
        if mode == 'write':
            game.command('new', dict(faction='observer', seed=2026, weather_rules_version=23), 0)
            for _ in range(21):
                game.command('observe_turn', {}, game.revision)
            transfer.mkdir(parents=True, exist_ok=True)
            for name in ('plain','compact'):
                to_json(transfer/f'{name}.json', game.export_save(compact=name=='compact'))
        else:
            for name in ('plain','compact'):
                data = json.loads((transfer/f'{name}.json').read_text(encoding='utf-8'))
                game.load_save(data, game.revision)
                assert game.export_save(compact=name=='compact')==data
        before=game.to_dict()
        game.command('observe_turn', {}, game.revision)
        after=game.to_dict()
    to_json(output, dict(before=digest(before), after=digest(after), rng=after['rng']))


def check_cross_save(output):
    names=('python-write','python-read','rust-write','rust-read')
    found={name:json.loads((output/f'{name}.json').read_text(encoding='utf-8')) for name in names}
    assert all(result==found['python-write'] for result in found.values())
    print(json.dumps(found,ensure_ascii=False))


def compare(output, baseline, artifacts):
    from common import ROOT, TOOL_ROOT
    root=output.resolve()
    root.mkdir(parents=True,exist_ok=True)
    pairs=(
        ('legacy-main-rust',baseline,'rust','legacy',artifacts),
        ('legacy-v23-rust',ROOT,'rust','legacy',artifacts),
        ('candidate-rust',ROOT,'rust','candidate',[]),
        ('candidate-python',ROOT,'python','candidate',[]),
    )

    def run(spec):
        name, engine, backend, regime, paths=spec
        evidence=root/f'{name}.json'
        command=[sys.executable,'-Bu',str(Path(__file__).resolve()),'probe',str(evidence),regime,*map(str,paths)]
        with (root/f'{name}.log').open('w',encoding='utf-8') as logs:
            logs.write(json.dumps(dict(command=command,root=str(engine),backend=backend,python_hash_seed=0))+'\n')
            logs.flush()
            result=subprocess.run(command,cwd=TOOL_ROOT,stdout=logs,stderr=subprocess.STDOUT,
                                  env=dict(os.environ,TK2_OBSERVER_RUNTIME_ROOT=str(engine),
                                           MARCH_CORE_BACKEND=backend,PYTHONHASHSEED='0'))
        result.check_returncode()
        return json.loads(evidence.read_text())

    with ThreadPoolExecutor(max_workers=3) as pool:
        list(pool.map(run,pairs))
    compare_proofs(root)


if __name__=='__main__':
    parser=ArgumentParser(description=__doc__)
    branches=parser.add_subparsers(dest='mode',required=True)
    one=branches.add_parser('probe')
    two=branches.add_parser('compare')
    reuse=branches.add_parser('check-proofs')
    reuse.add_argument('output',type=Path)
    check=branches.add_parser('check-cross-save')
    check.add_argument('output',type=Path)
    transfer=branches.add_parser('cross-save')
    transfer.add_argument('output',type=Path)
    transfer.add_argument('transfer',type=Path)
    transfer.add_argument('direction',choices=('write','read'))
    for branch in (one,two):
        branch.add_argument('output',type=Path)
        if branch is one:
            branch.add_argument('regime',choices=('legacy','candidate','archives'))
        else:
            branch.add_argument('baseline',type=Path)
        branch.add_argument('artifact',type=Path,nargs='*')
    args=parser.parse_args()
    if args.mode=='probe':
        probe(args.output,args.regime,args.artifact)
    elif args.mode=='compare':
        compare(args.output,args.baseline,args.artifact)
    elif args.mode=='check-proofs':
        compare_proofs(args.output)
    elif args.mode=='check-cross-save':
        check_cross_save(args.output)
    else:
        cross_save(args.output,args.transfer,args.direction)

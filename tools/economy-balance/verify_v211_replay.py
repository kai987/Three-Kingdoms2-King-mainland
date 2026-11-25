"""Compare independent backends and resume a supplied JSON save without copying it."""
from argparse import ArgumentParser
from pathlib import Path
from time import monotonic, process_time
from json import loads

from common import Catalog, HeadlessCampaign, ROOT, git, sha256, to_json
from remake.campaign import digest
from remake.march_core import using_backend


def advance(game, turns):
    start=game.state.turn
    fingerprints=[digest(game.export_save()['state'])]
    for _ in range(turns):
        if game.state.phase=='finished':
            break
        game.command('observe_turn',{},game.revision)
        fingerprints.append(digest(game.export_save()['state']))
    assert game.state.turn==start+len(fingerprints)-1
    return fingerprints


def parity(scenario, seed, turns):
    catalog=Catalog(ROOT/'game/data/campaigns'/(scenario+'.json'))
    observed,times={},{}
    for backend in ('python','rust'):
        with using_backend(backend):
            game=HeadlessCampaign(catalog,record_journal=False)
            game.command('new',dict(faction='observer', seed=seed, difficulty='normal'),0)
            started,cpu=monotonic(),process_time()
            observed[backend]=advance(game,turns)
            times[backend]=dict(wall=monotonic()-started,cpu=process_time()-cpu)
            restored_next=[]
            for compact in (False,True):
                save=game.export_save(compact=compact)
                restored=HeadlessCampaign(catalog,record_journal=False)
                restored.load_save(save,0)
                assert restored.export_save(compact=compact)==save
                restored_next.append(advance(restored,1))
            continued=advance(game,1)
            assert all(replay==continued for replay in restored_next), scenario
    assert observed['python']==observed['rust'], scenario
    return dict(scenario=scenario,seed=seed,turns=turns,matched=len(observed['rust']),
                canonical_state_sha256s=observed['rust'],times=times,
                head=git('rev-parse','HEAD').decode().strip())


def legacy(path, turns, catalog_path=None):
    raw=path.read_bytes()
    data=loads(raw)
    scenario=data['scenario'].removeprefix('mainland')
    catalog=Catalog(catalog_path or ROOT/'game/data/campaigns'/(scenario+'.json'))
    game=HeadlessCampaign(catalog,record_journal=False)
    game.load_save(data,0)
    first=game.export_save()['state']
    hashes=advance(game,turns)
    final=game.export_save()['state']
    for field in ('grain_units_version','economy_rules_version','logistics_rules_version',
                  'ai_logistics_strategy_version'):
        assert first['extension'].get(field)==final['extension'].get(field)
    for compact in (False,True):
        saved=game.export_save(compact=compact)
        restored=HeadlessCampaign(catalog,record_journal=False)
        restored.load_save(saved,0)
        assert restored.export_save(compact=compact)==saved
    return dict(input_filename=path.name,input_sha256=sha256(raw),input_version=data['version'],
                scenario=scenario,initial_turn=first['turn'],final_turn=final['turn'],matches=hashes,
                strategy=first['extension'].get('ai_logistics_strategy_version','legacy'), catalog_sha256=catalog.sha256,
                source=git('rev-parse','HEAD').decode().strip())


def main():
    parser=ArgumentParser(description=__doc__)
    parser.add_argument('--scenarios',nargs='+',default=('190-01','208-10'))
    parser.add_argument('--seed', type=int,default=2026)
    parser.add_argument('--turns',type=int,default=36)
    parser.add_argument('--legacy',type=Path,nargs='+')
    parser.add_argument('--catalog',type=Path)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    if args.legacy:
        result=[]
        for path in args.legacy:
            try:
                result.append(legacy(path,args.turns,args.catalog))
            except (ValueError,RuntimeError) as error:
                result.append(dict(input_filename=path.name,input_sha256=sha256(path.read_bytes()),
                                   outcome='error',reason=str(error)))
    else:
        result=[parity(scenario,args.seed,args.turns) for scenario in args.scenarios]
    to_json(args.output,result)
    for row in result:
        print({key:value for key,value in row.items() if key not in ('canonical_state_sha256s','matches')})
    return int(all(row.get('outcome')=='error' for row in result))


if __name__=='__main__':
    raise SystemExit(main())

"""Export independent endpoint and Army 111 evidence from completed actual runs."""
from collections import Counter
import csv,gzip,json
from pathlib import Path
import sys

sys.path.insert(0,str(Path.cwd()/'tools/economy-balance'))
from common import to_json
from v3021_checkpoints import campaign
from v3041_report import emit, read_run
from remake.campaign import digest
from remake import transport_infrastructure as wharf

observed=Path(sys.argv[1])
out=Path(sys.argv[2])
rows=json.loads((observed/'quick-completed.json').read_bytes())
ends={}
manifest=[]
soldiers=[]
for row in rows:
    actual=observed/row['path']
    case,score,_=read_run(actual)
    spec=row['case']
    assert score['completed_turns']==72 and case['outcome']=='complete'
    finalfile=actual.parent/'terminal-save.json.gz'
    engine=campaign(spec['scenario'])
    engine.load_save(json.loads(gzip.decompress(finalfile.read_bytes())),0)
    state=engine.to_dict()
    final_wharf=state['extension'].pop(wharf.POOL,None)
    state['extension'].pop(wharf.FIELD,None)
    identity=(spec['scenario'],spec['seed'],spec['strategy'])
    ends.setdefault(identity,{})[row['variant']]=dict(digest=digest(state),rng=state['rng'],
                    products=case['table_sha256'], wharf_active=len(final_wharf['jobs']) if final_wharf else 0)
    manifest.append(dict(case,variant=row['variant'],source_patch_sha256=spec['runtime_patch_sha256'],
                 observed_options=spec,proof=row['path'], normalized_opening=row['opening'],
                 final_normalized=ends[identity][row['variant']], facility_events=row['wharf_events'],
                 city_and_army_events=row['actual_events']))
    if spec['scenario']!='263-05':
        continue
    observed_meals=[]
    real_handoffs=[]
    with gzip.open(observed/row['actual_events'],'rt',encoding='utf-8') as file:
        for record in map(json.loads,file):
            if record['event']=='unit_meal_settled' and record.get('unit_id')==111:
                observed_meals.append(record)
            elif record['event']=='relief_handoff' and record.get('army')==111:
                real_handoffs.append(record)
    episodes=[]
    with (actual.parent/'supply-episodes-weather-aware.csv').open(newline='',encoding='utf-8') as data:
        for item in csv.DictReader(data):
            if item['army_id']=='111':
                episodes.append(item)
    totals=Counter()
    for meal in observed_meals:
        totals.update(required=meal['required_grain'],paid=meal['paid_grain'],missing=meal['missing_grain'],
                     hunger_days=int(meal['hunger_day']),hunger_losses=meal['losses'],
                     city_refill=(meal['refill'] or {}).get('actual_received_grain',0))
    assert totals['required']-totals['paid']==totals['missing']
    first=observed_meals[0] if observed_meals else None
    soldiers.append(dict(scenario=spec['scenario'],seed=spec['seed'],strategy=spec['strategy'],
          variant=row['variant'],observed_army=bool(first),army=111,
          owner=first and first['owner'],source=first and first['source'],target=first and first['target'],
          route=first and first['route'],first_tick=first and first['tick'],
          first_logged_shortage_deadline=min((int(x['original_shortage_deadline']) for x in episodes
                           if x['original_shortage_deadline'] not in ('','null')),default=None),
          real_rendezvous_handoffs=len(real_handoffs),actual_handoffs=real_handoffs,
          episode_count=len(episodes),episode_records=episodes,**(totals if first else {})))
paired=[]
for (scenario,seed,strategy),groups in ends.items():
   for a,b in (('N0','N1'),('N2','N3'),('N0','N3')):
       if {a,b} <= groups.keys():
           first,second=groups[a],groups[b]
           paired.append(dict(scenario=scenario,seed=seed,strategy=strategy,baseline=a,candidate=b,
                    equal_domain=first['digest']==second['digest'],equal_rng=first['rng']==second['rng'],
                    tables_equal=first['products']==second['products'],
                    before_digest=first['digest'],after_digest=second['digest']))
to_json(out/'checks/simulation-manifest.json',manifest)
emit(out/'data/natural-endpoint-equivalence.csv',paired)
emit(out/'data/army-111-natural-observation.csv',soldiers)

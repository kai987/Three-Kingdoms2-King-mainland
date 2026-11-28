from collections import Counter
import csv,gzip,json,shutil,sys
from pathlib import Path

build=Path(sys.argv[1])
target=Path(sys.argv[2])
summary=target/'summary'
raw=target/'raw'
for folder in (summary/'checks',summary/'data',summary/'docs',summary/'sources',raw):
 folder.mkdir(parents=True,exist_ok=True)

def read(path):
 return json.loads(path.read_bytes())

def put(name,path):
 entry=target/name
 entry.parent.mkdir(parents=True,exist_ok=True)
 shutil.copyfile(path,entry)

def table(name,rows):
 rows=list(rows)
 if not rows:
  raise ValueError(f'No evidence for {name}')
 with (summary/'data'/name).open('w',encoding='utf-8',newline='') as stream:
  fields=list(dict.fromkeys(k for row in rows for k in row))
  out=csv.DictWriter(stream,fieldnames=fields,lineterminator='\n')
  out.writeheader()
  for row in rows:
   out.writerow({k:json.dumps(v,ensure_ascii=False,separators=(',',':')) if isinstance(v,(dict,list,bool))
                 else v for k,v in row.items()})

def archive_phase(phase):
 root=build/phase
 if not (root/'results.json').exists():
  return
 for source in root.rglob('*'):
  if not source.is_file() or source.name=='results.json':
   continue
  put(f'raw/{phase}/{source.relative_to(root)}',source)
 with gzip.open(raw/phase/'results.json.gz','wb',compresslevel=6) as out:
  out.write((root/'results.json').read_bytes())

for phase in ('fixed-final','fixed-stable','south','historical','profile','performance'):
 archive_phase(phase)
for source in (build/'topology').glob('*'):
 if source.is_file():
  put('raw/topology/'+source.name,source)
for source in (build/'mechanism-postings').glob('*'):
 if source.is_file():
  put('raw/mechanism/'+source.name,source)
for source in (build/'probes').glob('*.jsonl.gz'):
 put('raw/probes/'+source.name,source)

for name,path in (
 ('data/controlled-lines.csv',build/'mechanism-postings/controlled-lines.csv'),
 ('data/map-directions.csv',build/'mechanism/map-directions.csv'),
 ('data/fixed-pairs.csv',build/'fixed-final/fixed-pairs.csv'),
 ('checks/opening-equivalence.json',build/'mechanism/opening-equivalence.json'),
 ('checks/fixed-stage-status.json',build/'fixed-final/fixed-stage-status.json'),
 ('checks/quick-admission.json',build/'fixed-final/quick-admission.json'),
 ('checks/checkpoint-probes.json',build/'probes/checkpoint-probes.json'),
 ('checks/independent-recompute-postings.json',build/'technical/independent-recompute-postings.json'),
):
 put('summary/'+name,path)

for path in sorted((build/'technical').glob('*.log')):
 # Logs of child processes still writing are staged only in the final pass.
 if path.name in ('quick.log','performance.log','python.log','rust-rules.log','full-browser.log','resupply-browser.log'):
  continue
 if path.stat().st_size:
  put('raw/technical/'+path.name,path)
for path in (build/'technical/screens').glob('*.png'):
 put('raw/technical/screens/'+path.name,path)

rows=read(build/'fixed-final/results.json')
meal_rows=[]
for r in rows:
 for item in r['consumption']:
  measured=next((m for m in item['rations_through_deadline'] if m['settlement_turn']==item['deadline']),{})
  meal_rows.append(dict(variant=r['variant'],fixture=r['fixture'],checkpoint_sha256=r['sha256'],
   owner=item['owner'],city=item['city'],first_deadline=item['deadline'],
   observed=item['due_meal_observed'],required=item['required'],paid=item['paid'],missing=item['actual_missing'],
   population=measured.get('population'),active=measured.get('active'),reserves=measured.get('reserves'),
   physical_receipts=item['physical_receipts'],local_purchase=item['local_grain_bought'],
   local_purchase_attribution_lower_bound=item['local_grain_consumed_minimum']))
table('fixed-actual-consumption.csv',meal_rows)

south=[]
for row in read(build/'south/results.json'):
 checks=row['city_ration_settlements']
 stats=Counter()
 with gzip.open(build/'south'/row['variant']/row['actual_ledger'],'rt',encoding='utf-8') as stream:
  for record in map(json.loads,stream):
   if record['event']=='unit_meal_settled' and record.get('unit_kind')=='march' and record.get('unit_id')==282 and row['city']=='baxi':
    stats.update(meals_282=1,hunger_days_282=int(record['hunger_day']), losses_282=record['losses'],
                 require_282=record['required_grain'],paid_282=record['paid_grain'])
 south.append(dict(variant=row['variant'], city=row['city'], input_sha256=row['checkpoint_sha256'],
                   missing=row['missing'], shortage_turns=row['shortages'], settlements=len(checks),
                   required=sum(x['required'] for x in checks), paid=sum(x['paid'] for x in checks),
                   markets=row['market_transport_receipts'],
                   main_actual_stream='raw/south/'+row['variant']+'/'+row['actual_ledger'],
                   physical_receipts=len(row['local_physical_receipts']),
                   stock_first=row['stock'][0] if isinstance(row['stock'],list) else None, **stats))
table('southern-checkpoints.csv',south)

historical=[]
for row in read(build/'historical/results.json'):
 last=row['snapshots'][-1]['convoy']
 terminal=next((r['row'] for r in row['receipts'] if r['event']=='terminal'),None)
 historical.append(dict(variant=row['variant'], convoy=row['convoy'], input_sha256=row['checkpoint_sha256'],
  active=last is not None, status=last['status'] if last else terminal and terminal['outcome'],
  reason=last['reason'] if last else None,hunger_losses=last['hunger'] if last else terminal and terminal['hunger_losses'],
  troops=last['troops'] if last else terminal and terminal['troops_received'],
  lawful_receiver=last['receives_here'] if last else None, capacity=row.get('capacity_background'),
  original_capacity_blocker=row.get('concurrency_only_control'),
  before_owner=(row['snapshots'][0]['convoy'] or {}).get('source_owner'),
  end_tick=row['snapshots'][-1]['turn'], inbound_warehouse=terminal and terminal['city']))
table('historical-convoy-comparison.csv',historical)

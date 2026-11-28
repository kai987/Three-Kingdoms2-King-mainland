"""Reproduce actual competition for the single Badong wharf berth."""
import gzip
import json
from pathlib import Path
import sys

sys.path.insert(0,str(Path.cwd()/'tools/economy-balance'))
from common import sha256, to_json

sys.path.insert(0,str(Path.cwd()/'tests'))
from test_remake_transport_infrastructure import advance, order, restore, world, D2
from remake import grain_units, transport_infrastructure as wharf
from remake.campaign import digest

output=Path(sys.argv[1])
game=world(transport_capacity_rules_version=303,transport_capacity_options=D2)
opening=game.to_dict()
rows=[]
raw=output/'R04-wharf.jsonl.gz'
with gzip.open(raw,'wt',encoding='utf-8',compresslevel=4) as stream:
 def record(kind,row):
  event=dict(event=kind,**row)
  if kind in ('departure','terminal') or kind=='wait' and row['blocked']=='queue':
   rows.append(event)
  stream.write(json.dumps(event,ensure_ascii=False,separators=(',',':'))+'\n')
 with wharf.observing(record):
  first,_=order(game,[4000],origin='fuling')
  game.command(wharf.COMMAND,first,game.revision)
  advance(game)
  with grain_units.using(game.state):
   rejected=wharf.quote(game,game.state,'shu','fuling:badong:river','badong',[12001],90)
  assert rejected=={'blocked':'storage'}
  second,_=order(game,[12000],origin='badong')
  game.command(wharf.COMMAND,second,game.revision)
  assert first['escort']!=second['escort']
  game=restore(game,True)
  advance(game,6)
assert [(r['tick'],r['chain'],r['at']) for r in rows if r['event']=='wait']==[(14,2,'wharf-badong')]
assert len([r for r in rows if r['event']=='terminal'])==2
to_json(output/'berth-contention.json',dict(proof='R04',scenario='227-02',seed=2026,
 opening_sha256=digest(opening),opening_rng=opening['rng'],rejected_second_batch=rejected,
 actual=rows,raw=raw.name,raw_sha256=sha256(raw.read_bytes())))

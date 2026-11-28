import json
from pathlib import Path

build=Path(__file__).parent
final=build/'corrected'
summary=json.loads((final/'fixed/fixed-stage-status.json').read_bytes())
assert summary['status']=='pass'
assert not any(summary['hard_errors'].values())
south=json.loads((final/'south/results.json').read_bytes())
history=json.loads((final/'historical/results.json').read_bytes())
probes=json.loads((final/'probes/checkpoint-probes.json').read_bytes())['results']
assert len(south)==32 and len(history)==32 and len(probes)==4
assert (build/'technical/infrastructure-gap-python.log').read_text().rstrip().endswith('OK')
assert (build/'technical/infrastructure-gap-rust.log').read_text().rstrip().endswith('OK')
assert '2 passed' in (build/'technical/wharf-browser-exact.log').read_text()
assert '"ok":true' in (build/'technical/worker-gap-corrected.log').read_text()
safety=[]
for first,second in [('N0','N1'),('N2','N3')]:
 s0={row['city']:row for row in south if row['variant']==first}
 s1={row['city']:row for row in south if row['variant']==second}
 h0={row['convoy']:row for row in history if row['variant']==first}
 h1={row['convoy']:row for row in history if row['variant']==second}
 assert len(s0)==len(h0)==8 and s0.keys()==s1.keys() and h0.keys()==h1.keys()
 for city,row in s0.items():
  other=s1[city]
  assert row['checkpoint_sha256']==other['checkpoint_sha256']
  assert row['missing']==other['missing'] and row['normalized_turns']==other['normalized_turns'], (second,city)
 for ident,row in h0.items():
  other=h1[ident]
  assert row['checkpoint_sha256']==other['checkpoint_sha256']
  assert row['snapshots']==other['snapshots'] and row['receipts']==other['receipts'],(second,ident)
 safety.append(dict(baseline=first,candidate=second,southern_windows=len(s0),historical_windows=len(h0)))
summary['admission_evidence']=dict(safety=safety,extra_short_windows=len(probes),
                          controlled_deadline_and_real_delivery=True,technology_browser_wharf=2)
(final/'fixed/quick-admission.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')

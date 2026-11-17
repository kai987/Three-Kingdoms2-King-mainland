from collections import Counter, defaultdict
from pathlib import Path
import csv
import json
import sys

root = Path(sys.argv[1])
opening = {r['device']:r for r in json.loads((root/'summary.json').read_bytes())}
parts = ('static_construct_ms','static_json_ms','static_utf8_ms','static_sha_ms','route_key_ms',
         'route_json_ms','route_utf8_ms','route_sha_ms','dynamic_assembly_ms')

def collect(device):
    profile = json.loads((root/device/'opening-start-profile.json').read_bytes())
    rows = [dict(device=device,scenario=r['scenario'],**r['pack_detail']) for r in profile['python']]
    assert len(rows) == opening[device]['opening_count'] == 18
    misses = [r for r in rows if not r['cache_hit']]
    hits = [r for r in rows if r['cache_hit']]
    assert all(r['cache_hit']==(r['source_sha'] in r['cache_before']) and len(r['cache_after'])<=2 for r in rows)
    assert all(r['sends_static'] != r['browser_static_hit'] and
               r['sends_quotes'] != r['browser_quote_hit'] for r in rows)
    assert all(abs(r['total_ms']-sum(r[k] for k in parts))<0.01 for r in rows)
    assert all(r['static_bytes']==0 for r in hits) and all(r['static_bytes']>0 for r in misses)
    totals = {k.removesuffix('_ms')+'_s':sum(r[k] for r in rows)/1000 for k in parts}
    totals['pack_s'] = sum(r['total_ms'] for r in rows)/1000
    assert totals['pack_s'] <= opening[device]['worker_pack_s']+0.01
    totals.update(device=device, openings=len(rows), pack_calls=len(rows),
                  other_pack_calls=len(profile['otherPackCalls']), static_worker_hits=len(hits),
                  static_worker_misses=len(misses),
                  browser_static_hits=sum(r['browser_static_hit'] for r in rows),
                  browser_quote_hits=sum(r['browser_quote_hit'] for r in rows),
                  static_digest_repeats=len(misses)-len(set(r['token'] for r in misses)),
                  route_digest_repeats=len(rows)-len(set(r['quote_token'] for r in rows)),
                  static_raw_bytes=sum(r['static_bytes'] for r in rows),
                  route_key_raw_bytes=sum(r['route_bytes'] for r in rows))
    components = defaultdict(list)
    for row in profile['components']:
        assert row['scenario'] in {r['scenario'] for r in misses}
        components[row['key']].append(row)
    grouped = []
    for key, group in sorted(components.items()):
        counts = Counter(r['sha256'] for r in group)
        unique_sizes = {r['sha256']:r['bytes'] for r in group}
        grouped.append(dict(device=device,key=key,calls=len(group),unique=len(counts),
                            greatest_repeat=max(counts.values()),
                            total_bytes=sum(r['bytes'] for r in group),
                            repeated_bytes=sum((count-1)*unique_sizes[digest] for digest,count in counts.items())))
    return totals, rows, grouped

def write(name, records):
    with (root/name).open('w',newline='') as stream:
        writer=csv.DictWriter(stream,fieldnames=records[0].keys())
        writer.writeheader()
        writer.writerows(records)

summary, rows, fields = [], [], []
for device in ('desktop-chromium','touch-chromium'):
    totals, detail, components = collect(device)
    summary.append(totals)
    rows.extend(detail)
    fields.extend(components)
write('pack-summary.csv',summary)
write('pack-by-scenario.csv',rows)
write('pack-component-repeats.csv',fields)
(root/'pack-summary.json').write_text(json.dumps(summary,indent=2)+'\n')
print('| Device | Pack time (s) | Static construction (s) | Static JSON (s) | Static SHA-256 (s) | Dynamic assembly (s) | Worker static cache hits/misses |')
print('| --- | ---: | ---: | ---: | ---: | ---: | ---: |')
for row in summary:
    print(f"| {row['device']} | {row['pack_s']:.3f} | {row['static_construct_s']:.3f} | {row['static_json_s']:.3f} | "
          f"{row['static_sha_s']:.3f} | {row['dynamic_assembly_s']:.3f} | {row['static_worker_hits']}/{row['static_worker_misses']} |")

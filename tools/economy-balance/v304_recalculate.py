"""Verify the published portable manifests and independently recalculate the two headline experiments."""
from argparse import ArgumentParser
from collections import Counter, defaultdict
import csv
from hashlib import sha256
from io import StringIO
import json
from pathlib import Path, PurePosixPath
from zipfile import ZipFile


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def digest(stream):
    result = sha256()
    for block in iter(lambda:stream.read(1024*1024),b''):
        result.update(block)
    return result.hexdigest()


def file_digest(path):
    with path.open('rb') as stream:
        return digest(stream)


def safe(root,name):
    relative=PurePosixPath(name)
    if relative.is_absolute() or '..' in relative.parts or not relative.parts:
        raise ValueError(f'Nonportable member: {name}')
    return root.joinpath(*relative.parts)


def rows(path):
    with path.open(encoding='utf-8',newline='') as stream:
        return list(csv.DictReader(stream))


def verify_summary(summary):
    manifest=read(summary/'sources'/'validation-manifest.json')
    sums={}
    for line in (summary/'SHA256SUMS.txt').read_text().splitlines():
        checksum,name=line.split('  ',1)
        if name in sums or file_digest(safe(summary,name))!=checksum:
            raise ValueError(f'Summary checksum error: {name}')
        sums[name]=checksum
    actual={p.relative_to(summary).as_posix() for p in summary.rglob('*') if p.is_file()}
    if actual!=set(sums)|{'SHA256SUMS.txt'} or manifest['files']!={
            name:checksum for name,checksum in sums.items() if name!='sources/validation-manifest.json'}:
        raise ValueError('The summary inventory does not match its manifest')
    return manifest


def verify_archives(index):
    info=read(index)
    data=index.parent
    seen=set()
    for pack in info['archives']:
        archive=safe(data,pack['archive'])
        external=safe(data,pack['file_manifest'])
        if (archive.stat().st_size!=pack['bytes'] or pack['bytes']>100_000_000
                or file_digest(archive)!=pack['sha256']
                or file_digest(external)!=pack['manifest_sha256']):
            raise ValueError(f'Invalid external archive hash or size: {archive.name}')
        with ZipFile(archive) as zipped:
            details=zipped.read('FILE-MANIFEST.csv').decode('utf-8')
            if zipped.testzip() is not None or details!=external.read_text(encoding='utf-8'):
                raise ValueError(f'Invalid ZIP or manifest: {archive.name}')
            members=list(csv.DictReader(StringIO(details)))
            names={item['member'] for item in members}
            if (len(members)!=pack['files'] or len(members)!=len(names)
                    or sorted(zipped.namelist())!=sorted(names|{'FILE-MANIFEST.csv'})
                    or seen & names):
                raise ValueError(f'Wrong archive contents: {archive.name}')
            for entry in members:
                name=entry['member']
                safe(data,name)
                safe(data,entry['source_path'])
                with zipped.open(name) as stream:
                    if digest(stream)!=entry['sha256'] or zipped.getinfo(name).file_size!=int(entry['size']):
                        raise ValueError(f'Invalid member checksum: {name}')
            seen.update(names)
    return dict(archives=len(info['archives']),members=len(seen))


def concurrency(summary):
    totals=defaultdict(Counter)
    identities=defaultdict(set)
    for row in rows(summary/'data'/'transport-capability-funnel.csv'):
        group=row['group']
        key=tuple(row[field] for field in ('scenario','strategy','turn','checkpoint_sha256',
            'owner','target','seed','weather','deadline_turn','first_uncovered_grain'))
        if key in identities[group]:
            raise ValueError('Duplicate fixed demand')
        identities[group].add(key)
        subtotal=totals[group]
        if row['l5_actual_reception']=='null':
            subtotal['censored']+=1
            continue
        actual=sum(item['cargo']['grain'] for item in json.loads(row['l5_actual_receipts']))
        if actual!=int(row['l5_actual_reception']):
            raise ValueError(f'Fixed report receipt mismatch: {key}')
        subtotal.update(targets=1,actual=actual,positive=actual>0,full=actual>=int(row['first_uncovered_grain']),
                        strategic=int(row['l5_strategic_reception']))
    if set(identities)!={'D0','D1','D2','D3'} or any(v!=identities['D1'] or len(v)!=89 for v in identities.values()):
        raise ValueError('Fixed target identity differs across groups')
    offer_checks=defaultdict(set)
    for row in rows(summary/'data'/'capacity-counterfactual.csv'):
        key=tuple(row[field] for field in ('scenario','strategy','start_turn','checkpoint_sha256','owner','source',
                                         'original_convoy','replay_end_turn'))
        group=row['group']
        if key in offer_checks[group]:
            raise ValueError('Duplicate fixed source')
        offer_checks[group].add(key)
        totals[group].update(returning=1,qualified=row['donor_qualified']=='true',
            timely=bool(json.loads(row['timely_quotes'])),actual_source=bool(json.loads(row['actual_shipments'])))
    if set(offer_checks)!=set(identities) or any(v!=offer_checks['D1'] or len(v)!=23 for v in offer_checks.values()):
        raise ValueError('Fixed source identity differs across groups')
    if totals!=read(summary/'data'/'report-status.json')['fixed']:
        raise ValueError('Recalculated demand statistics disagree with the report')
    return dict(fixed=totals,finite_concurrency_actual_delta=totals['D2']['actual']-totals['D1']['actual'],
                finite_concurrency_full_delta=totals['D2']['full']-totals['D1']['full'])


def proof_lane(summary,filename):
    e0,e1=read(summary/'checks'/filename)
    if e0['opening_sha256']!=e1['opening_sha256'] or e0['candidate_303']!=e1['candidate_303']:
        raise ValueError('Both controls must share their exact opening')
    plan=e1['plan']
    by_id={}
    usage=Counter()
    result={}
    for branch in (e0,e1):
        orders=branch['observed_transit']
        final=sum(row['cargo']['grain'] for row in orders if row['event']=='delivery' and row['target']==plan['target'])
        commands=sum(row['command_books'] for row in orders if row['event']=='departure')
        if final!=branch['final_grain'] or commands!=branch['commands']:
            raise ValueError('Departure and receipt evidence differs from the report')
        result[branch['group']]=dict(actual_final=final,commands=commands)
    for batch in plan['batches']:
        if batch['stage']:
            if sum(amount for _,amount in batch['parents'])!=batch['grain']+batch['rations']:
                raise ValueError('Invalid split or consolidation total')
            for ident,amount in batch['parents']:
                parent=by_id[ident]
                if parent['receipt']['turn']>=batch['turn'] or parent['target']!=batch['source']:
                    raise ValueError('A batch consumed grain before actual receipt or at another city')
                usage[ident]+=amount
        if batch['grain']+batch['rations']>batch['capacity'] or batch['convoy'] in by_id:
            raise ValueError('Duplicated convoy or exceeded physical capacity')
        by_id[batch['convoy']]=batch
    for ident,batch in by_id.items():
        if batch['target']!=plan['target'] and (batch['receipt']['grain']!=usage[ident]+batch['available']
                                              +sum(batch['released'].values())):
            raise ValueError('A hub credited more than its genuine receipt')
    book=Counter()
    for batch in plan['batches']:
        terminal=batch['terminal']
        cargo=terminal['cargo']
        if not batch['stage']:
            book.update(origin_cargo=batch['grain'],origin_rations=batch['rations'])
        book.update(external_ration_draw=terminal['external_rations'],
            travel_and_wait_rations=terminal['spent_rations'],route_loss=cargo['cargo_route_loss'],
            weather_loss=cargo['cargo_weather_loss'],returned_grain=cargo['cargo_returned']+terminal['returned_rations'],
            abandoned_grain=cargo['cargo_abandoned'],unloaded_grain=cargo.get('cargo_waypoint_unloaded',0))
        if batch['target']==plan['target']:
            book['final_received']+=batch['receipt']['grain']
        else:
            book['tag_left_at_hub']+=batch['available']+sum(batch['released'].values())
    inflow=book['origin_cargo']+book['origin_rations']+book['external_ration_draw']
    outflow=sum(book[key] for key in ('travel_and_wait_rations','route_loss','weather_loss','returned_grain',
                                    'abandoned_grain','unloaded_grain','tag_left_at_hub','final_received'))
    if inflow!=outflow or result['E1']['actual_final']!=book['final_received']:
        raise ValueError('Transshipment chain failed grain conservation')
    result['ledger']=dict(source_and_waypoint_grain=inflow,accounted_grain=outflow,residual=inflow-outflow)
    book['residual']=inflow-outflow
    return result,book


def intermodal(summary):
    main,book=proof_lane(summary,'controlled-route-results.json')
    if book!=read(summary/'checks'/'end-to-end-grain-account.json'):
        raise ValueError('Recalculated grain account differs from the published chain')
    short,_=proof_lane(summary,'short-chain-comparison.json')
    return dict(three_stage=main,two_stage=short)


def main():
    parser=ArgumentParser(description=__doc__)
    parser.add_argument('summary',type=Path)
    parser.add_argument('--archives',type=Path,help='Package index. Omit to check the readable summary only.')
    args=parser.parse_args()
    manifest=verify_summary(args.summary)
    recalculate={'3031':concurrency,'304-prototype':intermodal}[manifest['version']]
    result=dict(version=manifest['version'],files=len(manifest['files']),measurements=recalculate(args.summary))
    if args.archives:
        result['archives']=verify_archives(args.archives)
    print(json.dumps(result,ensure_ascii=False,sort_keys=True))


if __name__=='__main__':
    main()

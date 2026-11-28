"""Independently reconcile V3042 custody streams and a SHA-256 file index."""

from argparse import ArgumentParser
from collections import Counter
import gzip
from hashlib import file_digest
import json
from pathlib import Path, PurePosixPath

LOT_ACCOUNTS = {'cargo', 'bank0', 'bank1'}


def sha(path):
    with path.open('rb') as f:
        return file_digest(f, 'sha256').hexdigest()


def verify_index(root, name):
    paths = set()
    for line in (root/name).read_text(encoding='utf-8').splitlines():
        expected, raw = line.split('  ',1)
        relative = PurePosixPath(raw)
        path = root/relative
        if relative.is_absolute() or '..' in relative.parts or raw in paths or not path.is_file():
            raise ValueError(f'Invalid or repeated index path: {raw}')
        actual = sha(path)
        if actual != expected:
            raise ValueError(f'SHA-256 differs: {raw}')
        paths.add(raw)
    return len(paths)


def events(path):
    with gzip.open(path,'rt',encoding='utf-8') as stream:
        yield from map(json.loads,stream)


class Relay:
    def __init__(self):
        self.balances = Counter()
        self.lots = {}
        self.serial = 0
        self.posting_tick = 0
        self.departure = None
        self.arrival = None
        self.terminal = None
        self.stages = set()
        self.throughput = 0

    def grain(self, row):
        serial = row['serial']
        tick = row['tick']
        source, target, quantity = row['source'], row['target'], row['grain']
        assert self.terminal is None and serial == self.serial+1 and tick >= self.posting_tick
        assert quantity > 0 and source != target
        assert [self.balances[source],self.balances[target]] == row['before']
        if source == 'input':
            self.balances[source] += quantity
        else:
            self.balances[source] -= quantity
        self.balances[target] += quantity
        assert min(self.balances[source],self.balances[target]) >= 0
        assert [self.balances[source],self.balances[target]] == row['after']
        if source in LOT_ACCOUNTS:
            assert sum(amount for _,amount in row['parents']) == quantity
            assert len({lot for lot,_ in row['parents']}) == len(row['parents'])
            for lot,amount in row['parents']:
                account,available = self.lots[lot]
                assert source == account and 0 < amount <= available
                if amount == available:
                    del self.lots[lot]
                else:
                    self.lots[lot] = (account,available-amount)
        else:
            assert not row['parents']
        if target in LOT_ACCOUNTS:
            self.lots[serial] = (target,quantity)
        lot_sums = Counter()
        for account,available in self.lots.values():
            lot_sums[account] += available
        assert all(lot_sums[key] == self.balances[key] for key in LOT_ACCOUNTS)
        if row['city_delta']:
            city, before, after = row['city_delta']
            assert city and before >= 0 and after >= 0
            assert after-before == (-quantity if source == 'input' else quantity)
        if row['kind'] == 'unload':
            self.throughput += quantity
        self.serial, self.posting_tick = serial, tick

    def record(self,row):
        event = row['event']
        if event == 'grain':
            self.grain(row['entry'])
        elif event == 'departure':
            assert self.departure is None and row['books'] == 1
            self.departure = row
            self.stages.add(0)
        elif event == 'book':
            assert row['stage'] == len(self.stages) and row['amount'] == 1
            self.stages.add(row['stage'])
        elif event == 'delivery':
            assert self.arrival is None
            assert row['grain'] == self.balances['delivery']
            assert row['timely'] == (row['tick'] < row['original_deadline'])
            self.arrival = row
        elif event == 'terminal':
            assert self.terminal is None and row['books'] == len(self.stages)
            assert all(self.balances[key] == value for key,value in row['balances'].items())
            assert not self.lots and not any(self.balances[key] for key in LOT_ACCOUNTS|{'rations'})
            self.terminal = row
        assert self.balances['input'] == sum(value for key,value in self.balances.items() if key != 'input')

    def summary(self):
        assert self.departure is not None
        discharge = self.arrival
        return dict(input=self.balances['input'], delivery=self.balances['delivery'],
                    timely_grain=discharge['grain'] if discharge and discharge['timely'] else 0,
                    delivery_tick=discharge['tick'] if discharge else None,
                    command_books=len(self.stages), escort_days=(
                        self.terminal['tick']-self.departure['tick'] if self.terminal else None),
                    wharf_throughput=self.throughput, open=self.terminal is None,
                    posting_count=self.serial, accounts=dict(self.balances))


def relay_stream(path):
    chains = {}
    for row in events(path):
        if 'chain' in row:
            chains.setdefault(row['chain'],Relay()).record(row)
    return {ident:chain.summary() for ident,chain in chains.items()}


def line_evidence(root):
    inputs = json.loads((root/'controlled-lines.json').read_bytes())
    results = []
    for case in inputs:
        raw = root/case['evidence']
        assert case['evidence_sha256'] == sha(raw)
        if case['status'] == 'blocked':
            log = list(events(raw))
            assert len(log) == 1 and log[0]['event'] == 'opening_refusal'
            assert log[0]['opening_rng'] == log[0]['final_rng']
            values = dict(status='blocked', reason=log[0]['forecast']['blocked'])
        elif case['group'] in ('N1','N3'):
            audited = relay_stream(raw)
            assert len(audited) == 1
            values = next(iter(audited.values()))
            assert values['delivery'] == case['delivery'] and not values['open']
            assert values['delivery_tick'] == case['last_delivery_day']
            assert values['timely_grain'] == case['timely_grain']
            assert values['escort_days'] == case['officer_days']
            assert values['wharf_throughput'] == case['harbour_throughput']
        else:
            log = {row['event']:row for row in events(raw)}
            terminal = log['terminal']
            cargo = terminal['cargo_receipt']
            assert cargo['cargo_dispatched']+cargo['cargo_received'] == sum(cargo[name] for name in (
                'cargo_rations','cargo_route_loss','cargo_weather_loss','cargo_delivered',
                'cargo_returned','cargo_abandoned','cargo_remaining'))
            ration = terminal['rations']
            assert ration['loaded']+ration['received'] == ration['consumed']+ration['to_cargo']+ration['remaining']
            grain = log['delivery']['cargo']['grain']
            assert grain == cargo['cargo_delivered'] == case['delivery']
            assert (log['delivery']['turn']-1)*10 == case['last_delivery_day']
            values = dict(delivery=grain, cargo=cargo, rations=ration)
        if case['status']=='complete' and 'target_transport_net' in case:
            refill=-sum(row['delta'] for row in events(raw) if row['event']=='city_posting'
                        and row['city']==case['to_city'] and row['resource']=='grain'
                        and row['site'] in ('logistics._begin_journey','transport_emergency._take_local')
                        and row['delta']<0)
            assert refill==case['target_return_provisions']
            assert values['delivery']-refill==case['target_transport_net']
            values['target_transport_net']=case['target_transport_net']
        results.append(dict(proof=case['proof'], group=case['group'], **values))
    return results


def main():
    parser=ArgumentParser(description=__doc__)
    parser.add_argument('root',type=Path)
    parser.add_argument('--index',type=Path)
    parser.add_argument('--lines',type=Path)
    parser.add_argument('--streams',type=Path)
    args=parser.parse_args()
    result={}
    if args.index:
        result['verified_files']=verify_index(args.root,args.index)
    if args.lines:
        result['controlled_lines']=line_evidence(args.root/args.lines)
    if args.streams:
        result['campaigns']={str(path.relative_to(args.root)):relay_stream(path)
            for path in sorted((args.root/args.streams).rglob('*-wharf.jsonl.gz'))}
    print(json.dumps(result,ensure_ascii=False,indent=2))


if __name__=='__main__':
    main()

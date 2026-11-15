"""Compare independent placement reads, view projections and saved checkpoints."""
from collections import Counter
import json
from pathlib import Path

root = Path('build/battle-poll-profile')


def read(name):
    return json.loads((root / f'{name}.json').read_text())


def placement_timings(data, docs):
    original, = [doc for doc in docs if doc['placementReads']]
    samples = original['placementReads']
    node_samples = data['placements']
    assert len(samples) == len(node_samples) == 2
    origin = original['timeOrigin']
    left, right = original['nodeSample']
    assert left - 5 <= original['sampledAt'] <= right + 5
    output = []
    for stage, sample, node in zip(('before', 'after'), samples, node_samples):
        state = sample['state']
        save, = [row for row in original['saves'] if row['id'] == sample['saveId']]
        assert sample['stage'] == node['stage'] == stage
        assert state['path'] == '/api/state' and state['status'] == save['status'] == 200
        assert state['characters'] > 0 and save['bytes'] > 0 and save['kind'] == 'other'
        assert sample['began'] <= state['started'] <= state['received'] <= sample['stateParseStart']
        assert save['started'] <= save['received'] <= sample['saveParseStart']
        assert sample['stateParseStart'] <= sample['stateParseEnd'] <= sample['saveParseStart']
        assert sample['saveParseStart'] <= sample['saveParseEnd'] <= sample['done']
        assert node['started'] - 5 <= origin + sample['began'] <= origin + sample['done'] <= node['received'] + 5
        output.append({
            'stage': stage, 'state_worker_ms': state['received'] - state['started'],
            'save_worker_ms': save['received'] - save['started'],
            'state_browser_parse_ms': sample['stateParseEnd'] - sample['stateParseStart'],
            'save_browser_parse_ms': sample['saveParseEnd'] - sample['saveParseStart'],
            'playwright_return_ms': max(0, node['received'] - (origin + sample['done'])),
            'evaluate_total_ms': node['received'] - node['started'],
            'state_reply_characters': state['characters'],
            **{key: node[key] for key in ('viewBytes', 'saveBytes', 'saveDigest', 'viewDigest', 'rng')},
        })
    return output


identity = read('web-identity')
results = {}
for variant in ('baseline', 'response'):
    for device in ('desktop-chromium', 'touch-chromium'):
        for case in ('battle-movement', 'battle-layout'):
            data = read(f'{variant}-{device}-{case}')
            assert (data['variant'], data['project'], data['id'], data['status']) == (variant, device, case, 'passed')
            assert (data['source'], data['web'], data['runner'], data['runId']) == (
                identity['commit'], identity['content_sha256'], identity['runner'], identity['run_id'])
            docs = data['documents']
            assert len(docs) == (2 if case == 'battle-movement' else 1)
            workers = [w for doc in docs for w in doc['workers']]
            assert len(workers) == len(docs)
            assert all(worker['build'] == identity['commit'] and worker['ready'] > worker['started']
                       for worker in workers)
            saves = [row for doc in docs for row in doc['saves']]
            assert saves and all(row['status'] == 200 and row['bytes'] > 0 for row in saves)
            counts = Counter(row['kind'] for row in saves)
            assert counts['round-poll'] == 0
            proof = []
            for doc in docs:
                orders = {action['round']: action for action in doc['commands']
                          if action['kind'] == 'siege_orders'}
                steps = [action for action in doc['commands'] if action['kind'] == 'siege_step']
                assert len(orders) == len(steps) and len(doc['commands']) == 2 * len(steps)
                for reply in steps:
                    index = reply['round']
                    order = orders[index]
                    check = data['rounds'][index - 1]
                    before, committed, settled = (check[key] for key in ('before', 'committed', 'settled'))
                    assert order['status'] == reply['status'] == 200 and order['sawGame'] and reply['sawGame']
                    assert order['revision'] == order['inputRevision'] + 1 == reply['inputRevision']
                    assert reply['revision'] == reply['inputRevision'] + 1
                    assert order['siege'] == before['siege'] and not order['duel']
                    assert reply['siege'] is None or reply['duel'] or reply['siege'] > before['siege']
                    assert all(reply[key] == committed[key] for key in ('battle', 'siege', 'duel', 'rng'))
                    assert committed == settled
                    proof.append({key: check[key] for key in ('before', 'committed', 'settled')})
            assert proof and len(proof) == len(data['rounds']) == len(data['phases']['commit-wait'])
            results[variant, device, case] = {
                'total_s': data['duration'] / 1000,
                'all_save_calls': len(saves),
                'save_requests_s': sum(row['received'] - row['started'] for row in saves) / 1000,
                'poll_calls': counts['round-poll'],
                'macro_poll_calls': counts['macro-poll'],
                'commit_wait_s': sum(data['phases']['commit-wait']) / 1000,
                'proof': proof,
                'placements': placement_timings(data, docs),
                'placement_total_ms': sum(data['phases']['manual-placement']),
            }

rows = []
for device in ('desktop-chromium', 'touch-chromium'):
    for case in ('battle-movement', 'battle-layout'):
        baseline = results['baseline', device, case]
        response = results['response', device, case]
        assert baseline['proof'] == response['proof']
        assert baseline['macro_poll_calls'] == response['macro_poll_calls']
        for left, right in zip(baseline['placements'], response['placements']):
            for key in ('stage', 'state_reply_characters', 'saveBytes', 'saveDigest', 'viewDigest', 'rng'):
                assert left[key] == right[key], (device, case, key, left[key], right[key])
            assert right['viewBytes'] < left['viewBytes']
        rows.append(dict(device=device, case=case, baseline=baseline, response=response))
        print(device, case, 'save calls', baseline['all_save_calls'], response['all_save_calls'],
              'total seconds', baseline['total_s'], response['total_s'])
(root / 'summary.json').write_text(json.dumps(dict(identity=identity, pairs=rows),
                                              ensure_ascii=False, indent=2) + '\n')

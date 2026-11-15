"""Validate the measured test identity and compare response and save checkpoints."""
from collections import Counter
import json
from pathlib import Path

folder = Path('build/battle-poll-profile')
identity = json.loads((folder / 'web-identity.json').read_text())
cases = ('battle-movement', 'battle-layout')
projects = ('desktop-chromium', 'touch-chromium')
seconds = lambda ms: ms / 1000
summary = []

for project in projects:
    for case in cases:
        raw = json.loads((folder / f'{project}-{case}.json').read_text())
        assert (raw['project'], raw['id'], raw['status']) == (project, case, 'passed')
        assert raw['source'] == identity['commit']
        assert raw['web'] == identity['content_sha256']
        assert raw['runId'] == identity['run_id'] and raw['runner'] == identity['runner']
        docs = raw['documents']
        assert len(docs) == (2 if case == 'battle-movement' else 1)
        workers = [worker for doc in docs for worker in doc['workers']]
        assert len(workers) == len(docs)
        assert all(worker['build'] == identity['commit'] and worker['ready'] > worker['started']
                   for worker in workers)
        saves = [entry for doc in docs for entry in doc['saves']]
        assert saves and all(entry['status'] == 200 and entry['bytes'] > 0 and entry['received'] >= entry['started']
                             for entry in saves)
        measures, comparisons = {}, []
        for kind in ('round-poll', 'macro-poll', 'other'):
            entries = [entry for entry in saves if entry['kind'] == kind]
            measures[kind] = {
                'calls': len(entries),
                'worker_round_trip_s': seconds(sum(entry['received'] - entry['started'] for entry in entries)),
                'response_bytes': sum(entry['bytes'] for entry in entries),
                'read_and_parse_s': 0,
            }
        for doc in docs:
            classified = {entry['id']: entry for entry in doc['saves'] if entry['kind'] != 'other'}
            assert len(doc['polls']) == len(classified)
            for poll in doc['polls']:
                entry = classified[poll['request']]
                assert (entry['kind'], entry['round']) == (poll['kind'], poll['round'])
                assert poll['started'] <= entry['started'] <= entry['received'] <= poll['ended']
                measures[poll['kind']]['read_and_parse_s'] += seconds(poll['ended'] - poll['started'])
            orders = {command['round']: command for command in doc['commands'] if command['kind'] == 'siege_orders'}
            actions = [command for command in doc['commands'] if command['kind'] == 'siege_step']
            assert len(orders) == len(actions) and len(doc['commands']) == 2 * len(actions)
            for action in actions:
                number = action['round']
                order = orders[number]
                checkpoint = raw['rounds'][number - 1]
                before, committed, settled = (checkpoint[key] for key in ('before', 'committed', 'settled'))
                assert committed == settled and isinstance(committed['rng'], dict)
                polls = [poll for poll in doc['polls'] if poll['round'] == number and poll['kind'] == 'round-poll']
                assert polls and [p['decision'] for p in polls] == [False] * (len(polls) - 1) + [True]
                assert action['status'] == order['status'] == 200
                assert order['received'] <= action['started']
                def advances(response):
                    return (response['sawGame']
                            and (response['siege'] is None or response['duel'] or response['siege'] > before['siege']))
                advanced = advances(action)
                revision = action['revision'] == action['inputRevision'] + 1
                matching = all(action[key] == committed[key] for key in ('battle', 'siege', 'duel', 'rng'))
                comparisons.append({
                    'round': number, 'polls': len(polls), 'transport': action['transport'],
                    'request_revision': action['inputRevision'], 'response_revision': action['revision'],
                    'order_request_revision': order['inputRevision'], 'order_response_revision': order['revision'],
                    'order_response_matches_poll': advances(order),
                    'order_revision_applied': order['revision'] == order['inputRevision'] + 1 == action['inputRevision'],
                    'response_matches_poll': advanced, 'revision_incremented': revision,
                    'response_matches_committed_save_fields': matching,
                    'response_before_successful_poll_ms': polls[-1]['ended'] - action['received'],
                    'response_before_successful_poll_start_ms': polls[-1]['started'] - action['received'],
                    'before': before, 'committed': committed, 'settled': settled,
                })
        assert comparisons and sorted(row['round'] for row in comparisons) == list(range(1, len(raw['rounds'])+1))
        for phase in ('opening', 'march-through-arrivals', 'manual-placement'):
            assert len(raw['phases'][phase]) == 1
        assert len(raw['phases']['round-poll-wait']) == len(comparisons)
        summary.append({
            'project': project, 'case': case, 'playwright_test_s': seconds(raw['duration']),
            'worker_boot_s': [seconds(worker['ready'] - worker['started']) for worker in workers],
            'ui_opening_s': seconds(raw['phases']['opening'][0]),
            'march_through_arrivals_s': seconds(raw['phases']['march-through-arrivals'][0]),
            'manual_placement_s': seconds(raw['phases']['manual-placement'][0]),
            'poll_wait_s': seconds(sum(raw['phases']['round-poll-wait'])),
            'save_measures': measures,
            'all_save_calls': len(saves),
            'all_save_wire_s': seconds(sum(entry['received'] - entry['started'] for entry in saves)),
            'poll_decisions': dict(Counter(f'{poll["kind"]}/{poll["decision"]}' for doc in docs for poll in doc['polls'])),
            'command_response_checks': comparisons,
        })

report = {'identity': identity, 'cases': summary}
(folder / 'summary.json').write_text(json.dumps(report, indent=2) + '\n')
for row in summary:
    checks = row['command_response_checks']
    print(row['project'], row['case'], 'all saves', row['all_save_calls'],
          'readiness polls', row['save_measures']['round-poll']['calls'],
          'successful checks', sum(x['response_matches_poll'] and x['revision_incremented']
                                   and x['response_matches_committed_save_fields'] for x in checks),
          'of', len(checks))

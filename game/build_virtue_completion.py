#!/usr/bin/env python3
"""Complete the731 missing virtues without rewriting any released catalog."""
from dataclasses import asdict

from build_campaigns import read, write
from build_main_scenarios import build_all
from remake.officers import convert_profile, virtue_score


def complete_profiles(base):
    config=read('game/config/virtue-completion.json')
    people={p['person_id']:p for p in base['people']}
    pending={pid for pid,p in people.items() if p['profile']['virtue'] is None}
    reviewed={r['person_id']:r for r in config['reviewed']}
    defaults={r['person_id']:r for r in config['defaults']}
    if (len(reviewed)!=len(config['reviewed']) or len(defaults)!=len(config['defaults'])
            or set(reviewed)&set(defaults) or set(reviewed)|set(defaults)!=pending
            or len(pending)!=731):
        raise ValueError('Completion must cover exactly the731 missing identities once')
    for pid in sorted(pending):
        p=people[pid];row=reviewed.get(pid) or defaults[pid]
        if row['name']!=p['name']:raise ValueError('Name and stable identity differ: '+pid)
        if pid in reviewed:
            design=dict(row)
            anchor=design['calibration']
            if people[anchor['person_id']]['profile']['virtue']!=anchor['virtue']:
                raise ValueError('Stale virtue calibration anchor')
            if virtue_score(design['dimensions'])!=design['virtue']:
                raise ValueError('Virtue and weighted dimensions differ')
            basis='history_informed_authorial_rating_calibrated_individually'
        else:
            design=dict(row,**config['default_policy'])
            basis='explicit_user_default60_not_historical_rating'
        prior=p['profile']
        p['virtue_design']=design
        p['profile']=asdict(convert_profile(san14_stats=prior['source_stats'],legacy={},
            health_max=prior['health_max'],terrain_affinity=prior['terrain_affinity'],virtue_design=design))
        p['configuration']['virtue']=basis
    if any(p['profile']['virtue'] is None for p in people.values()):raise ValueError('Incomplete virtue coverage')
    write('expansion/officers/data/virtue-completion-audit.json',{
        'schema':'virtue-completion-audit-v1','policy_id':config['default_policy']['policy_id'],
        'preserved':269,'new_reviewed':len(reviewed),'new_default60':len(defaults),
        'configured':1000,'pending':0,
        'people':[{'person_id':pid,'name':p['name'],'virtue':p['profile']['virtue'],
            'basis':p['configuration']['virtue'],
            'completion': 'reviewed' if pid in reviewed else 'user_default60' if pid in defaults else 'preserved'}
            for pid,p in sorted(people.items())]})


if __name__=='__main__':
    import json
    print(json.dumps(build_all(generation=5,complete_profiles=complete_profiles),ensure_ascii=False))

"""Native AI group selection with the same safe cells as human deployment.

The original sorts noncommanders and directly writes group-table coordinates.
It does not check occupancy or the manual rectangle. Here unsafe choices use
the first free safe original default; source data is never edited or clamped.
No state, roster, terrain, resources, clock or random stream is changed.
"""
from functools import lru_cache
import hashlib
import json
from pathlib import Path

from . import battle_deployment

SIDES=('defenders','attackers')
# Original profile selection is a faction-slot property and survives succession.
# These stable remake factions bind to the corresponding original faction.
ORIGINAL_FACTIONS={'dong_zhuo':0,'yuan_shao':1,'wei':2,'wu':3,
                   'shu':4,'liu_zhang':5,'ma_teng':6}
LINEAGE_ALIASES={'sun_jian':3,'liu_yan':5}
FAMILIES=(0,1,2,0,2,1,0)


def _require(condition,message):
    if not condition:
        raise ValueError(message)


@lru_cache(maxsize=1)
def _library():
    path=Path(__file__).resolve().parents[2]/'game/config/references/original-battle-ai-deployment-v1.json'
    data=json.loads(path.read_text())
    _require(data.get('schema')=='tk2-original-battle-ai-deployment-v1'
        and data.get('rom_sha256')==battle_deployment.ROM_SHA
        and data.get('original_slot_families')==list(FAMILIES),'Invalid native AI deployment library')
    expected={'profiles':'a70cd1fc0a10600d3e662ac844e1c871b7911d255e966307b4914516f88f8cb5',
        'defender_group_offsets':'9b2cf966adf226a8e2028886d77bf2b63fcaa7aa571d5916af87e2c6b7fe2f8e',
        'attacker_group_offsets':'b2f3c5d4cef4b82ac0599dfa620c941a371480c01d12f492bf256ff88c274316'}
    raw={}
    for name,sha in expected.items():
        value=bytes.fromhex(data['source_tables'][name]['hex'])
        _require(hashlib.sha256(value).hexdigest()==sha,'Invalid native AI deployment bytes')
        raw[name]=value
    profiles=[]
    for index in range(6):
        counts=[]
        for count in range(9):
            a,b=raw['profiles'][index*18+count*2:index*18+count*2+2]
            groups=[a>>4,a&15,b>>4,b&15]
            _require(sum(groups)==count+1,'Invalid native AI profile count')
            counts.append(groups)
        profiles.append(dict(index=index,side='defenders' if index<3 else 'attackers',family=index%3,counts=counts))
    offsets={side:list(raw[singular+'_group_offsets'])
             for side,singular in [('defenders','defender'),('attackers','attacker')]}
    _require(data.get('profiles')==profiles and data.get('group_byte_offsets')==offsets,
             'Native AI deployment derived data differs')
    return profiles,offsets


def family_for(faction):
    """Fresh immutable-input binding; never infer a current ruler's personality."""
    _require(type(faction) is str and bool(faction),'Invalid deployment faction')
    slot=ORIGINAL_FACTIONS.get(faction)
    if slot is not None:
        policy='original_faction'
    else:
        slot=LINEAGE_ALIASES.get(faction)
        policy='lineage_alias' if slot is not None else 'expanded_default'
    return dict(family=FAMILIES[slot] if slot is not None else 0,policy=policy,original_slot=slot)


def _ordered(units):
    result=list(units)
    # B371 repeats the full comparison span n-1 times. Equal values swap too;
    # Python's stable sorted() would not reproduce the original identity order.
    for _ in range(max(0,len(result)-2)):
        for index in range(1,len(result)-1):
            if result[index+1]['martial']>=result[index]['martial']:
                result[index],result[index+1]=result[index+1],result[index]
    return result


def plan(catalog,battle,field,side,*,occupied=()):
    """Return a fresh deterministic proposal; occupied is an iterable of(x,y).

    Only the requested side's ID and opening martial values are used. Existing
    tactical positions are deliberately ignored, and the battle list is never
    reordered. This is valid for a new army of one to ten units.
    """
    _require(side in SIDES,'Invalid AI deployment side')
    units=battle[side]
    _require(type(units) is list and 1<=len(units)<=10,'Invalid AI deployment army')
    ids=[]
    for unit in units:
        ident=unit.get('id') if isinstance(unit,dict) else None
        _require(type(ident) is int and ident>=0 or type(ident) is str and 0<len(ident)<=128,
                 'Invalid AI deployment identity')
        _require(type(unit.get('martial')) is int and 0<=unit['martial']<=255,
                 'Invalid opening martial value')
        ids.append(str(ident))
    _require(len(ids)==len(set(ids)),'Duplicate AI deployment identity')
    taken=set()
    for point in occupied:
        _require(isinstance(point,(tuple,list)) and len(point)==2
            and type(point[0]) is int and 0<=point[0]<31
            and type(point[1]) is int and 0<=point[1]<19,'Invalid occupied deployment coordinate')
        _require(tuple(point) not in taken,'Duplicate occupied deployment coordinate')
        taken.add(tuple(point))
    zone=battle_deployment.placement_zone(catalog,battle,field,side)
    allowed={(p['x'],p['y'])for p in zone['cells']}
    record=battle['extended']['deployment']
    native=battle_deployment._library()[0][record['target_map']]['sides'][side]['zones'][record['attacker_zone' if side=='attackers' else 'defender_zone']]
    profiles,offsets=_library()
    binding=family_for(battle['attacker' if side=='attackers' else 'defender'])
    profile=binding['family']+(3 if side=='attackers' else 0)
    groups=[0]
    if len(units)>1:
        groups.extend(group for group,count in enumerate(profiles[profile]['counts'][len(units)-2],1)
                      for _ in range(count))
    ordered=_ordered(units);cursors=list(offsets[side]);positions={};intended={};repairs=[]
    for unit,group in zip(ordered,groups):
        key=str(unit['id']);offset=0 if group==0 else cursors[group-1]
        _require(offset%2==0 and offset//2<len(native['default_points']),'AI group cursor outside native point table')
        raw=native['default_points'][offset//2]
        intended[key]=dict(raw)
        x,y=raw['x'],raw['packed_y'];visible_y=y-int(y>=16)
        reason=('outside_grid' if not(0<=x<31 and 0<=y<20 and y!=15) else
                'outside_zone' if (x,visible_y)not in allowed else
                'occupied' if (x,visible_y)in taken else None)
        if reason:
            point=next((p for p in zone['defaults'] if (p['x'],p['y'])not in taken),None)
            _require(point is not None,'Insufficient shared safe AI deployment candidates')
            x,visible_y=point['x'],point['y']
            repairs.append(dict(id=key,reason=reason))
        positions[key]=dict(x=x,y=visible_y);taken.add((x,visible_y))
        if group:
            cursors[group-1]+=2
    return dict(binding=binding,profile=profile,order=[str(u['id'])for u in ordered],groups=groups,
                positions=positions,intended=intended,repairs=repairs)

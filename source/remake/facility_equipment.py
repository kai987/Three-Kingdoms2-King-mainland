"""Published equipment table and bounded remake duel adjustments.

Names, power, weight and listed shop prices follow the user-supplied cnblogs
table. Blank prices remain unavailable. The independent Web duel keeps its
existing damage scale: starter equipment adds zero, rather than changing every
old battle when shops become available. Price/stock and damage adaptations are
explicitly distinguished from a byte-for-byte NES implementation.
"""
from copy import deepcopy

SOURCE = 'https://www.cnblogs.com/strick/p/10171248.html'


def _rows(values, *, weapon):
    return tuple(dict(id=i, name_tc=tc, name_ja=ja, power=power, weight=weight,
                      price=price, **(dict(family=('sword','blade','spear')[i//8]) if weapon else {}))
                 for i, (tc, ja, power, weight, price) in enumerate(values))


WEAPONS = _rows([
    ('短劍','短剣',3,4,50), ('飛劍','飛剣',4,3,70), ('長劍','長剣',7,5,120),
    ('破斬劍','破斬剣',9,8,180), ('大劍','大剣',13,9,250), ('青釭劍','青釭剣',15,6,None),
    ('倚天劍','倚天剣',16,7,None), ('七星寶劍','七星宝剣',17,4,None),
    ('薙刀','薙刀',4,4,60), ('眉尖刀','眉尖刀',5,6,100), ('三尖刀','三尖刀',8,7,150),
    ('鉤鐮刀','鉤鎌刀',10,8,200), ('偃月刀','偃月刀',12,7,240), ('鳳嘴刀','鳳嘴刀',11,6,260),
    ('龍牙刀','竜牙刀',17,8,None), ('關王刀','関王刀',19,10,400),
    ('矛','矛',5,4,60), ('雙戟','双戟',6,5,100), ('單鉤槍','単鉤槍',7,6,120),
    ('戰斧','戦斧',10,8,200), ('雙鉤槍','双鉤槍',11,7,250), ('方天畫戟','方天画戟',16,8,300),
    ('狼牙槍','狼牙槍',18,6,350), ('蛇矛','蛇矛',20,10,400),
], weapon=True)
# Requested novel signature equipment is an explicit remake layer. Original
# IDs 0..23 remain stable; these additions are never ordinary shop merchandise.
WEAPONS += tuple(dict(id=24+i,name_tc=tc,name_ja=ja,power=power,weight=weight,
    price=None,family=family,appearance=appearance,source_kind='requested_novel_remake')
    for i,(tc,ja,power,weight,family,appearance) in enumerate([
        ('雙股劍','双股剣',13,6,'sword','dual-swords'),
        ('雙鐵戟','双鉄戟',12,7,'spear','dual-ji'),
        ('古錠刀','古錠刀',12,6,'blade','guding-dao'),
        ('九環刀','九環刀',14,9,'blade','ring-dao'),
        ('二石鐵胎弓','二石の鉄胎弓',12,5,'spear','bow'),
    ]))
WEAPON_MAX = len(WEAPONS)-1
ARMOR_MAX = 7
WEAPONS = tuple(dict(row,name_tc='關王刀（青龍偃月刀）',name_ja='関王刀（青龍偃月刀）')
    if row['id']==15 else row for row in WEAPONS)
WEAPONS = tuple(dict(row,appearance=row.get('appearance',
    {17:'dual-ji',19:'axe',21:'halberd',23:'serpent-spear'}.get(row['id'],
        {'sword':'sword','blade':'guandao','spear':'spear'}[row['family']]))) for row in WEAPONS)
ARMORS = _rows([
    ('綸巾','綸巾',2,1,50), ('籠手','籠手',3,2,80), ('兜','兜',5,4,100),
    ('硬皮','硬皮',7,6,150), ('鶴氅','鶴氅',8,5,200), ('甲冑','甲冑',10,10,250),
    ('聖者之衣','聖者の衣',11,3,350), ('龍鱗之鎧','竜鱗の鎧',12,7,None),
], weapon=False)


def item(slot, ident):
    if slot not in ('weapon','armor') or type(ident) is not int:
        raise ValueError('Invalid equipment identity')
    rows = WEAPONS if slot == 'weapon' else ARMORS
    if not 0 <= ident < len(rows):
        raise ValueError('Invalid equipment identity')
    return deepcopy(rows[ident])


def stock(town, slot):
    if type(town) is not int or town not in (1,2,3) or slot not in ('weapon','armor'):
        raise ValueError('Invalid equipment stock')
    if town < 2:
        return []
    rows = WEAPONS if slot == 'weapon' else ARMORS
    return [deepcopy(row) for row in rows
            if row['price'] is not None and (town == 3 or row['power'] <= 10)]


def duel_adjustment(weapon_id, armor_id, martial):
    """Return attack and defence additions without an RNG draw.

    Heavy replacement weapons penalise weak wielders. This is a documented Web
    scale, not the original weapon hit-rate or rejection-sampling algorithm.
    """
    weapon, armor = item('weapon',weapon_id), item('armor',armor_id)
    if type(martial) is not int or not 1 <= martial <= 99:
        raise ValueError('Invalid equipment wielder')
    weight_penalty = max(0,(weapon['weight']*8-martial+9)//10) if weapon_id else 0
    return dict(attack=max(-6,(weapon['power']-3)//3-weight_penalty),
                defense=max(0,(armor['power']-2)//3))

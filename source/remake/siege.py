"""Persistent castle soldier encounters with recovered native deployment data.

Original tables are copied as bounded declarative integers; this module neither
loads a ROM nor runs recovered machine code. Contact damage uses this remake's
existing kernel. Formation/order edits and movement previews consume no RNG.
"""
from copy import deepcopy
from .errors import GameError
from . import battle_grid, presentation

SCHEMA = 'tk2-siege-v1'
SIDES = ('attackers', 'defenders')
KINDS = ('infantry', 'archer', 'cavalry', 'general')
ORDERS = ('advance', 'retreat', 'wait', 'surround')
MAX_ROUNDS = 200
# physical14, X pointers B794 / Y pointers B7A0; slot0 is the commander.
FORMATIONS = (
 ((1,2,2,2,3,3,3,4,4,5,3),(5,1,2,3,4,5,6,7,8,9,9)),
 ((1,4,4,2,2,3,3,4,4,5,5),(5,4,6,4,6,3,7,2,8,1,9)),
 ((1,3,2,2,2,2,3,3,4,4,5),(5,5,4,6,2,8,3,7,4,6,5)),
 ((1,2,2,3,3,3,4,4,5,5,5),(5,4,6,3,5,7,4,6,3,5,7)),
 ((1,3,3,8,8,6,6,7,7,7,7),(5,4,6,2,8,2,8,1,9,2,8)),
 ((1,3,3,8,8,1,1,3,3,2,2),(5,4,6,2,8,3,7,2,8,1,9)),
)
# Each level has the >=80, >=50 and <50 martial threshold pairs.
THRESHOLDS = (
 ((6,9),(8,10),(8,11)),((5,9),(7,10),(7,11)),
 ((5,8),(6,9),(6,10)),((4,7),(5,8),(6,9)),
 ((3,6),(4,8),(5,9)),((2,6),(4,7),(4,8)),
 ((2,5),(3,6),(4,7)),((1,5),(2,6),(3,7)),
)
# Original16x10 castle collision classes, physical1:8A30 / bank15:CB59.
WALLS = frozenset(((6,0),(11,0),(11,1),(6,2),(11,2),(6,3),(7,3),
 (8,3),(9,3),(11,3),(6,7),(7,7),(8,7),(9,7),(11,7),(6,8),(11,8),(11,9)))
FIELDS = {'schema','actor','target','fort','map_id','cell','stage','round',
          'formations','orders','units'}
PIECE_FIELDS = {'id','side','kind','x','y','troops','health','withdrawn'}


def _side(battle, ident):
    return next((side for side in SIDES if any(u['id']==ident for u in battle[side])), None)


def _main(battle, row, side):
    return next(u for u in battle[side] if u['id'] in (row['actor'],row['target']))


def _live(piece):
    return not piece['withdrawn'] and (piece['health']>1 if piece['kind']=='general' else piece['troops']>0)


def _opposite(side):
    return SIDES[1] if side==SIDES[0] else SIDES[0]


def _player_side(state):
    return 'attackers' if state.battle['attacker']==state.player else 'defenders'


def _walls(battle, row):
    return WALLS if _side(battle,row['fort'])=='defenders' else {(15-x,y)for x,y in WALLS}


def _position(side, kind, slot, formation, fortified):
    selected = (4 if kind=='archer' else 5) if fortified else formation
    xs,ys=FORMATIONS[selected]
    return (xs[slot] if side=='attackers' else 15-xs[slot]),ys[slot]


def _deploy(game,state,row):
    battle=state.battle;pieces=[]
    for side in SIDES:
        unit=_main(battle,row,side);officer=state.officers[unit['id']]
        count=(unit['troops']+99)//100
        q,r=divmod(unit['troops'],count)
        group=0 if unit['martial']>=80 else 1 if unit['martial']>=50 else 2
        a,b=THRESHOLDS[min(7,officer.tier)][group]
        fortified=unit['id']==row['fort']
        if fortified:a=0
        for slot in range(count+1):
            kind='general' if slot==0 else 'infantry' if slot<a else 'archer' if slot<b else 'cavalry'
            troops=0 if slot==0 else q+int(slot<=r)
            health=battle['extended']['support'][str(unit['id'])]['health'] if slot==0 else troops
            x,y=_position(side,kind,slot,row['formations'][side] or 0,fortified)
            pieces.append(dict(id=('a'if side=='attackers'else'd')+str(slot),side=side,
                               kind=kind,x=x,y=y,troops=troops,health=health,withdrawn=False))
    row['units']=pieces


def begin(game,state,actor,target,context):
    battle=state.battle
    row=dict(schema=SCHEMA,actor=actor['id'],target=target['id'],**deepcopy(context),
             stage='formation',round=1,formations={side:3 for side in SIDES},
             orders={side:{kind:('wait' if _main_id==context['fort'] and kind=='general' else 'advance')for kind in KINDS}
                     for side,_main_id in ((_side(battle,actor['id']),actor['id']),(_side(battle,target['id']),target['id']))},units=[])
    if state.player in (battle['attacker'],battle['defender']):
        row['formations'][_player_side(state)]=None
    _deploy(game,state,row)
    battle['extended']['siege']=row
    battle['log'].append('接觸城砦守軍，進入攻城戰；請先選擇陣形。')
    battle['log'][:]=battle['log'][-80:]
    return row


def _require(game,state,payload,stages):
    battle=state.battle
    row=(battle or {}).get('extended',{}).get('siege')
    if (state.phase!='battle' or not row or payload.get('battle_id')!=battle['id']
            or row['stage'] not in stages or battle['extended']['duel']):
        raise GameError('目前不能執行這項攻城操作。')
    return battle,row


def form(game,state,payload):
    battle,row=_require(game,state,payload,('formation',))
    value=payload.get('formation')
    if type(value)is not int or not 0<=value<=3:raise GameError('請選擇四種陣形之一。')
    row['formations'][_player_side(state)]=value
    _deploy(game,state,row);row['stage']='orders'
    battle['log'].append('陣形已確定，請分別下達步、弓、騎、將的命令。')
    battle['log'][:]=battle['log'][-80:]


def orders(game,state,payload):
    _,row=_require(game,state,payload,('orders','combat'))
    value=payload.get('orders')
    if (not isinstance(value,dict) or set(value)!=set(KINDS)
            or any(type(v)is not str or v not in ORDERS for v in value.values())):
        raise GameError('請為步、弓、騎、將各選擇一項有效命令。')
    row['orders'][_player_side(state)]=dict(value);row['stage']='combat'


def _sync(state,row):
    battle=state.battle
    for side in SIDES:
        unit=_main(battle,row,side)
        troops=sum(p['troops'] for p in row['units'] if p['side']==side and p['kind']!='general')
        general=next(p for p in row['units']if p['side']==side and p['kind']=='general')
        unit['troops']=troops
        battle['extended']['support'][str(unit['id'])]['health']=max(1,general['health'])


def _finish(game,state,row,reason):
    _sync(state,row)
    battle=state.battle
    battle['extended'].pop('siege',None)
    battle['log'].append(reason)
    battle['log'][:]=battle['log'][-80:]
    own=_side(battle,row['actor']);foe=_opposite(own)
    actor=next(u for u in battle[own]if u['id']==row['actor'])
    if state.player in (battle['attacker'],battle['defender']):
        game._finish_action(state,actor,own,foe)
    else:game._battle_result(state)


def withdraw(game,state,payload):
    _,row=_require(game,state,payload,('formation','orders','combat'))
    _finish(game,state,row,'部隊退出本次攻城交鋒，返回戰術地圖。')


def _distance(first,second):
    return abs(first['x']-second['x'])+abs(first['y']-second['y'])


def _occupied(row,piece):
    return {(p['x'],p['y']) for p in row['units']if p is not piece and _live(p)}


def _ray_target(row,piece,enemies):
    # Original baseline ray probes accept distances2..4. Castle class4/5
    # does not block these arrows; a nearer occupied cell does.
    for dx,dy in ((1,0),(-1,0),(0,1),(0,-1)):
        for distance in range(1,5):
            x,y=piece['x']+dx*distance,piece['y']+dy*distance
            found=next((p for p in row['units'] if _live(p)and p['x']==x and p['y']==y),None)
            if found:
                if found in enemies and distance>=2:return found
                break
    return None


def _move_toward(battle,row,piece,goal):
    occupied=_occupied(row,piece);walls=_walls(battle,row)
    dx,dy=goal[0]-piece['x'],goal[1]-piece['y']
    axes=[(1 if dx>0 else -1,0)]if dx else[]
    if dy:axes.append((0,1 if dy>0 else -1))
    if abs(dy)>abs(dx):axes.reverse()
    for sx,sy in axes:
        point=piece['x']+sx,piece['y']+sy
        if 0<=point[0]<16 and 0<=point[1]<10 and point not in occupied and point not in walls:
            piece['x'],piece['y']=point;return True
    return False


def _hit(game,state,row,piece,target):
    battle=state.battle;actor=_main(battle,row,piece['side']);victim=_main(battle,row,target['side'])
    attacking=dict(actor,troops=100 if piece['kind']=='general' else piece['troops'])
    defending=dict(victim,troops=target['health'] if target['kind']=='general' else target['troops'])
    loss=game._damage(state,attacking,defending)
    support=battle['extended']['support'][str(victim['id'])]
    if support['guard']:loss=max(1,loss//2);support['guard']-=1
    if target['kind']=='general':
        target['health']=max(1,target['health']-loss)
        if target['health']==1:
            for p in row['units']:
                if p['side']==target['side']and p['kind']!='general':p['troops']=p['health']=0
    else:
        target['troops']-=loss;target['health']=target['troops']
    _sync(state,row)


def _duel(game,state,row):
    """Original general contact enters the existing duel, without another AP."""
    battle=state.battle
    own=_player_side(state);actor=_main(battle,row,own);target=_main(battle,row,_opposite(own))
    before=presentation.snapshot(game,state)
    battle['extended']['duel']=dict(actor=actor['id'],target=target['id'],round=1,log=[])
    battle['log'].append('雙方主將接觸，進入單挑。')
    battle['log'][:]=battle['log'][-80:]
    presentation.record(game,state,before,kind='duel_start',actor=actor['id'],target=target['id'],own=own)
    return True


def synchronize_duel(state):
    battle=state.battle
    if not battle or not battle['extended'].get('siege'):return
    row=battle['extended']['siege']
    for side in SIDES:
        unit=_main(battle,row,side)
        general=next(p for p in row['units']if p['side']==side and p['kind']=='general')
        general['health']=battle['extended']['support'][str(unit['id'])]['health']
        if unit['troops']==0:
            for p in row['units']:
                if p['side']==side and p['kind']!='general':p['troops']=p['health']=0


def finish_duel(game,state):
    battle=state.battle;row=battle['extended']['siege']
    battle['log'][:]=battle['log'][-80:]
    synchronize_duel(state)
    if any(_main(battle,row,side)['troops']==0 for side in SIDES):
        _finish(game,state,row,'主將已敗，攻城交鋒結束。')
    else:
        row['round']+=1
        if row['round']>MAX_ROUNDS:_finish(game,state,row,'攻城交鋒已達二百巡，雙方停止本次接戰。')
        else:row['stage']='orders'


def _surround(state,row):
    # Manual requires a weakened commander and surrounding without attacks;
    # the remake threshold is explicit and deterministic rather than guessing
    # an unverified native surrender probability.
    battle=state.battle
    for general in (p for p in row['units']if p['kind']=='general'and _live(p)and p['health']<=30):
        neighbors=[p for p in row['units']if p['side']!=general['side']and _live(p)
                   and row['orders'][p['side']][p['kind']]=='surround'and _distance(p,general)==1]
        if len(neighbors)<3:continue
        side=general['side'];unit=_main(battle,row,side)
        battle['extended']['surrenders'][str(unit['id'])]=unit['troops']
        for p in row['units']:
            if p['side']==side and p['kind']!='general':p['troops']=p['health']=0
        _sync(state,row)
        return True
    return False


def _step(game,state,row):
    battle=state.battle
    initiating=_side(battle,row['actor']);side_order=(initiating,_opposite(initiating))
    stunned=set()
    for side in SIDES:
        unit=_main(battle,row,side);support=battle['extended']['support'][str(unit['id'])]
        if support['stunned']:support['stunned']-=1;stunned.add(side)
    for kind in KINDS:
        by_side={side:[p for p in row['units']if p['side']==side and p['kind']==kind]for side in SIDES}
        for index in range(max(len(p)for p in by_side.values())):
            for side in side_order:
                if side in stunned or index>=len(by_side[side]):continue
                piece=by_side[side][index]
                for _ in range(2 if kind in ('cavalry','general')else 1):
                    if not _live(piece):break
                    enemies=[p for p in row['units']if p['side']!=side and _live(p)]
                    if not enemies:break
                    order=row['orders'][side][kind]
                    if order=='retreat':
                        edge=0 if side=='attackers'else 15
                        if piece['x']==edge:piece['withdrawn']=True
                        else:_move_toward(battle,row,piece,(edge,piece['y']))
                        if piece['kind']=='general'and piece['withdrawn']:
                            _finish(game,state,row,'主將退出攻城戰，部隊返回戰術地圖。');return
                        continue
                    adjacent=[p for p in enemies if _distance(piece,p)==1]
                    target=next(iter(adjacent),None)
                    if target is None and kind=='archer'and order=='advance':target=_ray_target(row,piece,enemies)
                    if target is not None and order!='surround':
                        if kind=='general'and target['kind']=='general'and _duel(game,state,row):return
                        _hit(game,state,row,piece,target)
                    elif order!='wait':
                        # Manual42: advance toward the enemy commander and
                        # attack troops met along the way. Chasing a closer
                        # wall archer can otherwise pin infantry on the wall.
                        enemy=next((p for p in enemies if p['kind']=='general'),None)
                        if enemy is None:enemy=min(enemies,key=lambda p:(_distance(piece,p),p['id']))
                        _move_toward(battle,row,piece,(enemy['x'],enemy['y']))
                    if any(_main(battle,row,s)['troops']==0 for s in SIDES):
                        _finish(game,state,row,'攻城交鋒已分勝負，返回戰術地圖。');return
    if _surround(state,row):
        _finish(game,state,row,'敵將被包圍而降伏，攻城交鋒結束。');return
    row['round']+=1
    if row['round']>MAX_ROUNDS:
        _finish(game,state,row,'攻城交鋒已達二百巡，雙方停止本次接戰。');return
    row['stage']='orders'
    battle['log'].append(f'攻城戰第{row["round"]-1}巡結束。')
    battle['log'][:]=battle['log'][-80:]


def step(game,state,payload):
    _,row=_require(game,state,payload,('combat',))
    _step(game,state,row)


def auto(game,state):
    """AI-only encounters execute exactly the same formations/orders/steps."""
    row=state.battle['extended']['siege'];row['stage']='combat'
    for _ in range(MAX_ROUNDS):
        if state.battle is None or not state.battle['extended'].get('siege'):return
        row=state.battle['extended']['siege'];row['stage']='combat';_step(game,state,row)
        # AI-only general contacts run the same duel actions and equipment
        # service as the player. Policy chooses a legal move, never damage.
        for _ in range(20):
            battle=state.battle
            if not battle or not battle['extended']['duel']:break
            actor=battle['extended']['duel']['actor']
            hp=battle['extended']['support'][str(actor)]['health']
            game._duel_action(state,dict(battle_id=battle['id'],move='desperate'if hp<=30 else 'strike'))
            synchronize_duel(state)
        if state.battle and state.battle['extended']['duel']:
            raise GameError('攻城單挑未能在二十合內結束。')
    if state.battle and state.battle['extended'].get('siege'):
        raise GameError('攻城戰未能在限定巡數內結束。')


def validate(game,state,battle):
    row=battle['extended'].get('siege')
    if 'siege' not in battle['extended']:return
    if (not isinstance(row,dict)or set(row)!=FIELDS or row['schema']!=SCHEMA
            or state.phase!='battle'or battle['outcome']
            or row['stage']not in ('formation','orders','combat')
            or type(row['round'])is not int or not 1<=row['round']<=MAX_ROUNDS):
        raise ValueError('Invalid siege stage')
    if (not all(any(type(row[k])is type(u['id'])and row[k]==u['id']for side in SIDES for u in battle[side])for k in ('actor','target','fort'))
            or _side(battle,row['actor'])==_side(battle,row['target'])
            or not isinstance(row['cell'],dict)or set(row['cell'])!={'x','y'}
            or any(type(row['cell'][axis])is not int for axis in ('x','y'))):
        raise ValueError('Invalid siege participants')
    context=battle_grid.siege_context(battle,row['actor'],row['target'])
    if context!={k:row[k]for k in ('fort','map_id','cell')}:raise ValueError('Invalid siege castle')
    duel=battle['extended']['duel']
    if duel is not None and(row['stage']!='combat'or {duel['actor'],duel['target']}!={row['actor'],row['target']}):raise ValueError('Invalid siege duel')
    if set(row['formations'])!=set(SIDES)or any(v is not None and(type(v)is not int or not 0<=v<=3)for v in row['formations'].values()):raise ValueError('Invalid siege formation')
    player=_player_side(state)
    if (row['stage']=='formation')!=(row['formations'][player]is None)and state.player in (battle['attacker'],battle['defender']):raise ValueError('Invalid siege formation stage')
    if any(value is None and(side!=player or row['stage']!='formation')for side,value in row['formations'].items()):raise ValueError('Invalid siege waiting formation')
    if set(row['orders'])!=set(SIDES)or any(not isinstance(o,dict)or set(o)!=set(KINDS)or any(v not in ORDERS for v in o.values())for o in row['orders'].values()):raise ValueError('Invalid siege orders')
    if not isinstance(row['units'],list)or not 4<=len(row['units'])<=22:raise ValueError('Invalid siege pieces')
    seen=set();occupied=set()
    for p in row['units']:
        if (not isinstance(p,dict)or set(p)!=PIECE_FIELDS or p['side']not in SIDES or p['kind']not in KINDS
                or not isinstance(p['id'],str)or p['id']in seen
                or type(p['x'])is not int or not 0<=p['x']<16 or type(p['y'])is not int or not 0<=p['y']<10
                or type(p['troops'])is not int or not 0<=p['troops']<=100
                or type(p['health'])is not int or not 0<=p['health']<=100 or type(p['withdrawn'])is not bool
                or p['kind']=='general'and p['troops']!=0 or p['kind']!='general'and p['troops']!=p['health']):raise ValueError('Invalid siege piece')
        seen.add(p['id'])
        if _live(p):
            point=p['x'],p['y']
            if point in occupied or point in _walls(battle,row):raise ValueError('Overlapping siege pieces')
            occupied.add(point)
    for side in SIDES:
        pieces=[p for p in row['units']if p['side']==side];unit=_main(battle,row,side)
        if (sum(p['kind']=='general'for p in pieces)!=1
                or not 2<=len(pieces)<=11
                or {p['id']for p in pieces}!={(('a'if side=='attackers'else'd')+str(i))for i in range(len(pieces))}
                or unit['troops']<=0
                or any(p['withdrawn']for p in pieces if p['kind']=='general')
                or sum(p['troops']for p in pieces)!=unit['troops']
                or next(p['health']for p in pieces if p['kind']=='general')!=battle['extended']['support'][str(unit['id'])]['health']):raise ValueError('Siege soldier conservation')

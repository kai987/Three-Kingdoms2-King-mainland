"""Recovered map/service rules from original6502 bytes, not original source.

Raw classes6/7/8 are single map-marker encodings, not new movement terrains.
Both playerDB46 and AI B6E5 normalize them to2. Map-service category is instead
the index of the city XY table; the two encodings are not interchangeable.
"""
from .game_enums import ROM_SHA256,MOVEMENT_COST_FIRST,MOVEMENT_COST_SECOND

CLASS_TABLE_OFFSET=0x1175B
CITY_CHUNKS_TABLE_OFFSET=0x31F5A
SERVICE_COORDINATES_OFFSET=0x23BB4
METATILE_TABLE_OFFSET=0x3F487
SERVICE_NAMES=('资源买卖','装备购买','体力治疗')
SERVICE_LABELS_ORIGINAL=('コメヤ','ブキヤ','ビョウイン')
SERVICE_NAME_CONFIDENCE='confirmed effect semantics and original core-rendered NPC labels'

def city_chunks(rom:bytes,city:int)->tuple[int,int,int,int]:
    if not 0<=city<30:raise ValueError('Original city domain0..29')
    pointer=int.from_bytes(rom[CITY_CHUNKS_TABLE_OFFSET+2*city:CITY_CHUNKS_TABLE_OFFSET+2*city+2],'little')
    offset=0x30010+pointer-0xc000
    return tuple(rom[offset:offset+4])

def legal_cell(x:int,y:int)->bool:
    return 0<=x<31 and 0<=y<20 and y!=15

def map_cell(rom:bytes,chunks,x:int,y:int)->dict:
    if len(chunks)!=4 or any(not 0<=c<120 for c in chunks):raise ValueError('Four original chunk IDs0..119 required')
    x&=255;y&=255;quadrant=int(x>=16)|2*int(y>=16);chunk=chunks[quadrant]
    pointer=int.from_bytes(rom[0x117DB+2*chunk:0x117DD+2*chunk],'little')
    bank=(rom[0x118CB+chunk]&63)%32
    offset=16+bank*8192+pointer-0x8000+(((y<<4)&255)|(x&15))
    tile=rom[offset];raw=rom[CLASS_TABLE_OFFSET+tile]if tile<128 else 0
    return {'x':x,'y':y,'chunk':chunk,'quadrant':quadrant,'bank':bank,'tile_offset':offset,'tile':tile,'raw_class':raw,
            'movement_class':raw if raw<6 else 2,'ai_class':raw if raw<6 else 2,
            'legal_cell':legal_cell(x,y),'is_attribute_row':y==15,'outside_playable_bounds':x>=31 or y>=20,
            'pixel_xy':(16*x,16*(y-int(y>=16)))}

def metatile(rom:bytes,tile:int)->bytes:
    """Original F477 dictionary: four8×8 BG tile codes for raw metatile0..127."""
    if not 0<=tile<128:raise ValueError('128 original metatiles')
    start=METATILE_TABLE_OFFSET+4*tile
    return rom[start:start+4]

def service_coordinates(rom:bytes,city:int):
    if not 0<=city<30:raise ValueError('Original city domain0..29')
    return tuple(tuple(rom[SERVICE_COORDINATES_OFFSET+6*city+2*i:SERVICE_COORDINATES_OFFSET+6*city+2*i+2])for i in range(3))

def service_at(rom:bytes,city:int,x:int,y:int):
    """First XY match at a valid playable cell; independent of raw class.

    Original A4D6 is reached after the movement bounds gate. This higher-level
    API enforces that precondition so FF/FF absent entries are not facilities.
    """
    if not legal_cell(x,y):return None
    for index,(cx,cy)in enumerate(service_coordinates(rom,city)):
        if (x&255,y&255)==(cx,cy):return index
    return None

def queue_message(memory,message:int,job:int):
    memory[0x311]=message&255;memory[0x310]=job&255
    memory[0x312]=memory[0x313]=255;memory[0x300]=0

def enter_map_service(memory,rom:bytes,renderer_hook=None):
    """A4D6..A51C: movement-end service check, after enemy-base handling.

    A match requires the explicit D6CC render dependency before final writes.
    No consumption bit is set here. Gameplay mode3 disables this interaction.
    """
    slot=memory[0x509];city=memory[0x50e]
    x,y=memory[0x600+slot],memory[0x614+slot]
    index=None if memory[0x50f]==3 else service_at(rom,city,x,y)
    if index is None:
        memory[0x501]=(memory[0x501]+1)&255
        return {'entered':False,'next_substate':memory[0x501]}
    memory[0x470]=index;memory[0x12]=1
    if renderer_hook is None:raise RuntimeError('Map service entry requires bank13 D6CC renderer_hook')
    renderer_hook(memory)
    memory[0x500]=memory[0x501]=9;queue_message(memory,0xa7,5)
    return {'entered':True,'service_index':index,'service_name':SERVICE_NAMES[index],'state':9,'substate':9,'message':0xa7,'consumed_flag_written':False}

def select_map_service(memory):
    """Bank9 C80B..C843 after menu/input readiness; 0012=0 means accept.

    Nonzero selection resets battle0/0. Accepted0470=0/1/other routes to
    resource trade sub0 / equipment sub5 / healing sub3 respectively.
    """
    if memory[0x12]!=0:
        memory[0x500]=memory[0x501]=0
        return {'accepted':False}
    memory[0x424]=memory[0x425]=0;index=memory[0x470]
    if index==0:sub,message=0,0xa8
    elif index==1:
        sub,message=5,0xad;memory[0xbd]=0x8c
    else:sub,message=3,0xb1
    memory[0x501]=sub;queue_message(memory,message,2)
    return {'accepted':True,'service_index':index,'substate':sub,'message':message}

def movement_quote(rom:bytes,chunks,x:int,y:int,officer_flags:int,hundred_troops_cache:int,action_points:int):
    """Player lookupDB46 + costA7E7; raw>=6 has already become terrain2.

    Cache is produced by DB03 from troops_low10//100 (FF for an empty slot).
    Affinity3 is retained as invalid raw encoding; zero cost is not a new skill.
    """
    cell=map_cell(rom,chunks,x,y);affinity=(officer_flags>>2)&3
    if not cell['legal_cell']:raise ValueError('Movement quote requires a playable cell, not attributes/unused data')
    table=MOVEMENT_COST_FIRST if (hundred_troops_cache&255)>=6 else MOVEMENT_COST_SECOND
    cost=table[cell['movement_class']][affinity];ap=action_points&255
    return {'cell':cell,'affinity':affinity,'affinity_supported':affinity<3,'cost':cost,'remaining_ap':(ap-cost)&255,'sufficient_ap':ap>=cost,'cache':hundred_troops_cache&255}

def map_service_heal(current_hp:int,initial_hp:int,sampled_0_to_10:int):
    """Bank9 C45B..C4A0 after50-gold payment:35..45 healing, byte arithmetic.

    Original first adds modulo256 then compares to initial HP. Out-of-domain
    HP overflow therefore survives; do not replace this with arbitrary min().
    """
    if not 0<=sampled_0_to_10<=10:raise ValueError('Original rejection-sampled0..10 domain')
    amount=sampled_0_to_10+35;hp=((current_hp&255)+amount)&255;initial=initial_hp&255
    if hp>=initial:amount=(amount-(hp-initial))&255;hp=initial
    return {'health':hp,'reported_healing':amount,'gold_cost':50}

def resource_trade(grain:int,gold:int,amount:int,price:int,buy_grain:bool):
    """Bank9 C21B/C2F2: branch-specific quote byte; addition wraps before cap.

    The buy branch uses amount*100/quote; the sell branch uses amount*quote/100.
    The two quote bytes are loaded from different positions in the city table;
    they must not be interpreted as one shared "gold per100 grain" price.
    Actual transactions floor the exchange. The earlier UI limit calculation
    has a different rounding rule. Zero requested amount performs no writes.
    """
    grain&=65535;gold&=65535;amount&=65535;price&=255
    if amount==0:return {'changed':False,'grain':grain,'gold':gold}
    if buy_grain:
        cost=((amount*100)//price)&65535 if price else 65535
        grain=min((grain+amount)&65535,9999);gold=max(0,gold-cost)
        return {'changed':True,'grain':grain,'gold':gold,'reported_amount':amount,'message':0xab,'substate':8}
    gained=(amount*price//100)&65535
    grain=max(0,grain-amount);gold=min((gold+gained)&65535,9999)
    return {'changed':True,'grain':grain,'gold':gold,'reported_amount':gained,'message':0xac,'substate':8}

def equipment_permission(item:int,officer_id:int,martial:int,virtue:int,allocation_flags:int):
    """Bank9 C73B: four rare-item restrictions plus global6FE1 allocation bits."""
    item&=255;flags=allocation_flags&255
    rare={15:(officer_id==38,2),23:(officer_id==153,4),22:((martial&255)>=90,8),30:((virtue&255)>=90,16)}
    if item not in rare:return {'allowed':True,'allocation_flags':flags,'message':None}
    eligible,bit=rare[item]
    if not eligible:return {'allowed':False,'allocation_flags':flags,'message':0x48}
    if flags&bit:return {'allowed':False,'allocation_flags':flags,'message':0x49}
    return {'allowed':True,'allocation_flags':flags|bit,'message':None}

def pack_purchased_equipment(packed:int,item:int)->int:
    """Bank9 C6D5..C706: IDs0..23 weapon;24..31 armor, preserving other bits."""
    if not 0<=item<32:raise ValueError('Original32-item table domain')
    return ((packed&224)|item) if item<24 else ((packed&31)|((item-24)<<5))

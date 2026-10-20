"""ROM-backed names and terrain behavior; reconstructed, not original source.

Names of the16 tactics are read from actual rendered CHR menu records, linked
to the action stored at $0543. Terrain language preserves confidence differences.
See analysis/names_terrain/evidence.json for byte addresses and screenshots.
"""
from enum import IntEnum

ROM_SHA256='26c8d921ff5c208191f136480bcd8d7e89c2e4ed40a0ac7b51482bcb52fe2b82'
TACTIC_NAMES=('火計','陥穽','虚兵','要撃','乱水','火箭','偽撃転殺','共殺',
              '籠絡','落石','連環','十面埋伏','水攻','連弩','劫火','奇門遁甲')
TACTIC_ACTION_COSTS=(6,5,4,6,7,8,8,8,10,9,9,10,10,8,12,10)
TACTIC_NAME_BG_CHR_PAGES=(0x5B,0x16,0x02,0x17)

class Tactic(IntEnum):
    FIRE_PLAN=0
    PITFALL=1
    FALSE_SOLDIERS=2
    INTERCEPTION=3
    DISTURB_WATER=4
    FIRE_ARROW=5
    FEIGNED_ATTACK_TURN_KILL=6
    MUTUAL_KILL=7
    ENTICE=8
    ROCKFALL=9
    CHAIN=10
    TEN_SIDED_AMBUSH=11
    WATER_ATTACK=12
    REPEATING_CROSSBOW=13
    RAID_FIRE=14
    QIMEN_DUNJIA=15

class OfficerStatus(IntEnum):
    UNROSTERED=0
    WAITING_APPEARANCE=1
    ROSTERED=2
    REMOVED=3

class DuelResult(IntEnum):
    """0515/0517 results, separate from byte11 officer-status low bits.

    Bank13 C782/C787: result2 later removes the defeated record; result3
    records a captive; result4 changes battle allegiance and calls the loyalty-adjustment
    service. Codes5..7 alias that handler but no producer is named here.
    """
    NORMAL=0
    RETURN_TO_ATTACK=1
    ZERO_HEALTH=2
    CAPTURE=3
    CHANGE_SIDE=4

OFFICER_STATUS_CONFIDENCE={
    0:('strong inference','Unrostered/roaming; byte5 receives a city index'),
    1:('strong inference','Script-year eligibility is checked before roster insertion'),
    2:('confirmed transition','Written immediately after city-roster insertion'),
    3:('confirmed removal flag','Removal/defeat flag; permanent-death meaning is path dependent'),
}

TERRAIN_AFFINITY_GLYPHS={0:'平',1:'山',2:'水'}
# The raw classifier has values0..8. AI B6E5 and player DB46 fold6..8 to2.
TERRAIN_LABELS={
    0:('森林','strong inference from original-renderer pixels'),
    1:('特殊地形 / 平滑土色','exact visual description; official name unresolved'),
    2:('平地','strong inference from original-renderer pixels'),
    3:('水域','strong inference from blue-water pixels and water-tactic gates'),
    4:('山地','strong inference from mountain pixels and affinity costs'),
    5:('城 / 城砦','strong inference from base location, original pixels and tactic gates'),
    6:('事件标记6','confirmed legal map encoding; player/AI movement class2; service type uses independent XY table'),
    7:('事件标记7','confirmed legal map encoding; player/AI movement class2; service type uses independent XY table'),
    8:('事件标记8','confirmed legal map encoding; player/AI movement class2; service type uses independent XY table'),
}

# ROM bank12 $A823 and $A83F; corresponding bank8 tables $A7CD/$A7E9.
# The first/second selector is read from RAM $063C[slot]>=6 in $A7E7.
# Bank13 $DB03 refreshes this cache from troops_low10//100, or FF for an empty
# slot. Thus a populated normal slot chooses the first table at600 troops.
MOVEMENT_COST_FIRST=((3,5,5,0),(4,4,4,0),(2,3,3,0),(5,6,3,0),
                     (5,3,6,0),(6,6,6,0),(6,6,6,0))
MOVEMENT_COST_SECOND=((2,3,3,0),(3,3,3,0),(1,2,2,0),(3,5,2,0),
                      (3,2,4,0),(4,4,4,0),(4,4,4,0))

def movement_cost(terrain_class:int,affinity_code:int,selector_byte:int)->int:
    """Exact verified table behavior of bank12 $A7E7 for classes0..6.

    Affinity3 yields0 in the ROM table but has no valid name/UI glyph record.
    It is retained as an undefined raw encoding, not offered as a new ability.
    selector_byte is the cached hundred-troop quotient at RAM063C[slot], not
    a terrain/branch type. The underlying refresh helper writes FF for empties.
    """
    if not 0<=terrain_class<=6 or not 0<=affinity_code<=3:
        raise ValueError('Validated table domain: terrain0..6, affinity0..3')
    table=MOVEMENT_COST_FIRST if (selector_byte&255)>=6 else MOVEMENT_COST_SECOND
    return table[terrain_class][affinity_code]

def tactic_name(action:int)->str:
    return TACTIC_NAMES[action&15]

def map_terrain(rom:bytes,chunk_ids,x:int,y:int):
    """Reproduce bank8 $B6EF/$B6E5 from original pointer/bank/tile tables.

    Returns byte provenance as well as raw and AI-normalized classes. Some
    coordinates land on metadata, not playable map cells; this is explicit.
    Normal movement gate requires x<31,y<20 and skips the attribute row15.
    """
    if len(chunk_ids)!=4:raise ValueError('Four chunk IDs required')
    if any(not 0<=chunk<=119 for chunk in chunk_ids):
        raise ValueError('Validated original map chunk domain: 0..119')
    x&=255;y&=255
    quadrant=int(x>=16)|2*int(y>=16);chunk=chunk_ids[quadrant]&255
    po=0x117DB+2*chunk
    cpu_pointer=int.from_bytes(rom[po:po+2],'little')
    register_value=rom[0x118CB+chunk]
    bank=(register_value&63)%32
    cell_index=((y<<4)&255)|(x&15)
    offset=16+bank*8192+cpu_pointer-0x8000+cell_index
    tile=rom[offset]
    raw_class=rom[0x1175B+tile] if tile<128 else 0
    return {'x':x,'y':y,'quadrant':quadrant,'chunk_id':chunk,
            'tile_rom_offset':offset,'tile_id':tile,'raw_class':raw_class,
            'ai_class':raw_class if raw_class<6 else 2,
            'valid_battle_cell':x<31 and y<20 and y!=15,
            'attribute_or_unused_row':y>=20 or y==15,
            'physical_pixel_x':x*16,'physical_pixel_y':(y-int(y>=16))*16}

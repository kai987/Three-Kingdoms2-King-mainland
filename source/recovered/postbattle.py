"""Readable battle-result officer allocation, reconstructed from this ROM.

The gameplay APIs implement bank8 BC46 and bank13 postbattle writes directly.
No original instructions execute here. Renderer/text/controller jobs are events
and explicit inputs to PostbattleEngine, not automatically completed services.
"""
from dataclasses import dataclass
import hashlib

ROM_SHA256='26c8d921ff5c208191f136480bcd8d7e89c2e4ed40a0ac7b51482bcb52fe2b82'
MAIN,SUB=0x0500,0x0501
UNAFFILIATED_DESTINATION=30
UNAFFILIATED_DESTINATION_ORIGINAL_NAME='ざいや'  # Native glyphs plus selector30
UNAFFILIATED_DESTINATION_CHINESE='转为在野/解除归属'
CITY_BASE,OFFICER_BASE,RULER_BASE=0x6000,0x63C0,0x6F07

class MissingPostbattleInput(RuntimeError): pass

@dataclass(frozen=True)
class PostbattleData:
    adjacency:bytes
    rng_table:bytes
    @classmethod
    def from_rom(cls,rom):
        if hashlib.sha256(rom).hexdigest()!=ROM_SHA256:raise ValueError('Wrong ROM identity')
        return cls(rom[0x21D82:0x21E82],rom[0x3E8CA:0x3E9CA])
    def rng_byte(self,memory):
        value=self.rng_table[memory[0x50]];memory[0x50]=(memory[0x50]+1)&255
        return value
    def neighbor_byte(self,city,slot):return self.adjacency[((city<<3)+slot)&255]


def city_address(city):return CITY_BASE+32*city

def officer_address(officer):return OFFICER_BASE+12*officer

def side_ruler(memory,side=None):
    side=memory[0x0504] if side is None else side
    return memory[0x0507]>>4 if side&128 else memory[0x0507]&15

def ruler_leader(memory,ruler):
    if not 0<=ruler<7:raise ValueError('Only seven F379 ruler pointers are proven')
    return memory[RULER_BASE+8*ruler]


def first_city_vacancy(memory,city):
    """Bank12 BC11: returns city-record offset17..26, or27 when full."""
    address=city_address(city)
    return next((offset for offset in range(17,27) if memory[address+offset]==255),27)


def remove_battle_reference(memory,officer):
    """Bank13 D299: erase first active slot, otherwise first captive entry.

    It does not change the officer record, erase every alias, compact a roster,
    or adjust attack-animation slot caches04D8/04DC.
    """
    for slot in range(20):
        if memory[0x0664+slot]==officer:
            for base in (0x0600,0x0614,0x0628,0x063C,0x0650,0x0664):memory[base+slot]=255
            return {'kind':'remove_active_reference','officer':officer,'slot':slot}
    for index in range(40):
        if memory[0x6F47+index]==officer:
            memory[0x6F47+index]=255
            return {'kind':'remove_captive_reference','officer':officer,'index':index}
    return {'kind':'no_reference','officer':officer}


def collect_ai_officers(memory):
    """Bank8 BDCD..BE54: original half first, transferred other-half second.

    The active-side list excludes sidebyteFF, but deliberately does NOT reject
    officerIDFF in otherwise active slots. Such inconsistent input inserts an
    early list terminator just as the original does. Captive arrays follow.
    """
    sign=memory[0x0504]&128;start=10 if sign else 0;other=0 if sign else 10
    ids=[]
    for first in (start,other):
        for slot in range(first,first+10):
            packed=memory[0x0628+slot]
            if packed!=255 and packed&128==sign:ids.append(memory[0x0664+slot])
    captured=0x6F5B if sign else 0x6F47
    ids.extend(memory[captured+i] for i in range(20) if memory[captured+i]!=255)
    for i,officer in enumerate(ids):memory[0x6FA1+i]=officer
    # A do-while fill: one terminator is written even if list length>=21.
    for i in range(len(ids),max(21,len(ids)+1)):memory[0x6FA1+i]=255
    return ids


def prioritize_commander(memory):
    """Bank8 BE55: swap the original side's commander into6FA1[0]."""
    slot=10 if memory[0x0504]&128 else 0;officer=memory[0x0664+slot]
    if officer==255:return None
    for i in range(20):
        if memory[0x6FA1+i]==officer:
            memory[0x6FA1],memory[0x6FA1+i]=memory[0x6FA1+i],memory[0x6FA1]
            return i
    return None


def ai_neighbor_cities(memory,data):
    """Bank8 BE90: same ruler or owner7, in original8-byte adjacency order."""
    for i in range(11):memory[0x042C+i]=memory[0x0550+i]=255
    ruler=side_ruler(memory);city=memory[0x050E];eligible=[]
    for i in range(8):
        candidate=data.neighbor_byte(city,i)
        if candidate&128:break
        owner=memory[city_address(candidate)]&7
        if owner not in (ruler,7):continue
        occupied=first_city_vacancy(memory,candidate)-17
        index=len(eligible);memory[0x042C+index]=candidate;memory[0x0550+index]=occupied
        eligible.append((candidate,occupied))
    return eligible


def process_ai_officers(memory,mode=None,*,data):
    """Bank8 BC46 three real dispositions, preserving original odd edges.

    mode0: winner fills current city, then nonempty eligible neighboring cities,
      then empty neighboring cities, then releases overflow.
    mode1: defeated defender allocates only to neighboring cities.
    mode2: defeated attacker first uses vacancies in source city052A.

    This does not recruit a record or set its status2. Roster-assigned records
    retain their previous packed state/location. Only overflow gets status0 and
    a random neighboring byte5; first special comparison is rulerID and gets low2=3; after a release,
    scratch02 becomes city*8, so later matching officer IDs also get3. A neutral
    EMPTY city filled here has its entire owner byte replaced by ruler ID.
    """
    mode=memory[0x6F91] if mode is None else mode
    if mode not in (0,1,2):raise ValueError('BC46 has exactly three proven entries')
    collect_ai_officers(memory);events=[]
    if mode in (1,2):prioritize_commander(memory)
    # BC46's EADE dispatcher writes target high byte to scratch04. Mode2
    # does not reset it when source city is FULL: this is $BD, not0.
    # Preserve even that anomalous original fallback, including its raw reads.
    if mode==2:memory[4]=0xBD
    cursor=memory[4] if mode==2 else 0
    def fill(city,offset):
        nonlocal cursor
        address=city_address(city)
        while offset<27:
            officer=memory[0x6FA1+cursor]
            if officer==255:return False
            if officer==memory[0x052B]:memory[0x052C]=city
            memory[address+offset]=officer
            events.append({'kind':'city_roster_write','city':city,'offset':offset,'officer':officer})
            cursor=(cursor+1)&255;offset+=1
        if memory[0x6FA1+cursor]==255:return False
        memory[4]=cursor
        return True
    if mode==0:
        cursor=0;memory[4]=0
        if not fill(memory[0x050E],17):return {'mode':mode,'events':events,'overflow':[]}
    elif mode==1:memory[4]=0;cursor=0
    else:
        vacancy=first_city_vacancy(memory,memory[0x052A])
        if vacancy<27:
            cursor=0;memory[4]=0
            if not fill(memory[0x052A],vacancy):return {'mode':mode,'events':events,'overflow':[]}
    neighbors=ai_neighbor_cities(memory,data)
    for city,occupied in neighbors:
        if occupied in (0,10):continue
        if not fill(city,17+occupied):return {'mode':mode,'events':events,'overflow':[]}
    ruler=side_ruler(memory)
    for city,occupied in neighbors:
        if occupied!=0:continue
        more=fill(city,17)
        if memory[city_address(city)+17]!=255:
            memory[city_address(city)]=ruler
            events.append({'kind':'whole_city_owner_write','city':city,'owner':ruler})
        if not more:return {'mode':mode,'events':events,'overflow':[]}
    comparison_id=ruler_leader(memory,ruler);overflow=[]
    while True:
        officer=memory[0x6FA1+cursor]
        if officer==255:break
        address=officer_address(officer)
        if officer==comparison_id:
            memory[address+11]|=3
            events.append({'kind':'overflow_special_match_status3','officer':officer,'comparison_id':comparison_id})
        else:
            memory[address+11]&=252
            # BD3E overwrites scratch02 (initially the ruler's ID) with the
            # adjacency-row base. Later CMP02 therefore uses this row byte.
            comparison_id=(memory[0x050E]<<3)&255
            destination=data.neighbor_byte(memory[0x050E],data.rng_byte(memory)&7)
            if destination&128:destination=memory[0x050E]
            memory[address+5]=destination
            events.append({'kind':'overflow_status0_location','officer':officer,'city':destination})
        overflow.append(officer);cursor=(cursor+1)&255
    return {'mode':mode,'events':events,'overflow':overflow}


def build_postbattle_roster(memory):
    """Bank13 D0E1: all20 matching-side slots then matching20 captive entries.

    Active sidebyteFF is not explicitly rejected here; a non-FF officer there
    is included for high side. This differs from collect_ai_officers.
    """
    for i in range(33):memory[0x0580+i]=255
    memory[0x050A]=255
    for i in range(32):memory[0x042C+i]=255
    sign=128 if memory[0x050B]&16 else 0;ids=[]
    for slot in range(20):
        officer=memory[0x0664+slot]
        if officer!=255 and memory[0x0628+slot]&128==sign:ids.append(officer)
    base=0x6F5B if sign else 0x6F47
    ids.extend(memory[base+i] for i in range(20) if memory[base+i]!=255)
    for i,officer in enumerate(ids):memory[0x042C+i]=officer
    memory[0x042C+len(ids)]=254
    return ids


def human_neighbor_cities(memory,data):
    """Bank12 BB84: city menu plus original occupancy packet scratch."""
    memory[0x050A]=255
    for i in range(64):memory[0x042C+i]=255
    for i in range(16):memory[0x0550+i]=255
    ruler=side_ruler(memory);result=[]
    for i in range(8):
        city=data.neighbor_byte(memory[0x050E],i)
        if city&128:break
        if memory[city_address(city)]&7 not in (ruler,7):continue
        index=len(result);memory[0x050A]=index;memory[0x042C+index]=city
        occupancy=first_city_vacancy(memory,city)-17
        packet=0x20+3*index
        memory[0x042C+packet]=occupancy;memory[0x042D+packet]=memory[0x042E+packet]=0
        memory[0x0550+index]=occupancy;result.append((city,occupancy))
    return result


def context_leader(memory):
    """Bank13 D0C3: 050B high nibble selects the high ruler in0507."""
    leader=ruler_leader(memory,memory[0x0507]>>4 if memory[0x050B]&240 else memory[0x0507]&15)
    memory[0x044C]=leader
    return leader


def toggle_officer_selection(memory):
    """Bank13 D167: A toggles, destination cap10, ruler cannot be released."""
    selected_count=sum(memory[0x0580+i]!=255 for i in range(32))
    index=memory[0x0508]
    if not memory[0x81]&1 or index==memory[0x050A]:return False
    if memory[0x0580+index]==0:memory[0x0580+index]=255;return True
    if memory[0x0540]==30:
        if context_leader(memory)==memory[0x042C+index]:return False
    elif ((9-memory[0x0550+memory[0x0541]])&255)<selected_count:return False
    memory[0x0580+index]=0
    return True


def apply_selected_officers(memory,*,data):
    """Bank13 D1F9/D20D: selected first20 entries to city or release option30."""
    events=[]
    for index in range(20):
        if memory[0x0580+index]&128:continue
        officer=memory[0x042C+index];destination=memory[0x0540]
        if destination==30:
            address=officer_address(officer);memory[address+11]&=252
            city=data.neighbor_byte(memory[0x050E],data.rng_byte(memory)&7)
            if city&128:city=memory[0x050E]
            memory[address+5]=city
            events.append({'kind':'release_status0_location','officer':officer,'city':city})
        else:
            offset=first_city_vacancy(memory,destination)
            memory[city_address(destination)+offset]=officer
            if officer==memory[0x052B]:memory[0x052C]=destination
            if memory[city_address(destination)]&7==7:
                ruler=memory[0x0507]>>4 if memory[0x050B]&240 else memory[0x0507]&15
                memory[city_address(destination)]=(memory[city_address(destination)]&240)|ruler
            events.append({'kind':'city_roster_write','city':destination,'offset':offset,'officer':officer})
        events.append(remove_battle_reference(memory,officer))
    return events


def accept_remaining_current_city(memory):
    """Bank13 D48D/D4A3: first20 list entries, no packed-status write."""
    events=[];city=memory[0x050E]
    for index in range(20):
        officer=memory[0x042C+index]
        if officer==255:continue
        offset=first_city_vacancy(memory,city);memory[city_address(city)+offset]=officer
        events.append({'kind':'city_roster_write','city':city,'offset':offset,'officer':officer})
        events.append(remove_battle_reference(memory,officer))
    return events


def release_all_without_destination(memory):
    """Bank13 CD9C..CDEF: nonleader status0/currentcity; leader status3.

    Unlike the selectable release option, this does not pick random neighbors,
    and does not remove active/captive reference arrays in its own body.
    """
    ruler=memory[0x0507]&15 if memory[0x050B]==2 else memory[0x0507]>>4
    leader=ruler_leader(memory,ruler);ids=build_postbattle_roster(memory);events=[]
    for officer in ids:
        if officer>=254:break
        address=officer_address(officer)
        if officer==leader:
            memory[address+11]|=3;events.append({'kind':'ruler_status3','officer':officer})
        else:
            memory[address+11]&=252;memory[address+5]=memory[0x050E]
            events.append({'kind':'status0_location','officer':officer,'city':memory[0x050E]})
    memory[MAIN],memory[SUB]=15,memory[0x050B]&15
    return events


class PostbattleEngine:
    """Readable main13/14 controller with explicit asynchronous UI inputs.

    `text_ready` is supplied by the caller's message/animation service. Destination
    and officer-grid stages also require `cursor_index`, supplied by its controller
    service. Output events request drawing/messages; they never imply those jobs
    completed. Gameplay writes below are independent source, not ROM stubs.
    """
    def __init__(self,memory,*,data):self.memory=memory;self.data=data
    def _return_to_parent(self):
        self.memory[MAIN],self.memory[SUB]=15,self.memory[0x050B]&15
    def _init(self,events):
        memory=self.memory;ids=build_postbattle_roster(memory);count=len(ids)
        memory[0x042C+count]=255
        if memory[MAIN]==14:
            memory[0x050A]=count
            if count<11:
                events.extend(accept_remaining_current_city(memory));self._return_to_parent();return
        elif count==0:self._return_to_parent();return
        events.append({'kind':'message','id':0xDF if memory[MAIN]==14 else 0xDC,'queue':'F293'})
        context_leader(memory);memory[SUB]=1
    def _finish_selection(self,events):
        memory=self.memory
        memory[0xE6]=memory[0xE7]=0xE1;memory[0x8E]=0;memory[0x90]=0x50;memory[SUB]=0
        events.extend(apply_selected_officers(memory,data=self.data));self._init(events)
    def step(self,*,text_ready=None,cursor_index=None):
        memory=self.memory;main,sub=memory[MAIN],memory[SUB];before=(main,sub);events=[]
        if main not in (13,14):raise ValueError('PostbattleEngine handles main13/14 only')
        if not 0<=sub<7:raise ValueError('Each main has exactly seven substates')
        if sub<=4:events.append({'kind':'draw_ruler_units'})
        if sub==0:self._init(events)
        elif sub in (1,2,3,4,6):
            if text_ready is None:raise MissingPostbattleInput('text_ready is required for this cooperative stage')
            if sub==2:
                if cursor_index is None:raise MissingPostbattleInput('Destination cursor_index requires a controller result')
                memory[0x12]=cursor_index&255
                events.append({'kind':'draw_destination_cursor','index':cursor_index})
                if text_ready and memory[0x81]&1:
                    destination=memory[0x042C+cursor_index]
                    memory[0x0540],memory[0x0541]=destination,cursor_index
                    if destination==30 or memory[0x0550+cursor_index]<10:
                        memory[SUB]=3;events.append({'kind':'message','id':0xE5 if destination==30 else 0xDD,'queue':'F283'})
                        context_leader(memory)
            elif sub==4:
                if text_ready:
                    memory[0x042C+memory[0x050A]]=255;memory[0xE6]=memory[0xE7]=0xE0
                    memory[SUB]=5;memory[0x8E]=memory[0x90]=0
                    if main==13:memory[0x0424]=memory[0x0425]=0
            elif text_ready and memory[0x81]&1:
                events.append({'kind':'dialog_highlight'})
                if sub==1:
                    memory[SUB]=2;memory[0x0424]=memory[0x0425]=0
                    memory[0x0504]=(memory[0x050B]&16)<<3
                    neighbors=human_neighbor_cities(memory,self.data)
                    memory[0x050A]=(memory[0x050A]+1)&255
                    if main==14 or neighbors:
                        memory[0x042C+memory[0x050A]]=30
                    if main==13 and not any(count<10 for city,count in neighbors):
                        events.extend(release_all_without_destination(memory))
                    else:events.append({'kind':'message','id':0xD7,'queue':'F283'})
                elif sub==3:
                    ids=build_postbattle_roster(memory);memory[0x050A]=len(ids)
                    if main==14:memory[0x0424]=memory[0x0425]=0
                    events.append({'kind':'message','id':0xDE,'queue':'F28B'});memory[SUB]=4
                elif sub==6:self._finish_selection(events)
        else:
            if cursor_index is None:raise MissingPostbattleInput('Officer-grid cursor_index requires a controller result')
            memory[0x12]=cursor_index&255;memory[0x0508]=cursor_index&255
            toggle_officer_selection(memory)
            events.append({'kind':'draw_selected_officers','indices':[i for i in range(20) if not memory[0x0580+i]&128]})
            if memory[0x81]&1 and memory[0x050A]==memory[0x0508]:
                selected=sum(not memory[0x0580+i]&128 for i in range(20))
                if selected:
                    events.append({'kind':'message','id':0xE6 if memory[0x0540]==30 else 0xD8,'queue':'F283'});memory[SUB]=6
                else:self._finish_selection(events)
        return {'before':before,'after':(memory[MAIN],memory[SUB]),'events':events}


def remove_inactive_unit_slot(memory,slot=None):
    """Bank9 D6CD..D70E, also bank8 A02A: remove battle membership.

    Health-zero tactic writer B60D sets record status3 before calling this.
    This helper itself changes no officer record/captive array: it clears six
    active arrays plus6FA1[slot], then the first matching attack-cache quartet.
    """
    slot=memory[0] if slot is None else slot
    if not 0<=slot<20:raise ValueError('Only active slot0..19 is a proven domain')
    for base in (0x0600,0x0614,0x0628,0x063C,0x0650,0x0664,0x6FA1):memory[base+slot]=255
    cache=0x04D8 if memory[0x04D8]==slot else 0x04DC if memory[0x04DC]==slot else None
    if cache is not None:
        for i in range(4):memory[cache+i]=255
    return {'slot':slot,'attack_cache':cache}

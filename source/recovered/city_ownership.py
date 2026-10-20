"""Independent city-owner and roster/resource transaction cores from this ROM.

These are gameplay algorithms, not original source or CPU/ROM adapters. Original
bank/pointer/stack protocols and strategic selection/UI are explicit outside
work. Existing battle/officer algorithms are composed as pure source, not copied.
"""
from dataclasses import dataclass
from .officer_transfer import OfficerTransfer,TransferData,ROM_SHA256,UnboundedOriginalScan
CITY,OFFICER,RULER=0x6000,0x63C0,0x6F07

def u8(v):return v&255
def word(m,a):return m[a]|m[a+1]<<8
def store_word(m,a,v):m[a]=v&255;m[a+1]=(v>>8)&255
def city_address(city):
    if not 0<=city<30:raise ValueError('Proven cities0..29')
    return CITY+32*city

def ruler_address(ruler):
    if not 0<=ruler<7:raise ValueError('Proven rulers0..6')
    return RULER+8*ruler

def officer_address(officer):
    if not 0<=officer<237:raise ValueError('Proven officers0..236')
    return OFFICER+12*officer

@dataclass(frozen=True)
class OwnershipData:
    adjacency:bytes
    transfer:TransferData
    @classmethod
    def from_rom(cls,rom):return cls(bytes(rom[0x21D82:0x21E82]),TransferData.from_rom(rom))
    def neighbors(self,city):
        start=u8(city*8)
        for i in range(256):
            value=self.adjacency[u8(start+i)]
            if value&128:return
            yield value
        raise UnboundedOriginalScan('Original adjacency scan lacks a high-bit terminator')

class CityOwnership:
    def __init__(self,memory,data):self.memory,self.data=memory,data;self.transfer=OfficerTransfer(memory,data.transfer)
    def _vacancy(self,address,start=17):
        for i in range(256):
            offset=u8(start+i)
            if self.memory[address+offset]==255:return offset
        raise UnboundedOriginalScan('Original unbounded Y vacancy scan has noFF')
    def _prefix_count(self,city):
        a=city_address(city)
        return next((i for i in range(10)if self.memory[a+17+i]==255),10)
    def _owner_write(self,city,ruler,mask):
        a=city_address(city);old=self.memory[a];self.memory[a]=(old&mask)|ruler
        return {'city':city,'before':old,'after':self.memory[a],'preservation_mask':mask}
    def commit_ai_capture(self,city,ruler,*,branch_zero):
        """10 A8FC..A90C, stopbeforeD249/CA19; only zero6F8C branch."""
        if not branch_zero:raise ValueError('A8FC commit is entered only on6F8C==0')
        ruler_address(ruler);self.transfer.cap_city_resources(city)
        return self._owner_write(city,ruler,248)
    def relocate_after_ai_battle(self,combat_city,officer,ruler,*,adjust_capture_loyalty):
        """10 ABA3..AC66: smallest ownprefix city; lastneutral; else release.

        Does not erase an existing roster, set status2, update ruler residence,
        or complete the caller's active-array removal. Argumentflag corresponds
        to0042==0. Releasing samples E89A/cursor54 and never chooses neighbor7.
        """
        city_address(combat_city);officer_address(officer);ruler_address(ruler)
        m=self.memory;own=None;best=255;neutral=None
        for city in self.data.neighbors(combat_city):
            owner=self.transfer.cap_city_resources(city)
            if owner==7:neutral=city
            elif owner==ruler:
                count=self._prefix_count(city)
                if count<10 and count<best:own=city;best=count
        destination=own if own is not None else neutral
        if destination is not None:
            address=city_address(destination);self.transfer.cap_city_resources(destination)
            slot=self._vacancy(address);m[address+slot]=officer
            ownership=self._owner_write(destination,ruler,248)
            loyalty=self.transfer.loyalty_after_capture(officer)if adjust_capture_loyalty else None
            return {'destination':destination,'roster_offset':slot,'choice':'own_minimum_prefix'if own is not None else'last_neutral_neighbor','owner_write':ownership,'loyalty':loyalty,'ruler_residence_unchanged':True}
        record=officer_address(officer);m[record+11]&=252;draws=[]
        while True:
            sample=self.transfer.data.rng[m[0x54]];m[0x54]=u8(m[0x54]+1);roll=sample&7;draws.append(sample)
            if roll==0:location=combat_city;break
            location=self.data.adjacency[u8(combat_city*8+roll-1)]
            if not location&128:break
        m[record+5]=location;m[0x2D]=255
        return {'destination':None,'status_low2':0,'location':location,'raw_rng_draws':draws,'neighbor_selector':'roll0=currentcity;roll1..7=neighbors0..6'}
    def colonize_city(self,source,destination,ruler,*,gold,grain,allocation_base_count):
        """10 B287..B356 core: pay/add supplies, move highloyal followers, claim.

        Prior B180/B1FD targetselection, affordability/amount selection are
        external. Validated inputallocationbase3..10, and at leastcount-2 eligible
        records beyondslot17. Highestloyalty, late tie; governor17 excluded.
        Firstdestination slots are overwritten, not appended. Status/location
        and ruler residence are untouched. Aliases preserve sequential effects.
        """
        if not 3<=allocation_base_count<=10:raise ValueError('Proven colonization allocationbase3..10')
        ruler_address(ruler);src=city_address(source);dst=city_address(destination);m=self.memory
        self.transfer.cap_city_resources(source)
        store_word(m,src+2,word(m,src+2)-(gold&65535));self.transfer.cap_city_resources(source)
        store_word(m,src+4,word(m,src+4)-(grain&65535));self.transfer.cap_city_resources(source)
        self.transfer.cap_city_resources(destination)
        store_word(m,dst+2,word(m,dst+2)+(gold&65535));store_word(m,dst+4,word(m,dst+4)+(grain&65535))
        self.transfer.cap_city_resources(destination);self.transfer.cap_city_resources(source)
        m[0x37]=u8(allocation_base_count-2);moved=[]
        for i in range(m[0x37]):
            best=0;chosen=None
            for offset in range(18,27):
                officer=m[src+offset]
                if officer!=255 and m[officer_address(officer)+3]>=best:chosen=offset;best=m[officer_address(officer)+3]
            if chosen is None:raise ValueError('Original would read sourceoffsetFF: insufficient eligible followers')
            officer=m[src+chosen];m[src+chosen]=255;m[dst+17+i]=officer;moved.append(officer)
        self.transfer.compact_city_roster(source,buffer=0x6F73,cap_resources=True)
        ownership=self._owner_write(destination,ruler,248)
        return {'source':source,'destination':destination,'moved':moved,'owner_write':ownership,'ruler_residence_unchanged':True,'prior_selection_and_affordability_external':True}
    def withdraw_city(self,source,destination):
        """10 B3B1..B42A; stopbeforeD152 AP/unwind andB17D nextcycle.

        Add fullwords withwrap and NO finaldestination cap. Clears source
        supplies. Move prefix untilfirstFF, inserting at successive unbounded
        vacancies; neutralize source withF8|7. Return actualcost4+2*count.
        Strategy choosing source and first ownneighbor is outside this core.
        """
        src=city_address(source);dst=city_address(destination);m=self.memory
        self.transfer.cap_city_resources(destination);self.transfer.cap_city_resources(source)
        for offset in (2,4):store_word(m,dst+offset,word(m,dst+offset)+word(m,src+offset))
        for offset in range(2,6):m[src+offset]=0
        moved=[];cursor=17
        for offset in range(17,27):
            officer=m[src+offset]
            if officer==255:break
            m[src+offset]=255
            vacancy=self._vacancy(dst,cursor);cursor=u8(vacancy+1);m[dst+vacancy]=officer;moved.append(officer)
        ownership=self._owner_write(source,7,248);m[0x26]=u8(4+2*len(moved))
        return {'source':source,'destination':destination,'moved':moved,'owner_write':ownership,'pending_ai_budget_cost':m[0x26],'source_equals_destination':source==destination,'destination_resources_not_finally_capped':True}
    def transfer_persuaded_officer(self,source,destination,officer,ruler):
        """10 BA8D..BAE1; stopbeforeformer-ruler reaction atBAE2.

        A real cross-city membership transaction. Destinationowner stays
        unchanged, so caller must supply a destinationowned bynewruler. Append,
        adjust loyalty, erase firstsource match, compact, wholebyte7 ifempty.
        Does not change officerstatus/byte5, rulerleader/residence, or diplomacy.
        """
        src=city_address(source);dst=city_address(destination);officer_address(officer);leader=self.memory[ruler_address(ruler)];m=self.memory
        self.transfer.cap_city_resources(destination);slot=self._vacancy(dst);m[dst+slot]=officer
        m[0x30]=leader;m[0x31]=officer;loyalty=self.transfer.loyalty_for_recruitment(leader,officer)
        old_owner=self.transfer.cap_city_resources(source);m[0x42]=old_owner
        offset=self.transfer._find_byte(src,officer);m[src+offset]=255
        remaining=self.transfer.compact_city_roster(source,buffer=0x6F73,cap_resources=True)
        self.transfer.cap_city_resources(source)
        if not remaining:m[src]=7
        return {'source':source,'destination':destination,'officer':officer,'old_ruler':old_owner,'new_ruler':ruler,'destination_offset':slot,'remaining_source':remaining,'loyalty':loyalty,'pending_former_ruler_reaction_entry':0xBAE2}
    def finish_empty_city_action(self,city,*,action_mode):
        """28 D16B..D182 afterUI prerequisites: mode2 + FIRSTslotFF =>whole7.

        city is original0471. No assertion that it is migration's source or
        destination without proving that menu route. Later occupiedholes do
        not preventneutralization. D183 cursor/UI tail is external.
        """
        address=city_address(city);m=self.memory;old=m[address]
        if action_mode==2 and m[address+17]==255:m[address]=7
        return {'city':city,'before':old,'after':m[address],'changed':m[address]!=old,'first_slot_empty':m[address+17]==255,'action_mode':action_mode}
    def finalize_battle_ownership(self):
        """Compose previously recovered8BBB8 pure algorithm, includingchiefswaps.

        This method addsno new claim for old source; outcome0 F0-mask capture
        differs fromAI A90B'sF8-mask. City/neighbors chiefswaps do NOT write ruler
        residence. Native BC00 readsowner&0F, so normalbit3-clear ownersrequired.
        """
        from .battle_state_machine import finalize_city_ownership
        return finalize_city_ownership(self.memory,self.data.adjacency)

    def retreat_unit_to_city(self,slot,city):
        """12 BC2D..BC92, excluding priorC91E helper atBC2A.

        Append at firstFF (offset27 when full), clear six battlearrays and
        matching04D8/04DC cachedslot references. Commander slots0/10 set escape
        officer052B/city052C. Neutralcity owner&7==7 becomesF0|side-ruler.
        No officerrecord/status, supplies, chiefswap or residence write here.
        """
        if not 0<=slot<20:raise ValueError('Proven battle slots0..19')
        address=city_address(city);m=self.memory;officer=m[0x664+slot]
        offset=next((i for i in range(17,27)if m[address+i]==255),27)
        if slot in (0,10):m[0x52B]=officer;m[0x52C]=city
        m[address+offset]=officer
        for base in (0x600,0x614,0x628,0x63C,0x650,0x664):m[base+slot]=255
        for cache in (0x4D8,0x4DC):
            if m[cache]==slot:m[cache]=255
        ownership=None
        if m[address]&7==7:
            ruler=(m[0x507]>>4)if m[0x504]&128 else(m[0x507]&15)
            ruler_address(ruler);ownership=self._owner_write(city,ruler,240)
        return {'slot':slot,'officer':officer,'city':city,'roster_offset':offset,'owner_write':ownership,'commander_escape_saved':slot in (0,10),'preceding_C91E_helper_external':True}

"""Recovered loyalty, roster movement/recruitment and ruler succession rules.

These are independent game-memory algorithms, not ROM-code adapters or an NES
emulator. CPU stack/pointer/mapper protocol is external. Reported A and C/V/N/Z flags
for the three loyalty endpoints are explicit; other methods preserve branches
and byte arithmetic but do not claim their full CPU register/flag side effects.
Scene acknowledgements/text are returned as pending work and never auto-finish.
"""
from dataclasses import dataclass
import hashlib

ROM_SHA256='26c8d921ff5c208191f136480bcd8d7e89c2e4ed40a0ac7b51482bcb52fe2b82'
CITY,OFFICER,RULER=0x6000,0x63C0,0x6F07

class UnboundedOriginalScan(RuntimeError):pass

def u8(value):return value&255
def city_address(city):return CITY+32*(city&255)
def officer_address(officer):return OFFICER+12*(officer&255)
def ruler_address(ruler):
    if not 0<=ruler<7:raise ValueError('Only seven ruler records are proven')
    return RULER+8*ruler
def sbc_overflow(left,right):return bool((left^right)&(left^u8(left-right))&128)


@dataclass(frozen=True)
class TransferData:
    families:tuple
    rng:bytes
    @classmethod
    def from_rom(cls,rom):
        if hashlib.sha256(rom).hexdigest()!=ROM_SHA256:raise ValueError('Wrong ROM')
        prg=rom[16+11*8192:16+12*8192];families=[]
        for i in range(7):
            address=int.from_bytes(prg[0xAD8+2*i:0xADA+2*i],'little')
            values=[]
            for j in range(256):
                value=prg[address-0xC000+j]
                if value==255:break
                values.append(value)
            else:raise ValueError('Unterminated family data')
            families.append(tuple(values))
        return cls(tuple(families),bytes(rom[0x3E8CA:0x3E9CA]))


class OfficerTransfer:
    """Shared-memory high-level rules, with explicitly bounded entry scopes."""
    def __init__(self,memory,data):self.memory,self.data=memory,data;self.draws=[]
    def field(self,officer,offset):return self.memory[officer_address(officer)+offset]
    def rng100(self,cursor_address=0x52):
        # D4BB uses E88A/cursor1; the player succession path uses E843/cursor0.
        while True:
            cursor=self.memory[cursor_address];value=self.data.rng[cursor]
            self.memory[cursor_address]=u8(cursor+1)
            self.draws.append({'cursor_address':cursor_address,'cursor':cursor,'value':value})
            if value<100:return value

    def loyalty_for_recruitment(self,new_leader,officer):
        """Physical10 A006→11 CF3F: only byte3, not political membership."""
        base=70+self.field(new_leader,4)//10
        old=self.field(officer,3);raw=u8(base-old);upper=min(raw,90)
        value=max(upper,10);self.memory[officer_address(officer)+3]=value
        return {'value':value,'cpu_a':value,'before':old,'raw_subtraction':raw,'changed':value!=old,
                'cpu_flags':{'C':upper>=10,'V':sbc_overflow(base,old),'N':False,'Z':False}}

    def loyalty_after_leader_change(self,new_leader,officer,ruler,old_leader):
        """A009→CF7C: family exemption, virtue delta and wrapped loyalty."""
        if not 0<=ruler<7:raise ValueError('Only seven family lists are proven')
        old=self.field(officer,3)
        if new_leader in self.data.families[ruler]:
            return {'value':old,'cpu_a':new_leader&255,'before':old,'changed':False,'family_exempt':True,
                    'cpu_flags':{'C':True,'V':'preserved','N':False,'Z':True}}
        delta=self.field(new_leader,4)//5-self.field(old_leader,4)//5
        adjusted=u8(old+delta) if delta>=0 else max(old+delta,0)
        after_penalty=max(adjusted-10,0);upper=min(after_penalty,99)
        value=max(upper,10);self.memory[officer_address(officer)+3]=value
        return {'value':value,'cpu_a':value,'before':old,'changed':value!=old,'family_exempt':False,
                'virtue_delta':delta,'wrapped_adjusted':adjusted,
                'cpu_flags':{'C':upper>=10,'V':sbc_overflow(adjusted,10),'N':False,'Z':False}}

    def loyalty_after_capture(self,officer):
        """A00C→D00C: normalize byte3 around50; does not remove any roster."""
        old=self.field(officer,3);distance=abs(50-old)
        before_min=max(51-distance,0);value=max(before_min,10)
        self.memory[officer_address(officer)+3]=value
        return {'value':value,'cpu_a':value,'before':old,'changed':value!=old,'distance_from50':distance,
                'cpu_flags':{'C':before_min>=10,'V':sbc_overflow(51,distance),'N':False,'Z':False}}

    def cap_city_resources(self,city):
        """D105 always calls D69D; preserve this scan-time side effect."""
        m=self.memory;address=city_address(city)
        for offset in (2,4):
            value=m[address+offset]|m[address+offset+1]<<8
            if value>=10000:m[address+offset]=15;m[address+offset+1]=39
        return m[address]&7

    def compact_city_roster(self,city,*,buffer=0x0580,buffer_size=16,cap_resources=False):
        """BD86 or D3DD: pack all nonFF among10 slots, never filter status."""
        if cap_resources:self.cap_city_resources(city)
        m=self.memory;address=city_address(city)
        for i in range(buffer_size):m[buffer+i]=255
        ids=[m[address+i] for i in range(17,27) if m[address+i]!=255]
        for i,value in enumerate(ids):m[buffer+i]=value
        for i in range(10):m[address+17+i]=m[buffer+i]
        return ids

    def delete_city_officer(self,city,slot_offset,officer):
        """25 BDBB..BE00: status3, selected-slot erase, compact, empty owner7."""
        m=self.memory;address=city_address(city);record=officer_address(officer)
        m[record+11]|=3;m[address+(slot_offset&255)]=255
        ids=self.compact_city_roster(city)
        if not ids:m[address]=(m[address]&248)|7
        return {'officer':officer,'city':city,'remaining':ids,'owner_byte':m[address]}

    def release_city_officer(self,city,slot_offset,officer,*,location=None):
        """26 C099..C0E1: status0, byte5 location, left shift and empty owner7.

        The empty-city write is whole-byte7, unlike the deletion's ANDF8/OR7.
        The source method is bounded to the valid roster offsets17..26.
        """
        if not 17<=slot_offset<=26:raise ValueError('Valid roster offset17..26 required')
        m=self.memory;address=city_address(city);record=officer_address(officer)
        m[record+11]&=252;m[record+5]=city if location is None else location&255
        for offset in range(slot_offset,26):m[address+offset]=m[address+offset+1]
        m[address+26]=255
        if all(m[address+i]==255 for i in range(17,27)):m[address]=7
        m[0x0402]=u8(m[0x0402]+1);m[0x042C]=officer&255
        return {'officer':officer,'city':city,'pending_dialogue_id':0xD4,'owner_byte':m[address]}

    def _find_byte(self,address,value,start=17):
        # AD41's scans have no roster bound and Y wraps. Refuse an original
        # infinite loop after exactly one full256-byte period; do not fake success.
        for step in range(256):
            offset=u8(start+step)
            if self.memory[address+offset]==value:return offset
        raise UnboundedOriginalScan(f'Original Y scan cannot find{value} at{address:04X}')

    def move_roster_group(self,source,destination,selected=None,*,ruler_record=None):
        """27 AD41..ADF1: append, leader swap/location, source delete+compact.

        No owner, loyalty, status or officer byte5 is changed by this core.
        It does not itself enforce that cities have the same ruler. Normal UI
        supplies a terminated selected list and enough destination capacity.
        """
        m=self.memory;src=city_address(source);dst=city_address(destination)
        if selected is not None:
            if len(selected)>10:raise ValueError('At most10 selected entries')
            for i in range(10):m[0x0481+i]=selected[i]&255 if i<len(selected) else 255
        if ruler_record is None:ruler_record=m[0xEE]|m[0xEF]<<8
        ids=[]
        for i in range(10):
            value=m[0x0481+i]
            if value==255:break
            ids.append(value)
        cursor=self._find_byte(dst,255)
        for value in ids:m[dst+cursor]=value;cursor=u8(cursor+1)
        leader=m[ruler_record]
        leader_slot=next((i for i in range(17,27) if m[dst+i]==leader),None)
        if leader_slot is not None:
            m[dst+17],m[dst+leader_slot]=m[dst+leader_slot],m[dst+17]
            m[ruler_record+1]=destination&255
        for value in ids:m[src+self._find_byte(src,value)]=255
        remaining=self.compact_city_roster(source,buffer=0x0481,buffer_size=10)
        return {'moved':ids,'source_remaining':remaining,'leader_slot_before_swap':leader_slot,
                'source_equals_destination':source==destination}

    def recruit_officer(self,city,officer):
        """27 ACF0..AD36: roster count index, status2, loyalty unless oldstatus1."""
        m=self.memory;address=city_address(city);count=sum(m[address+i]!=255 for i in range(17,27))
        # The original counts entries instead of finding the first hole. Full
        # input can overwrite offset27; normal controller disallows a full city.
        m[address+17+count]=officer&255
        owner=m[address]&15;leader=m[ruler_address(owner)]
        m[0x30]=leader;m[0x31]=officer&255
        record=officer_address(officer);old_status=m[record+11]&3
        m[record+11]=(m[record+11]&252)|2
        loyalty=None if old_status==1 else self.loyalty_for_recruitment(leader,officer)
        return {'roster_offset':17+count,'old_status':old_status,'leader':leader,
                'loyalty_adjustment':loyalty,'does_not_clear_old_rosters':True}

    def promote_city_chief(self,city,ruler):
        """11 C9A5..CA18: first loyalty100, else maxu8(loyalty+virtue), late tie."""
        m=self.memory;address=city_address(city)
        if self.cap_city_resources(city)!=ruler:return None
        chosen=None;score=0
        for offset in range(17,27):
            officer=m[address+offset]
            if officer==255:continue
            loyalty=self.field(officer,3)
            if loyalty==100:chosen=offset;break
            candidate=u8(loyalty+self.field(officer,4))
            if candidate>=score:score=candidate;chosen=offset
        if chosen is not None and chosen!=17:m[address+17],m[address+chosen]=m[address+chosen],m[address+17]
        return chosen

    def repair_ruler_city_chiefs(self,ruler):
        return [self.promote_city_chief(city,ruler) for city in range(30)]

    def choose_successor(self,ruler):
        """CA87/CAAD then CB05: family-order priority, else virtue with late ties.

        Eligibility is presence in a matching-owner city roster, NOT status/HP.
        D105 caps city resources even on cities rejected by the owner test.
        """
        m=self.memory;ruler_address(ruler)
        for family_index,officer in enumerate(self.data.families[ruler]):
            for city in range(30):
                if self.cap_city_resources(city)!=ruler:continue
                if any(m[city_address(city)+i]==officer for i in range(17,27)):
                    m[0x27]=officer
                    return {'officer':officer,'city':city,'selection':'family_order','family_index':family_index}
        chosen=255;best=0;home=None
        for city in range(30):
            if self.cap_city_resources(city)!=ruler:continue
            for offset in range(17,27):
                officer=m[city_address(city)+offset]
                if officer!=255 and self.field(officer,4)>=best:
                    best=self.field(officer,4);chosen=officer;home=city
        m[0x27]=chosen
        return {'officer':chosen,'city':home,'selection':'maximum_virtue_late_ties','virtue':best}

    def recalculate_ai_followers(self,ruler,new_leader,old_leader):
        """CB81..CC11: loyalty/release, preserving roster and tail-branch quirks.

        Released AI followers retain their roster ID: original CBDB has no
        erase-store and D3DD only packs nonFF. Early end/leader match tail-jumps
        into the caller, leaving return frames; final0045 has extra increments.
        """
        m=self.memory;m[0x30]=new_leader&255;m[0x33]=old_leader&255
        early_frames=0;changes=[]
        for city in range(30):
            m[0x0045]=city
            if self.cap_city_resources(city)!=ruler:continue
            m[0x0044]=17;early=False
            for offset in range(17,27):
                m[0x0044]=offset;officer=m[city_address(city)+offset]
                if officer in (255,new_leader):early=True;early_frames+=1;break
                m[0x31]=officer;m[0x32]=ruler
                result=self.loyalty_after_leader_change(new_leader,officer,ruler,old_leader)
                released=False
                if result['value']<31 and self.rng100()<20:
                    record=officer_address(officer);m[record+11]&=252;m[record+5]=city
                    released=True
                changes.append({'city':city,'officer':officer,'loyalty':result,'released_but_roster_retained':released})
            if early:continue
            m[0x0044]=27
            ids=self.compact_city_roster(city,buffer=0x6F73,cap_resources=True)
            self.cap_city_resources(city)
            if not ids:m[city_address(city)]=7
        m[0x0045]=u8(30+early_frames)
        return {'changes':changes,'early_tail_frames':early_frames,'final_scan_city':m[0x45]}

    def install_ai_successor(self,ruler,candidate):
        """CB52..CB78 game writes, ending at the explicit6F8B=FC UI barrier."""
        m=self.memory;address=ruler_address(ruler);old=m[address]
        m[address]=candidate&255;m[officer_address(candidate)+3]=100;m[0x27]=candidate&255
        followers=self.recalculate_ai_followers(ruler,candidate,old)
        m[0x27]=candidate&255;m[0x6F8B]=252
        return {'ruler':ruler,'old_leader':old,'new_leader':candidate,'followers':followers,
                'pending_ack_address':0x6F8B,'required_ack_value':1,
                'ruler_residence_unchanged':True}

    def resolve_ai_leader_death(self,ruler):
        """CA19/CA68 bounded decision+commit, stop before an original UI wait.

        Controller byte3 must equal3 and leader status must NOT equal2. HP is
        not the trigger. Candidate FF clears only ruler leaderID, not all city
        owners. A UI acknowledgement is explicit, never synthesized here.
        """
        m=self.memory;address=ruler_address(ruler);leader=m[address]
        if leader==255 or m[address+3]!=3:return {'handled':False,'reason':'absent_or_other_controller'}
        if self.field(leader,11)&3==2:return {'handled':False,'reason':'leader_status2'}
        m[officer_address(leader)+11]=(m[officer_address(leader)+11]&252)|3
        choice=self.choose_successor(ruler)
        if choice['officer']==255:
            m[address]=255;m[0x6F8B]=251
            return {'handled':True,'choice':choice,'pending_ack_address':0x6F8B,'required_ack_value':1,
                    'event':'no_successor','city_owners_not_globally_cleared':True}
        return {'handled':True,'choice':choice,**self.install_ai_successor(ruler,choice['officer'])}

    def set_city_chief(self,city,officer):
        """26 C101..C131: swap first matching ID into first roster slot."""
        m=self.memory;address=city_address(city)
        chosen=next((offset for offset in range(17,27) if m[address+offset]==officer),None)
        if chosen is not None:m[address+17],m[address+chosen]=m[address+chosen],m[address+17]
        return {'city':city,'officer':officer,'found_slot':chosen}

    def commit_player_successor(self,ruler,candidate,city,*,manual_choice):
        """BF85..BFA8 or C25D..C27C, ending before explicit text queue.

        Manual selection also writes ruler residence byte1 via the caller's
        EE pointer. Automatic selection does not. Caller pointer protocol is
        external; this API requires that EE identifies the supplied ruler.
        """
        m=self.memory;address=ruler_address(ruler);m[address]=candidate&255
        if manual_choice:m[address+1]=city&255
        chief=self.set_city_chief(city,candidate);m[0x0402]=u8(m[0x0402]+1);m[0x042C]=candidate&255
        if not manual_choice:m[0x04D0]=0
        return {'ruler':ruler,'candidate':candidate,'city':city,'chief':chief,
                'residence_changed':bool(manual_choice),
                'pending_dialogue_id':0xD3 if manual_choice else 0xC2}

    def recalculate_player_followers(self,ruler,new_leader,old_leader,*,process_followers,return_state):
        """26 C289..C341: optional loyalty and actual roster removal.

        Unlike CB81, owner reads do not cap resources and release does not
        write officer byte5 or clear an empty city's owner. First FF terminates
        each roster. Cursor0 advances on loyalty<31 before checking leader
        immunity. The CF7C family early return leaves $22/$23 stale: the caller
        reads and may clears status at that pointer while removing the current
        roster ID. Preserve it rather than pretending it returns a target ptr.
        Caller must supply the original valid officer-record pointer in $22/$23;
        arbitrary I/O/ROM or RAM-control aliases are outside this service.
        """
        m=self.memory;changes=[]
        if process_followers:
            for city in range(30):
                m[0x12]=city;address=city_address(city)
                if m[address]&7!=ruler:continue
                m[0x13]=17;offset=17
                while offset<27:
                    officer=m[address+offset]
                    if officer==255:break
                    m[0x30]=new_leader&255;m[0x31]=officer;m[0x32]=ruler;m[0x33]=old_leader&255
                    loyalty=self.loyalty_after_leader_change(new_leader,officer,ruler,old_leader)
                    if not loyalty['family_exempt']:
                        pointer=officer_address(officer);m[0x22]=pointer&255;m[0x23]=pointer>>8
                    pointer=m[0x22]|m[0x23]<<8
                    if loyalty['family_exempt'] and (not 0x63C0<=pointer<=0x6FC0 or (pointer-0x63C0)%12):
                        raise ValueError('Family-exempt path requires a stale officer-record pointer; arbitrary bus/control aliases are outside this high-level service')
                    # ROM uses CPU bus mirroring for RAM indirect reads/writes.
                    loyalty_address=(pointer+3)&65535
                    if loyalty_address<0x2000:loyalty_address&=2047
                    elif not 0x6000<=loyalty_address<0x8000:
                        raise ValueError('Player family early-return pointer must address RAM/SRAM; I/O and ROM bus effects are outside this semantic service')
                    read_loyalty=m[loyalty_address];released=False;draw=None
                    if read_loyalty<31:
                        draw=self.rng100(0x50)
                        if draw<20 and officer!=new_leader:
                            status_address=(pointer+11)&65535
                            if status_address<0x2000:status_address&=2047
                            elif not 0x6000<=status_address<0x8000:
                                raise ValueError('Status write through stale pointer is outside the RAM/SRAM scope')
                            m[status_address]&=252
                            for i in range(offset,26):m[address+i]=m[address+i+1]
                            m[address+26]=255;released=True
                    changes.append({'city':city,'officer':officer,'loyalty':loyalty,
                                    'loyalty_read_pointer':pointer,'loyalty_compared':read_loyalty,
                                    'rng_draw':draw,'removed_from_roster':released})
                    if not released:offset+=1
                    m[0x13]=offset
            m[0x12]=30
        m[officer_address(new_leader)+3]=100;m[0x0401]=return_state&255;m[0x0402]=0
        return {'changes':changes,'new_leader_loyalty':100,'returned_state':return_state&255,
                'processed_followers':bool(process_followers),'does_not_neutralize_empty_cities':True}

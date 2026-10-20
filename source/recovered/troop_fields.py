"""Explicit troop-word consumers and writers recovered from actual ROM code.

The low10 count is established. Upper6 bits are retained as uninterpreted raw
storage, not named training/status flags. Different real paths preserve,
discard or numerically consume them. All routines below are ordinary Python;
no original-ROM code, graphics stub or CPU instruction interpreter is called.
"""
from dataclasses import dataclass

MASK=0x03FF

@dataclass(frozen=True)
class TroopStorage:
    raw_word:int
    def __post_init__(self):object.__setattr__(self,'raw_word',self.raw_word&65535)
    @property
    def effective_count(self):return self.raw_word&MASK
    @property
    def upper6(self):return self.raw_word>>10

def low10_loss(raw_word,requested,*,preserve_upper6):
    """BA4E/B68B arithmetic; requested is the previously computed loss word."""
    raw_word&=65535;requested&=65535
    amount=min(raw_word&MASK,requested);remaining=(raw_word&MASK)-amount
    return {'raw_word':remaining|(raw_word&0xFC00 if preserve_upper6 else 0),
            'effective_count':remaining,'applied_loss':amount,'preserves_upper6':preserve_upper6}

def ai_recruitment_write(raw_word,increment):
    """Bank10 BF95..BFBA; mask after addition, then cap999, even on increment0.

    This is the proven writeback core, not its prior reserve/amount selection,
    AP deduction or monthly whole-controller tick.
    """
    updated=(raw_word+increment)&MASK
    return min(updated,999)

def attack_group_write(raw_word,groups):
    """Bank15 CA72/CAB6: sum ten non-FF bins and OR into retained high6.

    The sum's high byte is not itself masked. Abnormally large bins may therefore
    set additional upper bits; a normal group total is at most1000.
    """
    if len(groups)!=10:raise ValueError('Exactly ten attack-animation bins')
    total=sum(v&255 for v in groups if v&255!=255)&65535
    return (total&255)|((((raw_word>>8)&252)|(total>>8))<<8)

def raw_attrition_write(raw_word,loss):
    """Bank9 CE75..CE92: subtract full word; BPL on high byte clamps to0."""
    result=(raw_word-(loss&255))&65535
    return 0 if result&32768 else result

def normalize_reserve(raw_word,reserve):
    """Bank28 D987..DA01: normalize by100 against shared reserve cap10000.

    The cap adjustment subtracts only the overage's low byte from the remainder.
    Out-of-domain reserve values retain that actual byte behavior. No graphics
    are called or considered completed by this gameplay helper.
    """
    raw_word&=65535;reserve&=65535;remainder=raw_word%100
    if remainder:
        new_reserve=(reserve+remainder)&65535
        if new_reserve>=10000:
            remainder=(remainder-((new_reserve-10000)&255))&255
            new_reserve=10000
        reserve=new_reserve
    return {'raw_word':(raw_word-remainder)&65535,'reserve':reserve,'removed_remainder':remainder}

def garrison_allocation(raw_word,reserve,*,allocate):
    """Bank28 D805..D8B3 core, before numeric packet construction.

    Caller has chosen its selected roster member and a right/left action. This
    handler is not a generic idle-input tick: the parent guards its entry.
    reserve is the working042C/042D word, not yet the city's committed record.
    Full raw16 determines capacity/rounding here, unlike battlefield low10.
    """
    raw_word&=65535;reserve&=65535
    before=(raw_word,reserve);normalized=None;amount=0
    if allocate:
        if raw_word<=999:
            normalized=normalize_reserve(raw_word,reserve)
            raw_word,reserve=normalized['raw_word'],normalized['reserve']
            amount=min(reserve,100)
            raw_word=(raw_word+amount)&65535;reserve=(reserve-amount)&65535
    elif raw_word:
        normalized=normalize_reserve(raw_word,reserve)
        raw_word,reserve=normalized['raw_word'],normalized['reserve']
        if normalized['removed_remainder']==0 and reserve<9901:
            amount=100;raw_word=(raw_word-100)&65535;reserve=(reserve+100)&65535
    return {'before':before,'raw_word':raw_word,'reserve':reserve,'allocate':allocate,
            'changed':before!=(raw_word,reserve),'transferred_hundred_step':amount,
            'normalization':normalized,'pending_number_display':True}

class TroopFieldRules:
    """GameEngine-facing source over shared memory; explicit field contracts."""
    def __init__(self,memory):self.memory=memory
    def address(self,officer):
        if not 0<=officer<237:raise ValueError('Valid officer IDs0..236')
        return 0x63C0+12*officer
    def views(self,officer):
        address=self.address(officer)+8
        return TroopStorage(self.memory[address]|self.memory[address+1]<<8)
    def _write(self,officer,raw_word):
        address=self.address(officer)+8
        self.memory[address]=raw_word&255;self.memory[address+1]=(raw_word>>8)&255
    def ai_loss(self,slot,requested):
        """BA4E..BAB2 gameplay writes; its preceding stochastic formula excluded."""
        if not 0<=slot<20:raise ValueError('Valid battle slots0..19')
        officer=self.memory[0x664+slot]
        result=low10_loss(self.views(officer).raw_word,requested,preserve_upper6=True)
        self._write(officer,result['raw_word'])
        loss=result['applied_loss'];self.memory[0x42C]=loss&255;self.memory[0x42D]=loss>>8
        self.memory[0x42E]=0;self.memory[0x6F8F]=0;self.memory[0x6F8B]=255
        return result
    def recruitment_write(self,officer,increment):
        raw=ai_recruitment_write(self.views(officer).raw_word,increment);self._write(officer,raw)
        return self.views(officer)
    def refill_invasion(self,officer):
        """A54B..A555 writeback only; funding and AP charge are caller's work."""
        self._write(officer,1000);return self.views(officer)
    def commit_attack_groups(self):
        """CA3F..CAC7 gameplay: left then right; aliases preserve last write."""
        writes=[]
        for side in (0,1):
            officer=self.memory[0x560+side];address=self.address(officer)
            self.memory[address]=self.memory[0x5AC+11*side]
            groups=self.memory[0x5AD+11*side:0x5B7+11*side]
            raw=attack_group_write(self.views(officer).raw_word,groups);self._write(officer,raw)
            writes.append({'side':side,'officer_id':officer,'raw_word':raw})
        return writes

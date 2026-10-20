#!/usr/bin/env python3
"""Actual-ROM CPU differential for independent loyalty/roster/succession rules.

No ROM patches, graphics hooks or fabricated acknowledgements. Routines with a
text/wait tail stop at its actual entry, with explicit stop addresses recorded.
The high-level contract is game-memory writes + selected loyalty result flags,
not CPU stack, all scratch/registers, mapper or interrupt emulation.
"""
from collections import Counter
import argparse, hashlib, json, random, sys
from importlib.metadata import version
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT));sys.path.insert(0,str(ROOT/'scripts'))
from verify_battle import Oracle
from source.recovered.officer_transfer import *

class TransferOracle(Oracle):
    def run(self,entry,*,stop=None,limit=300000,a=0,p=0x60):
        cpu=self.cpu;cpu.pc=entry;cpu.sp=0xFD;cpu.p=p;cpu.a=a
        self.load(0x1FE,[0xFF,0x01])
        for step in range(limit):
            if cpu.pc==0x0200 or stop and stop(cpu.pc):return step
            self.bus.pc,self.bus.step_no=cpu.pc,step
            origin=self.bus.origin(cpu.pc)
            if origin is None:raise AssertionError(f'RAM execution {cpu.pc:04X}')
            bank,offset=origin;self.executed[(bank,cpu.pc,offset)]+=1
            if cpu.disassemble[self.bus.peek(cpu.pc)][0]=='???':raise AssertionError(f'Bad opcode {bank}:{cpu.pc:04X}')
            cpu.step()
        raise AssertionError(f'Budget {entry:04X} PC{cpu.pc:04X} SP{cpu.sp:02X}')

def context(rom,pair=10):
    o=TransferOracle(rom,pair);prefix=ROOT/'analysis/phase5/runtime/city-info/menu-0'
    o.load(0,(prefix.with_name(prefix.name+'-ram.bin')).read_bytes())
    o.load(0x6000,(prefix.with_name(prefix.name+'-sram.bin')).read_bytes())
    o.load(0xE1,[0x31,pair|0x20,(pair+1)|0x20]) # CPU far-call restore must match actual pair
    # Preserve real snapshot protocol bytes but replace game records explicitly
    # per case. Initial city owner7 and packed empty roster are documented.
    for city in range(30):
        o.load(city_address(city),bytes([7])+bytes(16)+bytes([255])*10+bytes(5))
    for ruler in range(7):o.load(ruler_address(ruler),[20+ruler,0,0,3,0,0,0,0])
    return o

def record(o,ident,*,loyalty=60,virtue=70,status=2,health=80,location=0):
    o.load(officer_address(ident),[health,75,80,loyalty,virtue,location,0,0,205,171,0,status])
def city(o,ident,owner,ids,resources=(0,0)):
    a=city_address(ident);o.set(a,owner)
    o.load(a+2,[resources[0]&255,resources[0]>>8,resources[1]&255,resources[1]>>8])
    o.load(a+17,list(ids)+[255]*(10-len(ids)))
def model(o,data):
    m=bytearray(65536);m[:2048]=o.bus.ram;m[0x6000:0x8000]=o.bus.sram
    return OfficerTransfer(m,data)
def compare(name,o,logic,ram=()):
    expected=bytes(logic.memory[0x6000:0x8000]);actual=bytes(o.bus.sram)
    if actual!=expected:
        diffs=[(hex(i+0x6000),actual[i],expected[i]) for i in range(8192) if actual[i]!=expected[i]]
        raise AssertionError((name,'SRAM',diffs[:20]))
    for address in ram:
        assert o.get(address)==logic.memory[address],(name,'RAM',hex(address),o.get(address),logic.memory[address])
def flags(o,result,p=0x60):
    assert o.cpu.a==result['cpu_a'],('CPU A',o.cpu.a,result)
    for flag,mask in [('C',1),('V',64),('N',128),('Z',2)]:
        value=result['cpu_flags'][flag]
        expected=bool(p&mask) if value=='preserved' else value
        assert bool(o.cpu.p&mask)==expected,('flags',flag,o.cpu.p,result)

def verify(rom):
    data=TransferData.from_rom(rom);counts=Counter();executed=Counter();samples=[];rng=random.Random(50165)
    def passed(name,o):counts[name]+=1;executed.update(o.executed)
    for i in range(1024):
        old=rng.randrange(256);virtue=rng.randrange(256)
        for name,entry in [('recruitment_loyalty',0xA006),('capture_loyalty',0xA00C)]:
            o=context(rom);record(o,20,virtue=virtue);record(o,21,loyalty=old)
            o.set(0x30,20);o.set(0x31,21);o.set(0x20,21)
            logic=model(o,data);result=logic.loyalty_for_recruitment(20,21) if entry==0xA006 else logic.loyalty_after_capture(21)
            o.run(entry);compare(name,o,logic);flags(o,result)
            assert o.cpu.a==result['value'];passed(name,o)
    for i in range(1536):
        ruler=i%7;leader=data.families[ruler][i%len(data.families[ruler])] if i%4==0 else 20
        o=context(rom);record(o,22,virtue=rng.randrange(256));record(o,21,loyalty=rng.randrange(256));record(o,leader,virtue=rng.randrange(256))
        o.load(0x30,[leader,21,ruler,22]);logic=model(o,data)
        result=logic.loyalty_after_leader_change(leader,21,ruler,22)
        o.run(0xA009);compare('leader_change_loyalty',o,logic);flags(o,result)
        assert o.cpu.a==(leader if result['family_exempt'] else result['value']);passed('leader_change_loyalty',o)
    for i in range(256):
        o=context(rom,pair=25);ids=list(range(30,30+rng.randrange(1,11)));slot=rng.randrange(len(ids));officer=ids[slot]
        owner=rng.randrange(32)*8+rng.randrange(7);city(o,3,owner,ids);record(o,officer,status=rng.randrange(256))
        o.load(0x0408,[3,17+slot,officer]);logic=model(o,data);logic.delete_city_officer(3,17+slot,officer)
        o.run(0xBDBB);compare('delete_city_officer',o,logic,range(0x0580,0x0590));passed('delete_city_officer',o)
    for i in range(256):
        o=context(rom,pair=25);ids=list(range(30,30+rng.randrange(1,11)));slot=rng.randrange(len(ids));officer=ids[slot]
        owner=rng.randrange(32)*8+rng.randrange(7);city(o,3,owner,ids);record(o,officer,status=rng.randrange(256))
        o.load(0,[officer_address(officer)&255,officer_address(officer)>>8]);o.load(0x10,[city_address(3)&255,city_address(3)>>8])
        o.set(0x040E,3);o.set(0x040F,17+slot);o.set(0x31,officer);o.set(0x0402,i&255)
        logic=model(o,data);logic.release_city_officer(3,17+slot,officer)
        o.run(0xC099,stop=lambda pc:pc==0xC0E2);compare('release_city_officer',o,logic,[0x0402,0x042C]);assert o.cpu.a==0xD4;passed('release_city_officer',o)
    for i in range(384):
        same=i%8==0;o=context(rom,pair=27);src=3;dst=3 if same else 4
        ids=list(range(30,30+rng.randrange(1,9)));count=rng.randrange(1,len(ids)+1);selected=ids[:count]
        if i%11==0 and len(ids)>=2:selected=[ids[0],ids[0]];ids[1]=ids[0]
        city(o,src,0xB8,ids)
        if not same:city(o,dst,0xB8,[40,41] if i&1 else [])
        leader=selected[0] if i%3==0 else 55;o.set(ruler_address(0),leader)
        o.load(0x0470,[src,dst]);o.load(0x0481,selected+[255]*(10-len(selected)))
        o.load(0xEE,[ruler_address(0)&255,ruler_address(0)>>8]);logic=model(o,data)
        logic.move_roster_group(src,dst);o.run(0xAD41);compare('move_roster_group_alias' if same else 'move_roster_group',o,logic,range(0x0481,0x048B));passed('move_roster_group_alias' if same else 'move_roster_group',o)
    for i in range(384):
        o=context(rom,pair=27);ids=list(range(30,30+rng.randrange(0,11)))
        if i%3==0 and ids:ids[0]=255
        city(o,3,i%7,ids);officer=80;leader=o.get(ruler_address(i%7));record(o,leader,virtue=rng.randrange(256));record(o,officer,loyalty=rng.randrange(256),status=i&255)
        o.set(0x0402,3);o.set(0x0472,officer);logic=model(o,data);logic.recruit_officer(3,officer)
        o.run(0xACF0,stop=lambda pc:pc==0xAD37);compare('recruit_officer',o,logic,[0x30,0x31]);passed('recruit_officer',o)
    for i in range(384):
        o=context(rom);ids=list(range(30,30+rng.randrange(0,11)));owner=(i%32)*8+i%7
        city(o,3,owner,ids,resources=(rng.randrange(65536),rng.randrange(65536)))
        for ident in ids:record(o,ident,loyalty=rng.choice([0,100,rng.randrange(256)]),virtue=rng.randrange(256))
        ruler=i%7 if i%3 else (i+1)%7;o.load(0x36,[3,ruler]);logic=model(o,data);logic.promote_city_chief(3,ruler)
        o.run(0xC9A5);compare('promote_city_chief',o,logic);passed('promote_city_chief',o)
    for i in range(128):
        ruler=i%7;o=context(rom)
        for k in range(5):
            ident=30+k;record(o,ident,virtue=(k%2)*50,health=0,status=3)
            city(o,k,ruler if i%4 else 7,[ident],resources=(65535,65535))
        if i%3==0:
            family=data.families[ruler][i%len(data.families[ruler])];record(o,family,virtue=0,health=0,status=3);city(o,6,ruler,[family],resources=(65535,65535))
        o.set(0x40,ruler);logic=model(o,data);choice=logic.choose_successor(ruler)
        o.run(0xCA68,stop=lambda pc:pc in (0xCB52,0xCA6E));compare('choose_successor',o,logic,[0x27]);passed('choose_successor',o)
        if i<4:samples.append({'kind':'selection','index':i,'result':choice,'stop_pc':hex(o.cpu.pc)})
    for i in range(128):
        ruler=i%7;o=context(rom);old=20+ruler;candidate=80;record(o,old,virtue=100);record(o,candidate,virtue=0)
        for k in range(5):
            ids=[candidate,31,32] if k==0 else ([31,32] if i%3 else list(range(30,40)))
            city(o,k,ruler,ids,resources=(65535,12345))
        for ident in range(30,40):record(o,ident,loyalty=20,virtue=0,status=0xAE,location=29)
        o.set(0x40,ruler);o.set(0x27,candidate);o.set(0x52,i);logic=model(o,data);result=logic.install_ai_successor(ruler,candidate)
        o.run(0xCB52,stop=lambda pc:pc==0xCB79);compare('install_ai_successor',o,logic,[0x45,0x52,0x27]);passed('install_ai_successor',o)
        if i<4:samples.append({'kind':'installation','index':i,'result':result,'stop_pc':hex(o.cpu.pc)})
    for i in range(256):
        o=context(rom,pair=25);ids=list(range(30,30+rng.randrange(0,11)));candidate=rng.choice(ids) if ids and i%3 else 80
        city(o,3,0,ids);o.set(0x040C,3);o.set(0x040D,candidate);logic=model(o,data);logic.set_city_chief(3,candidate)
        o.run(0xC101);compare('set_city_chief',o,logic);passed('set_city_chief',o)
    for i in range(256):
        o=context(rom,pair=25);ruler=i%7;candidate=80;city(o,3,ruler,[30,80,31])
        o.set(0x12,0);o.load(0x040A,[ruler,20+ruler,3,candidate]);o.set(0x0402,i);o.set(0x04D0,127)
        o.load(0xEE,[ruler_address(ruler)&255,ruler_address(ruler)>>8]);manual=i%2==0
        logic=model(o,data);logic.commit_player_successor(ruler,candidate,3,manual_choice=manual)
        entry=0xBF85 if manual else 0xC25D;stop=0xBFA9 if manual else 0xC27D
        o.run(entry,stop=lambda pc:pc==stop);compare('commit_player_successor_manual' if manual else 'commit_player_successor_automatic',o,logic,[0x0402,0x042C,0x04D0]);assert o.cpu.a==(0xD3 if manual else 0xC2);passed('commit_player_successor_manual' if manual else 'commit_player_successor_automatic',o)
    for i in range(384):
        ruler=i%7;candidate=data.families[ruler][0] if i%4==0 else 80;old=20+ruler
        o=context(rom,pair=25);record(o,old,virtue=100);record(o,candidate,loyalty=20,virtue=0,status=0xEE)
        for ident in range(30,40):record(o,ident,loyalty=20,virtue=0,status=0xAE,location=29)
        for k in range(3):
            ids=[candidate,31,32] if k==0 else list(range(30,40))
            if k==2 and i%3:ids[0]=255
            city(o,k,ruler,ids,resources=(65535,12345))
        # Family-exempt CF7C leaves the caller's existing pointer untouched.
        o.load(0x22,[officer_address(39)&255,officer_address(39)>>8]);o.set(0x50,i&255)
        active=i%8!=1;o.set(0x0409,128 if active else 0);o.load(0x040A,[ruler,old,0,candidate]);o.set(0x0470,i&255)
        logic=model(o,data);result=logic.recalculate_player_followers(ruler,candidate,old,process_followers=active,return_state=i&255)
        o.run(0xC289);compare('recalculate_player_followers',o,logic,[0x0401,0x0402,0x50]+([0x12,0x13] if active else []));passed('recalculate_player_followers',o)
        if i<4:samples.append({'kind':'player_followers','index':i,'result':result})
    for i in range(32):
        o=context(rom);ruler=i%7
        for k in range(30):
            ids=[30+k,70+k];city(o,k,k%7,ids,resources=(10000,65535))
            for ident in ids:record(o,ident,loyalty=rng.choice([100,rng.randrange(256)]),virtue=rng.randrange(256))
        logic=model(o,data);logic.repair_ruler_city_chiefs(ruler)
        o.run(0xC98F,a=ruler);compare('repair_ruler_city_chiefs',o,logic);passed('repair_ruler_city_chiefs',o)
    for i in range(64):
        ruler=i%7;old=20+ruler;o=context(rom);record(o,old,status=0xAC+(i%4),health=0 if i%2 else 80,virtue=100)
        o.set(0x40,ruler);o.set(0x38,old);o.set(0x52,i&255)
        for ident in (30,31):record(o,ident,loyalty=20,virtue=30,status=3,health=0)
        if i%4:city(o,3,ruler,[30,31]+([old] if i%4==3 else []),resources=(65535,12345))
        if i%5==0:
            family=data.families[ruler][0];record(o,family,virtue=0,status=3,health=0);city(o,5,ruler,[family])
        logic=model(o,data);result=logic.resolve_ai_leader_death(ruler)
        o.run(0xCA37,stop=lambda pc:pc in (0xCA52,0xCB79,0xCA7F));compare('resolve_ai_leader_death',o,logic);passed('resolve_ai_leader_death',o)
        if i<8:samples.append({'kind':'leader_death_decision','index':i,'result':result,'stop_pc':hex(o.cpu.pc)})
    # Explicit model-domain guards are source-only, never counted as ROM cases.
    guard_checks=[]
    o=context(rom,pair=27);logic=model(o,data);logic.memory[city_address(3):city_address(3)+256]=bytes([7])*256
    try:logic.move_roster_group(4,3,[])
    except UnboundedOriginalScan:guard_checks.append('unbounded original byte scan: refuse after256 positions')
    else:raise AssertionError('Missing unbounded scan guard')
    o=context(rom,pair=25);candidate=data.families[0][0];city(o,3,0,[30]);record(o,30,loyalty=20);logic=model(o,data);logic.memory[0x22:0x24]=bytes([0,0xA0])
    try:logic.recalculate_player_followers(0,candidate,20,process_followers=True,return_state=0)
    except ValueError:guard_checks.append('family stale pointer outside proven officer-record domain: refuse')
    else:raise AssertionError('Missing pointer domain guard')
    context_prefix=ROOT/'analysis/phase5/runtime/city-info/menu-0'
    context_files={suffix:{'path':str(context_prefix.with_name(context_prefix.name+suffix).relative_to(ROOT)),'sha256':hashlib.sha256(context_prefix.with_name(context_prefix.name+suffix).read_bytes()).hexdigest()} for suffix in ('-ram.bin','-sram.bin')}
    out={'source_only_guard_checks':guard_checks,'source_sha256':hashlib.sha256((ROOT/'source/recovered/officer_transfer.py').read_bytes()).hexdigest(),'context_files':context_files,'python_version':sys.version,'py65_version':version('py65'),'original_rom_sha256':hashlib.sha256(rom).hexdigest(),'oracle':'actual unmodified mapper19 ROM under py65; CPU only; no NMI/graphics or false scene acknowledgement',
         'contract':'all 8192 SRAM bytes per case; declared RAM buffers/control/RNG cursor; loyalty C/V/N/Z and A; CPU pointer/stack/mapper protocol external',
         'context':'real menu-0 RAM/SRAM snapshot, with explicit controlled city/ruler/officer records overwritten by each fixture',
         'counts':dict(counts),'total':sum(counts.values()),'failures':0,'unique_executed_instruction_locations':len(executed),'samples':samples,
         'entry_stops':{'ACF0':'AD37, before text/state tail','C099':'C0E2, before dialogue tail','CA68':'CB52 successor install or CA6E no successor','CB52':'CB79 before6F8B acknowledgement wait','CA37':'CA52 alive status2 / CB79 successor / CA7F none, before acknowledgements and repair','BF85/C25D':'BFA9/C27D before dialogue queues'},
         'coverage':[{'bank':bank,'cpu_address':f'{pc:04X}','rom_offset':offset,'execution_count':count} for (bank,pc,offset),count in sorted(executed.items())]}
    return out
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--rom',default='/Users/paulasmith/Downloads/三国志2超级版.nes');p.add_argument('--out',default=str(ROOT/'analysis/phase5/transfer/validation.json'));a=p.parse_args()
    result=verify(Path(a.rom).read_bytes());path=Path(a.out);path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n');print(json.dumps({'total':result['total'],'failures':result['failures'],'counts':result['counts']},ensure_ascii=False))

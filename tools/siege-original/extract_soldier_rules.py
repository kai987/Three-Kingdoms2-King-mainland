"""Optional read-only original6502 arithmetic witness extraction.

Requires py65 only for independent offline research. Runtime and CI use the
retained witness cases without a ROM, emulator or additional dependency.
"""
from pathlib import Path
import sys,json,hashlib,itertools,argparse
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('rom',type=Path)
parser.add_argument('--out',type=Path,default=Path(__file__).with_name('soldier-rules-reference.json'))
args=parser.parse_args()
from py65.devices.mpu6502 import MPU
rom=args.rom.read_bytes()
sha=lambda b:hashlib.sha256(b).hexdigest()
assert sha(rom)=='26c8d921ff5c208191f136480bcd8d7e89c2e4ed40a0ac7b51482bcb52fe2b82'
mem=[0]*65536
for bank,cpu in [(14,0xa000),(15,0xc000),(31,0xe000)]:mem[cpu:cpu+8192]=rom[16+bank*8192:16+(bank+1)*8192]
def run(entry,prepare,roll=0):
 m=MPU(memory=mem.copy(),pc=entry);prepare(m.memory);m.stPushWord(0x7fff)
 for step in range(2000):
  if m.pc==0x8000:return m
  if m.pc==0xe87a:
   m.a=roll;m.p=(m.p&~0x82)|(2 if roll==0 else 0);m.pc=m.stPopWord()+1
  else:m.step()
 raise RuntimeError((hex(m.pc),entry))
seed=[]
for martial in [1,49,50,64,65,79,80,86,87,91,92,96,97,99]:
 for roll in range(9):
  def prep(x):x[0]=0;x[1]=0x70;x[0x7001]=martial;x[0x700a]=0
  m=run(0xc991,prep,roll);seed.append([martial,roll,m.a])
kinds={'general':0,'cavalry':1,'archer':2,'infantry':3};damage=[]
for base_value,count,kind,target,ranged in itertools.product([1,20,45,78],[1,14,15,34,35,59,60,79,80,89,90,99,100],kinds,kinds,[False,True]):
 if ranged and kind!='archer':continue
 for weapon,armor in [(0,0),(20,12)]:
  def prep(x):
   actor=0 if kind=='general'else 1;victim=11 if target=='general'else 12
   x[0x545]=actor;x[0x54a]=victim;x[0x5c2+actor]=kinds[kind];x[0x5c2+victim]=kinds[target];x[0x5ac+actor]=count
   x[0x56a]=base_value;x[0x56b]=45;x[0x570]=weapon;x[0x56f]=armor
  entry=0xa871 if ranged else 0xa84d if kind=='archer'else 0xa8f2
  m=run(entry,prep);damage.append([base_value,count,kind,target,weapon,armor,ranged,m.memory[0]])
spans=[]
for name,bank,cpu,end in [('attack_parameters',15,0xc991,0xca1f),('archer_contact',14,0xa84d,0xa871),('archer_ray',14,0xa871,0xa8cf),('soldier_count_and_target',14,0xa8f2,0xa9a0)]:
 off=16+bank*8192+(cpu&8191);raw=rom[off:off+end-cpu];spans.append(dict(name=name,physical_bank=bank,cpu=hex(cpu),bytes=len(raw),sha256=sha(raw)))
result=dict(schema='tk2-original-soldier-arithmetic-reference-v1',rom_sha256=sha(rom),runner_sha256=sha(Path(__file__).read_bytes()),runner='py65 NMOS6502; pinned ROM bytes mapped physical14:A000,15:C000,31:E000',controlled_fixture=True,natural_gameplay=False,rom_modified=False,rng_note='Only the E87A boundary is replaced by the explicitly listed accepted0..8 return; original arithmetic executes unchanged. These samples do not assert the native RNG sequence equals the remake stream.',source_spans=spans,seed_columns=['martial','accepted_roll_0_8','native_base'],seed_cases=seed,damage_columns=['base','count','kind','target_kind','weapon_power','armor_power','ranged','native_loss'],damage_cases=damage,remake_adjustments=['No action for zero-person/dead slots','Campaign shared xorshift modulo9 seeds each side once on first contact; no draws on previews','Training and guard apply after native arithmetic','Maximum1000 people and individual commands are requested remake extensions'])
out=args.out;out.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({'seeds':len(seed),'damage':len(damage),'bytes':out.stat().st_size,'sha256':sha(out.read_bytes())}))

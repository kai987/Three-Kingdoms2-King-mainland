"""Independent new-scenario persistent-record initialization,29A018→30DD8B.

This service deliberately replaces the lower4KiB SRAM scenario records. It
is not a graphics loader. ROM is data only. It neither renders a scene nor
completes its caller's other initialization dependencies.
"""
from dataclasses import dataclass
import hashlib
from .battle_nmi_services import BattleNMIServices,ServiceCall
from .scene_shared_services import SceneSharedServices
ROM_SHA256='26c8d921ff5c208191f136480bcd8d7e89c2e4ed40a0ac7b51482bcb52fe2b82'
C,Z=1,2

@dataclass(frozen=True)
class ScenarioData:
    rom:bytes
    @classmethod
    def from_rom(cls,rom):
        if hashlib.sha256(rom).hexdigest()!=ROM_SHA256:raise ValueError('Pinned original ROM required')
        return cls(bytes(rom))

class ScenarioInitialization(BattleNMIServices):
    FIXED=()
    LOCAL_ENTRIES=(0xA018,0xDD8B)
    def __init__(self,memory,data,services=None):
        super().__init__(memory,callbacks=self._resolve_service)
        self.data=data if isinstance(data,ScenarioData)else ScenarioData.from_rom(data)
        self.shared=SceneSharedServices(memory,self.data.rom,callbacks=services)
        self.external_services=services;self._call_owner=None
    def _resolve_service(self,call):
        if call.target in self.shared.FIXED:result=self.shared(call)
        elif self.external_services is not None:result=self.external_services(call)
        else:return dict(status='dependency',reason='Scenario callee is not independently recovered')
        if not isinstance(result,dict)or result.get('status')!='returned':return dict(status='dependency',body=result)
        if call.registers.pc!=call.return_pc or call.registers.sp!=call.expected_sp:return dict(status='dependency',reason='Actual scenario helper PC/SP have not returned')
        return result
    def call(self,pc,target):
        r=self.registers;sp=r.sp;word=pc+2;self.push(word>>8);self.push(word);r.pc=target
        yield ServiceCall(target,pc+3,'call',r,self.memory,tuple(self.memory.banks),sp)
        if r.pc!=pc+3 or r.sp!=sp:raise RuntimeError('Scenario helper must return through its real frame')
    def run_entry(self,entry=0xA018,registers=None):
        if entry not in self.LOCAL_ENTRIES:raise ValueError('Only29A018/30DD8B is recovered here')
        if self._program is not None:raise RuntimeError('A scenario service is pending; resume it first')
        if registers is None:raise ValueError('Supply actual caller registers and RTS frame')
        if tuple(self.memory.banks[1:3])!=(29,30):raise ValueError('Actual physical29/30 pair required')
        return self._start(self.scenario_init,registers,'new_scenario_persistent_records')
    def __call__(self,call):
        if call.target not in self.LOCAL_ENTRIES or tuple(call.entry_banks[1:3])!=(29,30):return dict(status='dependency',reason='No scenario initialization body owns this pair/entry')
        if self._program is not None:
            if self._call_owner is not call:return dict(status='dependency',reason='Another caller owns scenario initialization')
            result=self.resume()
        else:self._call_owner=call;result=self.run_entry(call.target,call.registers)
        if result['status']=='returned':
            self._call_owner=None
            if call.registers.pc!=call.return_pc or call.registers.sp!=call.expected_sp:return dict(status='dependency',reason='Scenario body did not reach actual caller PC/SP')
        return result
    def result(self,status,**extra):
        return dict(super().result(status,**extra),persistent_SRAM_replaced=True,full_NES_frame=False,PPU_upload_completed=False)
    def scenario_init(self):
        """30DD8B..DE7D: clear, random variant, copy city/officer templates."""
        r=self.registers;m=self.memory
        self.a(m[0x6F43]);self.push(r.a)
        self.a(0x60);m[1]=r.a;self.a(0);m[0]=r.a;self.y(r.a)
        while True:
            m[(m[0]|m[1]<<8)+r.y]=r.a;self.y(r.y+1)
            if r.p&Z:
                self.inc(1);self.x(m[1]);self.cmp(r.x,0x70)
                if r.p&C:break
        self.a(self.pop());m[0x6F43]=r.a
        while True:
            yield from self.call(0xDDAD,0xE87A)
            self.a(r.a&7);self.cmp(r.a,5)
            if not r.p&C:break
        m[0x6F45]=r.a
        self.a(255);m[0x6F04]=r.a;self.a(255);m[0x6FE2]=r.a
        self.a(11);m[0x400]=r.a;self.a(0);m[0x401]=r.a
        self.y(48);yield from self.call(0xDDCF,0xF25F)
        self.a(0);m[0]=r.a;self.a(0x8C);m[1]=r.a
        self.a(0);m[2]=r.a;self.a(0x60);m[3]=r.a
        self.y(0);self.x(0);m[4]=r.x
        self.copy_template(3,0xC0)
        self.y(49);yield from self.call(0xDE14,0xF25F)
        self.a(0);m[0]=r.a;self.a(0x80);m[1]=r.a
        self.a(0xC0);m[2]=r.a;self.a(0x63);m[3]=r.a
        self.y(0);self.x(0);m[4]=r.x
        self.copy_template(11,0x40)
        self.a(0x59);m[0x6F00]=r.a;self.a(0);m[0x6F01]=r.a
        self.a(255)
        for addr in range(0x6F83,0x6F8A):m[addr]=r.a
        self.a(0);m[0x6F8A]=r.a;self.rts()
    def copy_template(self,high_count,low_count):
        """Original pointer-advancing byte copies, preserving scratch/flags."""
        r=self.registers;m=self.memory
        while True:
            self.a(m[(m[0]|m[1]<<8)+r.y]);m[(m[2]|m[3]<<8)+r.y]=r.a
            self.inc(0)
            if r.p&Z:self.inc(1)
            self.inc(2)
            if r.p&Z:self.inc(3)
            self.x(r.x+1)
            if r.p&Z:self.inc(4)
            self.a(m[4]);self.cmp(r.a,high_count)
            if r.p&C:
                self.cmp(r.x,low_count)
                if r.p&C:return

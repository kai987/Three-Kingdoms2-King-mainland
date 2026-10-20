"""A narrow, controlled current-JSR entry into existing readable owners.

The caller is stopped before A074/A07C's outer RTS. No outer return frame is
invented. The existing CityUIController._external pushes the current JSR;
SceneCoordinator owns EE07 and the actual banked callee. This adapter neither
executes ROM opcodes nor changes PC/SP to complete a service.
"""
from source.recovered.city_ui_controller import CityUIController,STATE,PHASE,ACTOR_SLOT


def current_jsr(memory,rom,registers,coordinator,site):
    if registers.pc!=site['call_pc'] or registers.y!=site['selector']:
        raise ValueError('Controlled current-call entry must already be at the declared PC/Y')
    if registers.p&8:raise ValueError('This contract declares binary arithmetic, D=0')
    owner=CityUIController(memory,rom,services=coordinator)
    owner.registers=registers
    owner._return_pc=site['continuation']
    owner._return_sp=registers.sp
    owner._before=(memory[STATE],memory[PHASE],memory[ACTOR_SLOT])
    owner._program=owner._external(site['call_pc'],0xEE07,site['continuation'],'far_call',site['target'])
    return owner,owner._drive()

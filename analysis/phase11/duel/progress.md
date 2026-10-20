# Phase11 Duel controller working contract

New owned paths only: source/recovered/duel_scene_controller.py, new analyze/verify
scripts, this directory. Frozen old modules remain read-only. Original ROM hash
26c8d921ff5c208191f136480bcd8d7e89c2e4ed40a0ac7b51482bcb52fe2b82.

22 main states; initialization aliases10/11/12 share state0 phases. Raw B100 main
control table is B118..B143; B11F is table DATA, not an initialization routine.
State0 dispatchB147, phase0B15A. Additional local graphicsCDFD/CEA5/CEE1/CFA3,
HP/menu/panel/status helpersD060..D2AA must be included in fresh source.

Plan: analyze original raw CFG, statically emit named state/phase Python with
structured if/while, fixed calls and binary flag helpers. Source runtime must
not read program.json, decode opcodes or dispatch per-instruction PC dictionaries.
Any unstructured gap must remain explicit. Source internal localcalls retain
real CPUstack return protocol; external services use ServiceCall(target,
return_pc,kind,registers,memory,entry_banks,expected_sp) and strict returncheck.
No missing service is acknowledged. Audio/PPU consumption is genuine service
work or explicit dependency; controller is one cooperative update, not frame.

Root owns scene_shared_services.py fixed helpers/queue/menu/math/RNG and
scene_initialization.py E2E8/E768/ECBF/ECEE. Need supplied true service callbacks
forF1AD(screen sprites),farEE07,and fixed services beyond ControlHelpers subset.

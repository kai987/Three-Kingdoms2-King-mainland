#!/usr/bin/env python3
"""Root-only isolated passive observer build; never builds frozen trees."""
from pathlib import Path
import hashlib,json,shutil,subprocess,os,time
ROOT=Path(__file__).resolve().parents[1];TREE=ROOT/'.toolchain/wp05-observer/upstream'
OUT=ROOT/'analysis/wp05-natural-nonempty/core-provenance'
COMMIT='135dfa6dfda5e7603d61e751b9ddd0cc42546bc3'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def pin(p):p=Path(p);return dict(path=str(p.relative_to(ROOT)),bytes=p.stat().st_size,sha256=sha(p))
def main():
 assert TREE.is_dir()and str(TREE.relative_to(ROOT)).startswith('.toolchain/wp05-observer/')
 OUT.mkdir(parents=True,exist_ok=True);assert not(OUT/'build.json').exists()
 assert subprocess.check_output(['git','-C',str(TREE),'rev-parse','HEAD'],text=True).strip()==COMMIT
 names=subprocess.check_output(['git','-C',str(TREE),'diff','--name-only',COMMIT],text=True).splitlines()
 assert set(names)=={'libretro/Makefile','source/core/NstCpu.cpp','source/core/board/NstBoard.cpp','source/core/board/NstBoard.hpp'},names
 sources=names+['source/core/NstWatch.hpp','source/core/NstWatch.cpp.inc']
 provenance=[]
 for name in sources:
  patched=TREE/name;dest=OUT/'patched'/name;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(patched,dest)
  raw=None
  if name in names:
   raw=subprocess.check_output(['git','-C',str(TREE),'show',COMMIT+':'+name]);p=OUT/'upstream'/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(raw)
  provenance.append(dict(path=name,official_sha256=hashlib.sha256(raw).hexdigest()if raw else None,patched_sha256=sha(patched)))
 patch=subprocess.check_output(['git','-C',str(TREE),'diff','--binary',COMMIT,'--',*names])
 for name in sources[-2:]:
  lines=(TREE/name).read_text().splitlines();patch+=('diff --git a/'+name+' b/'+name+'\nnew file mode 100644\n--- /dev/null\n+++ b/'+name+'\n@@ -0,0 +1,'+str(len(lines))+' @@\n'+''.join('+'+x+'\n'for x in lines)).encode()
 (OUT/'observer.patch').write_bytes(patch)
 def run(args,name):
  start=time.monotonic()
  with(OUT/name).open('wb')as log:subprocess.run(args,cwd=TREE/'libretro',stdout=log,stderr=subprocess.STDOUT,check=True)
  return dict(argv=args,log=pin(OUT/name),seconds=round(time.monotonic()-start,3))
 clean=run(['make','clean'],'clean.log')
 command=['make','platform=osx','arch=arm','CC=clang','CXX=clang++','-j6']
 build=run(command,'build.log');binary=TREE/'libretro/nestopia_libretro.dylib'
 observed=TREE.parent/'observed/nestopia_libretro.dylib';observed.parent.mkdir(exist_ok=True);shutil.copyfile(binary,observed)
 before=sha(binary);os.utime(TREE/'source/core/NstWatch.cpp.inc',None)
 rebuild=run(command,'dependency-rebuild.log');assert binary.read_bytes()==observed.read_bytes()
 j=dict(schema='wp05-isolated-passive-observer-build-v1',status='passed_build_identity_not_runtime',
  official_repository='https://github.com/libretro/nestopia.git',commit=COMMIT,
  inherited_draft='Frozen phase32 upstream, copied without old object files or dylib; actual new patch above is authoritative.',
  clean=clean,build=build,include_dependency_rebuild=rebuild,include_touch_rebuild_byte_identical=True,
  compiler=subprocess.check_output(['clang++','--version'],text=True).strip(),source_files=provenance,
  patch=pin(OUT/'observer.patch'),observer=pin(observed),last_build=pin(binary),
  ABI=dict(exports_prefix='nestopia_wp05_',words=72,bytes_per_record=288,snapshot_bytes=10240),
  design=dict(new_observer_only_storage=True,modified_emulator_object_layout=False,
   new_emulated_bus_reads=0,new_emulated_bus_writes=0,
   new_hooks='Original Push8 store before/after, selected true call/RTS/continuation opcode boundaries; unchanged original store/SP/bus/cycle expressions.',
   snapshot='Const 2K RAM+8K WRAM physical backing, no MMIO; no instantaneous PPU/APU/N163 capture.'),
  runtime_equivalence_proven=False)
 (OUT/'build.json').write_text(json.dumps(j,ensure_ascii=False,indent=2)+'\n');print(json.dumps({'build':'passed','observer':j['observer'],'runtime_equivalence_proven':False}),flush=True)
if __name__=='__main__':main()

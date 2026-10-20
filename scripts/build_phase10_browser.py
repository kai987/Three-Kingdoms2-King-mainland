#!/usr/bin/env python3
"""Summarize pinned original-core RGB/PCM replays and build a static browser.

Only already captured bytes are read. No emulator, gameplay formula, original
CPU or control IR is executed here. Missing module receipts remain pending.
"""
from pathlib import Path
from collections import Counter
from html.parser import HTMLParser
import hashlib,json,re,subprocess,wave
from PIL import Image

ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'analysis/phase10';RUN=OUT/'runtime'
MODULES={
 'graphics':('图形与16动画','battle_graphics_services.py','D6CC / D657 / DC63 / 计略动画','graphics'),
 'audio':('音序与寄存器输出','audio_services.py','E57F / E673 / E68B / bank15 D8D4','audio'),
 'nmi':('NMI / IRQ与端口','battle_nmi_services.py','F800 / FAD5 / EE53 / FB2D','nmi'),
 'text':('文字队列与消费者','text_services.py','bank29 A048 / A158 / 32个数据命令','text'),
 'scroll':('滚屏服务','scroll_graphics_services.py','原scroll / tile与attribute更新','scroll')}
FIELD_KEYS=('global_state','nmi_scene','battle_state','AP','tactic','result','animation',
            'message_progress','message_type','text_draw_cursor','PPU_jobs','NMI_busy','IRQ_pending')

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def read(p):return json.loads(Path(p).read_text())
def write(p,data):Path(p).write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n')
def compact(row):return {k:row[k]for k in ('frame',*FIELD_KEYS,'PCM_stereo_samples','PCM_nonzero','PCM_stop_byte','RGB_sha256','PCM_sha256')}
def wav_data(path,expected):
 with wave.open(str(path),'rb')as w:
  assert (w.getnchannels(),w.getsampwidth(),w.getframerate(),w.getnframes())==(2,2,48000,expected['stereo_sample_frames'])
  raw=w.readframes(w.getnframes())
 assert len(raw)==expected['PCM_bytes']and hashlib.sha256(raw).hexdigest()==expected['PCM_sha256']
 assert sha(path)==expected['WAV_sha256']and any(raw)
 return raw

def native():
 prior=read(ROOT/'analysis/phase9/runtime/evidence.json');groups=[];receipts=[]
 total=Counter();rates=set();core=None
 for old in prior['native_cases']:
  case=old['case'];path=RUN/case;v=read(path/'validation.json');rep=read(path/'repeat-validation.json');oldv=read(ROOT/v['preparation_reference'])
  assert v['status']==rep['status']=='passed'and rep['all_hashes_equal']
  assert v['rom_sha256']==prior['rom_sha256']and not v['rom_modified']and not v['natural_campaign']
  assert v['additional_core_memory_writes']==v['additional_input_events']==0
  assert v['native_internal_CPU_trace']is False and v['source_CPU_comparisons_in_this_receipt']==0
  assert v['initial_state_sha256']==sha(ROOT/v['initial_state'])and v['preparation_sha256']==sha(ROOT/v['preparation_reference'])
  for name,key in [('scripts/capture_service_flow.py','script_sha256'),('scripts/nes_service_runtime.py','runtime_extension_sha256'),('scripts/nes_runtime.py','original_runtime_sha256')]:assert sha(ROOT/name)==v[key]
  assert v['core']['core_sha256']==sha(ROOT/'.toolchain/nestopia/nestopia_libretro.dylib')
  if core is None:core=v['core']
  else:assert v['core']==core
  for name,expected in v['artifact_sha256'].items():assert (path/name).stat().st_size==expected['bytes']>0 and sha(path/name)==expected['sha256']
  second=ROOT/rep['second_run']
  assert len(rep['artifacts'])==rep['nonempty_artifact_checks']
  for item in rep['artifacts']:
   one=path/item['artifact'];two=second/item['artifact']
   assert item['equal']and one.stat().st_size==two.stat().st_size==item['bytes']>0
   assert sha(one)==sha(two)==item['sha256']
  frames=read(path/'frame-services.json');points=read(path/'checkpoints.json');calls=read(path/'audio-callbacks.json')
  assert len(frames)==v['frames']and len(points)==v['checkpoints']and [x['frame']for x in frames]==list(range(1,len(frames)+1))
  pcm=wav_data(path/'full-flow.wav',v['full_audio']);wav_data(path/'cast-and-result.wav',v['cast_excerpt']);rates.add(v['full_audio']['sample_rate'])
  cursor=0;callback_cursor=0;sample_counts=Counter();RGB_changes=0;audio_RAM_changes=0;prev_RGB=prev_audio=None;timeline=[];signature=None
  for row in frames:
   n=row['PCM_stereo_samples'];block=pcm[cursor:cursor+4*n];cursor+=4*n
   assert n>0 and len(block)==4*n and hashlib.sha256(block).hexdigest()==row['PCM_sha256']and row['PCM_stop_byte']==cursor
   assert row['PCM_nonzero']==any(block);sample_counts[n]+=1
   if prev_RGB is not None and row['RGB_sha256']!=prev_RGB:RGB_changes+=1
   if prev_audio is not None and row['audio_channels_0700_07FF']!=prev_audio:audio_RAM_changes+=1
   prev_RGB=row['RGB_sha256'];prev_audio=row['audio_channels_0700_07FF']
   state=tuple(str(row[k])for k in FIELD_KEYS)
   if state!=signature:timeline.append(compact(row));signature=state
  assert cursor==len(pcm)==v['full_audio']['PCM_bytes']
  for c in calls:
   n=c['stereo_sample_frames'];block=pcm[callback_cursor:callback_cursor+4*n];callback_cursor+=4*n
   assert hashlib.sha256(block).hexdigest()==c['pcm_sha256']
   assert 0<=c['emulated_frame_start']<v['frames']
  assert callback_cursor==len(pcm)
  captures=[]
  for point in points:
   label=point['label'];frame=point['frame'];row=frames[frame-1];same={}
   for suffix in('.png','-ram.bin','-sram.bin','.state'):
    assert (path/(label+suffix)).read_bytes()==(ROOT/'analysis/phase9/runtime'/case/(label+suffix)).read_bytes();same[suffix]=True
   assert point['prior_artifact_equal']==same
   png=path/(label+'.png');head=png.read_bytes();assert head[:8]==b'\x89PNG\r\n\x1a\n'and(int.from_bytes(head[16:20],'big'),int.from_bytes(head[20:24],'big'))==(256,240)
   with Image.open(png)as pixels:assert hashlib.sha256(pixels.convert('RGB').tobytes()).hexdigest()==row['RGB_sha256']
   ram=(path/(label+'-ram.bin')).read_bytes();assert len(ram)==2048 and hashlib.sha256(ram).hexdigest()==row['RAM_sha256']
   assert sha(path/(label+'-sram.bin'))==row['SRAM_sha256']
   assert row['PPU_jobs']==ram[0x7E]and row['animation']==ram[0x4C8]and row['message_progress']==ram[0x300]and row['text_draw_cursor']==ram[0x304]
   captures.append({'label':label,**compact(row),'image':str(png.relative_to(OUT))+'?sha='+sha(png),
      'PNG_sha256':sha(png),'RAM':f'runtime/{case}/{label}-ram.bin','SRAM':f'runtime/{case}/{label}-sram.bin','state':f'runtime/{case}/{label}.state',
      'audio_RAM_0700_07FF_hex':row['audio_channels_0700_07FF'],'palette_0100_011F_hex':row['palette_0100_011F']})
  audio={'full':{'path':f'{case}/full-flow.wav',**v['full_audio'],'seconds':v['full_audio']['stereo_sample_frames']/48000},
         'cast':{'path':f'{case}/cast-and-result.wav',**v['cast_excerpt'],'seconds':v['cast_excerpt']['stereo_sample_frames']/48000}}
  preparation={k:oldv[k]for k in('RAM_preparation','SRAM_preparation','rng_preparation','terrain_fixture','parent_state','parent_sha256','input_plan')}
  info={'case':case,'tactic_id':old['tactic_id'],'name':old['name'],'status':'passed','controlled_fixture':True,'natural_campaign':False,
     'frames':v['frames'],'checkpoint_count':len(captures),'nonempty_artifact_checks':rep['nonempty_artifact_checks'],
     'phase9_native_artifact_parity_checks':v['prior_byte_parity_checks'],'additional_core_memory_writes':0,'additional_input_events':0,
     'validation':f'{case}/validation.json','repeat_validation':f'{case}/repeat-validation.json','frame_services':f'{case}/frame-services.json',
     'checkpoints':f'{case}/checkpoints.json','audio_callbacks':f'{case}/audio-callbacks.json','input_plan':f'{case}/input-plan.json',
     'initial_state':v['initial_state'],'initial_state_sha256':v['initial_state_sha256'],'preparation_reference':v['preparation_reference'],'preparation_sha256':v['preparation_sha256'],
     'preparation':preparation,'audio':audio,'captures':captures,'state_change_timeline':timeline,
     'observation':{'audio_callback_count':len(calls),'PCM_sample_frames_per_video_frame':dict(sample_counts),'RGB_changed_frames':RGB_changes,'audio_RAM_changed_frames':audio_RAM_changes,
                    'frame_services_sha256':sha(path/'frame-services.json'),'all_native_RGB_PCM_observed':True},
     'excluded_directory_metadata':rep['excluded_directory_metadata'],'empty_VRAM_exports_excluded':v['empty_VRAM_exports_excluded'],
     'native_internal_CPU_trace':False,'source_CPU_comparisons_in_this_receipt':0}
  receipts.append(info);groups.append(info)
  for k,value in {'native_case_count':1,'frames_first_run':v['frames'],'checkpoint_count':len(captures),'nonempty_repeat_artifact_checks':rep['nonempty_artifact_checks'],
      'phase9_native_artifact_parity_checks':v['prior_byte_parity_checks'],'WAV_file_checks':2,'PCM_stereo_sample_frames_full':v['full_audio']['stereo_sample_frames'],
      'PCM_bytes_full':v['full_audio']['PCM_bytes'],'audio_callback_count':len(calls),'formal_JSON_repeat_checks':4,
      'excluded_directory_metadata_JSON':len(rep['excluded_directory_metadata']),'excluded_empty_VRAM':v['empty_VRAM_exports_excluded']}.items():total[k]+=value
 assert len(rates)==1;summary=dict(total);summary['frames_both_runs']=2*summary['frames_first_run'];summary['PCM_stereo_sample_frames_both_runs_full']=2*summary['PCM_stereo_sample_frames_full']
 summary['PCM_scalar_channel_samples_full']=2*summary['PCM_stereo_sample_frames_full'];summary['sample_rate']=rates.pop();summary['native_internal_CPU_trace']=False;summary['source_CPU_comparisons_in_this_receipt']=0
 manifest={'schema':'phase10-native-services-v1','status':'passed','rom_sha256':prior['rom_sha256'],'rom_modified':False,'core':core,'summary':summary,'native_cases':receipts,
     'native_internal_CPU_trace':False,'source_CPU_comparisons_in_this_receipt':0,
     'capture_script_sha256':sha(ROOT/'scripts/capture_service_flow.py'),'runtime_extension_sha256':sha(ROOT/'scripts/nes_service_runtime.py'),
     'original_runtime_sha256':sha(ROOT/'scripts/nes_runtime.py'),'generator_sha256':sha(Path(__file__)),
     'limits':['Prepared phase9 initial states and ordinary inputs are inherited exactly; these10 are controlled fixtures, not natural campaign reachability.',
               'Original Nestopia RGB and PCM callbacks are observed; readable source does not synthesize these WAVs.',
               'Frame-end service fields are not native CPU/NMI/IRQ instruction traces. Same-frame transitions may be invisible.',
               'The20 WAVs include10 full-flow and10 overlapping excerpts; excerpt samples are not added to full-flow PCM totals.',
               'Directory/event-path snapshotJSON and emptyVRAM exports are excluded from canonical hash parity.']}
 write(RUN/'evidence.json',manifest);write(RUN/'validation.json',{'status':'passed','rom_sha256':prior['rom_sha256'],'summary':summary,'native_internal_CPU_trace':False,
     'source_CPU_comparisons_in_this_receipt':0,'generator_sha256':manifest['generator_sha256'],'evidence_sha256':sha(RUN/'evidence.json'),
     'checks':{'all10_native_receipts_passed':True,'all10_repeats_passed':True,'all392_canonical_artifacts_nonempty_and_equal':True,'all332_checkpoint_artifacts_equal_phase9':True,
               'all20_WAV_headers_PCM_and_hashes_validated':True,'all_frame_PCM_segments_and_callback_hashes_verified':True,'no_additional_core_memory_writes':True,'inherited_preparation_hashes_verified':True}})
 return manifest,groups

def module_data(key):
 title,source,entries,area=MODULES[key];path=OUT/area/'validation.json'
 if not path.exists():return {'key':key,'title':title,'status':'pending','entries':entries,'links':[]}
 r=read(path);sourcepath=ROOT/'source/recovered'/source
 # The scroll agent may use a more specific filename; infer only from a pinned
 # path explicitly named by its evidence, otherwise omit that link.
 if key=='scroll'and not sourcepath.exists():
  evidence=OUT/area/'evidence.json'
  if evidence.exists():
   named=next((v['path']for v in read(evidence).get('dependency_pins',[])if v['path'].startswith('source/recovered/')and'scroll'in v['path']),None)
   if named:sourcepath=ROOT/named
 keys=('status','rom_cpu_case_count','source_guard_case_count','source_guard_count','failed_count','counts','original_complete_case_count','original_prefix_case_count',
       'native_field_comparison_count','native_snapshot_CPU_fixture_count','source_sha256','validator_sha256','comparison_contract','contract','register_contract','limitations','limits',
       'PCM_synthesis','source_uses_IR_or_original_CPU','actual_external_ROM_callback_count','source_fixture_stub_callback_count','PPU_queue_consumption_or_DMA_synthesized')
 links=[]
 for p,label in [(sourcepath,'可读源码'),(OUT/area/'README.md','服务说明'),(OUT/area/'evidence.json','原字节/表与来源'),(path,'差分回执'),(OUT/area/'original-ranges.asm','原汇编')]:
  if p.is_file():links.append({'path':str(p.relative_to(ROOT))if p.is_relative_to(ROOT)else str(p),'href':str(Path('..')/'..'/p.relative_to(ROOT)),'label':label})
 return {'key':key,'title':title,'entries':entries,'status':r.get('status','pending'),'receipt':{k:r[k]for k in keys if k in r},'links':links}

class Parsed(HTMLParser):
 def __init__(self):super().__init__();self.ids=[];self.targets=[];self.details=[]
 def handle_starttag(self,tag,attrs):
  d=dict(attrs)
  if'id'in d:self.ids.append(d['id'])
  if tag in('a','img','audio'):
   t=d.get('href'if tag=='a'else'src')
   if t:self.targets.append(t)
  if tag=='details':self.details.append(d)

def runtime_readme(manifest):
 s=manifest['summary'];rows=[]
 for r in manifest['native_cases']:rows.append(f"| [{r['case']}]({r['validation']}) | {r['name']} | {r['frames']} | {r['checkpoint_count']} | {r['nonempty_artifact_checks']} | {r['audio']['full']['stereo_sample_frames']} | {r['audio']['full']['seconds']:.3f} |")
 text=f'''# 原完整核心：第10轮图形、音频与服务状态回放

从第9轮10案已披露的 `initial.state` 和完整普通按键计划原样重放，仅观察原Nestopia的RGB与PCM输出。本轮没有新增核心内存写入或输入事件。武将ID、数值、坐标与三个RNG游标准备全部继承前轮受控起点，**不是自然战役流程**；旧/新字节逐案链接保存在 [evidence.json](evidence.json)。ROM不可变。

两次原核心回放均通过。首跑 **{s['frames_first_run']:,}帧**、两跑 **{s['frames_both_runs']:,}帧**、**{s['checkpoint_count']}检查点**；**{s['nonempty_repeat_artifact_checks']}份非空canonical产物**双跑逐字节hash相同，其中{ s['phase9_native_artifact_parity_checks']}份PNG/RAM/SRAM/state还与第9轮原文件逐字节相同。20份WAV与40份正式JSON另纳入重复检查。{s['excluded_directory_metadata_JSON']}份包含不同输出路径的snapshotJSON不作重复一致声明；{s['excluded_empty_VRAM']}个空VRAM导出明确排除。

10份完整回放音频累计 **{s['PCM_stereo_sample_frames_full']:,}个stereo sample frames（左右声道样本对）**，即{s['PCM_scalar_channel_samples_full']:,}个单声道标量样本、{s['PCM_bytes_full']:,}字节16bit stereo PCM，采样率48,000Hz。两跑完整PCM样本对总数{s['PCM_stereo_sample_frames_both_runs_full']:,}。10份施放/结果excerpt来自完整音频裁切，覆盖片段重叠，不能再加到完整PCM总数。每帧PCM段及每个libretro audio callback的hash均按原WAV字节重新验证。

| 正式场景 | 计略 | 帧数 | 检查点 | 双跑产物 | 完整PCM样本对 | 秒 |
|---|---|---:|---:|---:|---:|---:|
{chr(10).join(rows)}

每案 `full-flow.wav` 包含完整菜单、施放及返回音序；`cast-and-result.wav` 是effect-before前30帧到result-message的原PCM片段。它们来自 **原Nestopia**，不声称已复原源码合成了相同声波。

`frame-services.json` 逐帧记录原RGB / RAM / SRAM / PCM hash、global7A、NMI78、battle500/501、AP、tactic543、result544、动画04C8、PPU工作位007E、NMI忙007B、IRQ标志0062，以及0300/0304/0310文字队列原字段。0700..07FF音序RAM和0100..011F palette保留hex；不替未验证临时字段赋新语义，也不把队列字段当百分比。

这是帧末观测，**native_internal_CPU_trace=False，source_CPU_comparisons_in_this_receipt=0**。帧内置位/消费可能同帧完成，不能从帧末0值断言没有运行NMI或IRQ。PPU命令排队、同步软件CALL返回、实际PNG出现和PCM播放分别有自己的证据合同。源码CPU对照属于各graphics/audio/nmi/text/scroll回执，不并入本回放统计。

在工作区根目录复跑既有捕获器（不修改它）：

```sh
python3 scripts/capture_service_flow.py '/Users/paulasmith/Downloads/三国志2超级版.nes' --repeat
python3 scripts/build_phase10_browser.py
```

母档、准备回执、核心版本、输入计划、raw文件、WAV、重复hash与排除列表均在各案validation/repeat-validation和本 [汇总回执](validation.json) 内。源码是寄存器/命令编排，PPU/N163/APU的物理时序与PCM合成仍由原核心完成；不扩大为完整硬件或整场自然战役验证。
'''
 (RUN/'README.md').write_text(text)

def main():
 manifest,groups=native();runtime_readme(manifest);modules=[module_data(k)for k in MODULES]
 integration_path=OUT/'source-integration.json';integration=read(integration_path)if integration_path.exists()else{'status':'pending'}
 integration={k:v for k,v in integration.items()if k in('status','rom_cpu_case_count','actual_ROM_CPU_comparison_count','source_guard_count','source_guard_case_count','counts','checks','native_field_comparison_count','native_core_field_comparison_count','limits','failures')}
 old=(ROOT/'analysis/phase9/index.html').read_text();css=re.search(r'<style>([\s\S]+?)</style>',old).group(1)
 css+='\naudio{width:100%;max-width:520px;margin:12px 0} .audio-grid{display:grid;grid-template-columns:1fr 1fr;gap:24px} .timeline{max-height:430px;overflow:auto} .modules{display:flex;gap:12px;flex-wrap:wrap;margin:18px 0} .modules button[aria-pressed=true]{background:#273436;color:white} .tag{font-size:12px;color:#5b6667} .hash{overflow-wrap:anywhere} @media(max-width:700px){.audio-grid{grid-template-columns:1fr}}'
 data={'summary':manifest['summary'],'groups':groups,'modules':modules,'integration':integration,'core':manifest['core'],'limits':manifest['limits']}
 total_link='<a href="README.md">本轮总报告</a>'if(OUT/'README.md').is_file()else'<span class="tag">本轮总报告待整合</span>'
 integration_link='<a href="source-integration.json">统一接入回执</a>'if integration_path.is_file()else'<span class="tag">统一接入回执待落盘</span>'
 html=r'''<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>战斗呈现服务：图形、音序与NMI/IRQ</title><style>STYLES</style></head><body><main>
<small>第十轮 · 原ROM只读 · 原核心RGB / PCM与独立服务源码</small><h1>战斗呈现服务：图形、音序与NMI/IRQ</h1>
<nav><a href="../index.html">总入口</a><a href="../phase9/index.html">阶段9</a>TOTAL_LINK<a href="../../source/README.md">源码合同</a><a href="#runtime">原画面与声音</a><a href="#services">服务边界</a></nav>
<p class="note">10组受控起点、普通按键和原核心完整输出。图形排队、消息就绪、音频寄存器写入与实际PCM分别记录。<strong>本页浏览已保存证据，不运行游戏、玩法公式、CPU、IR或音频合成器。</strong></p>
<div class="metrics" id="metrics"></div><p id="summary"></p>
<h2 id="runtime">1 · 原完整核心画面、声音与状态</h2><p><a href="runtime/README.md">回放方法和准备说明</a> · <a href="runtime/evidence.json">正式manifest</a> · <a href="runtime/validation.json">native汇总回执</a></p>
<label for="runtime-group">正式实验：</label><select id="runtime-group"></select><label for="runtime-left">前检查点：</label><select id="runtime-left"></select><label for="runtime-right">后检查点：</label><select id="runtime-right"></select>
<div class="screens"><figure><img id="runtime-before" alt="原核心前检查点"><figcaption id="before-caption"></figcaption></figure><figure><img id="runtime-after" alt="原核心后检查点"><figcaption id="after-caption"></figcaption></figure></div><p id="transition"></p>
<div class="audio-grid"><section><h3>原施放 / 结果音频片段</h3><audio id="cast-audio" controls preload="metadata"></audio><p id="cast-audio-info"></p><a id="cast-audio-download">下载原WAV</a></section><section><h3>原完整菜单 / 施放 / 返回音频</h3><audio id="full-audio" controls preload="metadata"></audio><p id="full-audio-info"></p><a id="full-audio-download">下载完整WAV</a></section></div>
<p>WAV来自原Nestopia的实际audio callback，48kHz、16bit stereo。裁切片段是完整音频的子区间，样本数不重复相加。</p>
<h3>所选原检查点的服务字段</h3><div class="scroll"><table><thead><tr><th>字段</th><th>前</th><th>后</th></tr></thead><tbody id="service-fields"></tbody></table></div>
<h3>帧末服务状态变化时间线</h3><p id="timeline-info"></p><div class="timeline"><table><thead><tr><th>帧</th><th>battle</th><th>AP</th><th>04C8</th><th>007E</th><th>0300</th><th>0304</th><th>0310</th><th>007B / 0062</th><th>该帧PCM样本对</th></tr></thead><tbody id="timeline-fields"></tbody></table></div>
<p class="note">时间线只列发生变化的帧末字段。0300 / 0304 / 0310按原队列字节显示，不作百分比；007B / 0062帧末为0不等于该帧没有中断。帧内置位与消费可以落在同一帧，原CPU调用顺序须看独立指令对照。</p>
<details><summary>前后原音序RAM / palette字节与hash</summary><pre id="raw-fields"></pre></details><details><summary>继承的受控准备与实际普通按键</summary><pre id="preparation"></pre></details><details><summary>所选场景的音频计数、双跑与排除列表</summary><pre id="case-evidence"></pre></details><p id="runtime-links"></p>
<h2 id="services">2 · 独立服务源码与真实调用边界</h2><div class="modules" id="module-options"></div><h3 id="module-title"></h3><p id="module-entries"></p><div class="metrics" id="module-metrics"></div><p id="module-links"></p>
<ol class="steps"><li><strong>玩法 / 图形生产者</strong><br>产生地图、光标、动画与文字数据，设置原PPU工作位。</li><li><strong>NMI固定服务</strong><br>按原优先级消费队列、写PPU / CHR / DMA端口、分派真实controller与音序服务。</li><li><strong>IRQ / 输入 / readiness</strong><br>需要真实端口输入或实际服务返回；缺失依赖保持等待，不能默认RTS或补写完成。</li><li><strong>原核心呈现</strong><br>本轮独立记录实际PNG、RGB与PCM。源码的寄存器输出不等于已合成同样声波或扫描线时序。</li></ol>
<details><summary>所选服务的差分合同和来源回执</summary><pre id="module-receipt"></pre></details>
<p><a href="../../source/recovered/battle_presentation_services.py">统一呈现服务源码</a> · INTEGRATION_LINK</p><details><summary>统一接入回执（CPU / native字段范围分别计数）</summary><pre id="integration"></pre></details>
<footer>原字节来源、独立源码、原CPU对照、源码guards、原核心帧与PCM分别计数。原核心未录内部CPU指令；本回放没有额外准备写入，也不声明完整自然战役。</footer>
</main><script>const D=PAYLOAD,$=s=>document.querySelector(s),pretty=v=>JSON.stringify(v,null,2),esc=v=>String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c])),num=v=>v==null?'待回执':Number(v).toLocaleString(),hex=v=>Number(v).toString(16).toUpperCase().padStart(2,'0');
const s=D.summary;$('#metrics').innerHTML=[['正式原核心场景',s.native_case_count],['首跑帧',s.frames_first_run],['完整PCM样本对',s.PCM_stereo_sample_frames_full],['非空双跑产物',s.nonempty_repeat_artifact_checks]].map(([l,v])=>`<div class="metric"><small>${l}</small><strong>${num(v)}</strong></div>`).join('');$('#summary').textContent=`${num(s.checkpoint_count)}个同源检查点，${num(s.phase9_native_artifact_parity_checks)}份原PNG/RAM/SRAM/state与阶段9逐字节相同；两跑${num(s.frames_both_runs)}帧。${num(s.WAV_file_checks)}份原WAV有效，${num(s.excluded_empty_VRAM)}个空VRAM和${num(s.excluded_directory_metadata_JSON)}份目录metadata不计双跑一致产物。`;
$('#runtime-group').innerHTML=D.groups.map((g,i)=>`<option value="${i}">${esc(g.case)} · ${esc(g.name)}</option>`).join('');
function selected(){return D.groups[Number($('#runtime-group').value)];}
function options(){const g=selected();const opts=g.captures.map((c,i)=>`<option value="${i}">frame${c.frame} · ${esc(c.label)}</option>`).join('');$('#runtime-left').innerHTML=$('#runtime-right').innerHTML=opts;const index=t=>Math.max(0,g.captures.findIndex(c=>c.label===t));$('#runtime-left').value=String(index('effect-before'));$('#runtime-right').value=String(index(g.case.includes('levelup')?'continuation-1':'result-message'));
 for(const[k,id]of[['cast','cast'],['full','full']]){const a=g.audio[k],src='runtime/'+a.path+'?sha='+a.WAV_sha256,node=$('#'+id+'-audio');node.pause();node.src=src;node.load();$('#'+id+'-audio-info').textContent=`${num(a.stereo_sample_frames)}个stereo样本对 · ${a.seconds.toFixed(3)}秒 · PCM ${num(a.PCM_bytes)}字节`;$('#'+id+'-audio-download').href='runtime/'+a.path;}
 $('#timeline-info').textContent=`${g.frames}帧中${g.state_change_timeline.length}个服务字段变化检查点；RGB实际变化${g.observation.RGB_changed_frames}帧，音序RAM变化${g.observation.audio_RAM_changed_frames}帧。完整每帧RGB/PCM/hash可下载。`;
 $('#timeline-fields').innerHTML=g.state_change_timeline.map(c=>`<tr><td>${c.frame}</td><td>${c.battle_state.join('/')}</td><td>${c.AP}</td><td>${hex(c.animation)}</td><td>${hex(c.PPU_jobs)}</td><td>${hex(c.message_progress)}</td><td>${hex(c.text_draw_cursor)}</td><td>${hex(c.message_type)}</td><td>${hex(c.NMI_busy)} / ${hex(c.IRQ_pending)}</td><td>${c.PCM_stereo_samples}</td></tr>`).join('');$('#preparation').textContent=pretty({controlled_fixture:g.controlled_fixture,natural_campaign:g.natural_campaign,additional_core_memory_writes:0,additional_input_events:0,preparation:g.preparation});$('#case-evidence').textContent=pretty({case:g.case,observation:g.observation,audio:g.audio,nonempty_artifact_checks:g.nonempty_artifact_checks,phase9_native_artifact_parity_checks:g.phase9_native_artifact_parity_checks,excluded_directory_metadata:g.excluded_directory_metadata,empty_VRAM_exports_excluded:g.empty_VRAM_exports_excluded,native_internal_CPU_trace:false,source_CPU_comparisons_in_this_receipt:0});detail();}
function detail(){const g=selected(),l=g.captures[Number($('#runtime-left').value)],r=g.captures[Number($('#runtime-right').value)];for(const[name,c]of[['before',l],['after',r]]){$('#runtime-'+name).src=c.image;$('#'+name+'-caption').textContent=`${g.case} · ${c.label} · frame${c.frame} · 原PNG sha256=${c.PNG_sha256.slice(0,16)}…`;}
 const fields=[['global7A / NMI78',c=>c.global_state+' / '+c.nmi_scene],['battle0500 / 0501',c=>c.battle_state.join('/')],['AP0505',c=>c.AP],['计略0543 / 结果0544',c=>hex(c.tactic)+' / '+hex(c.result)],['动画04C8原值',c=>hex(c.animation)],['PPU工作位007E',c=>hex(c.PPU_jobs)],['文字队列0300原值',c=>hex(c.message_progress)],['文字游标0304原值',c=>hex(c.text_draw_cursor)],['消息队列头0310原值',c=>hex(c.message_type)],['NMI忙007B / IRQ标志0062',c=>hex(c.NMI_busy)+' / '+hex(c.IRQ_pending)],['该帧PCM样本对',c=>num(c.PCM_stereo_samples)],['累计PCM字节',c=>num(c.PCM_stop_byte)]];$('#service-fields').innerHTML=fields.map(([k,f])=>`<tr><th>${esc(k)}</th><td>${esc(f(l))}</td><td>${esc(f(r))}</td></tr>`).join('');$('#transition').textContent=`${l.label} → ${r.label}：AP ${l.AP}→${r.AP}，原动画字节 ${hex(l.animation)}→${hex(r.animation)}；原检查点与播放中的WAV是各自的已保存证据。`;
 $('#raw-fields').textContent=pretty({before:l,after:r});const links=[[g.validation,'回放回执'],[g.repeat_validation,'双跑哈希'],[g.frame_services,'完整逐帧RGB / PCM / 服务字段'],[g.audio_callbacks,'原audio callbacks'],[g.input_plan,'原按键计划']].map(([p,t])=>['runtime/'+p,t]);links.push([l.RAM,'前RAM'],[r.RAM,'后RAM'],[l.state,'前原核心state'],[r.state,'后原核心state']);$('#runtime-links').innerHTML=links.map(([p,t])=>`<a href="${esc(p)}">${esc(t)}</a>`).join(' · ');}
$('#runtime-group').addEventListener('change',options);$('#runtime-left').addEventListener('change',detail);$('#runtime-right').addEventListener('change',detail);options();
$('#module-options').innerHTML=D.modules.map(m=>`<button type="button" data-module="${m.key}" aria-pressed="false">${esc(m.title)}</button>`).join('');function module(key){const m=D.modules.find(x=>x.key===key);document.querySelectorAll('[data-module]').forEach(b=>b.setAttribute('aria-pressed',String(b.dataset.module===key)));$('#module-title').textContent=m.title;$('#module-entries').textContent=m.entries;const r=m.receipt||{};$('#module-metrics').innerHTML=[['状态',m.status],['原CPU对照',r.rom_cpu_case_count],['单列guards',r.source_guard_case_count??r.source_guard_count]].map(([k,v])=>`<div class="metric"><small>${esc(k)}</small><strong>${typeof v==='number'?num(v):esc(v??'待回执')}</strong></div>`).join('');$('#module-links').innerHTML=m.links.map(x=>`<a href="${esc(x.href)}">${esc(x.label)}</a>`).join(' · ');$('#module-receipt').textContent=pretty(r.status?r:{status:'pending',scope:'未落盘的回执不显示为已验证'});}
document.querySelectorAll('[data-module]').forEach(b=>b.addEventListener('click',()=>module(b.dataset.module)));module('graphics');$('#integration').textContent=pretty(D.integration);
</script></body></html>'''
 html=html.replace('STYLES',css).replace('PAYLOAD',json.dumps(data,ensure_ascii=False).replace('</','<\\/')).replace('TOTAL_LINK',total_link).replace('INTEGRATION_LINK',integration_link)
 OUT.mkdir(parents=True,exist_ok=True);(OUT/'index.html').write_text(html);parsed=Parsed();parsed.feed(html)
 assert len(parsed.ids)==len(set(parsed.ids))and all('open'not in d for d in parsed.details)
 js=re.search(r'<script>([\s\S]+)</script>',html).group(1);checked=subprocess.run(['node','--check','--input-type=commonjs'],input=js,text=True,capture_output=True);assert checked.returncode==0,checked.stderr
 for t in parsed.targets:
  if t.startswith('#'):assert t[1:]in parsed.ids
  else:assert(OUT/t.split('?',1)[0]).is_file(),t
 for g in groups:
  for c in g['captures']:
   for k in('image','RAM','SRAM','state'):assert(OUT/c[k].split('?',1)[0]).is_file(),c[k]
  for a in g['audio'].values():assert(RUN/a['path']).is_file()
 for m in modules:
  for l in m['links']:assert(OUT/l['href']).resolve().is_file(),l
 print(json.dumps({'status':'passed','output':'analysis/phase10/index.html','html_sha256':sha(OUT/'index.html'),'html_bytes':len(html.encode()),
    'runtime_case_options':len(groups),'actual_PNG_checkpoints':sum(len(g['captures'])for g in groups),'actual_WAV_controls':2,'actual_WAV_files':20,
    'formal_repeat_artifact_checks':manifest['summary']['nonempty_repeat_artifact_checks'],'PCM_sample_frames_full':manifest['summary']['PCM_stereo_sample_frames_full'],
    'unique_DOM_ids':len(parsed.ids),'closed_details':len(parsed.details),'JS_syntax':'passed','all_static_and_payload_links':'passed',
    'pending_module_receipts':[m['key']for m in modules if m['status']=='pending'],'integration_status':integration['status']},ensure_ascii=False))

if __name__=='__main__':main()

#!/usr/bin/env python3
"""Build the additive phase19 evidence view from completed local receipts."""
from pathlib import Path
import hashlib,json,wave,sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
from build_phase18_browser import HTML as PREVIOUS_HTML
OUT=ROOT/'analysis/phase19';RUN=OUT/'runtime'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def read(p):return json.loads(Path(p).read_text())
def href(p):return '../../'+str(p.relative_to(ROOT))
FIELDS=('frame','global_state','nmi_scene','active_controller','active_main','active_phase',
 'calendar_and_turn_6F00_6F06','domestic_control_6F5B_6F62','cooperation_status_6F8B',
 'all30_city_auxiliary_bytes','all30_city_owners','all30_city_gold','all30_city_reserve',
 'city_counts_by_owner','cooperation_UI_040A_040F','RAM_sha256','SRAM_sha256',
 'RGB_sha256','PCM_sha256','whole_serialized_state_sha256')

def main():
 static=read(OUT/'fields-static/analysis-summary.json')
 original=read(OUT/'fields-static/all-indirect-accesses.json')
 accesses=original['accesses'];assert len(accesses)==1526
 sources=[dict(label=n,href=href(ROOT/'source/recovered'/n)+'?sha='+sha(ROOT/'source/recovered'/n),sha256=sha(ROOT/'source/recovered'/n))for n in('domestic_secondary_services.py','domestic_secondary_integration.py','nestopia_context.py')]
 native=[]
 for folder in sorted(RUN.iterdir()):
  if not folder.is_dir()or not(folder/'validation.json').is_file():continue
  r=read(folder/'validation.json');assert r['status']=='passed'
  frames=read(folder/'frame-services.json');points=read(folder/'checkpoints.json');wav=folder/'full-audio.wav'
  assert len(frames)==r['frames']and len(points)==r['checkpoint_count']
  assert all(set(FIELDS)<=row.keys()for row in frames)
  with wave.open(str(wav),'rb')as w:
   sample_frames=w.getnframes();assert(w.getnchannels(),w.getsampwidth(),w.getframerate())==(2,2,48000)
  for p in points:p['image_href']=href(folder/p['image'])+'?sha='+sha(folder/p['image'])
  native.append(dict(case=folder.name,frames=[{k:row[k]for k in FIELDS}for row in frames],checkpoints=points,
    mother=r.get('mother',r.get('mother_state')),mother_sha256=r.get('mother_sha256'),preparation=r['preparation'],preparation_groups=r['preparation_groups'],plan=read(folder/'input-plan.json'),limits=r.get('limits',r.get('scope')),
    audio=dict(href=href(wav)+'?sha='+sha(wav),sha256=sha(wav),sample_frames=sample_frames),
    links=[dict(href=href(folder/name),label=name)for name in('validation.json','repeat-validation.json','frame-services.json','input-plan.json','preparation.json','secondary-events.json')]))
 assert len(native)>=4
 receipts={n:read(OUT/n)for n in('source-integration.json','services/validation.json','state-format/validation.json','cpu/consumer-sequences.json')}
 for r in receipts.values():
  assert r['status']=='passed'and not r.get('quick',False)
  for path,digest in r['source_sha256'].items():assert sha(ROOT/path)==digest,path
 show={n:{k:v for k,v in r.items()if k not in('rows','cases','artifact_sha256','source_sha256','executed_instruction_positions','upstream')}for n,r in receipts.items()}
 # Keep the full proof files authoritative; the table is a compact per-access
 # view rather than a duplicate of all large domain/trace arrays.
 table=[]
 for r in accesses:
  row={k:r[k]for k in('physical_bank','cpu','classification')}
  row['index_form']='($%02X,X)'%r['pointer_zero_page']if r.get('mode')=='ix'else'($%02X),Y'%r['pointer_zero_page']
  whole=r.get('whole_pointer_values');contract=r.get('address_contract')or{}
  index=r.get('Y_values')
  row.update(op=r.get('op',r.get('opcode','')),pointer_zero_page=r.get('pointer_zero_page',0),
   pointer_kind=r.get('proof_basis'),Y_values=index if index is None or len(index)<=16 else dict(count=len(index),preview=index[:16]),
   address_contract=dict(proof_basis=r.get('proof_basis'),newly_proved_disjoint=r.get('newly_proved_disjoint'),
    whole_pointer_count=None if whole is None else len(whole),whole_pointer_preview=None if whole is None else whole[:8],
    address_summary={k:v for k,v in contract.items()if not isinstance(v,(list,dict))},
    full_contract_file='fields-static/all-indirect-accesses.json'),
   limits=r.get('limits',r.get('reason')))
  table.append(row)
 visible_static={k:v for k,v in static.items()if k in('instruction_count','relational_domain_fixed_point','fixed_point_scope','classification_counts','all_indirect_classification_counts','new_indirect_classification_counts','newly_proved_disjoint_all_count')}
 data=dict(static_summary=visible_static,classifications=original['classification_counts'],accesses=table,
  sources=sources,native=native,frame_fields=FIELDS,source_receipts=show,
  metrics=[('完整间接访问',1526),('具名次级AI入口',4),('原机流程组',len(native)),('原存档快照',receipts['state-format/validation.json']['snapshot_count'])],
  cohort_comparison=read(RUN/'cohort-comparison.json'))
 html=PREVIOUS_HTML.replace('阶段十八','阶段十九')
 html=html.replace('城市辅助字节与实际内政AI','完整指针关系与次级内政AI')
 html=html.replace('城市+1的实际补兵门槛<br>与尾部四字节的访问合同','完整指针关系、次级内政AI<br>与原模拟器实际交涉流程')
 html=html.replace('775个跳转目标边界不计为源码RTS对照；未解析访问不计为已确认字段。','新增16位完整指针合同；原核寄存器快照与软件CPU后续轨迹分别计数。未解析访问不计为已确认字段。')
 html=html.replace('../phase17/index.html','../phase18/index.html').replace('阶段十七','阶段十八')
 html=html.replace('全部589条旧候选','全部1526条间接访问')
 html=html.replace('城市+1参加原内政AI读取的交叠字：','城市+1正式名称仍未证实；已确认它参加原内政AI读取的交叠字：')
 html=html.replace('102个跳转表与原字节','原存档上下文合同').replace('control/control-contracts.json','state-format/validation.json')
 html=html.replace('775个原CPU跳转边界','完整16位指针证明').replace('control/verification.json','fields-static/analysis-summary.json')
 html=html.replace('may-write摘要','具名AI验证').replace('fields-static/call-effect-summaries.json','services/validation.json')
 html=html.replace('条旧候选','条间接访问')
 html=html.replace('一次公开自然母档导入','${current.mother?"公开母档导入":"原冷启动按钮流程"}')
 html=html.replace('同一自然母档的对照','正常物资输送与自然扩城／月轮')
 for identity,label in(('classification','访问归类'),('access-search','地址或指针'),('source-select','源码文件'),('case','实际流程'),('point-a','原帧截图A'),('point-b','原帧截图B'),('frame-a','帧A'),('frame-b','帧B')):
  html=html.replace(f'id="{identity}"',f'id="{identity}" aria-label="{label}"')
 html=html.replace('<section id="native"><h2>','<section id="native"><p>本轮原机完成三组实际输送和一组冷启动扩城／月轮；没有观察到F8。源码／原CPU的四条消费者返回序列单独计数。</p><h2>')
 html=html.replace('<nav><a href="#fields">','<p>新增确认：城市+16是“宝／タカラ”数量。城市+1与+28..31的正式名称继续保留未知。</p><nav><a href="#fields">')
 html=html.replace('`${r.op} (${hex(r.pointer_zero_page||0)}),Y`','`${r.op} ${r.index_form}`')
 html=html.replace('完整合同保留所有候选及其边界','完整合同保留所有访问及其边界')
 html=html.replace('__DATA__',json.dumps(data,ensure_ascii=False,separators=(',',':')).replace('</','<\\/'))
 (OUT/'index.html').write_text(html)
 dependencies={}
 for folder in('fields-static','services','state-format','runtime'):
  for p in(OUT/folder).rglob('*'):
   if p.is_file()and '__pycache__'not in p.parts:dependencies[str(p.relative_to(ROOT))]=sha(p)
 for s in sources:dependencies['source/recovered/'+s['label']]=s['sha256']
 dependencies['analysis/phase19/source-integration.json']=sha(OUT/'source-integration.json')
 dependencies['analysis/phase19/cpu/consumer-sequences.json']=sha(OUT/'cpu/consumer-sequences.json')
 dependencies['scripts/build_phase18_browser.py']=sha(ROOT/'scripts/build_phase18_browser.py')
 result=dict(schema='phase19-browser-static-v1',status='passed',HTML_sha256=sha(OUT/'index.html'),
   builder_sha256=sha(__file__),native_case_count=len(native),source_file_count=len(sources),
   frame_field_count=len(FIELDS),access_count=len(table),dependency_pins=dependencies)
 (OUT/'browser-static-check.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
 print(json.dumps({k:result[k]for k in('status','HTML_sha256','native_case_count','source_file_count','access_count')}))

if __name__=='__main__':main()

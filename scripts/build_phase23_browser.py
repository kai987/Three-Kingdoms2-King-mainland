#!/usr/bin/env python3
"""Build the bounded city-threshold experiment and caller-group browser."""
from pathlib import Path
import hashlib, html, json
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'analysis/phase23'

def read(path):return json.loads(Path(path).read_text())
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def main():
    runtime=read(OUT/'runtime/evidence.json')
    grouping=read(OUT/'fields-static/shared-producer-caller-groups.json')
    static=read(OUT/'fields-static/analysis-summary.json')
    services=read(OUT/'threshold/validation.json')
    integration=read(OUT/'source-integration.json')
    cases=[]
    for item in runtime['native_cases']:
        folder=OUT/'runtime'/item['folder']
        prep=read(folder/'preparation.json')
        initial=(folder/'initial-sram.bin').read_bytes()
        assert initial[0x41:0x44]==bytes((0,184,34))
        start_path=prep['groups'][0]['after']['SRAM'] if prep['groups'] else 'initial-sram.bin'
        start=(folder/start_path).read_bytes()
        assert len(start)==8192
        points=[]
        for point in read(folder/'checkpoints.json'):
            if not point['label'].startswith('actual-frame-'):continue
            f=point['fields']
            points.append(dict(frame=point['frame'],label=point['label'],image=point['image'],
                               state=point['state'],SRAM=point['SRAM'],RAM=point['RAM'],
                               city2_raw32=f['all30_city_records_raw32'][2],
                               officer5_raw12=f['all237_officer_records_raw12'][5],
                               budget=f['domestic_budget_6F5D'],request=f['cooperation_status_6F8B']))
        assert len(points)==item['frames'] and [p['frame']for p in points]==list(range(1,item['frames']+1))
        assert bytes.fromhex(points[0]['city2_raw32'])==start[0x40:0x60]
        cases.append(dict(case=item['case'],frames=item['frames'],points=points,
                          natural=item['natural_gameplay'],preparation=prep['writes'],
                          start_SRAM=start_path,start_city2_raw32=start[0x40:0x60].hex(),
                          effects=item['verified_effects']))
    names=('city_threshold_services.py','city_threshold_integration.py','city_auxiliary_services.py')
    source=''.join('<details class="source"><summary>'+name+'</summary><p><a href="../../source/recovered/'+name+'">完整源文件</a> · SHA256 '+sha(ROOT/'source/recovered'/name)+'</p><pre>'+html.escape((ROOT/'source/recovered'/name).read_text())+'</pre></details>'for name in names)
    data=dict(cases=cases,groups=grouping['groups'],group_count=grouping['group_count'],
              previous_candidate_count=368,remaining_count=static['remaining_access_count'],
              runtime_summary=runtime['summary'])
    page='''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>阶段23 · 城市补兵门槛的判别实验</title><style>
    :root{color-scheme:light;font:16px/1.7 system-ui,sans-serif;color:#21312e;background:#f4f5f0}body{max-width:1160px;margin:32px auto;padding:0 24px}h1{font-size:32px;line-height:1.3}h2{margin-top:42px}a{color:#086353}table{width:100%;border-collapse:collapse;font-size:14px}th,td{padding:8px;text-align:left;border-bottom:1px solid #ccd4cb}thead{background:#e3e9df}section,details{margin:24px 0}input,select,button{font:inherit;padding:7px;max-width:100%}.numbers{display:flex;gap:36px;flex-wrap:wrap}.numbers strong{font-size:32px;display:block}.warning{border-left:4px solid #9b5f24;padding:14px 20px;background:#f6ecdb}.scroll{max-height:420px;overflow:auto}pre{white-space:pre-wrap;overflow-wrap:anywhere;background:#e8ece4;padding:18px;font:13px/1.6 ui-monospace,monospace}.native-grid{display:grid;grid-template-columns:548px minmax(0,1fr);gap:24px;align-items:start}.native-data{min-width:0}.screens{display:flex;gap:32px;flex-wrap:wrap}figure{margin:12px 0}img{width:256px;height:240px;image-rendering:pixelated;border:1px solid #64746a}audio{max-width:100%}summary{cursor:pointer;font-weight:650}footer{border-top:1px solid #ccd4cb;margin-top:40px;padding-top:20px;color:#56655b}@media(max-width:1100px){.native-grid{grid-template-columns:1fr}}@media(max-width:700px){body{padding:0 16px}h1{font-size:27px}}</style>
    <header><a href="../phase22/index.html">阶段22</a> ／ <a href="README.md">完整分析说明</a> ／ <a href="verification.json">最终审计</a><h1>城市补兵门槛的判别实验 · 阶段23</h1><p>沿原BD97完整调用链，比较一组自然续行和五组公开准备数值的原模拟器短路线，并将资源上限与支付依赖还原为具名源码。</p></header>
    <div class="numbers"><span><strong>6</strong>自然／诊断配置</span><span><strong>180</strong>两核心各双跑控制帧</span><span><strong>__REMAIN__</strong>剩余候选访问</span></div>
    <p class="warning">城市 +1、+28..31 的正式含义仍未知。下面的人工数值对照证明局部条件如何工作，不证明这些数值能经普通玩法自然产生，也不把字段命名为保留、填充或未使用。</p>
    <section id="experiments"><h2>能区分假设的实际结果</h2><div class="scroll"><table><thead><tr><th>配置</th><th>真实金币</th><th>+1</th><th>重叠字</th><th>兵700→1000</th><th>原请求结束金币</th></tr></thead><tbody id="experimentsRows"></tbody></table></div><p>金币258时补兵、512时未补；固定金币257时，+1为43／44使重叠字299／300产生不同分支。因此这条门槛不等同于真实金币≥300。补兵通过时先消耗库存300和预算2，金币当帧不变；随后原发展策略另有花金，不能把最终金币差当作补兵收费。</p><p>六案从同一自然存档导入，仅7或8帧无键续行至原request=FF。自然案新增准备0；后五案只准备金币2字节，最后两案另准备+1，共12个配置字节；24次fresh运行合计48次准备写。未准备武将、兵数、库存、名册、PC、RNG或请求。</p><p><a href="runtime/README.md">原模拟器输入与边界</a> · <a href="runtime/validation.json">四进程复跑回执</a> · <a href="cpu-threshold/README.md">独立原CPU精确前序</a></p></section>
    <section id="native"><h2>原画面、保存记录与实验起点</h2><label for="case">配置 </label><select id="case"></select> <label for="point">局部帧 </label><select id="point"></select><p id="caseScope"></p><div class="native-grid"><div class="screens"><figure><img id="originalImage" alt="固定原核心实际画面"><figcaption>固定原核心 · 实际帧</figcaption></figure><figure><img id="observerImage" alt="冻结观察核心同帧画面"><figcaption>独立观察核心 · 同帧</figcaption></figure></div><div class="native-data"><p id="pointCaption"></p><table><thead><tr><th>原始记录中的量</th><th>实际值</th></tr></thead><tbody id="pointValues"></tbody></table><details><summary>完整城2／武将5记录</summary><pre id="rawRecords"></pre></details></div></div><p><a id="pointState">原核心完整状态</a> · <a id="pointSRAM">该帧完整SRAM</a> · <a id="startSRAM">本实验准备后起点SRAM</a> · <a id="preparation">准备写账本</a></p><audio id="audio" controls preload="metadata"></audio><p>每组只有7或8帧，原始录音约0.12～0.13秒。</p><p>initial-sram.bin／initial-fields.json是导入后、人工准备前的共同母态，金币均为8888。诊断起点以上方“准备后起点SRAM”及首帧为准；自然案没有人工准备。原画面没有专门补兵通知，效果由保存内存和调用证据确认。</p><p>冻结观察核心只hook了BD97读取的+1字节；+2与真实金币的帧前／帧末记录属于frame envelope。独立原CPU从新第3帧真实PC继续，负责核对opcode时的两个精确字节；它省略后续硬件NMI时序，未冒称与整帧金币结算完全一致。</p></section>
    <section id="callers"><h2>368项共享生产者与调用链</h2><p>按共享指针、生产链、可信局部入口与incoming caller归并，保留每条原候选及未知。合同仍区分完整入口与裸后缀、raw selector、无额外中断前提、逻辑有效地址及dummy总线读。归组或分类变化不等于新增动态覆盖。</p><label for="search">组／银行／PC／生产者 </label><input id="search" type="search" placeholder="例如 D105、unknown、pointer"><p id="groupCount" aria-live="polite"></p><div id="groups" class="scroll"></div><p>原345个raw窗口仍逐项保留：104个在已证指令内部、13个在已有数据表内部、228个没有已证控制入口。这不是全ROM不可达证明。</p><p><a href="fields-static/README.md">字段关系及前提</a> · <a href="fields-static/shared-producer-caller-groups.json">完整分组账本</a> · <a href="fields-static/remaining-accesses.json">剩余候选</a> · <a href="fields-static/raw345-executability-ledger.json">345窗口来源</a></p></section>
    <section id="source"><h2>新增可读源码</h2><p>新手写149个原字节：城市指针及资源上限D105、金／粮9999上限D69D、金币支付D36F。原BD7A具名父过程保持冻结，通过真实虚方法调用这些依赖；新游戏入口继续保留战后释放与招募越层返回。</p><p>本轮源码及入口比较__SOURCE_CASES__案。原CPU合同、公式模型、原模拟器配置及控制帧分别计数，不把诊断输入当作自然战役可达证明。</p><p><a href="threshold/README.md">原字节／差分边界</a> · <a href="threshold/validation.json">源码比较回执</a> · <a href="source-integration.json">游戏入口比较</a></p>__SOURCE__</section>
    <footer><a href="delivery-manifest.json">v23增量范围</a> · <a href="../../build/三国志2超级版-逆向分析-v23增量.zip">下载v23增量包</a>。需要既有v22基线及用户自己的ROM复现；不重复打包历史大文件，不含原NES、重建NES或完整ROM字节源。v22归档与旧证据保持原哈希。</footer>
    <script id="evidenceData" type="application/json">__DATA__</script><script>
    const d=JSON.parse(document.getElementById('evidenceData').textContent),cs=document.getElementById('case'),ps=document.getElementById('point'),hex=n=>n.toString(16).toUpperCase().padStart(4,'0'),bytes=s=>s.match(/../g).map(x=>parseInt(x,16)),word=(a,i)=>a[i]+256*a[i+1],td=v=>{let e=document.createElement('td');e.textContent=v;return e};
    function cells(values){let tr=document.createElement('tr');values.forEach(v=>tr.append(td(v)));return tr}
    d.cases.forEach((c,i)=>{let o=document.createElement('option');o.value=i;o.textContent=(c.natural?'自然续行':'诊断对照')+' · '+c.case;cs.append(o);let b=bytes(c.start_city2_raw32);document.getElementById('experimentsRows').append(cells([c.natural?'自然':'准备'+c.preparation.length+'字节',word(b,2),b[1],word(b,1),c.effects.gate_acceptance_effect_observed?'是':'否',c.effects.final_gold]));});
    function showPoint(){let c=d.cases[+cs.value],p=c.points[+ps.value],b=bytes(p.city2_raw32),o=bytes(p.officer5_raw12),base='runtime/'+c.case+'/';document.getElementById('originalImage').src=base+'original-control/'+p.image;document.getElementById('observerImage').src=base+'observer/'+p.image;document.getElementById('pointCaption').textContent='局部帧 '+p.frame+'；城2／武将5的实际保存值';document.getElementById('pointValues').replaceChildren(...[['真实金币 +2/+3',word(b,2)],['未命名 +1',b[1]],['重叠字 +1/+2',word(b,1)],['库存兵 +12/+13',word(b,12)],['武将5兵数低10位',word(o,8)&1023],['AI预算',p.budget],['原request',p.request===255?'FF':p.request]].map(x=>cells(x)));document.getElementById('rawRecords').textContent=JSON.stringify({city2_raw32:p.city2_raw32,officer5_raw12:p.officer5_raw12},null,2);document.getElementById('pointState').href=base+'original-control/'+p.state;document.getElementById('pointSRAM').href=base+'original-control/'+p.SRAM;}
    function showCase(){let c=d.cases[+cs.value],base='runtime/'+c.case+'/original-control/';ps.replaceChildren(...c.points.map((p,i)=>{let o=document.createElement('option');o.value=i;o.textContent='帧 '+p.frame;return o}));ps.value=String(Math.min(4,c.points.length-1));document.getElementById('caseScope').textContent=c.natural?'自然案：继承准备0，新增准备0；由真实存档继续。':'诊断案：原存档准备后只改变'+c.preparation.length+'个公开字节；不证明普通玩法自然可达。';document.getElementById('startSRAM').href=base+c.start_SRAM;document.getElementById('preparation').href=base+'preparation.json';document.getElementById('audio').src=base+'full-audio.wav';showPoint();}cs.addEventListener('change',showCase);ps.addEventListener('change',showPoint);showCase();
    const search=document.getElementById('search');function accessText(a){if(typeof a==='number')return hex(a);if(typeof a==='string')return a;return a.cpu!==undefined?(a.physical_bank??'')+':'+hex(a.cpu):JSON.stringify(a)}function addressHex(v){if(typeof v==='number')return v>=32768&&v<=65535?hex(v):'';if(v&&typeof v==='object')return Object.values(v).map(addressHex).join(' ');return ''}function groupText(g){return JSON.stringify(g)+' '+(g.accesses||[]).map(accessText).join(' ')+' '+addressHex(g)}function showGroups(){let q=search.value.trim().toLowerCase(),gs=d.groups.filter(g=>groupText(g).toLowerCase().includes(q));document.getElementById('groupCount').textContent=gs.length+' / '+d.group_count+'组；原'+d.previous_candidate_count+'项逐条保留，当前剩余'+d.remaining_count+'项。';document.getElementById('groups').replaceChildren(...gs.map(g=>{let e=document.createElement('details'),s=document.createElement('summary'),p=document.createElement('pre');s.textContent=g.group_id+' · bank '+g.physical_bank+' · '+g.access_count+'项'+(g.unknown_producer?' · 生产者未决':'');p.textContent=JSON.stringify(g,null,2);e.append(s,p);return e}));}search.addEventListener('input',showGroups);showGroups();
    </script></html>'''
    page=page.replace('__REMAIN__',str(static['remaining_access_count'])).replace('__SOURCE_CASES__',str(services['original_CPU_parent_cases']+integration['original_CPU_parent_cases'])).replace('__SOURCE__',source).replace('__DATA__',json.dumps(data,ensure_ascii=False,separators=(',',':')).replace('</','<\\/'))
    (OUT/'index.html').write_text(page)
    print(json.dumps(dict(status='built',configurations=len(cases),actual_frames=sum(len(c['points'])for c in cases),groups=len(data['groups']),source_modules=3,HTML_sha256=sha(OUT/'index.html'),HTML_bytes=len(page.encode()))))

if __name__=='__main__':main()

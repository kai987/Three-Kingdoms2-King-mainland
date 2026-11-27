"""Create a timing-only copy of the pinned WASM/CPU replay in tests/."""
from pathlib import Path

root = Path(__file__).resolve().parents[2]
source = (root / 'tests/browser_engine_smoke.mjs').read_text(encoding='utf-8')

def replace(old, new):
    global source
    if source.count(old) != 1:
        raise ValueError(f'Expected one profiling insertion point: {old!r}')
    source = source.replace(old, new, 1)

replace("const root=path.resolve", """const profileStarted=performance.now();
const probe={wasm_requests:[],wasm_seen:new Set()};
const root=path.resolve""")
replace("const referenceScript=String.raw\x60", """probe.input_ms=performance.now()-profileStarted;
const referenceScript=String.raw`""")
replace("import json, os, pathlib, sys, tempfile, zipfile", """import json, os, pathlib, sys, tempfile, zipfile
from time import perf_counter
started=perf_counter()
seen=set()
profile=[]""")
replace("    for operation in request['trace']:", """    setup_ms=(perf_counter()-started)*1000
    for operation in request['trace']:
        dispatched=perf_counter()""")
replace("        semantic=json.dumps(json.loads(response['body']),sort_keys=True,ensure_ascii=False,allow_nan=False)", """        normalization=perf_counter()
        semantic=json.dumps(json.loads(response['body']),sort_keys=True,ensure_ascii=False,allow_nan=False)
        digest=sha256(semantic.encode('utf-8')).hexdigest()
        semantic_ms=(perf_counter()-normalization)*1000
        raw=response['body'].encode('utf-8')
        raw_hash=sha256(raw).hexdigest()
        profile.append(dict(dispatch_ms=(normalization-dispatched)*1000, semantic_ms=semantic_ms,
                            raw_sha256=raw_hash, bytes=len(raw), repeated=raw_hash in seen))
        seen.add(raw_hash)""")
replace("response_semantic_sha256=sha256(semantic.encode('utf-8')).hexdigest(),", "response_semantic_sha256=digest,")
replace("rng=json.loads(final['body'])['state']['rng']),ensure_ascii=False))", """rng=json.loads(final['body'])['state']['rng'],
                         profile=dict(setup_ms=setup_ms,requests=profile,
                                      total_ms=(perf_counter()-started)*1000)),ensure_ascii=False))""")
replace(" const result=body===undefined?bridge.dispatch_json(pathname,method):bridge.dispatch_json(pathname,method,body);", """ const dispatched=performance.now();
 const result=body===undefined?bridge.dispatch_json(pathname,method):bridge.dispatch_json(pathname,method,body);
 const dispatchMs=performance.now()-dispatched,converted=performance.now();""")
replace(" trace.push(operation);\n wasmResults.push({status:response.status,response_semantic_sha256:responseSemantic(response.body),", """ const conversionMs=performance.now()-converted,normalized=performance.now();
 const semantic=responseSemantic(response.body);
 const semanticMs=performance.now()-normalized,rawHash=sha(response.body);
 probe.wasm_requests.push({path:pathname,status:response.status,dispatch_ms:dispatchMs,
  conversion_ms:conversionMs,semantic_ms:semanticMs,raw_sha256:rawHash,bytes:Buffer.byteLength(response.body),
  repeated:probe.wasm_seen.has(rawHash)});
 probe.wasm_seen.add(rawHash);
 trace.push(operation);
 wasmResults.push({status:response.status,response_semantic_sha256:semantic,""")
replace(" py=await loadPyodide({indexURL:runtimeDirectory+path.sep});", """ const bootStarted=performance.now();
 py=await loadPyodide({indexURL:runtimeDirectory+path.sep});
 probe.wasm_boot_ms=performance.now()-bootStarted;
 const mountStarted=performance.now();""")
replace(" createBridge('primary');createBridge('isolated');", """ createBridge('primary');createBridge('isolated');
 probe.wasm_mount_ms=performance.now()-mountStarted;""")
replace(" const reference=spawnSync(process.env.PYTHON", """ const cpuStarted=performance.now();
 const reference=spawnSync(process.env.PYTHON""")
replace(" const cpu=JSON.parse(reference.stdout);", """ const cpu=JSON.parse(reference.stdout);
 probe.cpu_replay_ms=performance.now()-cpuStarted;""")
replace(" assert.deepEqual(cpu.rng,rng,'final RNG state and draw count agree');", """ assert.deepEqual(cpu.rng,rng,'final RNG state and draw count agree');
 const sum=(rows,key)=>rows.reduce((total,row)=>total+row[key],0);
 const summary=rows=>({requests:rows.length,bytes:sum(rows,'bytes'),dispatch_ms:sum(rows,'dispatch_ms'),
  semantic_ms:sum(rows,'semantic_ms'),repeated:rows.filter(row=>row.repeated).length,
  repeated_semantic_ms:sum(rows.filter(row=>row.repeated),'semantic_ms')});
 const profile={input_ms:probe.input_ms,wasm_boot_ms:probe.wasm_boot_ms,wasm_mount_ms:probe.wasm_mount_ms,
  wasm:summary(probe.wasm_requests),wasm_conversion_ms:sum(probe.wasm_requests,'conversion_ms'),
  cpu_replay_ms:probe.cpu_replay_ms,cpu_setup_ms:cpu.profile.setup_ms,cpu:summary(cpu.profile.requests),
  raw_equal:probe.wasm_requests.filter((row,index)=>row.raw_sha256===cpu.profile.requests[index].raw_sha256).length,
  trace_sha256:sha(JSON.stringify(trace)),response_semantics_sha256:sha(JSON.stringify(wasmResults.map(row=>row.response_semantic_sha256))),
  save_sha256:sha(finalSave),rng,wall_ms:performance.now()-profileStarted,
  rows:probe.wasm_requests.map((row,index)=>({wasm:row,cpu:cpu.profile.requests[index]}))};
 fs.writeFileSync(process.env.TK2_WASM_PROFILE_REPORT,JSON.stringify(profile,null,2)+'\\n');
 console.log(JSON.stringify({...profile,rows:undefined}));""")

(root / 'tests/_ci_wasm_profile.mjs').write_text(source,encoding='utf-8')

import json
import os
from pathlib import Path
import re
import subprocess
import time


ROOT = Path(__file__).resolve().parents[2]
TEST = Path('tests/browser_ui.spec.mjs')
CLI = 'tools/browser-tests/node_modules/@playwright/test/cli.js'
EVIDENCE = ROOT / 'evidence'
PREFIX = 'TK2_BATTLE_VIEW_AB '

HELPERS = r'''
const contactAB=new WeakMap();
function addContactSample(page,name,sample){
 let profile=contactAB.get(page);
 if(!profile){profile={decisions:[],settle:[],saves:[],reads:[]};contactAB.set(page,profile);}
 profile[name].push(sample);
}
function snapshotDigest(value){
 const json=JSON.stringify(value,(_,item)=>item&&typeof item==='object'&&!Array.isArray(item)
  ? Object.fromEntries(Object.keys(item).sort().map(key=>[key,item[key]])) : item);
 return createHash('sha256').update(json).digest('hex');
}
function contactSaveEvidence(page,label,save,timings={}){
 const {state,checksum,...envelope}=save;
 const {campaign_id,...extension}=state.extension;
 // Browser startup generates an independent campaign ID in each run. The
 // original save and its checksum still go through every existing assertion.
 const comparable={...envelope,state:{...state,extension}};
 addContactSample(page,'saves',{label,sha256:snapshotDigest(comparable),rng:state.rng,...timings});
}
async function contactMeasureSave(page,label){
 const started=performance.now();
 const {save,workerMs,jsonMs}=await page.evaluate(async()=>{
  const start=performance.now(),response=await fetch('/api/save'),received=performance.now();
  if(!response.ok)throw Error('Battle save inspection failed');
  const save=await response.json();
  return {save,workerMs:received-start,jsonMs:performance.now()-received};
 });
 contactSaveEvidence(page,label,save,{workerMs,jsonMs,wallMs:performance.now()-started});
 return save;
}
test.afterEach(async({page})=>{
 console.log('TK2_BATTLE_VIEW_AB '+JSON.stringify(contactAB.get(page)));
});

'''


def instrument(source, variant):
    def replace(old, new):
        nonlocal source
        if source.count(old) != 1:
            raise ValueError(f'Expected exactly one profiling marker for {old!r}')
        source = source.replace(old, new, 1)

    replace("import assert from 'node:assert/strict';", "import assert from 'node:assert/strict';\nimport {createHash} from 'node:crypto';")
    replace('const errors=new WeakMap();', HELPERS + 'const errors=new WeakMap();')
    replace("async function tacticalSave(page){return page.evaluate(async()=>{const response=await fetch('/api/save');if(!response.ok)throw Error('Tactical raw save inspection failed');return response.json();});}",
            "async function tacticalSave(page){return contactMeasureSave(page,'tactical');}")
    replace(" const read=()=>page.evaluate(async()=>{const r=await fetch('/api/save');if(!r.ok)throw Error('Battle save inspection failed');return r.json();});",
            " const read=()=>contactMeasureSave(page,'layout');")
    scope_var = 'placementStage' if variant == 'baseline' else 'viewScope'
    start = source.index('async function tacticalRead(')
    end = source.index('async function tacticalSave(', start)
    before = source[start:end]
    measured = before.replace(f'async function tacticalRead(page,{scope_var}){{\n return page.evaluate(async stage=>{{',
                              f'async function tacticalRead(page,{scope_var}){{\n const started=performance.now();\n const {{snapshot,measurements}}=await page.evaluate(async stage=>{{')
    measured = measured.replace("  const [saveResponse,stateResponse]=await Promise.all([fetch('/api/save'),fetch('/api/state')]);", '''  const browserStart=performance.now();
  const recordFetch=async path=>{
   const started=performance.now(),response=await fetch(path);
   return {response,ms:performance.now()-started};
  };
  const [saveFetch,stateFetch]=await Promise.all([recordFetch('/api/save'),recordFetch('/api/state')]);
  const saveResponse=saveFetch.response,stateResponse=stateFetch.response;''')
    measured = measured.replace('  const value=await stateResponse.json(),view=value.view||value,save=await saveResponse.json();', '''  const parseStarted=performance.now();
  const value=await stateResponse.json(),view=value.view||value;
  const stateParsed=performance.now(),save=await saveResponse.json(),saveParsed=performance.now();
  const tracked=snapshot=>({snapshot,measurements:{saveWorkerMs:saveFetch.ms,stateWorkerMs:stateFetch.ms,
   stateParseMs:stateParsed-parseStarted,saveParseMs:saveParsed-stateParsed,browserMs:performance.now()-browserStart}});''')
    measured, substitutions = re.subn(r'return (\{save,view.*?\});', r'return tracked(\1);', measured, flags=re.DOTALL)
    assert substitutions == (3 if variant == 'baseline' else 4)
    measured = measured.replace(f' }},{scope_var});\n}}', f''' }},{scope_var});
 const wallMs=performance.now()-started;
 const sha256=snapshotDigest({{battle:snapshot.view.game?.battle,board:snapshot.view.catalog.battle_tactical}});
 addContactSample(page,'reads',{{scope:{scope_var}??'full',sha256,wallMs,...measurements}});
 contactSaveEvidence(page,'read',snapshot.save);
 return snapshot;
}}''')
    assert 'return snapshot;' in measured and 'const tracked=' in measured and 'const {snapshot,measurements}=' in measured
    replace(before, measured)
    replace('async function tacticalSettle(page,{returnToMacro=false}={}){',
            'async function tacticalSettle(page,{returnToMacro=false}={}){\n const settleStarted=performance.now();')
    replace(' await waitIdle(page);await tacticalDismiss(page);\n if(returnToMacro){', ''' await waitIdle(page);
 const idle=performance.now();await tacticalDismiss(page);
 addContactSample(page,'settle',{waitMs:idle-settleStarted,eventMs:performance.now()-idle,returnToMacro});
 if(returnToMacro){''')

    old = "   const pending=await page.evaluate(async()=>{const r=await fetch('/api/save');const s=(await r.json()).state;return !!s.battle?.extended?.siege;});"
    read = '''   const sample=await page.evaluate(async()=>{
    const revision=view.revision, displayed=Boolean(view.game?.battle?.extended?.siege);
    const started=performance.now(),response=await fetch('/api/save'),received=performance.now();
    if(!response.ok)throw Error('Contact save inspection failed');
    const state=(await response.json()).state;
    return {pending:Boolean(state.battle?.extended?.siege),displayed,revision,
     revisionAfter:view.revision,workerMs:received-started,jsonMs:performance.now()-received};
   });'''
    check = '''
   expect(sample.revisionAfter).toBe(sample.revision,'No command advanced while the independent save was read');
   expect(sample.displayed).toBe(sample.pending,'The settled Worker view agrees with the independent full save');'''
    replace(old, '   const readStarted=performance.now();\n' + read + '''
   addContactSample(page,'decisions',{...sample,wallMs:performance.now()-readStarted});''' + check + '''
   const pending=sample.pending;''')
    return source


def run_trial(project, title, trial, variant):
    command = ['node', CLI, 'test', '--config', 'tools/browser-tests/playwright.config.mjs',
               '--project', project, '--grep', re.escape(title).replace(r'\ ', ' ') + '$', '--reporter', 'json']
    log = EVIDENCE / f'{trial}-{variant}.json'
    with log.open('w') as output, (EVIDENCE / f'{trial}-{variant}.stderr.txt').open('w') as errors:
        started = time.perf_counter()
        result = subprocess.run(command, cwd=ROOT, stdout=output, stderr=errors, timeout=340)
        wall_ms = (time.perf_counter() - started) * 1000
    report = json.loads(log.read_text())
    if result.returncode != 0:
        raise RuntimeError(f'{project} {variant} trial {trial} failed; see the test evidence')
    assert report['stats']['expected'] == 1 and report['stats']['unexpected'] == 0
    spec = report['suites'][0]['specs'][0]
    assert spec['title'] == title and spec['ok']
    test = spec['tests'][0]
    assert test['projectName'] == project and len(test['results']) == 1
    attempt = test['results'][0]
    assert attempt['status'] == 'passed'
    output = ''.join(entry.get('text', '') for entry in attempt['stdout'])
    profile = json.loads(next(line.removeprefix(PREFIX) for line in output.splitlines() if line.startswith(PREFIX)))
    decisions = profile['decisions']
    reads = profile['reads']
    expected_scope = 'full' if variant == 'baseline' else 'battle'
    affected = [row for row in reads if row['scope'] == expected_scope]
    assert affected and all(row['scope'] in ('before', 'after', expected_scope) for row in reads)
    signature = {
        'decisions': [[row['revision'], row['pending']] for row in decisions],
        'saves': [[row['label'], row['sha256'], row['rng']] for row in profile['saves']],
        'view_parts': [row['sha256'] for row in reads],
    }
    summary = dict(trial=trial, variant=variant, test_ms=attempt['duration'], wall_ms=wall_ms,
                   checks=len(decisions), contacts=sum(row['pending'] for row in decisions),
                   contact_save_requests=sum('workerMs' in row for row in decisions),
                   contact_worker_ms=sum(row.get('workerMs', 0) for row in decisions),
                   contact_json_ms=sum(row.get('jsonMs', 0) for row in decisions),
                   contact_wall_ms=sum(row['wallMs'] for row in decisions),
                   settle_wait_ms=sum(row['waitMs'] for row in profile['settle']),
                   event_wait_ms=sum(row['eventMs'] for row in profile['settle']),
                   full_save_checks=len(profile['saves']), affected_reads=len(affected),
                   affected_state_worker_ms=sum(row['stateWorkerMs'] for row in affected),
                   affected_save_worker_ms=sum(row['saveWorkerMs'] for row in affected),
                   affected_state_json_ms=sum(row['stateParseMs'] for row in affected),
                   affected_save_json_ms=sum(row['saveParseMs'] for row in affected),
                   affected_wall_ms=sum(row['wallMs'] for row in affected),
                   affected_playwright_ms=sum(row['wallMs']-row['browserMs'] for row in affected))
    print(json.dumps(summary), flush=True)
    return summary, signature


def main():
    base = os.environ['BASE_COMMIT']
    project, case = os.environ['BROWSER_PROJECT'], os.environ['BROWSER_CASE']
    registry = json.loads((ROOT / 'tools/browser-tests/cases.json').read_text())
    title = next(row['title'] for row in registry['cases'] if row['id'] == case)
    smoke = ROOT / TEST
    candidate = smoke.read_text()
    baseline = subprocess.check_output(['git', 'show', f'{base}:{TEST}'], cwd=ROOT, text=True)
    sources = {'baseline': instrument(baseline, 'baseline'), 'optimized': instrument(candidate, 'optimized')}
    summary, reference, coverage = [], None, None
    try:
        for name, source in sources.items():
            smoke.write_text(source)
            inventory = json.loads(subprocess.check_output(['node', 'tools/browser-tests/verify-shards.mjs', project], cwd=ROOT))
            assert inventory['selected'] == 55 and len(inventory['shards']) == 3
            if coverage is None:
                coverage = inventory
            assert coverage == inventory
            (EVIDENCE / f'coverage-{name}.json').write_text(json.dumps(inventory, indent=2) + '\n')

        order = ('baseline', 'optimized', 'optimized', 'baseline') if case == 'battle-movement' else ('baseline', 'optimized')
        for trial, variant in enumerate(order, start=1):
            smoke.write_text(sources[variant])
            row, signature = run_trial(project, title, trial, variant)
            (EVIDENCE / f'{trial}-{variant}-parity.json').write_text(json.dumps(signature, indent=2) + '\n')
            assert row['contact_save_requests'] == row['checks']
            if reference is None:
                reference = signature
            if signature != reference:
                changes = [key for key in signature if signature[key] != reference[key]]
                raise ValueError(f'{case} {project} {variant} trial {trial} differs in {changes}')
            summary.append(row)
            (EVIDENCE / 'metrics.json').write_text(json.dumps(summary, indent=2) + '\n')
            subprocess.run(['python', '-B', 'tools/ci/gate.py', 'artifact', '--root', 'build/web',
                            '--head', base, '--content-sha256', os.environ['CONTENT_SHA']], cwd=ROOT, check=True)
    finally:
        smoke.write_text(candidate)


if __name__ == '__main__':
    main()

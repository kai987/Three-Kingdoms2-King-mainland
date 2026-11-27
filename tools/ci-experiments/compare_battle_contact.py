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
PREFIX = 'TK2_CONTACT_AB '

HELPERS = r'''
const contactAB=new WeakMap();
function addContactSample(page,name,sample){
 let profile=contactAB.get(page);
 if(!profile){profile={decisions:[],settle:[],saves:[]};contactAB.set(page,profile);}
 profile[name].push(sample);
}
function contactSaveEvidence(page,label,save,timings={}){
 const {state,checksum,...envelope}=save;
 const {campaign_id,...extension}=state.extension;
 // Browser startup generates an independent campaign ID in each run. The
 // original save and its checksum still go through every existing assertion.
 const comparable={...envelope,state:{...state,extension}};
 const json=JSON.stringify(comparable,(_,value)=>value&&typeof value==='object'&&!Array.isArray(value)
  ? Object.fromEntries(Object.keys(value).sort().map(key=>[key,value[key]])) : value);
 addContactSample(page,'saves',{label,sha256:createHash('sha256').update(json).digest('hex'),rng:state.rng,...timings});
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
 console.log('TK2_CONTACT_AB '+JSON.stringify(contactAB.get(page)));
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
    replace('async function tacticalRead(page,placementStage){\n return page.evaluate(async stage=>{',
            'async function tacticalRead(page,placementStage){\n const started=performance.now();\n const snapshot=await page.evaluate(async stage=>{')
    replace(' },placementStage);\n}', " },placementStage);\n contactSaveEvidence(page,'read',snapshot.save,{wallMs:performance.now()-started});\n return snapshot;\n}")
    replace('async function tacticalSettle(page,{returnToMacro=false}={}){',
            'async function tacticalSettle(page,{returnToMacro=false}={}){\n const settleStarted=performance.now();')
    replace(' await waitIdle(page);await tacticalDismiss(page);\n if(returnToMacro){', ''' await waitIdle(page);
 const idle=performance.now();await tacticalDismiss(page);
 addContactSample(page,'settle',{waitMs:idle-settleStarted,eventMs:performance.now()-idle,returnToMacro});
 if(returnToMacro){''')

    if variant == 'baseline':
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
    else:
        old = '   const pending=await page.evaluate(()=>Boolean(view.game?.battle?.extended?.siege));'
        read = '''   const sample=await page.evaluate(()=>({pending:Boolean(view.game?.battle?.extended?.siege),revision:view.revision}));'''
        check = ''
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
    assert decisions, 'The test must exercise the changed routing branch'
    signature = {
        'decisions': [[row['revision'], row['pending']] for row in decisions],
        'saves': [[row['label'], row['sha256'], row['rng']] for row in profile['saves']],
    }
    summary = dict(trial=trial, variant=variant, test_ms=attempt['duration'], wall_ms=wall_ms,
                   checks=len(decisions), contacts=sum(row['pending'] for row in decisions),
                   contact_save_requests=sum('workerMs' in row for row in decisions),
                   contact_worker_ms=sum(row.get('workerMs', 0) for row in decisions),
                   contact_json_ms=sum(row.get('jsonMs', 0) for row in decisions),
                   contact_wall_ms=sum(row['wallMs'] for row in decisions),
                   settle_wait_ms=sum(row['waitMs'] for row in profile['settle']),
                   event_wait_ms=sum(row['eventMs'] for row in profile['settle']),
                   full_save_checks=len(profile['saves']))
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

        for trial, variant in enumerate(('baseline', 'optimized', 'optimized', 'baseline'), start=1):
            smoke.write_text(sources[variant])
            row, signature = run_trial(project, title, trial, variant)
            (EVIDENCE / f'{trial}-{variant}-parity.json').write_text(json.dumps(signature, indent=2) + '\n')
            expected_requests = row['checks'] if variant == 'baseline' else 0
            assert row['contact_save_requests'] == expected_requests
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

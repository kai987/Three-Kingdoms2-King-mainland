"""Compare only the projected view for the three real battlefield services."""
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[2]
TEST = Path('tests/browser_soldier_ui.spec.mjs')
CLI = 'tools/browser-tests/node_modules/@playwright/test/cli.js'
EVIDENCE = ROOT / 'evidence'


def instrument(source, optimized):
    def replace(old, new):
        nonlocal source
        if source.count(old) != 1:
            raise ValueError(f'Expected one profiling marker for {old!r}')
        source = source.replace(old, new, 1)

    replace("import {execFileSync} from 'node:child_process';",
            "import {execFileSync} from 'node:child_process';\nimport {createHash} from 'node:crypto';")
    replace('const fixtures=new Map(),pageErrors=new WeakMap();', '''const fixtures=new Map(),pageErrors=new WeakMap();
function facilityDigest(value){
 const comparable=JSON.stringify(value,(_,row)=>row&&typeof row==='object'&&!Array.isArray(row)
  ? Object.fromEntries(Object.keys(row).sort().map(key=>[key,row[key]])) : row);
 return createHash('sha256').update(comparable).digest('hex');
}''')

    start = source.index('async function read(page,withView=true,')
    end = source.index('async function load(', start)
    original = source[start:end]
    callback = 'async({sourceKinds,facilityActor})' if optimized else 'async sourceKinds'
    argument = '{sourceKinds:openingTroopSources,facilityActor}' if optimized else 'openingTroopSources'
    measured = original.replace(f' return page.evaluate({callback}=>{{',
                                f' const started=performance.now();\n const {{snapshot,phases}}=await page.evaluate({callback}=>{{')
    measured = measured.replace("  const [a,b]=await Promise.all([fetch('/api/save'),fetch('/api/state')]);", '''  const browserStarted=performance.now();
  const request=async pathname=>{
   const started=performance.now(),response=await fetch(pathname);
   return {response,workerMs:performance.now()-started};
  };
  const [saveRequest,stateRequest]=await Promise.all([request('/api/save'),request('/api/state')]);
  const a=saveRequest.response,b=stateRequest.response;''')
    measured = measured.replace('  const state=await b.json(),save=await a.json(),view=state.view||state;', '''  const parseStarted=performance.now(),state=await b.json(),stateParsed=performance.now();
  const save=await a.json(),saveParsed=performance.now(),view=state.view||state;
  const measured=snapshot=>({snapshot,phases:{
   saveWorkerMs:saveRequest.workerMs,stateWorkerMs:stateRequest.workerMs,
   stateParseMs:stateParsed-parseStarted,saveParseMs:saveParsed-stateParsed,
   browserMs:performance.now()-browserStarted
  }});''')
    measured, outputs = re.subn(r'return (\{save,view.*?\});', r'return measured(\1);',
                                measured, flags=re.DOTALL)
    assert outputs == (3 if optimized else 2)
    measured = measured.replace(f' }},{argument});\n}}', f''' }},{argument});
 const wallMs=performance.now()-started;
 console.log('TK2_FACILITY_READ '+JSON.stringify({{...phases,wallMs,playwrightMs:wallMs-phases.browserMs}}));
 return snapshot;
}}''')
    assert 'const {snapshot,phases}=' in measured and 'const measured=snapshot=>' in measured
    assert 'TK2_FACILITY_READ' in measured and 'return snapshot;' in measured
    replace(original, measured)
    proof = "  proof.push({kind,actor:value.actor,site:value.site,payer,before_gold:before.save.state.cities[payer].gold,after_gold:current.save.state.cities[payer].gold,before_rng:before.save.state.rng,after_rng:current.save.state.rng});"
    replace(proof, proof + '''
  console.log('TK2_FACILITY_PARITY '+JSON.stringify({
   kind,quote:facilityDigest(quote),before:facilityDigest(before.save),after:facilityDigest(current.save),
   beforeRng:before.save.state.rng,afterRng:current.save.state.rng
  }));''')
    return source


def trial(project, title, variant, ordinal):
    name = f'{ordinal}-{variant}'
    args = ['node', CLI, 'test', '--config', 'tools/browser-tests/playwright.config.mjs',
            '--project', project, '--grep', re.escape(title).replace(r'\ ', ' ') + '$', '--reporter', 'json']
    report_path = EVIDENCE / f'{name}.json'
    started = time.perf_counter()
    with report_path.open('w') as output, (EVIDENCE / f'{name}.stderr.txt').open('w') as errors:
        result = subprocess.run(args, cwd=ROOT, stdout=output, stderr=errors, timeout=310)
    wall_ms = (time.perf_counter() - started) * 1000
    if result.returncode != 0:
        raise RuntimeError(f'{project} {name} failed. See the Playwright report in the evidence artifact.')
    report = json.loads(report_path.read_text())
    assert report['stats']['expected'] == 1 and report['stats']['unexpected'] == 0
    spec = report['suites'][0]['specs'][0]
    assert spec['title'] == title and spec['ok']
    test = spec['tests'][0]
    assert test['projectName'] == project and len(test['results']) == 1
    result = test['results'][0]
    assert result['status'] == 'passed'
    stdout = ''.join(entry.get('text', '') for entry in result['stdout']).splitlines()
    def rows(prefix):
        return [json.loads(line.removeprefix(prefix)) for line in stdout if line.startswith(prefix)]
    phases = rows('TK2_FACILITY_READ ')
    signatures = rows('TK2_FACILITY_PARITY ')
    assert len(phases) == 3
    assert [row['kind'] for row in signatures] == ['hospital', 'market', 'armory']
    totals = {key: sum(row[key] for row in phases) for key in phases[0]}
    summary = dict(ordinal=ordinal, variant=variant, caseMs=result['duration'], invocationMs=wall_ms,
                   saveRequests=3, stateRequests=3, phases=phases, totals=totals)
    print(json.dumps(summary), flush=True)
    (EVIDENCE / f'{name}-parity.json').write_text(json.dumps(signatures, indent=2) + '\n')
    return summary, signatures


def main():
    base = os.environ['BASE_COMMIT']
    project = os.environ['BROWSER_PROJECT']
    registry = json.loads((ROOT / 'tools/browser-tests/cases.json').read_text())
    title = next(case['title'] for case in registry['cases'] if case['id'] == 'battlefield-services')
    path = ROOT / TEST
    candidate = path.read_text()
    baseline = subprocess.check_output(['git', 'show', f'{base}:{TEST}'], cwd=ROOT, text=True)
    copies = {'baseline': instrument(baseline, False), 'optimized': instrument(candidate, True)}
    coverage, expected, trials = None, None, []
    try:
        for name, source in copies.items():
            path.write_text(source)
            inventory = json.loads(subprocess.check_output(['node', 'tools/browser-tests/verify-shards.mjs', project], cwd=ROOT))
            assert inventory['selected'] == 55 and len(inventory['shards']) == 3
            if coverage is None:
                coverage = inventory
            assert inventory == coverage
            (EVIDENCE / f'coverage-{name}.json').write_text(json.dumps(inventory, indent=2) + '\n')
        for ordinal, name in enumerate(('baseline', 'optimized', 'optimized', 'baseline'), 1):
            path.write_text(copies[name])
            summary, signature = trial(project, title, name, ordinal)
            if expected is None:
                expected = signature
            assert signature == expected, 'The three facility quotes, complete saves or RNG differ from baseline'
            subprocess.run([sys.executable, '-B', 'tools/ci/gate.py', 'artifact', '--root', 'build/web',
                            '--head', base, '--content-sha256', os.environ['CONTENT_SHA']], cwd=ROOT, check=True)
            trials.append(summary)
            (EVIDENCE / 'metrics.json').write_text(json.dumps(trials, indent=2) + '\n')
    finally:
        path.write_text(candidate)


if __name__ == '__main__':
    main()

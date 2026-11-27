import json
import os
from pathlib import Path
import subprocess
import sys
import time


ROOT = Path(__file__).resolve().parents[2]
SMOKE = 'tests/browser_engine_smoke.mjs'
EVIDENCE = ROOT / 'evidence'
INPUT_COMMIT = os.environ['INPUT_COMMIT']


def instrument(source, raw_body):
    def insert(before, fragment):
        nonlocal source
        if source.count(before) != 1:
            raise ValueError(f'Expected exactly one timing marker for {before!r}')
        source = source.replace(before, fragment + before, 1)

    insert('const root=path.resolve', '''const experimentStarted=performance.now();
const responseHashes=[];
let transferMs=0;
''')
    # A fixed seed also makes the field order of non-canonical JSON comparable.
    insert('indexURL:runtimeDirectory+path.sep', 'env:{PYTHONHASHSEED:process.env.PYTHONHASHSEED},')
    insert(' let response;\n', ' const transferStarted=performance.now();\n')
    insert(' trace.push(operation);\n', f''' transferMs+=performance.now()-transferStarted;
 responseHashes.push(sha({raw_body}));
''')
    insert(' const reference=spawnSync', ' const replayStarted=performance.now();\n')
    insert(' assert.ifError(reference.error);', ' const replayMs=performance.now()-replayStarted;\n')
    insert(' console.log(JSON.stringify({ok:true,pyodide:', ''' console.log('SMOKE_EVIDENCE '+JSON.stringify({
  wasm_ms:replayStarted-experimentStarted,
  cpu_replay_ms:replayMs,
  response_transfer_ms:transferMs,
  parity:{trace_sha256:sha(JSON.stringify(trace)),
   responses:wasmResults.map((result,index)=>({path:trace[index].path,method:trace[index].method,
    status:result.status,raw_sha256:responseHashes[index],semantic_sha256:result.response_semantic_sha256,
    exact_save_sha256:'save' in result?sha(result.save):null})),
   final_save_sha256:sha(finalSave),rng}
 }));
''')
    return source


def run_smoke(script, variant, trial):
    log = EVIDENCE / f'{trial}-{variant}.log'
    rss = EVIDENCE / f'{trial}-{variant}.rss-kib.txt'
    started = time.perf_counter()
    with log.open('w', encoding='utf-8') as output:
        result = subprocess.run(
            ['/usr/bin/time', '-f', '%M', '-o', str(rss), 'node', str(script), 'build/web'],
            cwd=ROOT, stdout=output, stderr=subprocess.STDOUT, timeout=300,
        )
    elapsed_ms = (time.perf_counter() - started) * 1000
    lines = log.read_text(encoding='utf-8').splitlines()
    if result.returncode != 0:
        raise RuntimeError(f'{variant} smoke failed in trial {trial}: {lines[-1][-600:]}')
    details = json.loads(next(line.removeprefix('SMOKE_EVIDENCE ') for line in lines
                              if line.startswith('SMOKE_EVIDENCE ')))
    result = json.loads(next(line for line in lines if line.startswith('{"ok":true,')))
    parity = details.pop('parity')
    details.update(trial=trial, variant=variant, wall_ms=elapsed_ms, max_rss_kib=int(rss.read_text()))
    print(json.dumps(details), flush=True)
    return details, parity, result


def main():
    baseline = subprocess.check_output(['git', 'show', f'{INPUT_COMMIT}:{SMOKE}'], cwd=ROOT, text=True)
    sources = {
        'baseline': instrument(baseline, 'response.body'),
        'optimized': instrument((ROOT / SMOKE).read_text(encoding='utf-8'), 'responseBody'),
    }
    candidate_hash = (EVIDENCE / 'candidate-sha256.txt').read_text().strip()
    script = ROOT / 'tests' / '_ci_wasm_smoke_ab.mjs'
    timings = []
    expected = None
    try:
        for trial, variant in enumerate(('baseline', 'optimized', 'optimized', 'baseline'), start=1):
            script.write_text(sources[variant], encoding='utf-8')
            details, parity, summary = run_smoke(script, variant, trial)
            if expected is None:
                expected = (parity, summary)
                (EVIDENCE / 'parity.json').write_text(json.dumps(parity, indent=2) + '\n')
                (EVIDENCE / 'smoke-summary.json').write_text(json.dumps(summary, indent=2) + '\n')
            if (parity, summary) != expected:
                reference_parity, reference_summary = expected
                changed_fields = [field for field in parity if parity[field] != reference_parity[field]]
                changed_responses = [
                    [index, actual['path'], [field for field in actual if actual[field] != previous[field]]]
                    for index, (actual, previous) in enumerate(zip(parity['responses'], reference_parity['responses']), 1)
                    if actual != previous
                ]
                raise ValueError(f'{variant} trial {trial} differs in {changed_fields}, responses {changed_responses}, '
                                 f'summary changed: {summary != reference_summary}')
            subprocess.check_call([
                sys.executable, '-B', 'tools/ci/gate.py', 'artifact', '--root', 'build/web',
                '--head', INPUT_COMMIT, '--content-sha256', candidate_hash,
            ], cwd=ROOT, stdout=subprocess.DEVNULL)
            timings.append(details)
            (EVIDENCE / 'timings.json').write_text(json.dumps(timings, indent=2) + '\n')
    finally:
        script.unlink(missing_ok=True)


if __name__ == '__main__':
    main()

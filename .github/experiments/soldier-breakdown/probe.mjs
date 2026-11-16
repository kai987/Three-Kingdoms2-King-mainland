import {writeFile} from 'node:fs/promises';

let data;

export function begin() {
  data = {time_origin: performance.timeOrigin, start: performance.now(), spans: [], sections: [], documents: [], samples: []};
}

export function stamp() {
  return performance.now();
}

export function span(name, start, details = {}, end = stamp()) {
  data.spans.push({name, start, end, ...details});
}

export async function time(name, work, details) {
  const start = stamp();
  try {
    return await work();
  } finally {
    span(name, start, details);
  }
}

export function section(name) {
  data.sections.push({name, start: stamp()});
}

export async function observeWorker(page) {
  await page.addInitScript(() => {
    const clock = () => {
      const original = globalThis.__pwClock?.builtins.performance ?? performance;
      return original.timeOrigin + original.now();
    };
    const log = globalThis.__soldierProfile = {worker: [], samples: []};
    globalThis.Worker = new Proxy(globalThis.Worker, {
      construct(target, args, newTarget) {
        const start = clock();
        const worker = Reflect.construct(target, args, newTarget);
        if (!new URL(args[0], location.href).pathname.endsWith('/browser-engine-worker.js')) return worker;
        const pending = new Map();
        worker.addEventListener('message', ({data: message}) => {
          if (message?.type === 'ready') log.worker.push({path: 'boot', start, end: clock()});
          if (message?.type !== 'response' || !pending.has(message.id)) return;
          const end = clock();
          const request = pending.get(message.id);
          pending.delete(message.id);
          log.worker.push({...request, end, status: message.status});
        });
        const send = worker.postMessage;
        worker.postMessage = function (message, ...rest) {
          if (message?.type === 'request') {
            const kind = message.path === '/api/command' ? JSON.parse(message.body).kind : undefined;
            pending.set(message.id, {path: message.path, kind, start: clock()});
          }
          return Reflect.apply(send, this, [message, ...rest]);
        };
        return worker;
      },
    });
  });
}

export async function documentTimings(page) {
  const document = await page.evaluate(() => globalThis.__soldierProfile?.worker ?? []);
  if (document.length) data.documents.push(document);
}

export function sample(mode, tick, result, start, end) {
  if (!result) return;
  data.samples.push({mode, tick, start, end, browser_ms: result.soldierProfileBrowserMs,
    png_bytes: result.png.length + (result.reference_png?.length ?? 0)});
  delete result.soldierProfileBrowserMs;
}

async function measurePngReturn(page, sizes) {
  const count = await page.evaluate(() => globalThis.__soldierProfile.samples.length);
  if (count !== sizes.length) throw Error('PNG sample count changed');
  const readSample = (index, includePng) => page.evaluate(({index, includePng}) => {
    const frame = globalThis.__soldierProfile.samples[index];
    return {...frame, png: includePng ? frame.png : '',
      reference_png: includePng || frame.reference_png === null ? frame.reference_png : ''};
  }, {index, includePng});

  // Warm both return shapes, then alternate pair order and reverse the sample
  // order across passes. Both variants return identical frame metadata.
  for (let index = 0; index < Math.min(count, 8); index++) {
    await readSample(index, true);
    await readSample(index, false);
  }
  const passes = [];
  for (let pass = 0; pass < 4; pass++) {
    const pairs = [];
    for (let offset = 0; offset < count; offset++) {
      const index = pass % 2 ? count - 1 - offset : offset;
      const fullFirst = (offset + Number(pass >= 2)) % 2 === 0;
      const durations = {};
      let full, empty;
      for (const includePng of [fullFirst, !fullFirst]) {
        const start = stamp();
        const result = await readSample(index, includePng);
        durations[includePng ? 'full_ms' : 'empty_ms'] = stamp() - start;
        if (includePng) full = result;
        else empty = result;
      }
      const bytes = full.png.length + (full.reference_png?.length ?? 0);
      if (bytes !== sizes[index] || empty.png.length || empty.reference_png?.length
          || full.sha256 !== empty.sha256 || full.key !== empty.key || full.index !== empty.index)
        throw Error('PNG benchmark changed the sample or return shape');
      pairs.push({index, full_first: fullFirst, bytes, ...durations});
    }
    passes.push(pairs);
  }
  return passes;
}

export async function finish(page, testInfo) {
  data.end = stamp();
  await documentTimings(page);
  data.png_passes = await measurePngReturn(page, data.samples.map(row => row.png_bytes));
  await writeFile(testInfo.outputPath('soldier-orders-breakdown.json'), JSON.stringify(data));
}

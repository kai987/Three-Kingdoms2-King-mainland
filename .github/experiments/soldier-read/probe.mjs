import {createHash} from 'node:crypto';
import {writeFile} from 'node:fs/promises';

const mark = '__tk2OpeningReadMark';
const now = () => performance.timeOrigin + performance.now();
const sha256 = text => createHash('sha256').update(text).digest('hex');

export async function observeOpeningWorker(page) {
  await page.addInitScript(() => {
    const clock = () => {
      const native = globalThis.__pwClock?.builtins.performance ?? performance;
      return native.timeOrigin + native.now();
    };
    globalThis.Worker = new Proxy(globalThis.Worker, {
      construct(target, args, newTarget) {
        const worker = Reflect.construct(target, args, newTarget);
        if (!new URL(args[0], location.href).pathname.endsWith('/browser-engine-worker.js')) return worker;
        const pending = new Map();
        worker.addEventListener('message', ({data: message}) => {
          if (message?.type !== 'response' || !pending.has(message.id)) return;
          const {capture, endpoint, send} = pending.get(message.id);
          pending.delete(message.id);
          capture[endpoint] = {send, receive: clock(), status: message.status, raw: message.body};
        });
        const send = worker.postMessage;
        worker.postMessage = function (message, ...rest) {
          const capture = globalThis.__tk2OpeningReadCapture;
          if (capture && message?.type === 'request' && message.method === 'GET'
              && (message.path === '/api/save' || message.path === '/api/state')) {
            pending.set(message.id, {capture, endpoint: message.path, send: clock()});
          }
          return Reflect.apply(send, this, [message, ...rest]);
        };
        return worker;
      },
    });
  });
}

async function evaluateRead(page, label) {
  return page.evaluate(async label => {
    const native = globalThis.__pwClock.builtins.performance;
    const now = () => native.timeOrigin + native.now();
    const browser = {entry: now(), chunks: {}, json: {}};
    let pair;
    if (label === 'live') {
      const capture = globalThis.__tk2OpeningReadCapture = {};
      const [a,b] = await Promise.all([fetch('/api/save'),fetch('/api/state')]);
      browser.responsesReady = now();
      delete globalThis.__tk2OpeningReadCapture;
      if (!a.ok || !b.ok) throw Error('Actual soldier state could not be inspected');
      browser.json.state = {start: now()};
      const state = await b.json();
      browser.json.state.end = now();
      browser.json.save = {start: now()};
      const save = await a.json();
      browser.json.save.end = now();
      // Keep the original objects and raw bytes for diagnostics on this page.
      pair = {save, view: state.view || state};
      globalThis.__tk2OpeningReadInputs = {capture, pair};
      browser.worker = Object.fromEntries(Object.entries(capture).map(([endpoint, {send, receive, status}]) =>
        [endpoint, {send, receive, status}]));
    } else {
      pair = globalThis.__tk2OpeningReadInputs.pair;
    }

    // Playwright reads each own enumerable property before recursively
    // serializing its value. The next getter marks the end of that subtree.
    const keys = label === 'live' ? ['save', 'view'] : [label.split('-')[0]];
    const result = {};
    for (const key of keys) {
      Object.defineProperty(result, key, {enumerable: true, get() {
        browser.chunks[key] = now();
        return pair[key];
      }});
    }
    Object.defineProperties(result, {
      __tk2OpeningReadMark: {enumerable: true, get() {
        browser.serializationEnd = now();
        return label;
      }},
      __tk2OpeningReadBrowser: {enumerable: true, value: browser},
    });
    browser.callbackEnd = now();
    return result;
  }, label);
}

export async function readOpening(page, testInfo) {
  const results = {};
  const trace = {
    now,
    wireLabel(wrapper) {
      const value = wrapper?.o?.find?.(item => item.k === mark)?.v;
      return typeof value === 'string' ? value : value?.s;
    },
    record(label, stage, times) {
      if (typeof label === 'string') results[label].node[stage] = times;
    },
    step(label, stage, work) {
      if (typeof label !== 'string') return work();
      const start = now();
      try { return work(); }
      finally { this.record(label, stage, {start, end: now()}); }
    },
  };
  const execute = async label => {
    const row = results[label] = {node: {}, start: now()};
    const value = await evaluateRead(page, label);
    row.end = now();
    row.browser = value.__tk2OpeningReadBrowser;
    delete value[mark];
    delete value.__tk2OpeningReadBrowser;
    for (const stage of ['pipe', 'driverParse', 'driverSerialize', 'driverValidate', 'driverAfterCall', 'clientValidate', 'clientParse']) {
      if (!row.node[stage]) throw Error('Missing Playwright boundary for '+label+': '+stage);
    }
    return value;
  };

  globalThis.__tk2ReadTrace = trace;
  try {
    const original = await execute('live');
    const hashes = {save: sha256(JSON.stringify(original.save)), view: sha256(JSON.stringify(original.view))};
    for (const label of ['save-1', 'view-1', 'view-2', 'save-2']) {
      const result = await execute(label);
      const key = label.split('-')[0];
      if (sha256(JSON.stringify(result[key])) !== hashes[key]) throw Error('Endpoint replay differs from original '+key);
    }
    // Sizes and bare JSON.parse run separately so they cannot contaminate
    // the original Response.json() or any measured evaluated return.
    const raw = await page.evaluate(() => {
      const perf = globalThis.__pwClock.builtins.performance;
      const capture = globalThis.__tk2OpeningReadInputs.capture;
      return Object.fromEntries(Object.entries(capture).map(([endpoint, {raw}]) => {
        const parseMs = [];
        for (let i = 0; i < 5; i++) {
          const start = perf.now();
          JSON.parse(raw);
          parseMs.push(perf.now() - start);
        }
        return [endpoint, {utf8Bytes: new TextEncoder().encode(raw).byteLength, parseMs}];
      }));
    });
    if (!raw['/api/save'] || !raw['/api/state']) throw Error('Expected both Worker responses');
    await page.evaluate(() => { delete globalThis.__tk2OpeningReadInputs; });
    await writeFile(testInfo.outputPath('soldier-opening-read.json'), JSON.stringify({results, raw, hashes}));
    return original;
  } finally {
    delete globalThis.__tk2ReadTrace;
  }
}

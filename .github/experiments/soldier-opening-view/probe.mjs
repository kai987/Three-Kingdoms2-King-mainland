import {createHash} from 'node:crypto';
import {writeFile} from 'node:fs/promises';

const mark = '__tk2OpeningReadMark';
const now = () => performance.timeOrigin + performance.now();
const sha256 = value => createHash('sha256').update(JSON.stringify(value)).digest('hex');

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
          const {probe, endpoint, send} = pending.get(message.id);
          pending.delete(message.id);
          probe.receipts.push({endpoint, send, receive: clock(), status: message.status, raw: message.body});
        });
        const send = worker.postMessage;
        worker.postMessage = function (message, ...rest) {
          const probe = globalThis.__tk2OpeningProfile;
          if (probe?.capturing && message?.type === 'request' && message.method === 'GET'
              && (message.path === '/api/save' || message.path === '/api/state')) {
            pending.set(message.id, {probe, endpoint: message.path, send: clock()});
          }
          return Reflect.apply(send, this, [message, ...rest]);
        };
        return worker;
      },
    });
  });
}

export async function measureOpening(page, testInfo, read) {
  await page.evaluate(() => {
    const native = globalThis.__pwClock.builtins.performance;
    const clock = () => native.timeOrigin + native.now();
    const browser = {json: {}, chunks: {}};
    globalThis.__tk2OpeningProfile = {
      receipts: [], capturing: false, browser, clock,
      async parse(endpoint, response) {
        const start = clock();
        const value = await response.json();
        browser.json[endpoint] = {start, end: clock()};
        return value;
      },
      wrap({save, view}) {
        const result = {
          get save() { browser.chunks.save = clock(); return save; },
          get view() { browser.chunks.view = clock(); return view; },
          get __tk2OpeningReadMark() { browser.serializationEnd = clock(); return 'live'; },
          __tk2OpeningReadBrowser: browser,
        };
        browser.callbackEnd = clock();
        return result;
      },
    };
  });

  const timing = {node: {}};
  const trace = {
    now,
    wireLabel(wrapper) {
      const value = wrapper?.o?.find?.(item => item.k === mark)?.v;
      return typeof value === 'string' ? value : value?.s;
    },
    record(label, stage, times) {
      if (label === 'live') timing.node[stage] = times;
    },
    step(label, stage, work) {
      if (label !== 'live') return work();
      const start = now();
      try { return work(); }
      finally { this.record(label, stage, {start, end: now()}); }
    },
  };

  globalThis.__tk2ReadTrace = trace;
  let original;
  try {
    timing.start = now();
    original = await read();
    timing.end = now();
  } finally {
    delete globalThis.__tk2ReadTrace;
  }
  if (original[mark] !== 'live') throw Error('Missing profiled opening read');
  timing.browser = original.__tk2OpeningReadBrowser;
  delete original[mark];
  delete original.__tk2OpeningReadBrowser;
  for (const stage of ['pipe','driverParse','driverSerialize','driverValidate','driverAfterCall','clientValidate','clientParse']) {
    if (!timing.node[stage]) throw Error('Missing Playwright boundary: '+stage);
  }
  const metadata = await page.evaluate(() => {
    const {receipts} = globalThis.__tk2OpeningProfile;
    delete globalThis.__tk2OpeningProfile;
    const host = document.querySelector('[data-battle-scene]');
    return {
      selected:host.dataset.battleSelectedActor,
      markerIds:JSON.parse(host.dataset.battleMarkers).map(marker=>String(marker.id)),
      receipts:receipts.map(({raw,...details})=>({...details,utf8Bytes:new TextEncoder().encode(raw).byteLength})),
    };
  });
  if (metadata.receipts.map(row=>row.endpoint).sort().join(',') !== '/api/save,/api/state'
      || metadata.receipts.some(row=>row.status!==200)
      || Object.keys(timing.browser.json).sort().join(',') !== 'save,state')
    throw Error('Expected one independent, fully parsed response from each endpoint');

  const sourceKinds = ['verified_original_rom','original_table_transcription','design_trait_inference',
    'design_region_inference','retained_design','fallback_design'];
  const catalog = original.view.catalog;
  const types = catalog.officer_troop_types;
  const assertedView = {
    troopSchema: [types.schema, types.rules_version],
    officers: metadata.markerIds.map(id=>[id, types.officers[id]?.code, types.officers[id]?.base_code, types.officers[id]?.source_kind]),
    attackTargets: [metadata.selected, catalog.battle_tactical.actors[metadata.selected].attack_targets],
    sources: sourceKinds.map(kind=>[kind,catalog.library.find(p=>p.affinity_source?.source_kind===kind)?.person_id]),
  };
  await writeFile(testInfo.outputPath('soldier-opening-view.json'), JSON.stringify({
    ...timing, ...metadata, assertedView, hashes: {save: sha256(original.save), assertedView: sha256(assertedView)},
  }));
  return original;
}

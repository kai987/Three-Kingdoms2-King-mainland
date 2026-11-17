import {writeFile} from 'node:fs/promises';

const now = () => performance.timeOrigin + performance.now();

export async function installEquipmentProfile(page, testInfo) {
  const requests = [];
  const reads = [];

  await page.addInitScript(() => {
    const endpoints = new Set(['/api/save', '/api/state']);
    const rows = [];
    const responseRows = new WeakMap();
    let checkpoint = null;
    let receiving = null;

    window.Worker = new Proxy(window.Worker, {
      construct(target, args, newTarget) {
        const worker = Reflect.construct(target, args, newTarget);
        if (!new URL(args[0], location.href).pathname.endsWith('/browser-engine-worker.js')) return worker;
        const pending = new Map();
        worker.addEventListener('message', ({data}) => {
          if (data?.type !== 'response' || !pending.has(data.id)) return;
          const row = pending.get(data.id);
          pending.delete(data.id);
          row.received = performance.now();
          row.bodyUtf16Units = data.body?.length;
          row.status = data.status;
          receiving = {row, body: data.body};
        });
        const send = worker.postMessage;
        worker.postMessage = function(message, ...rest) {
          if (message?.type === 'request' && message.method === 'GET' && endpoints.has(message.path)) {
            const row = {
              id: message.id,
              endpoint: message.path,
              checkpoint,
              compact: typeof message.view_cache === 'string',
              sent: performance.now(),
              decodes: [],
            };
            rows.push(row);
            pending.set(message.id, row);
          }
          return Reflect.apply(send, this, [message, ...rest]);
        };
        return worker;
      },
    });

    // The transport creates a Response synchronously in its Worker reply handler.
    window.Response = new Proxy(window.Response, {
      construct(target, args, newTarget) {
        const response = Reflect.construct(target, args, newTarget);
        if (receiving && args[0] === receiving.body) {
          responseRows.set(response, receiving.row);
          receiving = null;
        }
        return response;
      },
    });

    for (const method of ['json', 'text']) {
      const original = Response.prototype[method];
      Response.prototype[method] = function(...args) {
        const row = responseRows.get(this);
        if (!row) return Reflect.apply(original, this, args);
        const started = performance.now();
        return Reflect.apply(original, this, args).then(value => {
          const finished = performance.now();
          row.decodes.push({method, started, finished});
          return value;
        });
      };
    }

    window.__equipmentProfile = {
      fetch(label, path) {
        checkpoint = label;
        try { return fetch(path); }
        finally { checkpoint = null; }
      },
      drain() { return rows.splice(0); },
    };
  });

  async function collect(document) {
    for (const row of await page.evaluate(() => window.__equipmentProfile.drain())) {
      requests.push({document, ...row});
    }
  }

  async function measure(label, saveOnly) {
    const result = await page.evaluate(async ({label, saveOnly}) => {
      const probe = window.__equipmentProfile;
      const started = performance.now();
      const a = await probe.fetch(label, '/api/save');
      let data;
      if (saveOnly) {
        if (!a.ok) throw Error('Tactical raw save inspection failed');
        data = await a.json();
      } else {
        const b = await probe.fetch(label, '/api/state');
        if (!a.ok || !b.ok) throw Error('Equipment read-only state failed');
        const value = await b.json();
        data = {save: await a.json(), view: value.view || value};
      }
      const ended = performance.now();
      return {data, browserEnd: performance.timeOrigin + ended, browserMs: ended - started};
    }, {label, saveOnly});
    const returnMs = now() - result.browserEnd;
    const save = saveOnly ? result.data : result.data.save;
    reads.push({
      label,
      saveOnly,
      browserMs: result.browserMs,
      returnMs,
      saveChecksum: save.checksum,
    });
    return result.data;
  }

  return {
    read: label => measure(label, false),
    save: label => measure(label, true),
    beforeReload: () => collect('before-reload'),
    async finish(rng) {
      await collect('after-reload');
      await writeFile(testInfo.outputPath('equipment-profile.json'), JSON.stringify({reads, requests, rng}, null, 2));
    },
  };
}

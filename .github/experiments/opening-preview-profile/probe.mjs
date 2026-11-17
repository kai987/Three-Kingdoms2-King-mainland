import {writeFile} from 'node:fs/promises';

const epoch = () => performance.timeOrigin + performance.now();

export async function installOpeningProfile(page, testInfo) {
  const started = performance.now();
  await page.addInitScript(() => {
    const cityRequest = path => typeof path === 'string' && path.startsWith('/api/city-preview?');
    const rows = [];
    let explicit = false;
    window.Worker = new Proxy(window.Worker, {
      construct(target, args, newTarget) {
        const worker = Reflect.construct(target, args, newTarget);
        if (!new URL(args[0], location.href).pathname.endsWith('/browser-engine-worker.js')) return worker;
        const pending = new Map();
        worker.addEventListener('message', ({data}) => {
          if (data?.type !== 'response' || !pending.has(data.id)) return;
          const row = pending.get(data.id);
          row.received = performance.now();
          row.status = data.status;
          row.responseUnits = data.body.length;
          pending.delete(data.id);
        });
        const send = worker.postMessage;
        worker.postMessage = function(message, ...rest) {
          if (message?.type === 'request' && (cityRequest(message.path) || message.path === '/api/save')) {
            const row = {id: message.id, path: message.path, explicit, sent: performance.now()};
            pending.set(message.id, row);
            rows.push(row);
          }
          return Reflect.apply(send, this, [message, ...rest]);
        };
        return worker;
      },
    });
    window.__openingPageProfile = {
      markedFetch(path) {
        explicit = true;
        try { return window.fetch(path); }
        finally { explicit = false; }
      },
      rows: () => rows,
    };
  });

  let worker, bootMs, clock;
  const scenarios = [];
  return {
    async openingReady(bootStarted) {
      bootMs = performance.now() - bootStarted;
      const matches = page.workers().filter(candidate => new URL(candidate.url()).pathname.endsWith('/browser-engine-worker.js'));
      if (matches.length !== 1) throw Error('Expected one shipped game Worker');
      [worker] = matches;
      await worker.evaluate(() => {
        // Measure inside the actual running Worker without replacing its module
        // or sending extra messages through the game's request protocol.
        const receive = self.onmessage;
        const send = self.postMessage;
        if (typeof receive !== 'function') throw Error('Game Worker handler is unavailable');
        const pending = new Map();
        const completed = [];
        self.onmessage = function(event) {
          const message = event.data;
          if (message?.type === 'request' && (message.path.startsWith('/api/city-preview?') || message.path === '/api/save')) {
            pending.set(message.id, {id: message.id, path: message.path, entered: performance.now()});
          }
          return Reflect.apply(receive, this, [event]);
        };
        self.postMessage = function(message, ...rest) {
          if (message?.type === 'response' && pending.has(message.id)) {
            const row = pending.get(message.id);
            completed.push({...row, exited: performance.now(), status: message.status});
            pending.delete(message.id);
          }
          return Reflect.apply(send, this, [message, ...rest]);
        };
        self.__openingWorkerProfile = () => ({completed, pending: [...pending.values()]});
      });
      // Estimate the cross-process clock offset from the shortest empty call.
      const samples = [];
      for (let index = 0; index < 5; index++) {
        const start = epoch();
        const browser = await page.evaluate(() => performance.timeOrigin + performance.now());
        const stop = epoch();
        samples.push({rttMs: stop - start, offsetMs: browser - (start + stop) / 2});
      }
      clock = samples.sort((a, b) => a.rttMs - b.rttMs)[0];
    },
    async previews(scenario, cities) {
      const start = epoch();
      const result = await page.evaluate(async({scenario,cities}) => {
        const values = [];
        let fetchMs = 0;
        let jsonMs = 0;
        const started = performance.now();
        for (const city of cities) {
          const sent = performance.now();
          const response = await window.__openingPageProfile.markedFetch('/api/city-preview?' + new URLSearchParams({scenario,city}));
          const ready = performance.now();
          if (!response.ok) throw new Error(`Opening preview failed: ${scenario}/${city}`);
          values.push((await response.json()).city);
          const parsed = performance.now();
          fetchMs += ready - sent;
          jsonMs += parsed - ready;
        }
        const ended = performance.now();
        return {values, fetchMs, jsonMs, callbackMs: ended - started, browserEnd: performance.timeOrigin + ended};
      }, {scenario,cities});
      const stop = epoch();
      const {values, browserEnd, ...metrics} = result;
      return {values, metrics: {...metrics, evaluateMs: stop - start,
        returnMs: stop - browserEnd + clock.offsetMs}};
    },
    scenario(row) { scenarios.push(row); },
    async finish() {
      const elapsedMs = performance.now() - started;
      const pageRows = await page.evaluate(() => window.__openingPageProfile.rows());
      const workerRows = await worker.evaluate(() => self.__openingWorkerProfile());
      const path = testInfo.outputPath('opening-profile.json');
      await writeFile(path, JSON.stringify({bootMs, elapsedMs, clock, scenarios, pageRows, workerRows}, null, 2));
    },
  };
}

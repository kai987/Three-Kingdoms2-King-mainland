import {writeFile} from 'node:fs/promises';

export async function profileCommandBooks(page, testInfo) {
  const samples = [];

  await page.addInitScript(() => {
    let activeRead = null;
    window.Worker = new Proxy(window.Worker, {
      construct(target, args, newTarget) {
        const worker = Reflect.construct(target, args, newTarget);
        if (!new URL(args[0], location.href).pathname.endsWith('/browser-engine-worker.js')) return worker;
        const pending = new Map();
        worker.addEventListener('message', event => {
          const arrived = performance.now();
          const message = event.data;
          if (message?.type !== 'response' || !pending.has(message.id)) return;
          const read = pending.get(message.id);
          pending.delete(message.id);
          read.arrived = arrived;
          read.body = message.body;
          read.status = message.status;
        });
        const send = worker.postMessage;
        worker.postMessage = function(message, ...rest) {
          if (activeRead && message?.type === 'request' && message.method === 'GET' && message.path === '/api/save') {
            pending.set(message.id, activeRead);
            activeRead.sent = performance.now();
          }
          return Reflect.apply(send, this, [message, ...rest]);
        };
        return worker;
      },
    });

    window.__measureCommandBookSave = async () => {
      const started = performance.now();
      const read = {};
      let promise;
      activeRead = read;
      try {
        promise = fetch('/api/save');
      } finally {
        activeRead = null;
      }
      const response = await promise;
      const parsing = performance.now();
      if (!response.ok) throw Error('Command-book save inspection failed');
      const save = await response.json();
      const parsed = performance.now();
      if (!(read.sent >= started && read.arrived >= read.sent && parsing >= read.arrived) ||
          read.status !== response.status || typeof read.body !== 'string') {
        throw Error('Failed to match the Worker save reply');
      }
      const sizing = performance.now();
      const bytes = new TextEncoder().encode(read.body).byteLength;
      const returning = performance.now();
      return {
        save,
        bytes,
        worker_ms: read.arrived - read.sent,
        response_bridge_ms: parsing - read.arrived,
        json_ms: parsed - parsing,
        byte_count_ms: returning - sizing,
        browser_ms: returning - started,
        browser_end: performance.timeOrigin + returning,
      };
    };
  });

  return {
    async read(round) {
      const started = performance.now();
      const result = await page.evaluate(() => window.__measureCommandBookSave());
      const received = performance.now();
      const {save, browser_end, ...sample} = result;
      samples.push({
        round,
        ...sample,
        evaluate_ms: received - started,
        // The processes share the runner clock. This segment includes
        // Playwright serialization, protocol transport and Node deserialization.
        playwright_return_ms: performance.timeOrigin + received - browser_end,
      });
      return save;
    },
    async finish() {
      await writeFile(testInfo.outputPath('command-books-timings.json'), JSON.stringify(samples, null, 2));
    },
  };
}

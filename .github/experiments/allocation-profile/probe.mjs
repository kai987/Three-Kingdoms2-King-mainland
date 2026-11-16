import {writeFile} from 'node:fs/promises';

const now = () => performance.timeOrigin + performance.now();

export async function installAllocationProfile(page, testInfo, variant) {
  await page.addInitScript(() => {
    const now = () => {
      const clock = globalThis.__pwClock?.builtins.performance ?? performance;
      return clock.timeOrigin + clock.now();
    };
    const probe = {
      reads: [], closeCommands: [], armed: null,
      async fetchJson(id, endpoint) {
        const row = {id, endpoint, entry: now()};
        probe.reads.push(row);
        probe.armed = row;
        let pending;
        try {
          pending = fetch(endpoint);
        } finally {
          probe.armed = null;
        }
        const response = await pending;
        row.parseStart = now();
        if (!response.ok) throw Error(endpoint === '/api/save' ? 'Save inspection failed' : 'Revision inspection failed');
        const body = await response.json();
        row.parseEnd = now();
        return body;
      },
      finish(id, result) {
        const row = probe.reads.at(-1);
        if (row?.id !== id) throw Error('Unexpected allocation read identifier');
        row.returnType = typeof result;
        if (row.endpoint === '/api/state') row.revision = result;
        row.ready = now();
        return result;
      },
    };
    globalThis.__tk2AllocationProbe = probe;
    globalThis.Worker = new Proxy(globalThis.Worker, {
      construct(target, args, newTarget) {
        const worker = Reflect.construct(target, args, newTarget);
        if (!new URL(args[0], location.href).pathname.endsWith('/browser-engine-worker.js')) return worker;
        const pending = new Map();
        worker.addEventListener('message', ({data: message}) => {
          if (message?.type !== 'response' || !pending.has(message.id)) return;
          const row = pending.get(message.id);
          pending.delete(message.id);
          row.receive = now();
          row.status = message.status;
          row.bodyUtf16Units = message.body?.length;
        });
        const send = worker.postMessage;
        worker.postMessage = function (message, ...rest) {
          if (message?.type === 'request') {
            if (probe.armed && probe.armed.endpoint === message.path && message.method === 'GET') {
              const row = probe.armed;
              row.send = now();
              pending.set(message.id, row);
            }
            if (message.path === '/api/command' && typeof message.body === 'string'
                && message.body.includes('"kind":"allocation_close"')) {
              const row = {send: now()};
              probe.closeCommands.push(row);
              pending.set(message.id, row);
            }
          }
          return Reflect.apply(send, this, [message, ...rest]);
        };
        return worker;
      },
    });
  });

  const calls = [], flows = [], documents = [];
  const collect = async () => {
    documents.push(await page.evaluate(() => {
      const {reads, closeCommands} = globalThis.__tk2AllocationProbe;
      return {reads, closeCommands};
    }));
  };
  const measure = async (endpoint, evaluate, flow) => {
    const row = {id: calls.length + 1, endpoint, flow: flow?.id};
    calls.push(row);
    if (globalThis.__tk2AllocationTrace) throw Error('Overlapping targeted reads');
    row.start = now();
    globalThis.__tk2AllocationTrace = {now, row};
    try {
      return await evaluate(row.id);
    } finally {
      row.end = now();
      delete globalThis.__tk2AllocationTrace;
    }
  };
  return {
    revision: evaluate => measure('/api/state', evaluate),
    async close(dialog, poll, idle) {
      const flow = {id: flows.length + 1, polls: [], start: now()};
      flows.push(flow);
      await dialog();
      flow.pollStart = now();
      await poll(async (evaluate, observe, isClosed) => {
        const value = observe(await measure('/api/save', evaluate, flow));
        flow.polls.push({closed:isClosed(value), observed:now()});
        return value;
      });
      flow.pollEnd = now();
      await idle();
      flow.end = now();
    },
    collect,
    async finish() {
      await collect();
      const reads = documents.flatMap(doc => doc.reads);
      if (reads.length !== calls.length || calls.filter(row => row.endpoint === '/api/state').length !== 8)
        throw Error('Missing allocation read timings or revision checkpoints');
      const rows = reads.map(read => {
        const call = calls[read.id-1];
        if (read.endpoint !== call?.endpoint || read.status !== 200 || !call.cdpReceived || !read.receive)
          throw Error('Missing Worker or Chromium boundary for allocation read '+read.id);
        const type = read.endpoint === '/api/state' ? 'number' : variant === 'optimized' ? 'boolean' : 'object';
        if (read.returnType !== type) throw Error('Unexpected allocation read result type');
        return {...read, ...call};
      });
      if (flows.some(flow => !flow.polls.at(-1)?.closed ||
          rows.filter(row => row.flow === flow.id).length !== flow.polls.length))
        throw Error('Missing allocation flow poll evidence');
      await writeFile(testInfo.outputPath('allocation-profile.json'), JSON.stringify({
        variant, rows, flows, workers: documents.flatMap(doc => doc.closeCommands),
      }));
    },
  };
}

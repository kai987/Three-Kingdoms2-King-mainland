(runtime, python) => {
  if (globalThis.__tk2RevisionWorker) throw Error('Duplicate Worker probe');
  runtime.runPython(python);
  const now = () => performance.timeOrigin + performance.now();
  const rows = new Map();
  const onmessage = self.onmessage;
  self.onmessage = function(event) {
    const message = event.data;
    if (message?.path === '/api/state' && message.method === 'GET') {
      rows.set(message.id, {id:message.id, received:now(), compact:typeof message.view_cache==='string'});
    }
    return onmessage.call(this,event);
  };
  const postMessage = self.postMessage;
  self.postMessage = function(message, ...rest) {
    const row = message?.type === 'response' ? rows.get(message.id) : undefined;
    if (!row) return postMessage.call(this,message,...rest);
    row.postStart = now();
    const result = postMessage.call(this,message,...rest);
    row.postEnd = now();
    row.status = message.status;
    row.bodyUtf16Units = message.body?.length;
    return result;
  };
  globalThis.__tk2RevisionWorker = () => ({
    messages: [...rows.values()],
    python: JSON.parse(runtime.runPython('json.dumps(_tk2p_records)')),
  });
  return true;
}

import {readFile} from 'node:fs/promises';

const port = 18928;

export async function prepareWorkerProbe(workerURL) {
  const {webSocketDebuggerUrl} = await (await fetch(`http://127.0.0.1:${port}/json/version`)).json();
  const socket = new WebSocket(webSocketDebuggerUrl);
  await new Promise((resolve, reject) => {
    socket.addEventListener('open', resolve, {once:true});
    socket.addEventListener('error', reject, {once:true});
  });
  const pending = new Map();
  let sequence = 0;
  let paused;
  const call = (method, params={}, sessionId) => new Promise((resolve, reject) => {
    const id = ++sequence;
    const timer = setTimeout(() => {
      pending.delete(id);
      reject(Error(`DevTools timed out in ${method}`));
    }, 15000);
    pending.set(id, {resolve, reject, timer});
    socket.send(JSON.stringify({id,method,params,sessionId}));
  });
  socket.addEventListener('message', event => {
    const message = JSON.parse(event.data);
    const request = pending.get(message.id);
    if (request) {
      pending.delete(message.id);
      clearTimeout(request.timer);
      if (message.error) request.reject(Error(message.error.message));
      else request.resolve(message.result);
    }
    if (message.method === 'Debugger.paused') paused?.(message);
  });
  try {
    const {targetInfos} = await call('Target.getTargets');
    const [target, ...extra] = targetInfos.filter(info => info.type === 'worker' && info.url === workerURL);
    if (!target || extra.length) throw Error(`Expected one dedicated game Worker target, found ${targetInfos.map(x=>x.type+':'+x.url).join(', ')}`);
    const {sessionId} = await call('Target.attachToTarget',{targetId:target.targetId,flatten:true});
    const send = (method,params) => call(method,params,sessionId);
    await send('Debugger.enable');
    const source = await readFile('build/web/browser-engine-worker.js','utf8');
    const lines = source.split('\n');
    const lineNumber = lines.findIndex(line => line.includes('const scenario=requestedScenario(message.path,message.body)'));
    if (lineNumber < 0) throw Error('Worker breakpoint location missing');
    const script = await readFile(new URL('./opening-shared-worker.py',import.meta.url),'utf8');
    let resumeID;
    const ready = new Promise((resolve, reject) => {
      const timer = setTimeout(() => reject(Error('No real request reached the Worker probe')), 20000);
      paused = async message => {
        if (message.sessionId !== sessionId) return;
        paused = undefined;
        clearTimeout(timer);
        let error;
        try {
          const expression = `py.globals.set('_experimental_preview_sha',manifest.previews.sha256); py.runPython(${JSON.stringify(script)}); globalThis.__openingPythonProfile = () => py.runPython('json.dumps(_rows)'); true`;
          const result = await send('Debugger.evaluateOnCallFrame',{
            callFrameId:message.params.callFrames[0].callFrameId, expression, returnByValue:true
          });
          if (result.exceptionDetails || result.result.value !== true) throw Error(JSON.stringify(result.exceptionDetails ?? result.result));
        } catch (failure) { error = failure; }
        try {
          const breakpointId=resumeID ?? message.params.hitBreakpoints[0];
          if (breakpointId) await send('Debugger.removeBreakpoint',{breakpointId});
          await send('Debugger.resume');
        } catch (failure) { error ??= failure; }
        if (error) reject(error);
        else resolve();
      };
    });
    ready.catch(() => {});
    const {breakpointId} = await send('Debugger.setBreakpointByUrl',{lineNumber,url:workerURL});
    resumeID = breakpointId;
    return {ready,close:()=>socket.close()};
  } catch (error) {
    socket.close();
    throw error;
  }
}

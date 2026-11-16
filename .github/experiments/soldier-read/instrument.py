"""Add timings to the installed, integrity-pinned Playwright 1.64.1 bundle."""
from pathlib import Path
import json
import sys

package = Path(sys.argv[1])
if json.loads((package / "package.json").read_text())["version"] != "1.64.1":
    raise SystemExit("Playwright version changed")
path = package / "lib/coreBundle.js"
source = path.read_text()


def substitute(region, old, new):
    if region.count(old) != 1:
        raise ValueError(f"Expected unique Playwright anchor: {old[:100]}")
    return region.replace(old, new)


def section(start, end, callback):
    global source
    a = source.index(start)
    b = source.index(end, a+len(start))
    source = source[:a] + callback(source[a:b]) + source[b:]


def instrument_pipe(region):
    return substitute(region, """      _dispatch(buffer) {
        let end = buffer.indexOf("\\0");
        if (end === -1) {
          this._pendingBuffers.push(buffer);
          return;
        }
        this._pendingBuffers.push(buffer.slice(0, end));
        const message = Buffer.concat(this._pendingBuffers).toString();
        setImmediate(() => {
          if (this.onmessage)
            this.onmessage.call(null, JSON.parse(message));
        });
        let start3 = end + 1;
        end = buffer.indexOf("\\0", start3);
        while (end !== -1) {
          const message2 = buffer.toString(void 0, start3, end);
          setImmediate(() => {
            if (this.onmessage)
              this.onmessage.call(null, JSON.parse(message2));
          });
          start3 = end + 1;
          end = buffer.indexOf("\\0", start3);
        }
        this._pendingBuffers = [buffer.slice(start3)];
      }""", """      _dispatch(buffer) {
        const probe = globalThis.__tk2ReadTrace;
        const received = probe?.now();
        if (!this._pendingBuffers.length || this._tk2FirstChunk === undefined) this._tk2FirstChunk = received;
        const dispatch = (message, bytes, firstChunk, decodedAt) => {
          if (!this.onmessage) return;
          if (!probe) {
            this.onmessage.call(null, JSON.parse(message));
            return;
          }
          const parseStart = probe.now();
          const parsed = JSON.parse(message);
          const parseEnd = probe.now();
          const label = probe.wireLabel(parsed.result?.result?.value);
          probe.record(label, "pipe", {bytes, firstChunk, lastChunk: received, decodedAt, parseStart, parseEnd});
          this.onmessage.call(null, parsed);
        };
        let end = buffer.indexOf("\\0");
        if (end === -1) {
          this._pendingBuffers.push(buffer);
          return;
        }
        this._pendingBuffers.push(buffer.slice(0, end));
        const joined = Buffer.concat(this._pendingBuffers);
        const message = joined.toString(), firstChunk = this._tk2FirstChunk, decodedAt = probe?.now();
        setImmediate(() => dispatch(message, joined.length, firstChunk, decodedAt));
        let start3 = end + 1;
        end = buffer.indexOf("\\0", start3);
        while (end !== -1) {
          const message2 = buffer.toString(void 0, start3, end), bytes = end - start3, decodedAt2 = probe?.now();
          setImmediate(() => dispatch(message2, bytes, received, decodedAt2));
          start3 = end + 1;
          end = buffer.indexOf("\\0", start3);
        }
        this._pendingBuffers = [buffer.slice(start3)];
        this._tk2FirstChunk = start3 < buffer.length ? received : undefined;
      }""")


section("var PipeTransport2;", "// packages/playwright-core/src/server/transport.ts", instrument_pipe)
section("var CRExecutionContext;", "// packages/playwright-core/src/server/chromium/crInput.ts",
    lambda r: substitute(r,
        "return returnByValue ? parseEvaluationResultValue(remoteObject.value) : createHandle(utilityScript._context, remoteObject);",
        """if (!returnByValue) return createHandle(utilityScript._context, remoteObject);
        const probe = globalThis.__tk2ReadTrace;
        const label = probe?.wireLabel(remoteObject.value);
        return label ? probe.step(label, "driverParse", () => parseEvaluationResultValue(remoteObject.value))
                     : parseEvaluationResultValue(remoteObject.value);"""))
source = substitute(source, """function serializeResult(arg2) {
  return serializeValue(arg2, (value2) => ({ fallThrough: value2 }));
}""", """function serializeResult(arg2) {
  const probe = globalThis.__tk2ReadTrace, label = arg2?.__tk2OpeningReadMark;
  const run = () => serializeValue(arg2, (value2) => ({ fallThrough: value2 }));
  return probe && label ? probe.step(label, "driverSerialize", run) : run();
}""")
source = substitute(source, """          response2.result = validator(result2, "", this._validatorToWireContext());""",
    """          const probe = globalThis.__tk2ReadTrace;
          const label = probe?.wireLabel(result2?.value);
          const validate = () => validator(result2, "", this._validatorToWireContext());
          response2.result = label ? probe.step(label, "driverValidate", validate) : validate();""")
source = substitute(source, """          await afterController.run((progress2) => sdkObject.instrumentation.onAfterCall(progress2, sdkObject), 3e3).catch(() => {
          });""",
    """          const probe = globalThis.__tk2ReadTrace;
          const label = probe?.wireLabel(callMetadata.result?.value);
          const afterStart = label ? probe.now() : undefined;
          await afterController.run((progress2) => sdkObject.instrumentation.onAfterCall(progress2, sdkObject), 3e3).catch(() => {
          });
          if (label) probe.record(label, "driverAfterCall", {start: afterStart, end: probe.now()});""")
source = substitute(source, """            callback.resolve(validator2(result2, "", this._validatorFromWireContext()));""",
    """            const probe = globalThis.__tk2ReadTrace;
            const label = probe?.wireLabel(result2?.value);
            const validate = () => validator2(result2, "", this._validatorFromWireContext());
            callback.resolve(label ? probe.step(label, "clientValidate", validate) : validate());""")
source = substitute(source, """function parseResult(value2) {
  return parseSerializedValue(value2, void 0);
}""",
    """function parseResult(value2) {
  const probe = globalThis.__tk2ReadTrace;
  const label = probe?.wireLabel(value2);
  return label ? probe.step(label, "clientParse", () => parseSerializedValue(value2, void 0))
               : parseSerializedValue(value2, void 0);
}""")
path.write_text(source)

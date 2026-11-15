import { mkdir, writeFile } from 'node:fs/promises';
import { performance } from 'node:perf_hooks';

const profiles = new WeakMap();
const cases = new Map([
  ['city-specific battlefield keeps both armies visible and supports real battle controls', 'battle-layout'],
  ['authoritative tactical movement, shared points and contact attacks persist with a missing battlefield image', 'battle-movement'],
]);

export async function install(page, title) {
  const id = cases.get(title);
  if (!id) throw new Error('The profiling run discovered an unexpected case');
  profiles.set(page, { id, phases: {}, timeline: [], documents: [], rounds: [] });
  await page.addInitScript(() => {
    const NativeWorker = window.Worker;
    const tracked = new WeakMap();
    const profile = {
      workers: [], saves: [], commands: [], requests: [], polls: [], replay: [], busy: [], round: null, label: null,
      poll(kind) {
        const entry = {
          kind, round: this.round, started: performance.now(),
          revisionBeforeFetch: typeof view === 'undefined' ? null : view?.revision ?? null,
        };
        this.label = entry;
        this.polls.push(entry);
        return entry;
      },
      finish(entry, decision) {
        entry.ended = performance.now();
        entry.decision = decision;
      },
    };

    document.addEventListener('DOMContentLoaded', () => {
      const stage = document.querySelector('#stage');
      if (!stage) return;
      let playing = false;
      new MutationObserver(() => {
        const active = !!stage.querySelector('[data-battle-skip]:not([hidden])');
        if (active !== playing) {
          playing = active;
          profile.replay.push({ at: performance.now(), active, round: profile.round,
            mode: stage.querySelector('[data-battle-scene]')?.dataset.battleSceneMode ?? null });
        }
      }).observe(stage, { attributes: true, attributeFilter: ['hidden'], childList: true, subtree: true });
      let busy = document.body.classList.contains('busy');
      new MutationObserver(() => {
        const active = document.body.classList.contains('busy');
        if (active !== busy) {
          busy = active;
          profile.busy.push({ at: performance.now(), active });
        }
      }).observe(document.body, { attributes: true, attributeFilter: ['class'] });
    }, { once: true });

    class ObservedWorker extends NativeWorker {
      constructor(url, options) {
        const started = performance.now();
        super(url, options);
        if (!new URL(String(url), document.baseURI).pathname.endsWith('/browser-engine-worker.js')) return;
        const worker = { started, ready: null, build: null, progress: [] };
        profile.workers.push(worker);
        const pending = new Map();
        tracked.set(this, pending);
        this.addEventListener('message', ({ data }) => {
          const received = performance.now();
          if (data.type === 'progress' && worker.progress.at(-1)?.phase !== data.phase) {
            worker.progress.push({ at: received, phase: data.phase });
          }
          if (data.type === 'ready') {
            worker.ready = received;
            worker.build = data.build_commit;
          }
          if (data.type !== 'response') return;
          const entry = pending.get(data.id);
          if (!entry) return;
          pending.delete(data.id);
          Object.assign(entry, { received, status: data.status });
          if (entry.keepWire) entry.wire = data.body;
        });
      }

      postMessage(message, ...options) {
        const pending = tracked.get(this);
        if (pending && message.type === 'request') {
          const started = performance.now();
          if (message.path === '/api/save') {
            const poll = profile.label;
            profile.label = null;
            const entry = { id: message.id, started, kind: poll?.kind ?? 'other', round: profile.round, keepWire: true };
            if (poll) poll.request = message.id;
            profile.saves.push(entry);
            pending.set(message.id, entry);
          }
          if (['/api/command', '/api/state', '/api/load'].includes(message.path)) {
            const { kind, revision } = message.path === '/api/command' ? JSON.parse(message.body) : {};
            const entry = { id: message.id, kind: kind ?? message.path, started, inputRevision: revision,
              round: profile.round, keepWire: profile.round !== null && ['siege_orders', 'siege_step'].includes(kind) };
            profile.requests.push(entry);
            if (entry.keepWire) profile.commands.push(entry);
            pending.set(message.id, entry);
          }
        }
        return super.postMessage(message, ...options);
      }
    }
    window.Worker = ObservedWorker;
    window.__battleSaveProfile = profile;
  });
}

export function phase(page, name, started) {
  const state = profiles.get(page);
  const ended = performance.now();
  (state.phases[name] ??= []).push(ended - started);
  state.timeline.push({ name, start: performance.timeOrigin + started, end: performance.timeOrigin + ended });
}

export async function measure(page, name, callback) {
  const started = performance.now();
  try {
    return await callback();
  } finally {
    phase(page, name, started);
  }
}

export async function beginRound(page) {
  const index = profiles.get(page).rounds.length + 1;
  await page.evaluate(value => { window.__battleSaveProfile.round = value; }, index);
  return performance.now();
}

export async function finishRound(page, started, before, committed, settled) {
  const brief = save => {
    const battle = save.state.battle;
    const siege = battle?.extended?.siege;
    return { checksum: save.checksum, rng: save.state.rng, battle: battle?.id ?? null,
      siege: siege?.round ?? null, duel: !!battle?.extended?.duel };
  };
  profiles.get(page).rounds.push({
    elapsed: performance.now() - started,
    before: brief(before), committed: brief(committed), settled: brief(settled),
  });
  await page.evaluate(() => { window.__battleSaveProfile.round = null; });
}

export async function snapshot(page) {
  const before = performance.timeOrigin + performance.now();
  const doc = await page.evaluate(() => {
    const profile = window.__battleSaveProfile;
    if (!profile) return null;
    const utf8 = new TextEncoder();
    const outline = ({ wire, keepWire, ...row }) => ({ ...row, bytes: wire ? utf8.encode(wire).length : null });
    const commands = profile.commands.map(({ wire, keepWire, ...row }) => {
      const decoded = wire ? JSON.parse(wire) : {};
      const value = decoded.view ?? decoded;
      const game = value.game;
      const battle = game?.battle;
      return { ...row, revision: value.revision ?? null, rng: game?.rng ?? null,
        battle: battle?.id ?? null, siege: battle?.extended?.siege?.round ?? null,
        duel: !!battle?.extended?.duel, sawGame: !!game, transport: decoded.transport ?? 'full' };
    });
    const requests = profile.requests.map(({ wire, keepWire, ...row }) => row);
    return { workers: profile.workers, saves: profile.saves.map(outline), commands, polls: profile.polls,
      requests, replay: profile.replay, busy: profile.busy, timeOrigin: performance.timeOrigin,
      sampledAt: performance.timeOrigin + performance.now() };
  });
  if (doc) {
    doc.nodeSample = [before, performance.timeOrigin + performance.now()];
    profiles.get(page).documents.push(doc);
  }
}

export async function record(page, testInfo) {
  const profile = profiles.get(page);
  if (!profile) return;
  await snapshot(page);
  await mkdir('build/battle-poll-profile', { recursive: true });
  const { project, status, duration } = testInfo;
  const data = { ...profile, project: project.name, status, duration, variant: process.env.PROFILE_VARIANT,
    runId: process.env.GITHUB_RUN_ID ?? null, runner: process.env.RUNNER_NAME ?? null,
    source: process.env.SOURCE_SHA ?? null, web: process.env.WEB_CONTENT_SHA ?? null };
  await writeFile(`build/battle-poll-profile/${data.variant}-${project.name}-${profile.id}.json`, JSON.stringify(data));
}

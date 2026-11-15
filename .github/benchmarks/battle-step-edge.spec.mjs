import { test, expect } from '../../tools/browser-tests/node_modules/@playwright/test/index.mjs';
import { readFile, writeFile } from 'node:fs/promises';
import { waitForSoldierStep } from '../../tests/browser_soldier_step_wait.mjs';

const fixtures = JSON.parse(await readFile('build/battle-step-edge-fixtures.json', 'utf8'));

for (const branch of ['ended', 'duel']) {
  test(`real siege_step response when the encounter reaches ${branch}`, async ({ page }) => {
    const { before, expected } = fixtures[branch];
    const save = () => page.evaluate(async () => {
      const response = await fetch('/api/save');
      if (!response.ok) throw new Error('Could not read the real Worker save');
      return response.json();
    });

    await page.goto('./');
    const start = page.locator('#game-loading-start');
    await expect(start).toBeEnabled({ timeout: 180_000 });
    await start.click();
    await expect(page.locator('#game-loading-cover')).toBeHidden();
    await expect.poll(() => page.evaluate(() => GameBrowserEngine.ready)).toBe(true);
    await page.locator('#load').click();
    await page.locator('#save-file').setInputFiles({
      name: 'controlled-soldier-step.json', mimeType: 'application/json',
      buffer: Buffer.from(JSON.stringify(before)),
    });
    await expect(page.locator('#dialog')).toBeHidden();
    await expect(page.locator('body')).not.toHaveClass(/\bbusy\b/);
    expect(await save()).toEqual(before);

    const revision = await page.evaluate(() => view.revision);
    const battle = before.state.battle;
    const button = page.locator('#siege-step');
    const inspector = page.locator('#inspector-toggle');
    if (!await button.isVisible() && await inspector.isVisible()) await inspector.click();
    await button.click();
    await waitForSoldierStep(page, {
      battleId: battle.id, round: battle.extended.siege.round, revision,
    });
    const response = await page.evaluate(() => {
      const current = view.game.battle.extended;
      return {
        revision: view.revision,
        worker: GameBrowserEngine.version,
        scenes: view.presentation.scenes.map(scene => ({ kind: scene.kind, battle: scene.battle_id })),
        round: current.siege?.round ?? null,
        duelRound: current.duel?.round ?? null,
        rng: view.game.rng,
      };
    });
    expect(response.revision).toBe(revision + 2);
    expect(response.scenes).toContainEqual({ kind: 'soldier_step', battle: battle.id });
    expect(response.worker).toBe(process.env.SOURCE_SHA);
    const committed = await save();
    expect(committed).toEqual(expected);
    const ext = committed.state.battle.extended;
    if (branch === 'ended') {
      expect(response.round).toBeNull();
      expect(response.duelRound).toBeNull();
      expect(ext.siege).toBeUndefined();
    } else {
      expect(response.round).toBe(battle.extended.siege.round);
      expect(response.duelRound).toBe(1);
      expect(ext.duel.round).toBe(1);
      expect(response.scenes).toContainEqual({ kind: 'duel_start', battle: battle.id });
    }

    const skip = page.locator('[data-battle-skip]');
    await expect.poll(() => page.evaluate(() =>
      !document.body.classList.contains('busy') ||
      !!document.querySelector('[data-battle-skip]:not([hidden])'))).toBe(true);
    if (await skip.isVisible()) {
      try { await skip.click({ timeout: 1_000 }); }
      catch (error) { if (await skip.isVisible()) throw error; }
    }
    await expect(page.locator('body')).not.toHaveClass(/\bbusy\b/);
    const settled = await save();
    expect(settled).toEqual(committed);
    expect(settled.state.rng).toEqual(response.rng);
    await writeFile(`build/battle-poll-profile/edge-${branch}.json`, JSON.stringify({
      branch, originalRevision: revision, response,
      committed: committed.checksum, settled: settled.checksum, rng: settled.state.rng,
    }, null, 2));
  });
}

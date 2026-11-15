/* The app has already applied the authoritative Worker response to view. */
export async function waitForSoldierStep(page, { battleId, round, revision }) {
 const committed = await page.waitForFunction(({ battleId, round, revision }) => {
  const receipt = view?.presentation;
  if (!view?.game || view.revision <= revision || receipt?.revision !== view.revision ||
      !receipt.scenes?.some(scene => scene.kind === 'soldier_step' && scene.battle_id === battleId)) return false;
  const battle = view.game.battle;
  return !battle?.extended?.siege || !!battle.extended.duel || battle.extended.siege.round > round;
 }, { battleId, round, revision }, { timeout: 30_000 });
 await committed.dispose();
}

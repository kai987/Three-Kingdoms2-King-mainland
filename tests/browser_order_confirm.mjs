/* Existing acceptance flows approve the new visible payment dialog through
 * its real button. Dedicated confirmation coverage opts out to test cancel. */
import {expect} from '../tools/browser-tests/node_modules/@playwright/test/index.mjs';
export async function approveVisibleOrders(page){
 await page.addLocatorHandler(page.locator('#order-confirm-dialog[open]'),async()=>{
  const modal=page.locator('#order-confirm-dialog');
  await expect(modal).toHaveAttribute('data-command-book-cost','1');
  await expect(modal).toHaveAttribute('data-command-book-kind',/^[a-z_]+$/);
  await expect(modal.locator('#order-confirm-message')).toContainText(/1張命令書|命令書1枚/,{useInnerText:true});
  await modal.locator('#order-confirm-accept').click();
 });
}


void thunk_FUN_fb2d(void)

{
  undefined1 uStack0000;
  
  uStack0000 = 0xa0;
                    /* WARNING: Could not recover jumptable at 0xa01b. Too many branches */
                    /* WARNING: Treating indirect jump as call */
  (*(code *)IRQ)();
  return;
}



void FUN_a045(void)

{
  undefined1 uStack0000;
  
  DAT_000a = 0xa5;
  uStack0000 = 0xa0;
  far_call_inline_word(0);
  uStack0000 = 0xa0;
  (*(code *)IRQ)();
  return;
}


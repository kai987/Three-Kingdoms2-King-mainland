
void FUN_a030(void)

{
  undefined1 uStack0000;
  
  if (((DAT_0540 != '\0') && (DAT_0540 != '\x01')) && (DAT_0540 != '\x02')) {
    FUN_a069();
    return;
  }
  DAT_0000 = DAT_0560;
  DAT_000a = 0xa5;
  uStack0000 = 0xa0;
  far_call_inline_word(0);
  uStack0000 = 0xa0;
  (*(code *)IRQ)();
  return;
}



void FUN_df35(void)

{
  undefined1 uVar1;
  undefined1 uStack0000;
  
  DAT_000e = DAT_0420;
  DAT_000f = '\x1d';
  uVar1 = DAT_007c;
  if (DAT_008f == '\0') {
    do {
      uStack0000 = 0xdf;
      FUN_df62();
      DAT_000f = DAT_000f + -1;
    } while (-1 < DAT_000f);
  }
  DAT_007c = uVar1;
  DAT_04e0 = 0;
  DAT_04e1 = 0;
  DAT_04e2 = 0;
  DAT_04e3 = 0;
  return;
}


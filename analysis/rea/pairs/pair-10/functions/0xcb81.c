
void FUN_cb81(void)

{
  char cVar1;
  undefined1 uStack0000;
  
  DAT_0030 = DAT_0027;
  DAT_0045 = 0;
  do {
    uStack0000 = 0xcb;
    cVar1 = FUN_d105(DAT_0045);
    if (cVar1 == DAT_0040) {
      uStack0000 = 0xcb;
      FUN_cba3();
    }
    DAT_0045 = DAT_0045 + 1;
  } while (DAT_0045 < 0x1e);
  return;
}


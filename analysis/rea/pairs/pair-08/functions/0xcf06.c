
/* WARNING: Globals starting with '_' overlap smaller symbols at the same address */

void FUN_cf06(void)

{
  undefined1 uStack0000;
  
  DAT_052b = DAT_0664;
  uStack0000 = 0xcf;
  FUN_f368(DAT_0507 & 0xf);
  if (*(char *)(_DAT_0000 + 3) == '\x03') {
    DAT_6f44 = DAT_050f;
    DAT_0509 = 10;
    DAT_042c = DAT_0507 >> 4;
    DAT_00a4 = 3;
    DAT_050a = 0xb5;
  }
  else {
    uStack0000 = 0xcf;
    FUN_cf92();
    DAT_0509 = 0;
    DAT_042c = DAT_0507 & 0xf;
    DAT_00a4 = 4;
    DAT_050a = 0xbf;
  }
  DAT_0514 = 0;
  return;
}



/* WARNING: Globals starting with '_' overlap smaller symbols at the same address */

void thunk_FUN_d66e(void)

{
  undefined1 uStack0000;
  
  DAT_0514 = 0;
  DAT_052b = DAT_0664;
  if (DAT_050f == '\x03') {
    uStack0000 = 0xd6;
    FUN_f368(DAT_0507 & 0xf);
    DAT_6f44 = *(char *)(_DAT_0000 + 3);
    DAT_0509 = 0;
    DAT_042c = DAT_0507 & 0xf;
    DAT_00a4 = 4;
    DAT_050a = 0x51;
  }
  else {
    DAT_6f44 = DAT_050f;
    DAT_042c = DAT_0507 >> 4;
    DAT_00a4 = 3;
    DAT_050a = 0x50;
  }
  DAT_0500 = 7;
  DAT_0501 = 2;
  return;
}


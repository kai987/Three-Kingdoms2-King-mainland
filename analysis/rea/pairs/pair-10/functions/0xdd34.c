
void FUN_dd34(void)

{
  byte bVar1;
  byte bVar2;
  undefined1 uStack0000;
  
  uStack0000 = 0xdd;
  FUN_f25f(0x21);
  bVar1 = 0;
  DAT_0012 = DAT_0542;
  do {
    bVar2 = DAT_0012 & 1;
    DAT_0012 = DAT_0012 >> 1;
    if (bVar2 != 0) {
      uStack0000 = 0xdd;
      FUN_dd53();
    }
    bVar1 = bVar1 + 1;
  } while (bVar1 < 5);
  return;
}



void thunk_FUN_a77f(void)

{
  byte bVar1;
  undefined1 uStack0000;
  
  if ((DAT_005e + 5U & 0xf) != 0) {
    return;
  }
  DAT_0001 = DAT_6f05;
  DAT_0002 = 0;
  DAT_0003 = 0;
  uStack0000 = 0xa7;
  FUN_e9ba();
  bVar1 = 0x3a;
  do {
    *(undefined1 *)(bVar1 + 0x380) = *(undefined1 *)(bVar1 + 0xa7f6);
    bVar1 = bVar1 - 1;
  } while (-1 < (char)bVar1);
  if (DAT_0007 >> 4 != 0) {
    DAT_03aa = (DAT_0007 >> 4) + 0x76;
  }
  DAT_03ab = (DAT_0007 & 0xf) + 0x76;
  DAT_007e = DAT_007e | 4;
  return;
}


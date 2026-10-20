
/* WARNING: Globals starting with '_' overlap smaller symbols at the same address */

void FUN_ecbf(void)

{
  byte bVar1;
  
  DAT_0087 = 0;
  DAT_0088 = 4;
  DAT_0089 = 4;
  _DAT_0000 = 0x100;
  _DAT_0002 = &DAT_0120;
  bVar1 = 0;
  do {
    _DAT_0002[bVar1] = *(undefined1 *)(_DAT_0000 + (ushort)bVar1);
    *(undefined1 *)(_DAT_0000 + (ushort)bVar1) = 0xf;
    bVar1 = bVar1 + 1;
  } while (bVar1 < 0x20);
  return;
}


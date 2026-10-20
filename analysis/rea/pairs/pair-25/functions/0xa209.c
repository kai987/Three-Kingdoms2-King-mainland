
/* WARNING: Globals starting with '_' overlap smaller symbols at the same address */

void FUN_a209(void)

{
  byte bVar1;
  undefined1 uStack0000;
  
  DAT_0002 = 0;
  do {
    uStack0000 = 0xa2;
    FUN_f368(DAT_0002);
    bVar1 = 4;
    do {
      if ((*(byte *)(_DAT_0000 + (ushort)bVar1) & 0xf) != 0) {
        *(char *)(_DAT_0000 + (ushort)bVar1) = *(char *)(_DAT_0000 + (ushort)bVar1) + -1;
      }
      if ((*(byte *)(_DAT_0000 + (ushort)bVar1) & 0xf0) != 0) {
        *(char *)(_DAT_0000 + (ushort)bVar1) = *(char *)(_DAT_0000 + (ushort)bVar1) + -0x10;
      }
      bVar1 = bVar1 + 1;
    } while (bVar1 < 8);
    DAT_0002 = DAT_0002 + 1;
  } while (DAT_0002 < 7);
  return;
}


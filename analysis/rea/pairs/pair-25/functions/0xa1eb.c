
/* WARNING: Globals starting with '_' overlap smaller symbols at the same address */

byte FUN_a1eb(void)

{
  byte bVar1;
  byte bVar2;
  undefined1 uStack0000;
  
  bVar1 = 0;
  do {
    uStack0000 = 0xa1;
    region_address(bVar1);
    bVar2 = 0x11;
    do {
      if (*(char *)(_DAT_0000 + (ushort)bVar2) == DAT_000a) {
        return bVar1;
      }
      bVar2 = bVar2 + 1;
    } while (bVar2 < 0x1b);
    bVar1 = bVar1 + 1;
  } while (bVar1 < 0x1e);
  return 0;
}


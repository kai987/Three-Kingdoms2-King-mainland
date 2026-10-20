
void FUN_d337(void)

{
  byte bVar1;
  
  DAT_0001 = DAT_000b >> 1;
  DAT_0000 = (byte)(DAT_000a >> 1 | DAT_000b << 7) >> 3;
  DAT_0003 = DAT_000d >> 1;
  DAT_0002 = (byte)(DAT_000c >> 1 | DAT_000d << 7) >> 3;
  bVar1 = 0;
  while ((*(byte *)(bVar1 + 0x600) != DAT_0002 || (*(byte *)(bVar1 + 0x614) != DAT_0000))) {
    bVar1 = bVar1 + 1;
    if (0x13 < bVar1) {
      return;
    }
  }
  if ((DAT_005e & 0x40) == 0) {
    return;
  }
  return;
}


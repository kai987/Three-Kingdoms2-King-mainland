
byte FUN_d249(void)

{
  byte bVar1;
  undefined1 uStack0000;
  
  uStack0000 = 0xd2;
  FUN_d6e5();
  DAT_0036 = 0;
  DAT_002a = *DAT_00ee;
  do {
    uStack0000 = 0xd2;
    bVar1 = FUN_d105(DAT_0036);
    if ((bVar1 & 7) == DAT_6f03) {
      bVar1 = 0x11;
      do {
        if (*(char *)(DAT_0020 + (ushort)bVar1) == DAT_002a) {
          return DAT_0036;
        }
        bVar1 = bVar1 + 1;
      } while (bVar1 < 0x1b);
    }
    DAT_0036 = DAT_0036 + 1;
  } while (DAT_0036 < 0x1e);
  return 0xff;
}


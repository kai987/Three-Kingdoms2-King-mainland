
void FUN_c50e(void)

{
  byte bVar1;
  char cVar2;
  undefined1 uStack0000;
  
  uStack0000 = 0xc5;
  DAT_0036 = FUN_d249();
  cVar2 = DAT_0036 == '\0';
  uStack0000 = 0xc5;
  DAT_0045 = DAT_0036;
  FUN_d1a4();
  if (cVar2 != '\0') {
    return;
  }
  DAT_003b = 0;
  DAT_003c = 0;
  DAT_003d = 0xff;
  do {
    DAT_0036 = DAT_003b;
    uStack0000 = 0xc5;
    bVar1 = FUN_d105();
    cVar2 = (bVar1 & 7) == DAT_6f03;
    if ((bool)cVar2) {
      uStack0000 = 0xc5;
      FUN_d1a4();
      if (cVar2 != '\0') {
        uStack0000 = 0xc5;
        cVar2 = FUN_d583(DAT_0045,DAT_0036);
        if (cVar2 == -1) {
          uStack0000 = 0xc5;
          bVar1 = FUN_d304(DAT_003b);
          if ((DAT_003c <= bVar1) && (bVar1 != 10)) {
            DAT_003d = DAT_003b;
            DAT_003c = bVar1;
          }
        }
      }
    }
    DAT_003b = DAT_003b + 1;
  } while (DAT_003b < 0x1e);
  if (DAT_003d != 0xff) {
    uStack0000 = 0xc5;
    FUN_d105(DAT_0045);
    DAT_002a = *DAT_00ee;
    for (bVar1 = 0x11; *(char *)(DAT_0020 + (ushort)bVar1) != DAT_002a; bVar1 = bVar1 + 1) {
    }
    *(undefined1 *)(DAT_0020 + (ushort)bVar1) = 0xff;
    uStack0000 = 0xc5;
    FUN_d105(DAT_003d);
    for (bVar1 = 0x11; *(char *)(DAT_0020 + (ushort)bVar1) != -1; bVar1 = bVar1 + 1) {
    }
    *(char *)(DAT_0020 + (ushort)bVar1) = DAT_002a;
    uStack0000 = 0xc5;
    FUN_d3dd(DAT_0045);
    uStack0000 = 0xc5;
    FUN_d165(2);
  }
  uStack0000 = 0xc5;
  FUN_d249();
  return;
}


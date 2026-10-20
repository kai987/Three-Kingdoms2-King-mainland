
void FUN_cba3(void)

{
  byte bVar1;
  char cVar2;
  byte bVar3;
  undefined1 uStack0000;
  
  DAT_0044 = 0x11;
  do {
    uStack0000 = 0xcb;
    FUN_d105(DAT_0045);
    cVar2 = DAT_0020[DAT_0044];
    if ((cVar2 == -1) || (cVar2 == DAT_0030)) {
      while (DAT_0045 = DAT_0045 + 1, DAT_0045 < 0x1e) {
        uStack0000 = 0xcb;
        cVar2 = FUN_d105(DAT_0045);
        if (cVar2 == DAT_0040) {
          uStack0000 = 0xcb;
          FUN_cba3();
        }
      }
      return;
    }
    DAT_0032 = DAT_0040;
    uStack0000 = 0xcb;
    DAT_0031 = cVar2;
    FUN_cf7c();
    uStack0000 = 0xcb;
    bVar1 = FUN_d2ab(DAT_0031,3);
    if (bVar1 < 0x1f) {
      uStack0000 = 0xcb;
      bVar1 = FUN_d4bb(100);
      if (bVar1 < 0x14) {
        bVar3 = 0xb;
        uStack0000 = 0xcb;
        bVar1 = FUN_d2ab(DAT_0031);
        *(byte *)(DAT_0022 + (ushort)bVar3) = bVar1 & 0xfc;
        *(byte *)(DAT_0022 + 5) = DAT_0045;
      }
    }
    DAT_0044 = DAT_0044 + 1;
  } while (DAT_0044 < 0x1b);
  uStack0000 = 0xcb;
  FUN_d3dd(DAT_0045);
  uStack0000 = 0xcc;
  cVar2 = FUN_d304(DAT_0045);
  if (cVar2 == '\0') {
    uStack0000 = 0xcc;
    FUN_d105(DAT_0045);
    *DAT_0020 = 7;
  }
  return;
}


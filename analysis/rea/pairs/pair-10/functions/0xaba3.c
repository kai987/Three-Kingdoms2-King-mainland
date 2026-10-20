
void FUN_aba3(void)

{
  char cVar1;
  byte bVar2;
  byte bVar3;
  undefined1 uStack0000;
  
  uStack0000 = 0xab;
  FUN_f266(0x30);
  DAT_002b = 0xff;
  DAT_002c = -1;
  DAT_002d = -1;
  for (DAT_002a = DAT_0038 << 3; -1 < *(char *)(DAT_002a + 0x9d72); DAT_002a = DAT_002a + 1) {
    uStack0000 = 0xab;
    bVar2 = FUN_d105();
    if (bVar2 == 7) {
      DAT_002d = *(char *)(DAT_002a + 0x9d72);
    }
    else if (bVar2 == DAT_0040) {
      uStack0000 = 0xab;
      bVar2 = FUN_d307();
      if ((bVar2 < 10) && (bVar2 < DAT_002b)) {
        DAT_002c = *(char *)(DAT_002a + 0x9d72);
        DAT_002b = bVar2;
      }
    }
  }
  if ((DAT_002c == -1) && (DAT_002d == -1)) {
    bVar3 = 0xb;
    uStack0000 = 0xac;
    bVar2 = FUN_d2ab(DAT_0041);
    *(byte *)(DAT_0022 + (ushort)bVar3) = bVar2 & 0xfc;
    do {
      uStack0000 = 0xac;
      bVar2 = FUN_e89a();
      if ((bVar2 & 7) == 0) {
        *(char *)(DAT_0022 + 5) = DAT_0038;
        DAT_002d = 0xff;
        return;
      }
      DAT_002d = (bVar2 & 7) - 1;
      cVar1 = *(char *)((byte)(DAT_0038 * '\b' + DAT_002d) + 0x9d72);
    } while (cVar1 < '\0');
    *(char *)(DAT_0022 + 5) = cVar1;
    DAT_002d = 0xff;
    return;
  }
  uStack0000 = 0xab;
  FUN_d105();
  for (bVar2 = 0x11; DAT_0020[bVar2] != 0xff; bVar2 = bVar2 + 1) {
  }
  DAT_0020[bVar2] = DAT_0041;
  *DAT_0020 = *DAT_0020 & 0xf8 | DAT_0040;
  if (DAT_0042 == '\0') {
    DAT_0020 = (byte *)CONCAT11(DAT_0020._1_1_,DAT_0041);
    uStack0000 = 0xac;
    FUN_d00c();
  }
  return;
}


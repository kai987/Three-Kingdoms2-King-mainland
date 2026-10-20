
/* WARNING: Globals starting with '_' overlap smaller symbols at the same address */

void FUN_b933(void)

{
  char cVar1;
  byte bVar2;
  undefined1 uStack0000;
  
  DAT_6f8f = 0xff;
  DAT_002a = 4;
  if (DAT_0504 < '\0') {
    DAT_002a = 0;
  }
  if ((&DAT_04d8)[DAT_002a] != -1) {
    bVar2 = *(byte *)(DAT_002a + 0x4da);
    if ((*(char *)(DAT_6f8c + 0x600) != *(char *)(DAT_002a + 0x4d9)) ||
       (*(byte *)(DAT_002a + 0x614) != bVar2)) {
      if (0xf < bVar2) {
        bVar2 = bVar2 - 1;
      }
      _DAT_0020 = CONCAT11(bVar2,*(char *)(DAT_002a + 0x4d9));
      DAT_0022 = 2;
      uStack0000 = 0xb9;
      FUN_a8e8();
      if (*(char *)(DAT_6f8c + 0x6fc9) == '\0') {
        DAT_6f8b = 0xff;
        return;
      }
    }
    _DAT_0020 = CONCAT11(*(undefined1 *)(DAT_6f8c + 0x614),*(undefined1 *)(DAT_6f8c + 0x600));
    uStack0000 = 0xb9;
    cVar1 = FUN_b6e5();
    if (cVar1 == '\0') {
      uStack0000 = 0xb9;
      FUN_b491((&DAT_0664)[(byte)(&DAT_04d8)[DAT_002a]]);
      DAT_0023._0_1_ = *(byte *)(_DAT_0020 + 2);
      DAT_0023._1_1_ = *(byte *)(_DAT_0020 + 0xb);
      uStack0000 = 0xb9;
      FUN_b491((&DAT_0664)[DAT_6f8c]);
      DAT_0022 = *(char *)(_DAT_0020 + 2);
      cVar1 = (byte)DAT_0023 - DAT_0022;
      if (cVar1 < '\0') {
        cVar1 = '\0';
      }
      _DAT_0020 = CONCAT11(DAT_0021,cVar1 + '\n');
      do {
        uStack0000 = 0xb9;
        bVar2 = FUN_b5d5();
      } while (100 < bVar2);
      DAT_002a = DAT_0023._1_1_ * '\n' + CARRY1(DAT_0023._1_1_ * '\b',DAT_0023._1_1_);
      _DAT_0020 = (ushort)(byte)DAT_0023;
      DAT_0022 = 0;
      do {
        uStack0000 = 0xba;
        bVar2 = FUN_b5d5();
      } while (10 < bVar2);
      DAT_0023._0_1_ = bVar2 + 0x1e;
      uStack0000 = 0xba;
      FUN_b585();
      _DAT_0020 = CONCAT11(DAT_0027,DAT_0026);
      DAT_0023._0_1_ = 10;
      DAT_0022 = 0;
      DAT_0023._1_1_ = 0;
      uStack0000 = 0xba;
      FUN_b536();
      DAT_0022 = DAT_0020 + DAT_002a;
      DAT_0023._0_1_ = DAT_0021 + CARRY1(DAT_0020,DAT_002a);
      uStack0000 = 0xba;
      FUN_b491((&DAT_0664)[DAT_6f8c]);
      DAT_0023._1_1_ = *(byte *)(_DAT_0020 + 8);
      DAT_0025 = *(byte *)(_DAT_0020 + 9) & 3;
      DAT_0026 = DAT_0023._1_1_ - DAT_0022;
      DAT_0027 = (DAT_0025 - (byte)DAT_0023) -
                 (((DAT_0022 & (~DAT_0023._1_1_ | DAT_0026) | DAT_0026 & ~DAT_0023._1_1_) & 0x80) ==
                 0);
      if ((((byte)DAT_0023 & (~DAT_0025 | DAT_0027) | DAT_0027 & ~DAT_0025) & 0x80) == 0) {
        DAT_0026 = 0;
        DAT_0027 = 0;
        DAT_0022 = DAT_0023._1_1_;
        DAT_0023._0_1_ = DAT_0025;
      }
      *(byte *)(_DAT_0020 + 8) = DAT_0026;
      *(byte *)(_DAT_0020 + 9) = *(byte *)(_DAT_0020 + 9) & 0xfc | DAT_0027;
      DAT_042c = DAT_0022;
      DAT_042d = (byte)DAT_0023;
      DAT_042e = 0;
      DAT_6f8f = 0;
    }
  }
  DAT_6f8b = 0xff;
  return;
}


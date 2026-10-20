
void FUN_cc12(void)

{
  byte bVar1;
  byte bVar2;
  byte bVar3;
  byte bVar4;
  bool bVar5;
  undefined1 uStack0000;
  
  DAT_0036 = 0xff;
  while (DAT_0036 = DAT_0036 + 1, DAT_0036 < 0x1e) {
    uStack0000 = 0xcc;
    bVar4 = FUN_d105(DAT_0036);
    if (((bVar4 & 7) == DAT_6f03) &&
       (bVar4 = *(byte *)(DAT_0020 + 3) -
                ((*(byte *)(DAT_0020 + 2) - 0x32 & ~*(byte *)(DAT_0020 + 2) & 0x80) == 0),
       (bVar4 & ~*(byte *)(DAT_0020 + 3) & 0x80) == 0)) {
      uStack0000 = 0xcc;
      FUN_f266(bVar4,0x30);
      if ((*(byte *)(DAT_0036 + 0x8ffc) & 4) != 0) {
        uStack0000 = 0xcc;
        FUN_ccf8();
        uStack0000 = 0xcc;
        FUN_d105(DAT_0036);
        bVar2 = *(byte *)(DAT_0020 + 4) - DAT_0039;
        bVar4 = ~*(byte *)(DAT_0020 + 4);
        bVar3 = (*(byte *)(DAT_0020 + 5) - DAT_003a) -
                (((DAT_0039 & (bVar4 | bVar2) | bVar2 & bVar4) & 0x80) == 0);
        bVar4 = ~*(byte *)(DAT_0020 + 5);
        bVar1 = DAT_003a & (bVar4 | bVar3);
        DAT_0039 = bVar2;
        DAT_003a = bVar3;
        if (((bVar1 | bVar3 & bVar4) & 0x80) != 0) {
          if (((bVar3 - 1) - ((bVar2 - 0x2c & ~bVar2 & 0x80) == 0) & ~bVar3 & 0x80) != 0) {
            DAT_0039 = 0x2c;
            DAT_003a = 1;
          }
          bVar2 = *(byte *)(DAT_0020 + 4) - DAT_0039;
          bVar4 = ~*(byte *)(DAT_0020 + 4);
          bVar1 = DAT_0039 & (bVar4 | bVar2);
          *(byte *)(DAT_0020 + 4) = bVar2;
          *(byte *)(DAT_0020 + 5) =
               (*(char *)(DAT_0020 + 5) - DAT_003a) - (((bVar1 | bVar2 & bVar4) & 0x80) == 0);
          uStack0000 = 0xcc;
          FUN_f266(0x30);
          DAT_0022._1_1_ = *(undefined1 *)((byte)(DAT_0036 << 1) + 0x8fc0);
          DAT_0020 = CONCAT11(DAT_003a,DAT_0039);
          DAT_0022._0_1_ = 0;
          uStack0000 = 0xcc;
          FUN_d438();
          DAT_0020 = CONCAT11(DAT_0027,DAT_0026);
          DAT_0022._0_1_ = DAT_0028;
          DAT_0022._1_1_ = 100;
          DAT_0024 = 0;
          uStack0000 = 0xcc;
          FUN_d336();
          DAT_0039 = (byte)DAT_0020;
          DAT_003a = DAT_0020._1_1_;
          uStack0000 = 0xcc;
          FUN_d105(DAT_0036);
          bVar5 = CARRY1(*(byte *)(DAT_0020 + 2),DAT_0039);
          *(byte *)(DAT_0020 + 2) = *(byte *)(DAT_0020 + 2) + DAT_0039;
          *(byte *)(DAT_0020 + 3) = *(char *)(DAT_0020 + 3) + DAT_003a + bVar5;
          uStack0000 = 0xcc;
          FUN_d69d();
          uStack0000 = 0xcc;
          FUN_d165(2);
        }
      }
    }
  }
  return;
}


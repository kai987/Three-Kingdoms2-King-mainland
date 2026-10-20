
void FUN_a91f(void)

{
  byte bVar1;
  byte bVar2;
  char cVar3;
  byte bVar4;
  char cStack0000;
  
  DAT_6f73 = 0;
  DAT_6f74 = 0;
  DAT_6f75 = 0;
  DAT_6f76 = 0;
  DAT_6f77 = 0;
  DAT_6f78 = 0;
  DAT_0040 = 0;
  do {
    cStack0000 = *(char *)(DAT_0040 + 0x664);
    if (cStack0000 != -1) {
      bVar4 = FUN_d2ab(0);
      DAT_0020._0_1_ = *(byte *)(DAT_0022 + 8);
      DAT_0020._1_1_ = *(byte *)(DAT_0022 + 9) & 3;
      DAT_0022 = (ushort)bVar4 << 8;
      DAT_0030 = (byte)DAT_0020;
      DAT_0031 = DAT_0020._1_1_;
      FUN_d438();
      DAT_0020._0_1_ = DAT_0026;
      DAT_0020._1_1_ = DAT_0027;
      DAT_0022 = CONCAT11(100,DAT_0028);
      DAT_0024 = 0;
      FUN_d336();
      cVar3 = cStack0000;
      cStack0000 = 0xa9;
      FUN_d2ab(cVar3,0);
      *(byte *)(DAT_0022 + 8) = (byte)DAT_0020;
      *(byte *)(DAT_0022 + 9) = *(byte *)(DAT_0022 + 9) & 0xfc | DAT_0020._1_1_;
      bVar1 = DAT_0030 - (byte)DAT_0020;
      bVar2 = (DAT_0031 - DAT_0020._1_1_) -
              ((((byte)DAT_0020 & (~DAT_0030 | bVar1) | bVar1 & ~DAT_0030) & 0x80) == 0);
      bVar4 = ~DAT_0031;
      DAT_0030 = bVar1;
      DAT_0031 = bVar2;
      if (((DAT_0020._1_1_ & (bVar4 | bVar2) | bVar2 & bVar4) & 0x80) != 0) {
        bVar4 = 0;
        if (9 < DAT_0040) {
          bVar4 = 2;
        }
        bVar2 = (&DAT_6f73)[bVar4];
        (&DAT_6f73)[bVar4] = bVar1 + bVar2;
        (&DAT_6f74)[bVar4] = DAT_0031 + (&DAT_6f74)[bVar4] + CARRY1(bVar1,bVar2);
      }
    }
    DAT_0040 = DAT_0040 + 1;
  } while (DAT_0040 < 0x14);
  return;
}


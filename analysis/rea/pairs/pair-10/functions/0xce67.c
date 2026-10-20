
void FUN_ce67(void)

{
  byte bVar1;
  byte bVar2;
  byte bVar3;
  undefined1 uStack0000;
  
  bVar3 = 0xfe;
  do {
    bVar3 = bVar3 + 2;
    bVar1 = DAT_0522 - (&DAT_cec9)[bVar3];
    bVar1 = (DAT_0523 - (&DAT_ceca)[bVar3]) -
            ((((&DAT_cec9)[bVar3] & (~DAT_0522 | bVar1) | bVar1 & ~DAT_0522) & 0x80) == 0);
  } while ((((&DAT_ceca)[bVar3] & (~DAT_0523 | bVar1) | bVar1 & ~DAT_0523) & 0x80) != 0);
  DAT_0022._1_1_ = (&DAT_ced3)[bVar3 >> 1];
  DAT_0020._0_1_ = DAT_0522;
  DAT_0020._1_1_ = DAT_0523;
  DAT_0022._0_1_ = 0;
  uStack0000 = 0xce;
  FUN_d438();
  DAT_0020._0_1_ = DAT_0026;
  DAT_0020._1_1_ = DAT_0027;
  DAT_0022._0_1_ = DAT_0028;
  DAT_0022._1_1_ = 100;
  DAT_0024 = 0;
  uStack0000 = 0xce;
  FUN_d336();
  bVar1 = DAT_0522 - (byte)DAT_0020;
  bVar2 = (DAT_0523 - DAT_0020._1_1_) -
          ((((byte)DAT_0020 & (~DAT_0522 | bVar1) | bVar1 & ~DAT_0522) & 0x80) == 0);
  bVar3 = ~DAT_0523;
  DAT_0522 = bVar1;
  DAT_0523 = bVar2;
  if (((DAT_0020._1_1_ & (bVar3 | bVar2) | bVar2 & bVar3) & 0x80) == 0) {
    DAT_0522 = 0;
    DAT_0523 = 0;
  }
  return;
}


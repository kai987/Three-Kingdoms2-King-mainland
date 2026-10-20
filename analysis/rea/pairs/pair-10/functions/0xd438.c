
void FUN_d438(void)

{
  char cVar1;
  byte bVar2;
  bool bVar3;
  bool bVar4;
  byte bVar5;
  
  cVar1 = '\a';
  DAT_0024 = 0;
  DAT_0025 = 0;
  DAT_0026 = 0;
  DAT_0027 = 0;
  DAT_0028 = 0;
  DAT_0029 = '\0';
  do {
    bVar2 = DAT_0022._1_1_ & 1;
    DAT_0022._1_1_ = DAT_0022._1_1_ >> 1;
    if (bVar2 != 0) {
      bVar3 = CARRY1((byte)DAT_0020,DAT_0026);
      DAT_0026 = (byte)DAT_0020 + DAT_0026;
      bVar4 = CARRY1(DAT_0020._1_1_,DAT_0027);
      DAT_0027 = DAT_0020._1_1_ + DAT_0027 + bVar3;
      bVar3 = CARRY1((byte)DAT_0022,DAT_0028);
      DAT_0028 = (byte)DAT_0022 + DAT_0028 + bVar4;
      DAT_0029 = DAT_0024 + DAT_0029 + bVar3;
    }
    bVar2 = (byte)DAT_0020 >> 7;
    DAT_0020._0_1_ = (byte)DAT_0020 << 1;
    bVar5 = DAT_0020._1_1_ >> 7;
    DAT_0020._1_1_ = DAT_0020._1_1_ << 1 | bVar2;
    bVar2 = (byte)DAT_0022 >> 7;
    DAT_0022._0_1_ = (byte)DAT_0022 << 1 | bVar5;
    DAT_0024 = DAT_0024 << 1 | bVar2;
    cVar1 = cVar1 + -1;
  } while (-1 < cVar1);
  return;
}


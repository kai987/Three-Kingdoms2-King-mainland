
void FUN_d40f(void)

{
  char cVar1;
  byte bVar2;
  byte bVar3;
  
  DAT_0025 = 0;
  DAT_0026 = 0;
  cVar1 = '\x0f';
  do {
    bVar2 = DAT_0020._1_1_ >> 7;
    DAT_0020._1_1_ = DAT_0020._1_1_ * '\x02';
    bVar3 = (byte)DAT_0022 >> 7;
    DAT_0022._0_1_ = (byte)DAT_0022 << 1 | bVar2;
    bVar3 = DAT_0025 << 1 | bVar3;
    DAT_0026 = DAT_0026 << 1 | DAT_0025 >> 7;
    DAT_0027 = bVar3 - DAT_0022._1_1_;
    bVar2 = (DAT_0026 - DAT_0024) -
            (((DAT_0022._1_1_ & (~bVar3 | DAT_0027) | DAT_0027 & ~bVar3) & 0x80) == 0);
    DAT_0025 = bVar3;
    if (((DAT_0024 & (~DAT_0026 | bVar2) | bVar2 & ~DAT_0026) & 0x80) != 0) {
      DAT_0020._1_1_ = DAT_0020._1_1_ + 1;
      DAT_0025 = DAT_0027;
      DAT_0026 = bVar2;
    }
    cVar1 = cVar1 + -1;
  } while (-1 < cVar1);
  return;
}


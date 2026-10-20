
void FUN_d336(void)

{
  byte bVar1;
  char cVar2;
  byte bVar3;
  byte bVar4;
  
  DAT_0025 = 0;
  DAT_0026 = 0;
  DAT_0027 = 0;
  cVar2 = '\x17';
  do {
    bVar3 = (byte)DAT_0020 >> 7;
    DAT_0020._0_1_ = (byte)DAT_0020 * '\x02';
    bVar4 = DAT_0020._1_1_ >> 7;
    DAT_0020._1_1_ = DAT_0020._1_1_ << 1 | bVar3;
    bVar3 = (byte)DAT_0022 >> 7;
    DAT_0022._0_1_ = (byte)DAT_0022 << 1 | bVar4;
    bVar3 = DAT_0025 << 1 | bVar3;
    bVar4 = DAT_0026 << 1 | DAT_0025 >> 7;
    DAT_0027 = DAT_0027 << 1 | DAT_0026 >> 7;
    DAT_0028 = bVar3 - DAT_0022._1_1_;
    DAT_0029 = (bVar4 - DAT_0024) -
               (((DAT_0022._1_1_ & (~bVar3 | DAT_0028) | DAT_0028 & ~bVar3) & 0x80) == 0);
    bVar1 = DAT_0027 - (((DAT_0024 & (~bVar4 | DAT_0029) | DAT_0029 & ~bVar4) & 0x80) == 0);
    DAT_0025 = bVar3;
    DAT_0026 = bVar4;
    if ((bVar1 & ~DAT_0027 & 0x80) != 0) {
      DAT_0020._0_1_ = (byte)DAT_0020 + 1;
      DAT_0025 = DAT_0028;
      DAT_0026 = DAT_0029;
      DAT_0027 = bVar1;
    }
    cVar2 = cVar2 + -1;
  } while (-1 < cVar2);
  return;
}


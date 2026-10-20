
/* WARNING: Globals starting with '_' overlap smaller symbols at the same address */

void FUN_cf7c(void)

{
  char cVar1;
  byte bVar2;
  byte bVar3;
  byte bStack0000;
  
  _DAT_0024 = CONCAT11((&DAT_cad9)[(byte)(DAT_0032 << 1)],(&DAT_cad8)[(byte)(DAT_0032 << 1)]);
  bVar3 = 0xff;
  do {
    bVar3 = bVar3 + 1;
    if (*(char *)(_DAT_0024 + bVar3) == -1) {
      bStack0000 = 0xcf;
      DAT_0020._1_1_ = FUN_d2ab(DAT_0030,4);
      DAT_0022 = &DAT_0500;
      _DAT_0024 = _DAT_0024 & 0xff00;
      bStack0000 = 0xcf;
      FUN_d40f();
      bStack0000 = DAT_0020._1_1_;
      DAT_0020._1_1_ = FUN_d2ab(DAT_0033,4);
      DAT_0022 = &DAT_0500;
      _DAT_0024 = _DAT_0024 & 0xff00;
      FUN_d40f();
      DAT_0020._0_1_ = bStack0000 - DAT_0020._1_1_;
      if (((DAT_0020._1_1_ & (~bStack0000 | (byte)DAT_0020) | (byte)DAT_0020 & ~bStack0000) & 0x80)
          == 0) {
        DAT_0020._0_1_ = ((byte)DAT_0020 ^ 0xff) + 1;
        bStack0000 = 0xcf;
        bVar2 = FUN_d2ab(DAT_0031,3);
        bVar3 = bVar2 - (byte)DAT_0020;
        if ((((byte)DAT_0020 & (~bVar2 | bVar3) | bVar3 & ~bVar2) & 0x80) == 0) {
          bVar3 = 0;
        }
      }
      else {
        bStack0000 = 0xcf;
        cVar1 = FUN_d2ab(DAT_0031,3);
        bVar3 = cVar1 + (byte)DAT_0020;
      }
      bVar2 = bVar3 - 10;
      if ((bVar2 & ~bVar3 & 0x80) == 0) {
        bVar2 = 0;
      }
      if (0x62 < bVar2) {
        bVar2 = 99;
      }
      if (bVar2 < 10) {
        bVar2 = 10;
      }
      DAT_0022[3] = bVar2;
      bStack0000 = 0xd0;
      FUN_d61e();
      return;
    }
  } while (*(char *)(_DAT_0024 + bVar3) != DAT_0030);
  return;
}


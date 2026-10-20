
void FUN_af9c(void)

{
  bool bVar1;
  undefined1 uStack0000;
  
  DAT_0020._0_1_ = DAT_6f77;
  DAT_0020._1_1_ = 0x78;
  uStack0000 = 0xaf;
  FUN_d471();
  bVar1 = CARRY1(DAT_002a,DAT_6f73);
  DAT_6f73 = DAT_002a + DAT_6f73;
  DAT_6f74 = DAT_002b + DAT_6f74 + bVar1;
  DAT_0020._0_1_ = DAT_6f78;
  DAT_0020._1_1_ = 0x78;
  uStack0000 = 0xaf;
  FUN_d471();
  DAT_0020._1_1_ = DAT_002a + DAT_6f75;
  DAT_0022._0_1_ = DAT_002b + DAT_6f76 + CARRY1(DAT_002a,DAT_6f75);
  DAT_0022._1_1_ = DAT_003c;
  DAT_0024 = 0;
  uStack0000 = 0xaf;
  DAT_6f75 = DAT_0020._1_1_;
  DAT_6f76 = (char)DAT_0022;
  FUN_d40f();
  DAT_6f75 = DAT_0020._1_1_;
  DAT_6f76 = (char)DAT_0022;
  DAT_0020._1_1_ = DAT_6f73;
  DAT_0022._0_1_ = DAT_6f74;
  DAT_0022._1_1_ = DAT_003d;
  DAT_0024 = 0;
  uStack0000 = 0xb0;
  FUN_d40f();
  DAT_6f73 = DAT_0020._1_1_;
  DAT_6f74 = (char)DAT_0022;
  DAT_0036 = 0;
  do {
    if (*(byte *)(DAT_0036 + 0x664) != 0xff) {
      DAT_002b = DAT_6f75;
      DAT_002c = DAT_6f76;
      uStack0000 = 0xb0;
      DAT_002a = *(byte *)(DAT_0036 + 0x664);
      FUN_b067();
    }
    DAT_0036 = DAT_0036 + 1;
  } while (DAT_0036 < 10);
  DAT_0036 = 0;
  do {
    if (*(byte *)(DAT_0036 + 0x66e) != 0xff) {
      DAT_002b = DAT_6f73;
      DAT_002c = DAT_6f74;
      uStack0000 = 0xb0;
      DAT_002a = *(byte *)(DAT_0036 + 0x66e);
      FUN_b067();
    }
    DAT_0036 = DAT_0036 + 1;
  } while (DAT_0036 < 10);
  return;
}


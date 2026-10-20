
void FUN_a03f(void)

{
  byte bVar1;
  undefined1 uStack0000;
  
  DAT_0039 = 0;
  DAT_003a = 0;
  DAT_003b = 0;
  DAT_003c = 0;
  DAT_003d = 0;
  bVar1 = DAT_6f02 << 3 | DAT_6f03;
  DAT_6f5f = (&DAT_a133)[bVar1];
  DAT_6f60 = (&DAT_a14b)[bVar1];
  DAT_6f61 = (&DAT_a163)[bVar1];
  uStack0000 = 0xa0;
  FUN_a0d3();
  DAT_0020._0_1_ = DAT_0038;
  DAT_0020._1_1_ = 0;
  DAT_0022._0_1_ = 0;
  DAT_0022._1_1_ = 100;
  uStack0000 = 0xa0;
  FUN_d438();
  DAT_0020._1_1_ = DAT_0026;
  DAT_0022._0_1_ = DAT_0027;
  DAT_0022._1_1_ = DAT_0037;
  DAT_0024 = 0;
  uStack0000 = 0xa0;
  FUN_d40f();
  DAT_0020._0_1_ = 0;
  if ((0x1e < DAT_0020._1_1_) && (DAT_0020._0_1_ = 1, 0x46 < DAT_0020._1_1_)) {
    DAT_0020._0_1_ = 2;
  }
  bVar1 = DAT_6f02 << 2 | (byte)DAT_0020;
  DAT_6f5f = (&DAT_a17b)[bVar1] + DAT_6f5f;
  DAT_6f60 = (&DAT_a186)[bVar1] + DAT_6f60;
  DAT_6f61 = (&DAT_a191)[bVar1] + DAT_6f61;
  DAT_6f5b = DAT_6f5b + '\x01';
  return;
}


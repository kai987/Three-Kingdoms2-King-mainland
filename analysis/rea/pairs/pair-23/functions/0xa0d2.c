
void FUN_a0d2(void)

{
  bool bVar1;
  
  bVar1 = 0xfe < (byte)DAT_000a;
  DAT_000a._0_1_ = (byte)DAT_000a + 1;
  DAT_000a._1_1_ = DAT_000a._1_1_ + bVar1;
  return;
}


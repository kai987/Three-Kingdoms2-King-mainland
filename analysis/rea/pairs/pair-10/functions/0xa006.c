
void thunk_FUN_cf3f(void)

{
  byte bVar1;
  char cStack0000;
  
  cStack0000 = 0xcf;
  DAT_0020._1_1_ = FUN_d2ab(DAT_0030,4);
  DAT_0022 = 0xa00;
  DAT_0024 = 0;
  cStack0000 = 0xcf;
  FUN_d40f();
  cStack0000 = DAT_0020._1_1_ + 'F';
  DAT_0020._0_1_ = FUN_d2ab(DAT_0031,3);
  bVar1 = cStack0000 - (char)DAT_0020;
  if (0x59 < bVar1) {
    bVar1 = 0x5a;
  }
  if (bVar1 < 10) {
    bVar1 = 10;
  }
  *(byte *)(DAT_0022 + 3) = bVar1;
  cStack0000 = 0xcf;
  FUN_d61e();
  return;
}


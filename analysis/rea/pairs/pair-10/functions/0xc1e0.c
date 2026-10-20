
void FUN_c1e0(void)

{
  byte bVar1;
  char cVar2;
  undefined1 uStack0000;
  
  bVar1 = 0xf;
  do {
    (&DAT_6f73)[bVar1] = 0xff;
    bVar1 = bVar1 - 1;
  } while (-1 < (char)bVar1);
  uStack0000 = 0xc1;
  bVar1 = FUN_d4bb(100);
  if (0x1d < bVar1) {
    FUN_c298();
    return;
  }
  do {
    uStack0000 = 0xc1;
    FUN_c248();
    if (DAT_0022._1_1_ == -1) {
      FUN_c337();
      return;
    }
    DAT_0036 = DAT_0022._1_1_;
    uStack0000 = 0xc2;
    bVar1 = FUN_d283(3);
    cVar2 = 0x45 < bVar1;
  } while ((bool)cVar2);
  DAT_0022._0_1_ = '\x14';
  DAT_0022._1_1_ = 0;
  DAT_0024 = 10;
  uStack0000 = 0xc2;
  FUN_d36f(DAT_6f5e);
  if (cVar2 != '\0') {
    uStack0000 = 0xc2;
    cVar2 = FUN_d4ad(5);
    DAT_0022._0_1_ = cVar2 + (&DAT_c04b)[DAT_6f02];
    bVar1 = 3;
    uStack0000 = 0xc2;
    cVar2 = FUN_d283(DAT_0036);
    *(char *)(DAT_0020 + (ushort)bVar1) = cVar2 + (char)DAT_0022;
    uStack0000 = 0xc2;
    FUN_d5e7();
    uStack0000 = 0xc2;
    FUN_d152(5);
  }
  FUN_bec7();
  return;
}


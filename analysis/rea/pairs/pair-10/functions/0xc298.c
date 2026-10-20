
void FUN_c298(void)

{
  byte bVar1;
  char cVar2;
  undefined1 uStack0000;
  
  do {
    uStack0000 = 0xc2;
    FUN_c2eb();
    if (DAT_0022._1_1_ == -1) goto LAB_c2e8;
    DAT_0036 = DAT_0022._1_1_;
    uStack0000 = 0xc2;
    bVar1 = FUN_d283(2);
  } while ((bVar1 < 0x32) || (cVar2 = 0x4f < bVar1, (bool)cVar2));
  DAT_0022._0_1_ = '\x14';
  DAT_0022._1_1_ = '\0';
  DAT_0024 = 10;
  uStack0000 = 0xc2;
  FUN_d36f(DAT_6f5e);
  if (cVar2 != '\0') {
    uStack0000 = 0xc2;
    cVar2 = FUN_d4ad(5);
    DAT_0022._0_1_ = cVar2 + (&DAT_c04b)[DAT_6f02];
    bVar1 = 2;
    uStack0000 = 0xc2;
    cVar2 = FUN_d283(DAT_0036);
    *(char *)(DAT_0020 + (ushort)bVar1) = cVar2 + (char)DAT_0022;
    uStack0000 = 0xc2;
    FUN_d5e7();
    uStack0000 = 0xc2;
    FUN_d152(5);
  }
LAB_c2e8:
  FUN_bec7();
  return;
}


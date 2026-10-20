
void FUN_c2eb(void)

{
  byte bVar1;
  undefined1 uStack0000;
  
  DAT_0024 = 0x11;
  DAT_0022._0_1_ = 0xff;
  DAT_0022._1_1_ = 0xff;
  do {
    uStack0000 = 0xc2;
    FUN_d105(DAT_6f5e);
    DAT_0025 = *(char *)(DAT_0020 + (ushort)DAT_0024);
    if ((DAT_0025 != -1) && ((&DAT_6f62)[DAT_0024] != '\0')) {
      uStack0000 = 0xc3;
      bVar1 = FUN_d283(DAT_0025,2);
      if (bVar1 < (byte)DAT_0022) {
        DAT_0022._1_1_ = DAT_0024;
        DAT_0022._0_1_ = bVar1;
      }
    }
    DAT_0024 = DAT_0024 + 1;
  } while (DAT_0024 < 0x1b);
  uStack0000 = 0xc3;
  FUN_d105(DAT_6f5e);
  if (-1 < (char)DAT_0022._1_1_) {
    (&DAT_6f62)[DAT_0022._1_1_] = 0;
    DAT_0022._1_1_ = *(byte *)(DAT_0020 + (ushort)DAT_0022._1_1_);
  }
  return;
}



void FUN_c3a4(byte param_1)

{
  byte bVar1;
  byte bVar2;
  
  DAT_0022._0_1_ = *(byte *)(DAT_0020 + 2) - (&DAT_c3bf)[param_1];
  bVar1 = ~*(byte *)(DAT_0020 + 2);
  bVar2 = (*(byte *)(DAT_0020 + 3) - (&DAT_c3c0)[param_1]) -
          ((((&DAT_c3bf)[param_1] & (bVar1 | (byte)DAT_0022) | (byte)DAT_0022 & bVar1) & 0x80) == 0)
  ;
  bVar1 = ~*(byte *)(DAT_0020 + 3);
  if ((((&DAT_c3c0)[param_1] & (bVar1 | bVar2) | bVar2 & bVar1) & 0x80) != 0) {
    *(byte *)(DAT_0020 + 3) = bVar2;
    *(byte *)(DAT_0020 + 2) = (byte)DAT_0022;
  }
  return;
}


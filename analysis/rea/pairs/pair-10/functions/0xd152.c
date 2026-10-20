
void FUN_d152(byte param_1)

{
  byte bVar1;
  byte bVar2;
  
  DAT_0020._0_1_ = param_1;
  bVar2 = DAT_6f5d - param_1;
  bVar1 = ~DAT_6f5d;
  DAT_6f5d = bVar2;
  if ((bVar2 != 0) && (((param_1 & (bVar1 | bVar2) | bVar2 & bVar1) & 0x80) != 0)) {
    return;
  }
  FUN_d140();
  return;
}


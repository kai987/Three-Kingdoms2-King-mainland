
void FUN_d165(byte param_1)

{
  byte bVar1;
  byte bVar2;
  undefined1 unaff_retaddr;
  
  DAT_0020._0_1_ = param_1;
  bVar2 = DAT_6f5d - param_1;
  bVar1 = ~DAT_6f5d;
  DAT_6f5d = bVar2;
  if (((param_1 & (bVar1 | bVar2) | bVar2 & bVar1) & 0x80) == 0) {
    FUN_d140(unaff_retaddr);
    return;
  }
  return;
}


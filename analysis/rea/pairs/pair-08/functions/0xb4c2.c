
void FUN_b4c2(byte param_1)

{
  byte bVar1;
  
  bVar1 = (param_1 & 0xf) << 1;
  DAT_0020 = (&DAT_b4d3)[bVar1];
  DAT_0021 = (&DAT_b4d4)[bVar1];
  return;
}


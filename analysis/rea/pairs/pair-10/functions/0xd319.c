
void FUN_d319(byte param_1)

{
  byte bVar1;
  
  bVar1 = (param_1 & 0xf) << 1;
  DAT_0024 = (&DAT_d328)[bVar1];
  DAT_0025 = (&DAT_d329)[bVar1];
  return;
}


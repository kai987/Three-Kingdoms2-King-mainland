
void FUN_f368(byte param_1)

{
  byte bVar1;
  
  bVar1 = (param_1 & 0xf) << 1;
  DAT_0000 = (&DAT_f379)[bVar1];
  DAT_0001 = (&DAT_f37a)[bVar1];
  return;
}


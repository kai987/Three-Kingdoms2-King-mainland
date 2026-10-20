
void FUN_af66(byte param_1,byte param_2)

{
  byte bVar1;
  
  bVar1 = (&DAT_0140)[param_2];
  (&DAT_0140)[param_2] = param_1 + bVar1;
  (&DAT_0140)[(byte)(param_2 + 1)] = (&DAT_0140)[(byte)(param_2 + 1)] + CARRY1(param_1,bVar1);
  return;
}


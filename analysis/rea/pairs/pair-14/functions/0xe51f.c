
void FUN_e51f(char param_1)

{
  byte bVar1;
  
  bVar1 = param_1 * '\b';
  DAT_00e6 = (&DAT_e567)[bVar1];
  DAT_c000 = (&DAT_e567)[bVar1];
  DAT_00e7 = (&DAT_e567)[(byte)(bVar1 + 1)];
  DAT_c800 = (&DAT_e567)[(byte)(bVar1 + 1)];
  DAT_00e8 = (&DAT_e567)[(byte)(bVar1 + 2)];
  DAT_d000 = (&DAT_e567)[(byte)(bVar1 + 2)];
  DAT_00e9 = (&DAT_e567)[(byte)(bVar1 + 3)];
  FUN_d7fb = (&DAT_e567)[(byte)(bVar1 + 3)];
  DAT_00ea = (&DAT_e567)[(byte)(bVar1 + 4)];
  DAT_00eb = (&DAT_e567)[(byte)(bVar1 + 5)];
  DAT_00ec = (&DAT_e567)[(byte)(bVar1 + 6)];
  DAT_00ed = (&DAT_e567)[(byte)(bVar1 + 7)];
  return;
}


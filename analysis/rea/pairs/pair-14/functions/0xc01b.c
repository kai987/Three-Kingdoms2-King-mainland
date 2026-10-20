
void FUN_c01b(void)

{
  byte bVar1;
  
  bVar1 = DAT_005e >> 3 & 3;
  if (DAT_0544 == '\x03') {
    bVar1 = bVar1 + 4;
  }
  DAT_00b3 = (&DAT_c054)[bVar1];
  DAT_00c3 = DAT_00b3;
  DAT_00cb = DAT_00b3;
  DAT_00d3 = DAT_00b3;
  DAT_00db = DAT_00b3;
  DAT_00b5 = (&DAT_c05c)[bVar1];
  DAT_00c5 = DAT_00b5;
  DAT_00cd = DAT_00b5;
  DAT_00d5 = DAT_00b5;
  DAT_00dd = DAT_00b5;
  return;
}


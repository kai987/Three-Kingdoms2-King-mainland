
byte FUN_dc31(void)

{
  byte bVar1;
  byte unaff_retaddr;
  
  bVar1 = (&DAT_dd4e)[DAT_07f3];
  if (((&DAT_dd4e)[DAT_07f3] & DAT_07f2) != 0) {
    bVar1 = unaff_retaddr;
  }
  return bVar1;
}


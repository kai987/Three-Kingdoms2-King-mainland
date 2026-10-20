
void FUN_bc41(void)

{
  byte bVar1;
  
  DAT_2000 = DAT_008b & 0xfb;
  DAT_2006 = DAT_0480;
  bVar1 = 0;
  do {
    DAT_2007 = (&DAT_0160)[bVar1];
    bVar1 = bVar1 + 1;
  } while (bVar1 < 0x40);
  return;
}


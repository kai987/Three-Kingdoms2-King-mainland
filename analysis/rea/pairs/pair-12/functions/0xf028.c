
void FUN_f028(void)

{
  byte bVar1;
  
  DAT_2000 = DAT_008b & 0xfb;
  DAT_0000 = 8 - (DAT_019d & 7);
  bVar1 = 0;
  do {
    DAT_2007 = (&DAT_019e)[bVar1];
    bVar1 = bVar1 + 1;
  } while (bVar1 < DAT_0000);
  DAT_2006 = DAT_019d & 0xf8;
  do {
    if (7 < bVar1) {
      return;
    }
    DAT_2007 = (&DAT_019e)[bVar1];
    bVar1 = bVar1 + 1;
  } while (bVar1 != 0);
  return;
}


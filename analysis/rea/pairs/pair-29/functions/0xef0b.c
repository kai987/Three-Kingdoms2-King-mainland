
void FUN_ef0b(void)

{
  byte bVar1;
  
  DAT_0001 = (((DAT_0140 & 3) << 1 | DAT_0141 >> 7) << 1 | (DAT_0141 & 0x7f) >> 6) << 1 |
             (DAT_0141 & 0x3f) >> 5;
  DAT_0000 = 0x1e - DAT_0001;
  DAT_2000 = DAT_008b | 4;
  bVar1 = 0;
  do {
    DAT_2007 = (&DAT_0142)[bVar1];
    bVar1 = bVar1 + 1;
  } while (bVar1 < DAT_0000);
  DAT_2006 = DAT_0141 & 0x1f;
  do {
    if (0x1d < bVar1) {
      return;
    }
    DAT_2007 = (&DAT_0142)[bVar1];
    bVar1 = bVar1 + 1;
  } while (bVar1 != 0);
  return;
}



void FUN_efc0(void)

{
  byte bVar1;
  byte bVar2;
  
  DAT_0001 = DAT_0189;
  DAT_0000 = 8 - ((DAT_0189 & 0x38) >> 3);
  bVar2 = 0;
  do {
    DAT_2006 = DAT_0001;
    DAT_2007 = (&DAT_018a)[bVar2];
    DAT_0001 = DAT_0001 + 8;
    bVar2 = bVar2 + 1;
  } while (bVar2 < DAT_0000);
  bVar1 = DAT_0189 & 199;
  do {
    DAT_0001 = bVar1;
    if (7 < bVar2) {
      return;
    }
    DAT_2006 = DAT_0001;
    DAT_2007 = (&DAT_018a)[bVar2];
    bVar2 = bVar2 + 1;
    bVar1 = DAT_0001 + 8;
  } while (bVar2 != 0);
  DAT_0001 = DAT_0001 + 8;
  return;
}


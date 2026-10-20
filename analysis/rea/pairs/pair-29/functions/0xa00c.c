
void thunk_FUN_b29f(void)

{
  byte bVar1;
  byte bVar2;
  bool bVar3;
  
  DAT_2000 = DAT_008b & 0xfb;
  DAT_0001 = DAT_0142;
  DAT_0000 = DAT_0141;
  bVar1 = 0;
  do {
    bVar2 = 0;
    do {
      bVar2 = bVar2 + 1;
      bVar1 = bVar1 + 1;
    } while (bVar2 < 0xe);
    bVar3 = 0xdf < DAT_0000;
    DAT_0000 = DAT_0000 + 0x20;
    DAT_0001 = DAT_0001 + bVar3;
  } while (bVar1 < DAT_0154);
  DAT_2006 = DAT_0147;
  bVar1 = 0;
  do {
    DAT_2007 = (&DAT_014b)[bVar1];
    bVar1 = bVar1 + 1;
  } while (bVar1 < 4);
  return;
}


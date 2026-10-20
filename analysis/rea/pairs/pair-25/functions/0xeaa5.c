
void FUN_eaa5(void)

{
  byte bVar1;
  char cVar2;
  byte bVar3;
  byte bVar4;
  
  DAT_0005 = 0;
  DAT_0006 = 0;
  DAT_0007 = 0;
  cVar2 = '\x17';
  do {
    bVar3 = DAT_0000 >> 7;
    DAT_0000 = DAT_0000 * '\x02';
    bVar4 = DAT_0001 >> 7;
    DAT_0001 = DAT_0001 << 1 | bVar3;
    bVar3 = DAT_0002 >> 7;
    DAT_0002 = DAT_0002 << 1 | bVar4;
    bVar3 = DAT_0005 << 1 | bVar3;
    bVar4 = DAT_0006 << 1 | DAT_0005 >> 7;
    DAT_0007 = DAT_0007 << 1 | DAT_0006 >> 7;
    DAT_0008 = bVar3 - DAT_0003;
    DAT_0009 = (bVar4 - DAT_0004) -
               (((DAT_0003 & (~bVar3 | DAT_0008) | DAT_0008 & ~bVar3) & 0x80) == 0);
    bVar1 = DAT_0007 - (((DAT_0004 & (~bVar4 | DAT_0009) | DAT_0009 & ~bVar4) & 0x80) == 0);
    DAT_0005 = bVar3;
    DAT_0006 = bVar4;
    if ((bVar1 & ~DAT_0007 & 0x80) != 0) {
      DAT_0000 = DAT_0000 + 1;
      DAT_0005 = DAT_0008;
      DAT_0006 = DAT_0009;
      DAT_0007 = bVar1;
    }
    cVar2 = cVar2 + -1;
  } while (-1 < cVar2);
  return;
}


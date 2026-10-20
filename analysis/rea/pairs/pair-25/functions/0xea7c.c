
void FUN_ea7c(void)

{
  char cVar1;
  byte bVar2;
  byte bVar3;
  
  DAT_0005 = 0;
  DAT_0006 = 0;
  cVar1 = '\x0f';
  do {
    bVar2 = DAT_0001 >> 7;
    DAT_0001 = DAT_0001 * '\x02';
    bVar3 = DAT_0002 >> 7;
    DAT_0002 = DAT_0002 << 1 | bVar2;
    bVar3 = DAT_0005 << 1 | bVar3;
    DAT_0006 = DAT_0006 << 1 | DAT_0005 >> 7;
    DAT_0007 = bVar3 - DAT_0003;
    bVar2 = (DAT_0006 - DAT_0004) -
            (((DAT_0003 & (~bVar3 | DAT_0007) | DAT_0007 & ~bVar3) & 0x80) == 0);
    DAT_0005 = bVar3;
    if (((DAT_0004 & (~DAT_0006 | bVar2) | bVar2 & ~DAT_0006) & 0x80) != 0) {
      DAT_0001 = DAT_0001 + 1;
      DAT_0005 = DAT_0007;
      DAT_0006 = bVar2;
    }
    cVar1 = cVar1 + -1;
  } while (-1 < cVar1);
  return;
}


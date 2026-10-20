
void FUN_ebe9(void)

{
  char cVar1;
  byte bVar2;
  bool bVar3;
  bool bVar4;
  byte bVar5;
  
  cVar1 = '\a';
  DAT_0004 = 0;
  DAT_0005 = 0;
  DAT_0006 = 0;
  DAT_0007 = 0;
  DAT_0008 = 0;
  DAT_0009 = '\0';
  do {
    bVar2 = DAT_0003 & 1;
    DAT_0003 = DAT_0003 >> 1;
    if (bVar2 != 0) {
      bVar3 = CARRY1(DAT_0000,DAT_0006);
      DAT_0006 = DAT_0000 + DAT_0006;
      bVar4 = CARRY1(DAT_0001,DAT_0007);
      DAT_0007 = DAT_0001 + DAT_0007 + bVar3;
      bVar3 = CARRY1(DAT_0002,DAT_0008);
      DAT_0008 = DAT_0002 + DAT_0008 + bVar4;
      DAT_0009 = DAT_0004 + DAT_0009 + bVar3;
    }
    bVar2 = DAT_0000 >> 7;
    DAT_0000 = DAT_0000 << 1;
    bVar5 = DAT_0001 >> 7;
    DAT_0001 = DAT_0001 << 1 | bVar2;
    bVar2 = DAT_0002 >> 7;
    DAT_0002 = DAT_0002 << 1 | bVar5;
    DAT_0004 = DAT_0004 << 1 | bVar2;
    cVar1 = cVar1 + -1;
  } while (-1 < cVar1);
  return;
}



void FUN_ec22(void)

{
  char cVar1;
  byte bVar2;
  bool bVar3;
  bool bVar4;
  byte bVar5;
  
  cVar1 = '\x0f';
  DAT_0006 = 0;
  DAT_0007 = 0;
  DAT_0008 = 0;
  DAT_0009 = 0;
  DAT_000a = '\0';
  DAT_000b = 0;
  DAT_000c = 0;
  do {
    bVar5 = DAT_0004;
    DAT_0004 = DAT_0004 >> 1;
    bVar2 = DAT_0003 & 1;
    DAT_0003 = DAT_0003 >> 1 | bVar5 << 7;
    if (bVar2 != 0) {
      bVar3 = CARRY1(DAT_0000,DAT_0006);
      DAT_0006 = DAT_0000 + DAT_0006;
      bVar4 = CARRY1(DAT_0001,DAT_0007);
      DAT_0007 = DAT_0001 + DAT_0007 + bVar3;
      bVar3 = CARRY1(DAT_0002,DAT_0008);
      DAT_0008 = DAT_0002 + DAT_0008 + bVar4;
      bVar4 = CARRY1(DAT_000b,DAT_0009);
      DAT_0009 = DAT_000b + DAT_0009 + bVar3;
      DAT_000a = DAT_000c + DAT_000a + bVar4;
    }
    bVar5 = DAT_0000 >> 7;
    DAT_0000 = DAT_0000 << 1;
    bVar2 = DAT_0001 >> 7;
    DAT_0001 = DAT_0001 << 1 | bVar5;
    bVar5 = DAT_0002 >> 7;
    DAT_0002 = DAT_0002 << 1 | bVar2;
    bVar2 = DAT_000b >> 7;
    DAT_000b = DAT_000b << 1 | bVar5;
    DAT_000c = DAT_000c << 1 | bVar2;
    cVar1 = cVar1 + -1;
  } while (-1 < cVar1);
  return;
}


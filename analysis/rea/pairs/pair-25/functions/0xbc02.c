
/* WARNING: Globals starting with '_' overlap smaller symbols at the same address */

void FUN_bc02(void)

{
  byte bVar1;
  byte bVar2;
  bool bVar3;
  
  DAT_6ffc = 0x49;
  DAT_6ffd = 0x44;
  DAT_0004 = 0;
  DAT_0005 = '\0';
  _DAT_0000 = 0x6000;
  _DAT_0002 = 0x7000;
  do {
    bVar2 = 0;
    do {
      bVar1 = *(byte *)(_DAT_0000 + (ushort)bVar2);
      *(byte *)(_DAT_0002 + (ushort)bVar2) = bVar1;
      bVar3 = CARRY1(bVar1,DAT_0004);
      DAT_0004 = bVar1 + DAT_0004;
      DAT_0005 = DAT_0005 + bVar3;
      bVar2 = bVar2 + 1;
    } while (bVar2 != 0);
    bVar2 = DAT_0001 + 1;
    _DAT_0000 = CONCAT11(bVar2,DAT_0000);
    _DAT_0002 = CONCAT11(DAT_0003 + '\x01',DAT_0002);
  } while (bVar2 < 0x6f);
  bVar2 = 0;
  do {
    bVar1 = *(byte *)(_DAT_0000 + (ushort)bVar2);
    *(byte *)(_DAT_0002 + (ushort)bVar2) = bVar1;
    bVar3 = CARRY1(bVar1,DAT_0004);
    DAT_0004 = bVar1 + DAT_0004;
    DAT_0005 = DAT_0005 + bVar3;
    bVar2 = bVar2 + 1;
  } while (bVar2 != 0xfe);
  DAT_7ffe = DAT_0004;
  DAT_7fff = DAT_0005;
  DAT_00a5 = 0x4c;
  LAB_f800 = 0x4c;
  return;
}



void FUN_e9ba(void)

{
  byte bVar1;
  byte bVar2;
  byte bVar3;
  bool bVar4;
  
  DAT_0007 = 0;
  DAT_0008 = '\0';
  DAT_0009 = '\0';
  bVar3 = DAT_0001;
  bVar1 = DAT_0002;
  bVar2 = DAT_0003;
  do {
    DAT_0003 = bVar2;
    DAT_0002 = bVar1;
    DAT_0001 = bVar3;
    bVar1 = (DAT_0002 + 0xbe) - ((DAT_0001 - 0x40 & ~DAT_0001 & 0x80) == 0);
    bVar2 = (DAT_0003 - 0xf) - ((bVar1 & ~DAT_0002 & 0x80) == 0);
    bVar3 = DAT_0001 - 0x40;
  } while ((bVar2 & ~DAT_0003 & 0x80) != 0);
  do {
    bVar1 = DAT_0001 + 0x60;
    bVar2 = (DAT_0002 + 0x7a) -
            (((~DAT_0001 & 0xa0 | bVar1 & 0xa0 | bVar1 & ~DAT_0001) & 0x80) == 0);
    bVar3 = (DAT_0003 - 1) - (((~DAT_0002 & 0x86 | bVar2 & 0x86 | bVar2 & ~DAT_0002) & 0x80) == 0);
    bVar4 = (bVar3 & ~DAT_0003 & 0x80) != 0;
    if (!bVar4) break;
    DAT_0009 = DAT_0009 + '\x0f' + bVar4;
    DAT_0001 = bVar1;
    DAT_0002 = bVar2;
    DAT_0003 = bVar3;
  } while (DAT_0009 != '\0');
  do {
    bVar1 = DAT_0001 - 0x10;
    DAT_0005 = (DAT_0002 - 0x27) - ((bVar1 & ~DAT_0001 & 0x80) == 0);
    bVar2 = DAT_0003 - ((DAT_0005 & ~DAT_0002 & 0x80) == 0);
    if ((bVar2 & ~DAT_0003 & 0x80) == 0) break;
    DAT_0009 = DAT_0009 + '\x01';
    DAT_0001 = bVar1;
    DAT_0002 = DAT_0005;
    DAT_0003 = bVar2;
  } while (DAT_0009 != '\0');
  do {
    bVar1 = DAT_0001 + 0x18;
    bVar2 = (DAT_0002 - 3) - (((~DAT_0001 & 0xe8 | bVar1 & 0xe8 | bVar1 & ~DAT_0001) & 0x80) == 0);
    bVar4 = (bVar2 & ~DAT_0002 & 0x80) != 0;
    if (!bVar4) break;
    DAT_0008 = DAT_0008 + '\x0f' + bVar4;
    DAT_0001 = bVar1;
    DAT_0002 = bVar2;
  } while (DAT_0008 != '\0');
  do {
    bVar1 = DAT_0001 + 0x9c;
    bVar2 = DAT_0002 - ((bVar1 & ~DAT_0001 & 0x80) == 0);
    if ((bVar2 & ~DAT_0002 & 0x80) == 0) break;
    DAT_0008 = DAT_0008 + '\x01';
    DAT_0001 = bVar1;
    DAT_0002 = bVar2;
  } while (DAT_0008 != '\0');
  do {
    DAT_0004 = DAT_0001 - 10;
    bVar1 = DAT_0002 - ((DAT_0004 & ~DAT_0001 & 0x80) == 0);
    bVar4 = (bVar1 & ~DAT_0002 & 0x80) != 0;
    if (!bVar4) break;
    DAT_0007 = DAT_0007 + 0xf + bVar4;
    DAT_0001 = DAT_0004;
    DAT_0002 = bVar1;
  } while (DAT_0007 != 0);
  DAT_0007 = DAT_0001 | DAT_0007;
  return;
}


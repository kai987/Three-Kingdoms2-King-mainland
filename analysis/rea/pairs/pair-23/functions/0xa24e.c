
/* WARNING: Globals starting with '_' overlap smaller symbols at the same address */

void FUN_a24e(void)

{
  char cVar1;
  char cVar2;
  byte bVar3;
  byte bStack0000;
  
  DAT_2000 = DAT_008b & 0xfb;
  DAT_2006 = DAT_0000;
  bStack0000 = (byte)DAT_000a - 0x40;
  cVar1 = DAT_000a._1_1_ - ((bStack0000 & ~(byte)DAT_000a & 0x80) == 0);
  DAT_0002 = 0;
  DAT_0003 = 0;
  do {
    cVar2 = '\0';
    bVar3 = *DAT_000a;
    _DAT_0000 = CONCAT11(((bVar3 >> 7) << 1 | (bVar3 & 0x7f) >> 6) + DAT_000d +
                         CARRY1(bVar3 * '\x04',DAT_000c),bVar3 * '\x04' + DAT_000c);
    if ((DAT_0002 & 0x10) != 0) {
      cVar2 = '\x02';
    }
    DAT_2007 = *(undefined1 *)(_DAT_0000 + (ushort)(byte)(cVar2 + 1));
    FUN_a2e4();
    DAT_0002 = DAT_0002 + 1;
    if (((DAT_0002 & 0xf) == 0) && (DAT_0003 = DAT_0003 + 1, (DAT_0003 & 1) != 0)) {
      FUN_a2ed();
    }
  } while (DAT_0003 < 0x1e);
  DAT_000a = (byte *)CONCAT11(cVar1,bStack0000);
  cVar1 = '@';
  bVar3 = 0;
  do {
    DAT_2007 = *(undefined1 *)((short)DAT_000a + (ushort)bVar3);
    bVar3 = bVar3 + 1;
    cVar1 = cVar1 + -1;
  } while (cVar1 != '\0');
  return;
}


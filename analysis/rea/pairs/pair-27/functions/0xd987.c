
/* WARNING: Globals starting with '_' overlap smaller symbols at the same address */

void FUN_d987(void)

{
  byte bVar1;
  byte bVar2;
  byte bVar3;
  bool bVar4;
  undefined1 uStack0000;
  
  DAT_0010 = DAT_0000;
  DAT_0011 = DAT_0001;
  _DAT_0000 = CONCAT11(DAT_0002,DAT_0000);
  DAT_0002 = DAT_0003;
  DAT_0003 = 100;
  DAT_0004 = 0;
  uStack0000 = 0xd9;
  FUN_ea7c();
  if (DAT_0005 != 0) {
    bVar4 = CARRY1(DAT_0005,DAT_042c);
    DAT_042c = DAT_0005 + DAT_042c;
    DAT_042d = DAT_042d + bVar4;
    DAT_0006 = DAT_042c - 0x10;
    if (((DAT_042d - 0x27) - ((DAT_0006 & ~DAT_042c & 0x80) == 0) & ~DAT_042d & 0x80) != 0) {
      DAT_042c = 0x10;
      DAT_042d = 0x27;
      DAT_0005 = DAT_0005 - DAT_0006;
    }
  }
  _DAT_0000 = CONCAT11(DAT_0011,DAT_0010);
  bVar3 = *(byte *)(_DAT_0000 + 8) - DAT_0005;
  bVar1 = ~*(byte *)(_DAT_0000 + 8);
  bVar2 = DAT_0005 & (bVar1 | bVar3);
  *(byte *)(_DAT_0000 + 8) = bVar3;
  *(char *)(_DAT_0000 + 9) = *(char *)(_DAT_0000 + 9) - (((bVar2 | bVar3 & bVar1) & 0x80) == 0);
  return;
}


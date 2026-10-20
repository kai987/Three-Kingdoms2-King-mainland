
/* WARNING: Globals starting with '_' overlap smaller symbols at the same address */

void FUN_d7c5(void)

{
  byte bVar1;
  byte bVar2;
  bool bVar3;
  undefined1 uStack0000;
  
  if (DAT_0012 == DAT_047b) {
    if ((bool)(DAT_0081 & 1)) {
      DAT_047c = 0x80;
      DAT_0090 = 0;
      DAT_008f = 0;
      DAT_0061 = 3;
      DAT_00b2 = 0;
      DAT_00b3 = 5;
      DAT_00b4 = 9;
      return;
    }
  }
  else if ((DAT_0081 & 0xc0) != 0) {
    uStack0000 = 0xd8;
    region_address(DAT_0402);
    uStack0000 = 0xd8;
    officer_address(*(undefined1 *)(_DAT_0000 + (ushort)(byte)(DAT_0012 + 0x11)));
    DAT_0002 = *(byte *)(_DAT_0000 + 8);
    DAT_0003 = *(byte *)(_DAT_0000 + 9);
    if ((char)DAT_0081 < '\0') {
      bVar2 = ('\x03' - DAT_0003) - ((DAT_0002 & -DAT_0002 - 0x19 & 0x80) == 0);
      if (((DAT_0003 & (bVar2 | 0xfc) | bVar2 & 0xfc) & 0x80) != 0) {
        uStack0000 = 0xd8;
        FUN_d987(bVar2);
        DAT_0002 = 100;
        if ((DAT_042d == 0) && (DAT_042c < 100)) {
          DAT_0002 = DAT_042c;
        }
        bVar3 = CARRY1(*(byte *)(_DAT_0000 + 8),DAT_0002);
        *(byte *)(_DAT_0000 + 8) = *(byte *)(_DAT_0000 + 8) + DAT_0002;
        *(char *)(_DAT_0000 + 9) = *(char *)(_DAT_0000 + 9) + bVar3;
        bVar2 = DAT_042c - DAT_0002;
        DAT_042d = DAT_042d - (((DAT_0002 & (~DAT_042c | bVar2) | bVar2 & ~DAT_042c) & 0x80) == 0);
        DAT_042c = bVar2;
      }
    }
    else if ((DAT_0003 != 0) || (DAT_0002 != 0)) {
      uStack0000 = 0xd8;
      FUN_d987();
      if ((DAT_0005 == '\0') &&
         (((DAT_042d - 0x26) -
           (((~DAT_042c & 0xad | DAT_042c + 0x53 & 0xad | DAT_042c + 0x53 & ~DAT_042c) & 0x80) == 0)
           & ~DAT_042d & 0x80) == 0)) {
        bVar2 = *(byte *)(_DAT_0000 + 8);
        bVar1 = bVar2 + 0x9c;
        *(byte *)(_DAT_0000 + 8) = bVar1;
        *(char *)(_DAT_0000 + 9) = *(char *)(_DAT_0000 + 9) - ((bVar1 & ~bVar2 & 0x80) == 0);
        DAT_042d = DAT_042d + (0x9b < DAT_042c);
        DAT_042c = DAT_042c + 100;
      }
    }
    DAT_0002 = *(undefined1 *)(_DAT_0000 + 9);
    _DAT_0000 = CONCAT11(*(undefined1 *)(_DAT_0000 + 8),DAT_0000);
    DAT_0003 = 0;
    uStack0000 = 0xd8;
    FUN_e9ba();
    DAT_000a = 1;
    bVar2 = 0;
    uStack0000 = 0xd8;
    FUN_d94e();
    (&DAT_031e)[bVar2] = 0x80;
    _DAT_0000 = 0x40;
    DAT_0002 = 0;
    DAT_0003 = DAT_0012;
    uStack0000 = 0xd8;
    FUN_ebe9();
    DAT_031c = DAT_0006 + 0xbb;
    DAT_031d = DAT_0007 + '$' + (0x44 < DAT_0006);
    goto LAB_d93d;
  }
  _DAT_0000 = CONCAT11(DAT_042c,DAT_0000);
  DAT_0002 = DAT_042d;
  DAT_0003 = '\0';
  uStack0000 = 0xd9;
  FUN_e9ba();
  bVar2 = 0;
  DAT_000a = 1;
  uStack0000 = 0xd9;
  FUN_d96f(DAT_0009 & 0xf);
  uStack0000 = 0xd9;
  FUN_d94e();
  (&DAT_031e)[bVar2] = 0x80;
  DAT_031c = ':';
  DAT_031d = '\'';
LAB_d93d:
  DAT_0303 = 1;
  DAT_030c = 1;
  DAT_007e = DAT_007e | 1;
  return;
}


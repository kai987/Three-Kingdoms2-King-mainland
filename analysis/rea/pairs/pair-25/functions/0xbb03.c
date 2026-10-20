
/* WARNING: Globals starting with '_' overlap smaller symbols at the same address */

void FUN_bb03(void)

{
  byte bVar1;
  char cVar2;
  undefined1 uStack0000;
  
  uStack0000 = 0xbb;
  region_address(DAT_0402);
  DAT_042d = 2;
  do {
    *(undefined1 *)(ushort)DAT_042d = *(undefined1 *)(_DAT_0000 + DAT_042d);
    DAT_042d = DAT_042d + 1;
  } while (DAT_042d < 5);
  DAT_0006 = DAT_0002 - DAT_0004;
  bVar1 = (DAT_0003 - DAT_0005) -
          (((DAT_0004 & (~DAT_0002 | DAT_0006) | DAT_0006 & ~DAT_0002) & 0x80) == 0);
  if (((DAT_0005 & (~DAT_0003 | bVar1) | bVar1 & ~DAT_0003) & 0x80) == 0) {
    DAT_042d = 7;
  }
  else if ((bVar1 != 0) || (DAT_0006 != 0)) {
    DAT_042d = 3;
  }
  cVar2 = -0x10;
  uStack0000 = 0xbb;
  bVar1 = FUN_e862(10);
  if (DAT_042d <= bVar1) {
    cVar2 = cVar2 + '\x01';
  }
  _DAT_0000 = (ushort)(byte)(100 - DAT_042f);
  DAT_0002 = 0;
  DAT_0003 = 4;
  uStack0000 = 0xbb;
  DAT_042d = cVar2;
  FUN_ebe9();
  DAT_042f = DAT_0006;
  DAT_0430 = DAT_0007;
  DAT_0431 = 0;
  return;
}


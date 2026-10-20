
/* WARNING: Globals starting with '_' overlap smaller symbols at the same address */

void FUN_b130(void)

{
  byte bVar1;
  undefined1 uStack0000;
  
  bVar1 = 0;
  do {
    (&DAT_6fa1)[bVar1] = 0xff;
    bVar1 = bVar1 + 1;
  } while (bVar1 < 0x40);
  bVar1 = 0;
  do {
    *(undefined1 *)(bVar1 + 0x6fc9) = 0;
    bVar1 = bVar1 + 1;
  } while (bVar1 < 0x14);
  DAT_0022 = DAT_0507 & 0xf;
  uStack0000 = 0xb1;
  FUN_b4c2();
  if (*(char *)(_DAT_0020 + 3) == '\x03') {
    DAT_6f91 = 0;
    DAT_6fa1 = 0;
    uStack0000 = 0xb1;
    FUN_b371();
    _DAT_0020 = _DAT_0020 & 0xff00;
    uStack0000 = 0xb1;
    FUN_b1b0();
  }
  DAT_0022 = DAT_0507 >> 4;
  uStack0000 = 0xb1;
  FUN_b4c2();
  if (*(char *)(_DAT_0020 + 3) == '\x03') {
    DAT_6f91 = 10;
    DAT_6fab = 0;
    uStack0000 = 0xb1;
    FUN_b371();
    _DAT_0020 = CONCAT11(DAT_0021,0x36);
    uStack0000 = 0xb1;
    FUN_b1b0();
  }
  bVar1 = 0;
  do {
    (&DAT_04d8)[bVar1] = 0xff;
    bVar1 = bVar1 + 1;
  } while (bVar1 < 8);
  DAT_6f94 = 0;
  DAT_6f95 = 0;
  DAT_6f96 = 0;
  return;
}


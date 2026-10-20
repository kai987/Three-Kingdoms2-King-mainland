
/* WARNING: Globals starting with '_' overlap smaller symbols at the same address */

void thunk_FUN_ba70(void)

{
  byte bVar1;
  undefined1 uStack0000;
  
  DAT_0471 = '\x7f';
  if ((DAT_0470 != '\0') && (DAT_0471 = -0x78, DAT_0470 != '\x01')) {
    DAT_0471 = -0x6f;
  }
  do {
    uStack0000 = 0xba;
    bVar1 = FUN_e856();
  } while (4 < bVar1);
  uStack0000 = 0xba;
  DAT_0010._0_1_ = bVar1;
  officer_address(DAT_0481);
  if (*(byte *)(_DAT_0000 + 2) < 0x51) {
    if (0x32 < *(byte *)(_DAT_0000 + 2)) {
      DAT_0010._0_1_ = (byte)DAT_0010 + 2;
    }
  }
  else {
    DAT_0010._0_1_ = (byte)DAT_0010 + 4;
  }
  DAT_0471 = (byte)DAT_0010 + DAT_0471;
  DAT_0472 = (&DAT_badf)[(byte)DAT_0010];
  DAT_04a2 = (&DAT_bae8)[(byte)(DAT_0470 * '\t' + (byte)DAT_0010)];
  return;
}


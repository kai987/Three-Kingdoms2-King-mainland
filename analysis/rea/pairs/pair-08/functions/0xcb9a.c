
void FUN_cb9a(void)

{
  byte bVar1;
  undefined1 uStack0000;
  
  bVar1 = 0;
  DAT_0010 = 0;
  DAT_0011 = 0;
  do {
    uStack0000 = 0xcb;
    FUN_cc92();
    if ((&DAT_6fa1)[bVar1] == '\x01') {
      DAT_0010 = DAT_0010 + 1;
    }
    else if ((&DAT_6fa1)[bVar1] == '\x03') {
      DAT_0011 = DAT_0011 + 1;
    }
    bVar1 = bVar1 + 1;
  } while (bVar1 < 0x14);
  if (DAT_0010 < DAT_6f99) {
    DAT_0000 = 2;
    uStack0000 = 0xcb;
    FUN_cbdf();
  }
  if (DAT_0011 < DAT_6f9b) {
    DAT_0000 = 4;
    uStack0000 = 0xcb;
    FUN_cbdf();
  }
  return;
}


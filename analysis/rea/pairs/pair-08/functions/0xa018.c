
/* WARNING: Globals starting with '_' overlap smaller symbols at the same address */

void thunk_FUN_d390(void)

{
  byte bVar1;
  undefined1 uStack0000;
  
  uStack0000 = 0xd3;
  officer_address(DAT_042c);
  bVar1 = *(byte *)(_DAT_0000 + 0xb) >> 4;
  if (bVar1 == 3) {
    bVar1 = 0;
  }
  else if (bVar1 == 4) {
    bVar1 = 0xb;
  }
  else if (bVar1 == 5) {
    bVar1 = 0x11;
  }
  else {
    if (bVar1 != 6) {
      DAT_042d = 0xff;
      return;
    }
    bVar1 = 0x14;
  }
  while( true ) {
    if ((&DAT_d3d8)[bVar1] == -1) {
      DAT_042d = 0xff;
      return;
    }
    if ((&DAT_d3d8)[bVar1] == DAT_042c) break;
    bVar1 = bVar1 + 1;
  }
  return;
}


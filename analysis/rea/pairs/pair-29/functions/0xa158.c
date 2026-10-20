
void FUN_a158(void)

{
  byte bVar1;
  undefined1 uStack0000;
  
  if ((DAT_0081 & 1) != 0) {
    DAT_0308 = 1;
  }
  if ((DAT_0300 != -1) && ((DAT_007e & 1) == 0)) {
    DAT_0304 = 0;
    uStack0000 = 0xa1;
    FUN_a690();
    if (DAT_0300 == '\0') {
      uStack0000 = 0xa1;
      FUN_a61d();
      bVar1 = 0;
      DAT_0306 = *DAT_00a6;
      uStack0000 = 0xa1;
      FUN_a1df();
      DAT_0307 = DAT_00a6[bVar1];
      uStack0000 = 0xa1;
      FUN_a1df();
      DAT_0300 = '\x01';
      DAT_0303 = 0;
      DAT_0308 = 0;
      DAT_030c = 0;
      DAT_030f = 0;
      DAT_0305 = 3;
    }
    uStack0000 = 0xa1;
    FUN_a60f();
    DAT_031c = DAT_0306;
    DAT_034c = DAT_0306 - 0x20;
    DAT_031d = DAT_0307;
    DAT_034d = DAT_0307 - ((DAT_034c & ~DAT_0306 & 0x80) == 0);
    while( true ) {
      uStack0000 = 0xa1;
      DAT_0012 = FUN_a1df(*DAT_00a6);
      if (((char)DAT_0012 < '\0') && (DAT_0012 < 0xc0)) break;
      uStack0000 = 0xa1;
      FUN_a1e8();
    }
    uStack0000 = 0xa2;
                    /* WARNING: Subroutine does not return */
    tail_dispatch_inline_table(DAT_0012 + 0x80);
  }
  return;
}



void FUN_be36(void)

{
  undefined1 uStack0000;
  
  if (DAT_04a0 == 0) {
    return;
  }
  if ((char)DAT_04a0 < '\0') {
    if ((DAT_04a0 & 0xf) != 0) {
      DAT_04a3 = DAT_04a3 + '\x01';
      DAT_04d0 = DAT_04d0 + '\x01';
      uStack0000 = 0xbe;
      FUN_f25f(0x36);
      uStack0000 = 0xbe;
                    /* WARNING: Subroutine does not return */
      tail_dispatch_inline_table(DAT_04a2);
    }
  }
  else {
    DAT_04a2 = DAT_04a0 - 1;
    DAT_04a1 = 0;
    DAT_0420 = 0x40;
    if (-1 < DAT_0150) {
      DAT_0420 = 0x80;
    }
    DAT_04a0 = 0x80;
  }
  uStack0000 = 0xc9;
                    /* WARNING: Subroutine does not return */
  tail_dispatch_inline_table(DAT_04a1);
}


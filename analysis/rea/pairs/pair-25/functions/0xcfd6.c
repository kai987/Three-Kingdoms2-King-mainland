
void FUN_cfd6(void)

{
  undefined1 uStack0000;
  
  if (((DAT_04c8 != 0) && (DAT_0300 == -1)) && (DAT_0304 == -1)) {
    if (-1 < (char)DAT_04c8) {
      DAT_04c9 = DAT_04c8 - 1;
      DAT_04ca = 0;
      DAT_04c8 = 0x80;
      DAT_04d1 = 7;
      uStack0000 = 0xd4;
                    /* WARNING: Subroutine does not return */
      tail_dispatch_inline_table(0);
    }
    uStack0000 = 0xd0;
                    /* WARNING: Subroutine does not return */
    tail_dispatch_inline_table(DAT_04c8 & 0xf);
  }
  return;
}


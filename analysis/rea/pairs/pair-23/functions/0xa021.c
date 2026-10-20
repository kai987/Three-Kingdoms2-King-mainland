
void thunk_FUN_de25(void)

{
  undefined1 uStack0000;
  
  if ((DAT_0081 & 8) != 0) {
    DAT_0541 = 4;
    DAT_0115 = 0xf;
    DAT_0116 = 0xf;
    DAT_0117 = 0xf;
    return;
  }
  uStack0000 = 0xde;
                    /* WARNING: Subroutine does not return */
  tail_dispatch_inline_table(DAT_0541);
}


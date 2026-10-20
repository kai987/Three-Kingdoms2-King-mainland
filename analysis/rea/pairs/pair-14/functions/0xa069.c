
/* WARNING: Control flow encountered bad instruction data */

void FUN_a069(void)

{
  undefined1 uStack0000;
  
  uStack0000 = 0xa0;
  DAT_00a0 = tail_dispatch_inline_table(DAT_0540);
                    /* WARNING: Bad instruction - Truncating control flow here */
  halt_baddata();
}


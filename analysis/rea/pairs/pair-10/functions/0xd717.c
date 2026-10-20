
/* WARNING: Control flow encountered bad instruction data */

void FUN_d717(void)

{
  undefined1 uStack0000;
  
  uStack0000 = 0xd7;
  FUN_dd34();
  uStack0000 = 0xd7;
  tail_dispatch_inline_table(DAT_0540);
                    /* WARNING: Bad instruction - Truncating control flow here */
  halt_baddata();
}


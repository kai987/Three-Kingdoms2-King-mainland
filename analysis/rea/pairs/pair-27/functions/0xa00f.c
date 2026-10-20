
/* WARNING: Control flow encountered bad instruction data */

void FUN_a00f(void)

{
  undefined1 uStack0000;
  
  uStack0000 = 0xa0;
  FUN_df35();
  uStack0000 = 0xa0;
  far_call_inline_word(0x39);
                    /* WARNING: Bad instruction - Truncating control flow here */
  halt_baddata();
}


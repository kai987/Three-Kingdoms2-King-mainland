
/* WARNING: Control flow encountered bad instruction data */

void FUN_a01e(void)

{
  undefined1 uStack0000;
  
  DAT_0081 = DAT_057b;
  uStack0000 = 0xa0;
  far_call_inline_word(0x3d);
                    /* WARNING: Bad instruction - Truncating control flow here */
  halt_baddata();
}



/* WARNING: Control flow encountered bad instruction data */

void FUN_a00f(void)

{
  undefined1 uStack0000;
  
  uStack0000 = 0xa0;
  FUN_c01b();
  DAT_057b = 0;
  uStack0000 = 0xa0;
  FUN_a030();
  uStack0000 = DAT_0081;
  DAT_0081 = DAT_057b;
  far_call_inline_word(0x3d);
                    /* WARNING: Bad instruction - Truncating control flow here */
  halt_baddata();
}


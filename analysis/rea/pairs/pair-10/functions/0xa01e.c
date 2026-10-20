
/* WARNING: Control flow encountered bad instruction data */

void FUN_a01e(void)

{
  undefined1 uStack0000;
  
  uStack0000 = 0xa0;
  FUN_d4cb();
  uStack0000 = 0xa0;
  FUN_c50e();
  uStack0000 = 0xa0;
  FUN_c5b9();
  uStack0000 = 0xa0;
  FUN_c79a();
  uStack0000 = 0xa0;
  FUN_c98f(DAT_6f03);
  uStack0000 = 0xa0;
  FUN_d249();
  uStack0000 = 0xa0;
  FUN_cc12();
  uStack0000 = 0xa0;
  FUN_d494(DAT_6f5b);
                    /* WARNING: Bad instruction - Truncating control flow here */
  halt_baddata();
}


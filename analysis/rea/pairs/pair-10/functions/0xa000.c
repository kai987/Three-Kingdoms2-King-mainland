
/* WARNING: Control flow encountered bad instruction data */

void bank10_entry_00(void)

{
  undefined1 uStack0000;
  
  if (DAT_6f8b < '\0') {
    return;
  }
  if (DAT_6f8b == '\x01') {
    uStack0000 = 0xa0;
    FUN_d4cb();
    if (DAT_6f8c == '\0') {
      uStack0000 = 0xa8;
      FUN_cd68();
    }
    uStack0000 = 0xa8;
    DAT_003e = FUN_d105(DAT_0038);
    uStack0000 = 0xa8;
    FUN_a91f();
    uStack0000 = 0xa8;
    FUN_a9cc();
    uStack0000 = 0xa8;
    FUN_af9c();
    if (DAT_6f8c == '\0') {
      uStack0000 = 0xa8;
      FUN_aa80();
      uStack0000 = 0xa8;
      FUN_ac67();
      uStack0000 = 0xa9;
      FUN_d105(DAT_0038);
      *DAT_0020 = *DAT_0020 & 0xf8 | DAT_6f03;
      uStack0000 = 0xa9;
      FUN_d249();
      FUN_ca19();
      return;
    }
    uStack0000 = 0xa9;
    FUN_ab10();
    uStack0000 = 0xa9;
    FUN_ac67();
    uStack0000 = 0xa9;
    FUN_d249();
    FUN_ca19();
    return;
  }
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


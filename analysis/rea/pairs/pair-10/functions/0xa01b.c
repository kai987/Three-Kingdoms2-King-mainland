
void thunk_FUN_a8d7(void)

{
  undefined1 uStack0000;
  
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



/* WARNING: Control flow encountered bad instruction data */

byte FUN_ee53(void)

{
  byte bVar1;
  bool bVar2;
  byte bStack0000;
  
  if (DAT_007d == '\0') {
    if ((char)DAT_007e < '\0') {
      bStack0000 = DAT_007e;
      DAT_007e = DAT_007e & 0x7f;
      FUN_ef0b();
      return bStack0000;
    }
    bStack0000 = DAT_007e << 1;
    if ((char)bStack0000 < '\0') {
      DAT_007e = DAT_007e & 0xbf;
      FUN_ef71();
      return bStack0000;
    }
    if ((char)(DAT_007e << 2) < '\0') {
      DAT_007e = DAT_007e & 0xdf;
      bVar1 = FUN_efc0();
      return bVar1;
    }
    if ((char)(DAT_007e << 3) < '\0') {
      DAT_007e = DAT_007e & 0xef;
      bVar1 = FUN_f028();
      return bVar1;
    }
    if ((char)(DAT_007e << 4) < '\0') {
      bStack0000 = 0xee;
      FUN_f237(0x3d);
      DAT_007e = DAT_007e & 0xf7;
      bVar1 = thunk_FUN_d00c();
      return bVar1;
    }
    if ((char)(DAT_007e << 5) < '\0') {
      DAT_007e = DAT_007e & 0xfb;
      bStack0000 = 0xee;
      FUN_f237(0x3d);
      bVar1 = thunk_FUN_cf3f();
      return bVar1;
    }
    if ((char)(DAT_007e << 6) < '\0') {
      DAT_007e = DAT_007e & 0xfd;
      bVar2 = false;
      bStack0000 = 0xee;
      bVar1 = FUN_f237();
      if (bVar2) {
        return bVar1;
      }
      if (bVar1 == 1) {
        bStack0000 = 0xa0;
        FUN_d4cb();
        if (DAT_6f8c == '\0') {
          bStack0000 = 0xa8;
          FUN_cd68();
        }
        bStack0000 = 0xa8;
        DAT_003e = FUN_d105(DAT_0038);
        bStack0000 = 0xa8;
        FUN_a91f();
        bStack0000 = 0xa8;
        FUN_a9cc();
        bStack0000 = 0xa8;
        FUN_af9c();
        if (DAT_6f8c == '\0') {
          bStack0000 = 0xa8;
          FUN_aa80();
          bStack0000 = 0xa8;
          FUN_ac67();
          bStack0000 = 0xa9;
          FUN_d105(DAT_0038);
          *DAT_0020 = *DAT_0020 & 0xf8 | DAT_6f03;
          bStack0000 = 0xa9;
          FUN_d249();
          bVar1 = FUN_ca19();
          return bVar1;
        }
        bStack0000 = 0xa9;
        FUN_ab10();
        bStack0000 = 0xa9;
        FUN_ac67();
        bStack0000 = 0xa9;
        FUN_d249();
        bVar1 = FUN_ca19();
        return bVar1;
      }
      bStack0000 = 0xa0;
      FUN_d4cb();
      bStack0000 = 0xa0;
      FUN_c50e();
      bStack0000 = 0xa0;
      FUN_c5b9();
      bStack0000 = 0xa0;
      FUN_c79a();
      bStack0000 = 0xa0;
      FUN_c98f(DAT_6f03);
      bStack0000 = 0xa0;
      FUN_d249();
      bStack0000 = 0xa0;
      FUN_cc12();
      bStack0000 = 0xa0;
      FUN_d494(DAT_6f5b);
                    /* WARNING: Bad instruction - Truncating control flow here */
      halt_baddata();
    }
    if ((char)(DAT_007e << 7) < '\0') {
      bStack0000 = 0xee;
      FUN_f237(DAT_007e << 7,0x3d);
      bVar1 = bank10_entry_00();
      return bVar1;
    }
  }
  bVar1 = FUN_e70e();
  return bVar1;
}


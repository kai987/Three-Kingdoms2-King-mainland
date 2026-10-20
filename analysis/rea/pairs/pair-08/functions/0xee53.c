
byte FUN_ee53(void)

{
  byte bVar1;
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
      bVar1 = thunk_FUN_c983();
      return bVar1;
    }
    if ((char)(DAT_007e << 5) < '\0') {
      DAT_007e = DAT_007e & 0xfb;
      bStack0000 = 0xee;
      FUN_f237(0x3d);
      bVar1 = thunk_FUN_bab3();
      return bVar1;
    }
    if ((char)(DAT_007e << 6) < '\0') {
      DAT_007e = DAT_007e & 0xfd;
      bStack0000 = 0xee;
      FUN_f237(0x3d);
      bVar1 = thunk_FUN_cfa2();
      return bVar1;
    }
    if ((char)(DAT_007e << 7) < '\0') {
      bStack0000 = 0xee;
      FUN_f237(DAT_007e << 7,0x3d);
      bVar1 = bank8_entry_00();
      return bVar1;
    }
  }
  bVar1 = FUN_e70e();
  return bVar1;
}


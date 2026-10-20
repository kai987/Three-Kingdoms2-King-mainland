// Ghidra-generated fixed-bank-pair pseudocode. Bank switching and inline pointer dispatch need manual correction. Not original source.

/* 0xa000 bank10_entry_00 */

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



/* 0xa003 thunk_FUN_d717 */

/* WARNING: Control flow encountered bad instruction data */

void thunk_FUN_d717(void)

{
  undefined1 uStack0000;
  
  uStack0000 = 0xd7;
  FUN_dd34();
  uStack0000 = 0xd7;
  tail_dispatch_inline_table(DAT_0540);
                    /* WARNING: Bad instruction - Truncating control flow here */
  halt_baddata();
}



/* 0xa006 thunk_FUN_cf3f */

void thunk_FUN_cf3f(void)

{
  byte bVar1;
  char cStack0000;
  
  cStack0000 = 0xcf;
  DAT_0020._1_1_ = FUN_d2ab(DAT_0030,4);
  DAT_0022 = 0xa00;
  DAT_0024 = 0;
  cStack0000 = 0xcf;
  FUN_d40f();
  cStack0000 = DAT_0020._1_1_ + 'F';
  DAT_0020._0_1_ = FUN_d2ab(DAT_0031,3);
  bVar1 = cStack0000 - (char)DAT_0020;
  if (0x59 < bVar1) {
    bVar1 = 0x5a;
  }
  if (bVar1 < 10) {
    bVar1 = 10;
  }
  *(byte *)(DAT_0022 + 3) = bVar1;
  cStack0000 = 0xcf;
  FUN_d61e();
  return;
}



/* 0xa009 thunk_FUN_cf7c */

/* WARNING: Globals starting with '_' overlap smaller symbols at the same address */

void thunk_FUN_cf7c(void)

{
  char cVar1;
  byte bVar2;
  byte bVar3;
  byte bStack0000;
  
  _DAT_0024 = CONCAT11((&DAT_cad9)[(byte)(DAT_0032 << 1)],(&DAT_cad8)[(byte)(DAT_0032 << 1)]);
  bVar3 = 0xff;
  do {
    bVar3 = bVar3 + 1;
    if (*(char *)(_DAT_0024 + bVar3) == -1) {
      bStack0000 = 0xcf;
      DAT_0020._1_1_ = FUN_d2ab(DAT_0030,4);
      DAT_0022 = &DAT_0500;
      _DAT_0024 = _DAT_0024 & 0xff00;
      bStack0000 = 0xcf;
      FUN_d40f();
      bStack0000 = DAT_0020._1_1_;
      DAT_0020._1_1_ = FUN_d2ab(DAT_0033,4);
      DAT_0022 = &DAT_0500;
      _DAT_0024 = _DAT_0024 & 0xff00;
      FUN_d40f();
      DAT_0020._0_1_ = bStack0000 - DAT_0020._1_1_;
      if (((DAT_0020._1_1_ & (~bStack0000 | (byte)DAT_0020) | (byte)DAT_0020 & ~bStack0000) & 0x80)
          == 0) {
        DAT_0020._0_1_ = ((byte)DAT_0020 ^ 0xff) + 1;
        bStack0000 = 0xcf;
        bVar2 = FUN_d2ab(DAT_0031,3);
        bVar3 = bVar2 - (byte)DAT_0020;
        if ((((byte)DAT_0020 & (~bVar2 | bVar3) | bVar3 & ~bVar2) & 0x80) == 0) {
          bVar3 = 0;
        }
      }
      else {
        bStack0000 = 0xcf;
        cVar1 = FUN_d2ab(DAT_0031,3);
        bVar3 = cVar1 + (byte)DAT_0020;
      }
      bVar2 = bVar3 - 10;
      if ((bVar2 & ~bVar3 & 0x80) == 0) {
        bVar2 = 0;
      }
      if (0x62 < bVar2) {
        bVar2 = 99;
      }
      if (bVar2 < 10) {
        bVar2 = 10;
      }
      DAT_0022[3] = bVar2;
      bStack0000 = 0xd0;
      FUN_d61e();
      return;
    }
  } while (*(char *)(_DAT_0024 + bVar3) != DAT_0030);
  return;
}



/* 0xa00c thunk_FUN_d00c */

void thunk_FUN_d00c(void)

{
  byte bVar1;
  undefined1 uStack0000;
  
  uStack0000 = 0xd0;
  bVar1 = FUN_d2ab((byte)DAT_0020,3);
  DAT_0020._0_1_ = 0x32 - bVar1;
  if (((bVar1 & ((byte)DAT_0020 | 0xcd) | (byte)DAT_0020 & 0xcd) & 0x80) == 0) {
    DAT_0020._0_1_ = ((byte)DAT_0020 ^ 0xff) + 1;
  }
  bVar1 = 0x33 - (byte)DAT_0020;
  if ((((byte)DAT_0020 & (bVar1 | 0xcc) | bVar1 & 0xcc) & 0x80) == 0) {
    bVar1 = 0;
  }
  if (bVar1 < 10) {
    bVar1 = 10;
  }
  *(byte *)(DAT_0022 + 3) = bVar1;
  uStack0000 = 0xd0;
  FUN_d61e();
  return;
}



/* 0xa00f FUN_a00f */

/* WARNING: Control flow encountered bad instruction data */

void FUN_a00f(void)

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



/* 0xa01b thunk_FUN_a8d7 */

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



/* 0xa01e FUN_a01e */

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



/* 0xa024 FUN_a024 */

/* WARNING: Control flow encountered bad instruction data */

void FUN_a024(void)

{
  undefined1 uStack0000;
  
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



/* 0xa03f FUN_a03f */

void FUN_a03f(void)

{
  byte bVar1;
  undefined1 uStack0000;
  
  DAT_0039 = 0;
  DAT_003a = 0;
  DAT_003b = 0;
  DAT_003c = 0;
  DAT_003d = 0;
  bVar1 = DAT_6f02 << 3 | DAT_6f03;
  DAT_6f5f = (&DAT_a133)[bVar1];
  DAT_6f60 = (&DAT_a14b)[bVar1];
  DAT_6f61 = (&DAT_a163)[bVar1];
  uStack0000 = 0xa0;
  FUN_a0d3();
  DAT_0020._0_1_ = DAT_0038;
  DAT_0020._1_1_ = 0;
  DAT_0022._0_1_ = 0;
  DAT_0022._1_1_ = 100;
  uStack0000 = 0xa0;
  FUN_d438();
  DAT_0020._1_1_ = DAT_0026;
  DAT_0022._0_1_ = DAT_0027;
  DAT_0022._1_1_ = DAT_0037;
  DAT_0024 = 0;
  uStack0000 = 0xa0;
  FUN_d40f();
  DAT_0020._0_1_ = 0;
  if ((0x1e < DAT_0020._1_1_) && (DAT_0020._0_1_ = 1, 0x46 < DAT_0020._1_1_)) {
    DAT_0020._0_1_ = 2;
  }
  bVar1 = DAT_6f02 << 2 | (byte)DAT_0020;
  DAT_6f5f = (&DAT_a17b)[bVar1] + DAT_6f5f;
  DAT_6f60 = (&DAT_a186)[bVar1] + DAT_6f60;
  DAT_6f61 = (&DAT_a191)[bVar1] + DAT_6f61;
  DAT_6f5b = DAT_6f5b + '\x01';
  return;
}



/* 0xa045 FUN_a045 */

void FUN_a045(undefined1 param_1)

{
  byte bVar1;
  undefined1 uStack0000;
  
  bVar1 = DAT_6f02 << 3 | DAT_6f03;
  DAT_6f5f = (&DAT_a133)[bVar1];
  DAT_6f60 = (&DAT_a14b)[bVar1];
  DAT_6f61 = (&DAT_a163)[bVar1];
  uStack0000 = 0xa0;
  DAT_0039 = param_1;
  DAT_003a = param_1;
  DAT_003b = param_1;
  DAT_003c = param_1;
  DAT_003d = param_1;
  FUN_a0d3();
  DAT_0020._0_1_ = DAT_0038;
  DAT_0020._1_1_ = 0;
  DAT_0022._0_1_ = 0;
  DAT_0022._1_1_ = 100;
  uStack0000 = 0xa0;
  FUN_d438();
  DAT_0020._1_1_ = DAT_0026;
  DAT_0022._0_1_ = DAT_0027;
  DAT_0022._1_1_ = DAT_0037;
  DAT_0024 = 0;
  uStack0000 = 0xa0;
  FUN_d40f();
  DAT_0020._0_1_ = 0;
  if ((0x1e < DAT_0020._1_1_) && (DAT_0020._0_1_ = 1, 0x46 < DAT_0020._1_1_)) {
    DAT_0020._0_1_ = 2;
  }
  bVar1 = DAT_6f02 << 2 | (byte)DAT_0020;
  DAT_6f5f = (&DAT_a17b)[bVar1] + DAT_6f5f;
  DAT_6f60 = (&DAT_a186)[bVar1] + DAT_6f60;
  DAT_6f61 = (&DAT_a191)[bVar1] + DAT_6f61;
  DAT_6f5b = DAT_6f5b + '\x01';
  return;
}



/* 0xa0d3 FUN_a0d3 */

void FUN_a0d3(void)

{
  byte bVar1;
  undefined1 uStack0000;
  
  uStack0000 = 0xa0;
  FUN_f266(0x30);
  DAT_0036 = 0;
  DAT_0037 = '\0';
  DAT_0038 = '\0';
  do {
    DAT_0039 = 0;
    bVar1 = DAT_0036 << 3;
    do {
      if (*(char *)(bVar1 + 0x9d72) < '\0') break;
      uStack0000 = 0xa0;
      DAT_0022._1_1_ = *(char *)(bVar1 + 0x9d72);
      DAT_0024 = bVar1;
      bVar1 = FUN_d105();
      if (((bVar1 & 7) == 7) || ((bVar1 & 7) == DAT_6f03)) {
        DAT_0037 = DAT_0037 + '\x01';
        uStack0000 = 0xa1;
        bVar1 = FUN_d304(DAT_0036);
        if (bVar1 < 4) {
          DAT_0038 = DAT_0038 + '\x01';
          break;
        }
      }
      bVar1 = DAT_0024 + 1;
      DAT_0039 = DAT_0039 + 1;
    } while (DAT_0039 < 8);
    DAT_0036 = DAT_0036 + 1;
    if (0x1d < DAT_0036) {
      return;
    }
  } while( true );
}



/* 0xa8d7 FUN_a8d7 */

void FUN_a8d7(void)

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



/* 0xa91f FUN_a91f */

void FUN_a91f(void)

{
  byte bVar1;
  byte bVar2;
  char cVar3;
  byte bVar4;
  char cStack0000;
  
  DAT_6f73 = 0;
  DAT_6f74 = 0;
  DAT_6f75 = 0;
  DAT_6f76 = 0;
  DAT_6f77 = 0;
  DAT_6f78 = 0;
  DAT_0040 = 0;
  do {
    cStack0000 = *(char *)(DAT_0040 + 0x664);
    if (cStack0000 != -1) {
      bVar4 = FUN_d2ab(0);
      DAT_0020._0_1_ = *(byte *)(DAT_0022 + 8);
      DAT_0020._1_1_ = *(byte *)(DAT_0022 + 9) & 3;
      DAT_0022 = (ushort)bVar4 << 8;
      DAT_0030 = (byte)DAT_0020;
      DAT_0031 = DAT_0020._1_1_;
      FUN_d438();
      DAT_0020._0_1_ = DAT_0026;
      DAT_0020._1_1_ = DAT_0027;
      DAT_0022 = CONCAT11(100,DAT_0028);
      DAT_0024 = 0;
      FUN_d336();
      cVar3 = cStack0000;
      cStack0000 = 0xa9;
      FUN_d2ab(cVar3,0);
      *(byte *)(DAT_0022 + 8) = (byte)DAT_0020;
      *(byte *)(DAT_0022 + 9) = *(byte *)(DAT_0022 + 9) & 0xfc | DAT_0020._1_1_;
      bVar1 = DAT_0030 - (byte)DAT_0020;
      bVar2 = (DAT_0031 - DAT_0020._1_1_) -
              ((((byte)DAT_0020 & (~DAT_0030 | bVar1) | bVar1 & ~DAT_0030) & 0x80) == 0);
      bVar4 = ~DAT_0031;
      DAT_0030 = bVar1;
      DAT_0031 = bVar2;
      if (((DAT_0020._1_1_ & (bVar4 | bVar2) | bVar2 & bVar4) & 0x80) != 0) {
        bVar4 = 0;
        if (9 < DAT_0040) {
          bVar4 = 2;
        }
        bVar2 = (&DAT_6f73)[bVar4];
        (&DAT_6f73)[bVar4] = bVar1 + bVar2;
        (&DAT_6f74)[bVar4] = DAT_0031 + (&DAT_6f74)[bVar4] + CARRY1(bVar1,bVar2);
      }
    }
    DAT_0040 = DAT_0040 + 1;
  } while (DAT_0040 < 0x14);
  return;
}



/* 0xa9cc FUN_a9cc */

void FUN_a9cc(void)

{
  byte bVar1;
  byte bVar2;
  byte bStack0000;
  
  bVar2 = 0;
  DAT_003c = 0;
  do {
    if (*(char *)(bVar2 + 0x664) != -1) {
      DAT_003c = DAT_003c + 1;
    }
    bVar2 = bVar2 + 1;
  } while (bVar2 < 10);
  bVar2 = 0;
  DAT_003d = 0;
  do {
    if (*(char *)(bVar2 + 0x66e) != -1) {
      DAT_003d = DAT_003d + 1;
    }
    bVar2 = bVar2 + 1;
  } while (bVar2 < 10);
  bVar2 = DAT_6f77;
  if (4 < DAT_003c) {
    bStack0000 = DAT_003c >> 2;
    bVar1 = bStack0000;
    for (; DAT_6f77 = bVar1, bStack0000 != 0; bStack0000 = bStack0000 - 1) {
      FUN_aa2d(0);
      bVar1 = DAT_6f77;
      bVar2 = DAT_6f77;
    }
  }
  DAT_6f77 = bVar2;
  bVar2 = DAT_6f78;
  if (4 < DAT_003d) {
    bStack0000 = DAT_003d >> 2;
    bVar1 = bStack0000;
    for (; DAT_6f78 = bVar1, bStack0000 != 0; bStack0000 = bStack0000 - 1) {
      FUN_aa2d(10);
      bVar1 = DAT_6f78;
      bVar2 = DAT_6f78;
    }
  }
  DAT_6f78 = bVar2;
  return;
}



/* 0xaa2d FUN_aa2d */

void FUN_aa2d(byte param_1)

{
  undefined1 uVar1;
  char cVar2;
  byte bVar3;
  byte bVar4;
  undefined1 uStack0000;
  
  DAT_0025 = 0xff;
  DAT_0026 = 0xff;
  DAT_0027 = 0;
  DAT_0024 = param_1;
  do {
    if (*(char *)(DAT_0024 + 0x664) != -1) {
      uStack0000 = 0xaa;
      cVar2 = FUN_d2ab(3);
      if ((cVar2 != 'd') &&
         (bVar3 = *(char *)(DAT_0022 + 1) + *(char *)(DAT_0022 + 2), bVar3 < DAT_0025)) {
        DAT_0026 = DAT_0024;
        DAT_0025 = bVar3;
      }
    }
    DAT_0024 = DAT_0024 + 1;
    DAT_0027 = DAT_0027 + 1;
  } while (DAT_0027 < 10);
  uVar1 = *(undefined1 *)(DAT_0026 + 0x664);
  *(undefined1 *)(DAT_0026 + 0x664) = 0xff;
  bVar4 = 0xb;
  uStack0000 = 0xaa;
  bVar3 = FUN_d2ab(uVar1);
  *(byte *)(DAT_0022 + (ushort)bVar4) = bVar3 & 0xfc | 3;
  return;
}



/* 0xaa80 FUN_aa80 */

void FUN_aa80(void)

{
  byte bVar1;
  byte bVar2;
  undefined1 uStack0000;
  
  uStack0000 = 0xaa;
  FUN_d105(DAT_0038);
  bVar1 = 0;
  bVar2 = 0x11;
  do {
    if (*(char *)(bVar1 + 0x66e) != -1) {
      *(char *)(DAT_0020 + (ushort)bVar2) = *(char *)(bVar1 + 0x66e);
      bVar2 = bVar2 + 1;
    }
    bVar1 = bVar1 + 1;
  } while (bVar1 < 10);
  DAT_0024 = 0;
  do {
    if (*(char *)(DAT_0024 + 0x664) != -1) {
      uStack0000 = 0xaa;
      DAT_0026 = *(char *)(DAT_0024 + 0x664);
      bVar1 = FUN_d2ab(3);
      if (bVar1 != 100) {
        uStack0000 = 0xaa;
        DAT_0025 = bVar1;
        bVar1 = FUN_d4bb(100);
        if (DAT_0025 <= bVar1) {
          uStack0000 = 0xaa;
          FUN_aade();
          goto LAB_aad5;
        }
      }
      DAT_0040 = DAT_003e;
      DAT_0041 = DAT_0026;
      DAT_0042 = 1;
      uStack0000 = 0xaa;
      FUN_aba3();
    }
LAB_aad5:
    DAT_0024 = DAT_0024 + 1;
    if (9 < DAT_0024) {
      return;
    }
  } while( true );
}



/* 0xaade FUN_aade */

void FUN_aade(void)

{
  byte bVar1;
  undefined1 uStack0000;
  
  uStack0000 = 0xaa;
  FUN_d105(DAT_0038);
  bVar1 = 0x11;
  do {
    if (*(char *)(DAT_0020 + (ushort)bVar1) == -1) {
      *(undefined1 *)(DAT_0020 + (ushort)bVar1) = DAT_0026;
      DAT_0020 = CONCAT11(DAT_0020._1_1_,DAT_0026);
      uStack0000 = 0xab;
      FUN_d00c();
      return;
    }
    bVar1 = bVar1 + 1;
  } while (bVar1 < 0x1b);
  DAT_0040 = DAT_6f03;
  DAT_0041 = DAT_0026;
  DAT_0042 = 0;
  FUN_aba3();
  return;
}



/* 0xab10 FUN_ab10 */

void FUN_ab10(void)

{
  char cVar1;
  byte bVar2;
  byte bVar3;
  undefined1 uStack0000;
  
  uStack0000 = 0xab;
  FUN_d105(DAT_0038);
  bVar2 = 0;
  bVar3 = 0x11;
  do {
    if (*(char *)(bVar2 + 0x664) != -1) {
      *(char *)(DAT_0020 + (ushort)bVar3) = *(char *)(bVar2 + 0x664);
      bVar3 = bVar3 + 1;
    }
    bVar2 = bVar2 + 1;
  } while (bVar2 < 10);
  DAT_0024 = 0;
  do {
    cVar1 = *(char *)(DAT_0024 + 0x66e);
    if (cVar1 != -1) {
      DAT_0026 = cVar1;
      *(undefined1 *)(DAT_0024 + 0x66e) = 0xff;
      uStack0000 = 0xab;
      DAT_0025 = FUN_d2ab(cVar1,3);
      uStack0000 = 0xab;
      bVar2 = FUN_d4bb(100);
      if (bVar2 < DAT_0025) {
        DAT_0040 = DAT_6f03;
        DAT_0041 = DAT_0026;
        DAT_0042 = 1;
        uStack0000 = 0xab;
        FUN_aba3();
      }
      else {
        uStack0000 = 0xab;
        FUN_ab71();
      }
    }
    DAT_0024 = DAT_0024 + 1;
  } while (DAT_0024 < 10);
  return;
}



/* 0xab71 FUN_ab71 */

void FUN_ab71(void)

{
  byte bVar1;
  undefined1 uStack0000;
  
  uStack0000 = 0xab;
  FUN_d105(DAT_0038);
  bVar1 = 0x11;
  do {
    if (*(char *)(DAT_0020 + (ushort)bVar1) == -1) {
      *(undefined1 *)(DAT_0020 + (ushort)bVar1) = DAT_0026;
      DAT_0020 = CONCAT11(DAT_0020._1_1_,DAT_0026);
      uStack0000 = 0xab;
      FUN_d00c();
      return;
    }
    bVar1 = bVar1 + 1;
  } while (bVar1 < 0x1b);
  DAT_0040 = DAT_003e;
  DAT_0041 = DAT_0026;
  DAT_0042 = 0;
  FUN_aba3();
  return;
}



/* 0xaba3 FUN_aba3 */

void FUN_aba3(void)

{
  char cVar1;
  byte bVar2;
  byte bVar3;
  undefined1 uStack0000;
  
  uStack0000 = 0xab;
  FUN_f266(0x30);
  DAT_002b = 0xff;
  DAT_002c = -1;
  DAT_002d = -1;
  for (DAT_002a = DAT_0038 << 3; -1 < *(char *)(DAT_002a + 0x9d72); DAT_002a = DAT_002a + 1) {
    uStack0000 = 0xab;
    bVar2 = FUN_d105();
    if (bVar2 == 7) {
      DAT_002d = *(char *)(DAT_002a + 0x9d72);
    }
    else if (bVar2 == DAT_0040) {
      uStack0000 = 0xab;
      bVar2 = FUN_d307();
      if ((bVar2 < 10) && (bVar2 < DAT_002b)) {
        DAT_002c = *(char *)(DAT_002a + 0x9d72);
        DAT_002b = bVar2;
      }
    }
  }
  if ((DAT_002c == -1) && (DAT_002d == -1)) {
    bVar3 = 0xb;
    uStack0000 = 0xac;
    bVar2 = FUN_d2ab(DAT_0041);
    *(byte *)(DAT_0022 + (ushort)bVar3) = bVar2 & 0xfc;
    do {
      uStack0000 = 0xac;
      bVar2 = FUN_e89a();
      if ((bVar2 & 7) == 0) {
        *(char *)(DAT_0022 + 5) = DAT_0038;
        DAT_002d = 0xff;
        return;
      }
      DAT_002d = (bVar2 & 7) - 1;
      cVar1 = *(char *)((byte)(DAT_0038 * '\b' + DAT_002d) + 0x9d72);
    } while (cVar1 < '\0');
    *(char *)(DAT_0022 + 5) = cVar1;
    DAT_002d = 0xff;
    return;
  }
  uStack0000 = 0xab;
  FUN_d105();
  for (bVar2 = 0x11; DAT_0020[bVar2] != 0xff; bVar2 = bVar2 + 1) {
  }
  DAT_0020[bVar2] = DAT_0041;
  *DAT_0020 = *DAT_0020 & 0xf8 | DAT_0040;
  if (DAT_0042 == '\0') {
    DAT_0020 = (byte *)CONCAT11(DAT_0020._1_1_,DAT_0041);
    uStack0000 = 0xac;
    FUN_d00c();
  }
  return;
}



/* 0xac67 FUN_ac67 */

void FUN_ac67(void)

{
  byte bVar1;
  byte bVar2;
  byte bVar3;
  bool bVar4;
  undefined1 uStack0000;
  
  uStack0000 = 0xac;
  FUN_aebf();
  bVar2 = DAT_0522 - DAT_002a;
  bVar3 = (DAT_0523 - DAT_002b) -
          (((DAT_002a & (~DAT_0522 | bVar2) | bVar2 & ~DAT_0522) & 0x80) == 0);
  bVar1 = ~DAT_0523;
  DAT_0522 = bVar2;
  DAT_0523 = bVar3;
  if (((DAT_002b & (bVar1 | bVar3) | bVar3 & bVar1) & 0x80) == 0) {
    DAT_0522 = 0;
    DAT_0523 = 0;
  }
  bVar2 = DAT_0524 - DAT_002c;
  bVar3 = (DAT_0525 - DAT_002d) -
          (((DAT_002c & (~DAT_0524 | bVar2) | bVar2 & ~DAT_0524) & 0x80) == 0);
  bVar1 = ~DAT_0525;
  DAT_0524 = bVar2;
  DAT_0525 = bVar3;
  if (((DAT_002d & (bVar1 | bVar3) | bVar3 & bVar1) & 0x80) == 0) {
    DAT_0524 = 0;
    DAT_0525 = 0;
  }
  uStack0000 = 0xac;
  FUN_ce67();
  uStack0000 = 0xac;
  FUN_cedd();
  uStack0000 = 0xac;
  FUN_d105(DAT_0038);
  bVar4 = CARRY1(DAT_0522,DAT_0524);
  *(byte *)(DAT_0020 + 4) = DAT_0522 + DAT_0524;
  *(byte *)(DAT_0020 + 5) = DAT_0523 + DAT_0525 + bVar4;
  bVar4 = CARRY1(DAT_0526,DAT_0528);
  *(byte *)(DAT_0020 + 2) = DAT_0526 + DAT_0528;
  *(char *)(DAT_0020 + 3) = DAT_0527 + DAT_0529 + bVar4;
  return;
}



/* 0xaebf FUN_aebf */

void FUN_aebf(void)

{
  byte bVar1;
  char cVar2;
  bool bVar3;
  undefined1 uStack0000;
  
  DAT_0024 = 0;
  DAT_0025 = 0;
  DAT_0026 = '\0';
  do {
    if (*(char *)(DAT_0024 + 0x664) != -1) {
      cVar2 = '\b';
      uStack0000 = 0xae;
      bVar1 = FUN_d2ab();
      bVar3 = CARRY1(bVar1,DAT_0025);
      DAT_0025 = bVar1 + DAT_0025;
      DAT_0026 = *(char *)(DAT_0022 + (ushort)(byte)(cVar2 + 1)) + DAT_0026 + bVar3;
    }
    DAT_0024 = DAT_0024 + 1;
  } while (DAT_0024 < 10);
  DAT_0020._1_1_ = DAT_0025;
  DAT_0022 = CONCAT11(100,DAT_0026);
  DAT_0024 = 0;
  uStack0000 = 0xae;
  FUN_d40f();
  DAT_0020._0_1_ = DAT_0020._1_1_;
  DAT_0020._1_1_ = (undefined1)DAT_0022;
  DAT_0022 = (ushort)(byte)(DAT_6f8d << 2) << 8;
  uStack0000 = 0xaf;
  FUN_d438();
  DAT_0020._1_1_ = DAT_0026;
  DAT_0022 = CONCAT11(10,DAT_0027);
  DAT_0024 = 0;
  uStack0000 = 0xaf;
  FUN_d40f();
  DAT_002a = DAT_0020._1_1_;
  DAT_002b = (undefined1)DAT_0022;
  DAT_0024 = 0;
  DAT_0025 = 0;
  DAT_0026 = '\0';
  do {
    if (*(char *)(DAT_0024 + 0x66e) != -1) {
      cVar2 = '\b';
      uStack0000 = 0xaf;
      bVar1 = FUN_d2ab();
      bVar3 = CARRY1(bVar1,DAT_0025);
      DAT_0025 = bVar1 + DAT_0025;
      DAT_0026 = *(char *)(DAT_0022 + (ushort)(byte)(cVar2 + 1)) + DAT_0026 + bVar3;
    }
    DAT_0024 = DAT_0024 + 1;
  } while (DAT_0024 < 10);
  DAT_0020._1_1_ = DAT_0025;
  DAT_0022 = CONCAT11(100,DAT_0026);
  DAT_0024 = 0;
  uStack0000 = 0xaf;
  FUN_d40f();
  DAT_0020._0_1_ = DAT_0020._1_1_;
  DAT_0020._1_1_ = (undefined1)DAT_0022;
  DAT_0022 = (ushort)(byte)(DAT_6f8d << 2) << 8;
  uStack0000 = 0xaf;
  FUN_d438();
  DAT_0020._1_1_ = DAT_0026;
  DAT_0022 = CONCAT11(10,DAT_0027);
  DAT_0024 = 0;
  uStack0000 = 0xaf;
  FUN_d40f();
  DAT_002c = DAT_0020._1_1_;
  DAT_002d = (undefined1)DAT_0022;
  return;
}



/* 0xaf9c FUN_af9c */

void FUN_af9c(void)

{
  bool bVar1;
  undefined1 uStack0000;
  
  DAT_0020._0_1_ = DAT_6f77;
  DAT_0020._1_1_ = 0x78;
  uStack0000 = 0xaf;
  FUN_d471();
  bVar1 = CARRY1(DAT_002a,DAT_6f73);
  DAT_6f73 = DAT_002a + DAT_6f73;
  DAT_6f74 = DAT_002b + DAT_6f74 + bVar1;
  DAT_0020._0_1_ = DAT_6f78;
  DAT_0020._1_1_ = 0x78;
  uStack0000 = 0xaf;
  FUN_d471();
  DAT_0020._1_1_ = DAT_002a + DAT_6f75;
  DAT_0022._0_1_ = DAT_002b + DAT_6f76 + CARRY1(DAT_002a,DAT_6f75);
  DAT_0022._1_1_ = DAT_003c;
  DAT_0024 = 0;
  uStack0000 = 0xaf;
  DAT_6f75 = DAT_0020._1_1_;
  DAT_6f76 = (char)DAT_0022;
  FUN_d40f();
  DAT_6f75 = DAT_0020._1_1_;
  DAT_6f76 = (char)DAT_0022;
  DAT_0020._1_1_ = DAT_6f73;
  DAT_0022._0_1_ = DAT_6f74;
  DAT_0022._1_1_ = DAT_003d;
  DAT_0024 = 0;
  uStack0000 = 0xb0;
  FUN_d40f();
  DAT_6f73 = DAT_0020._1_1_;
  DAT_6f74 = (char)DAT_0022;
  DAT_0036 = 0;
  do {
    if (*(byte *)(DAT_0036 + 0x664) != 0xff) {
      DAT_002b = DAT_6f75;
      DAT_002c = DAT_6f76;
      uStack0000 = 0xb0;
      DAT_002a = *(byte *)(DAT_0036 + 0x664);
      FUN_b067();
    }
    DAT_0036 = DAT_0036 + 1;
  } while (DAT_0036 < 10);
  DAT_0036 = 0;
  do {
    if (*(byte *)(DAT_0036 + 0x66e) != 0xff) {
      DAT_002b = DAT_6f73;
      DAT_002c = DAT_6f74;
      uStack0000 = 0xb0;
      DAT_002a = *(byte *)(DAT_0036 + 0x66e);
      FUN_b067();
    }
    DAT_0036 = DAT_0036 + 1;
  } while (DAT_0036 < 10);
  return;
}



/* 0xb067 FUN_b067 */

byte FUN_b067(void)

{
  ushort uVar1;
  byte bVar2;
  byte bVar3;
  char cVar4;
  bool bVar5;
  undefined1 uStack0000;
  
  uStack0000 = 0xb0;
  FUN_d2ab(DAT_002a,0);
  DAT_002b = DAT_002b >> 1 | DAT_002c << 7;
  bVar5 = CARRY1(*(byte *)(DAT_0022 + 6),DAT_002b);
  DAT_002d = *(byte *)(DAT_0022 + 6) + DAT_002b;
  DAT_002c = DAT_002c >> 1;
  *(byte *)(DAT_0022 + 6) = DAT_002d;
  DAT_002e = *(char *)(DAT_0022 + 7) + DAT_002c + bVar5;
  *(byte *)(DAT_0022 + 7) = DAT_002e;
  bVar2 = (*(byte *)(DAT_0022 + 7) + 0x3d) -
          ((*(byte *)(DAT_0022 + 6) + 0xb1 & ~*(byte *)(DAT_0022 + 6) & 0x80) == 0);
  bVar3 = ~*(byte *)(DAT_0022 + 7);
  if (((bVar3 & 0xc3 | bVar2 & 0xc3 | bVar2 & bVar3) & 0x80) != 0) {
    *(undefined1 *)(DAT_0022 + 6) = 0x4f;
    *(undefined1 *)(DAT_0022 + 7) = 0xc3;
  }
  bVar3 = (*(byte *)(DAT_0022 + 0xb) & 0xf0) >> 3;
  if ((bVar3 < 0xe) &&
     (bVar2 = DAT_002d - (&DAT_b0bc)[bVar3], uVar1 = (ushort)bVar3,
     bVar3 = (DAT_002e - (&DAT_b0bd)[uVar1]) -
             ((((&DAT_b0bc)[bVar3] & (~DAT_002d | bVar2) | bVar2 & ~DAT_002d) & 0x80) == 0),
     (((&DAT_b0bd)[uVar1] & (~DAT_002e | bVar3) | bVar3 & ~DAT_002e) & 0x80) != 0)) {
    DAT_002f = ((*(byte *)(DAT_0022 + 0xb) >> 4) + 1) * '\x10';
    bVar3 = *(byte *)(DAT_0022 + 0xb) & 0xf0;
    if (bVar3 < DAT_002f) {
      *(byte *)(DAT_0022 + 0xb) = *(byte *)(DAT_0022 + 0xb) & 0xf | DAT_002f;
      bVar3 = *(byte *)(DAT_0022 + 1);
      cVar4 = '\x06';
      if ((((bVar3 < 0x33) || (cVar4 = '\x05', bVar3 < 0x47)) || (cVar4 = '\x04', bVar3 < 0x51)) ||
         (cVar4 = '\x02', bVar3 < 0x5a)) {
        bVar3 = cVar4 + *(char *)(DAT_0022 + 1);
        *(byte *)(DAT_0022 + 1) = bVar3;
      }
      return bVar3;
    }
  }
  return bVar3;
}



/* 0xbec7 FUN_bec7 */

void FUN_bec7(void)

{
  byte bVar1;
  char cVar2;
  char cVar3;
  bool bVar4;
  byte bStack0000;
  
code_r0xbec7:
  do {
    while( true ) {
      bStack0000 = 0xbe;
      FUN_bee6();
      bStack0000 = 0xbe;
      bStack0000 = FUN_d4bb(0x50);
      if ((byte)(&DAT_bedf)[DAT_6f03 & 7] <= bStack0000) {
        FUN_c1e0();
        return;
      }
      bStack0000 = 0xbf;
      bVar1 = FUN_d4bb(100);
      if (bVar1 < 0x28) break;
      cVar2 = 0x45 < bVar1;
      if ((bool)cVar2) {
        cVar2 = 0x59 < bVar1;
        if ((bool)cVar2) {
          DAT_0022._0_1_ = 0x1e;
          DAT_0022._1_1_ = 0;
          DAT_0024 = 0x1e;
          bStack0000 = 0xc1;
          FUN_d36f(DAT_6f5e);
          if (cVar2 != '\0') {
            DAT_002a = (byte)DAT_0022;
            DAT_002b = DAT_0022._1_1_;
            DAT_0022._0_1_ = 0x1e;
            DAT_0022._1_1_ = 0;
            DAT_0024 = 0x1e;
            bStack0000 = 0xc1;
            FUN_d3a9(DAT_6f5e);
            if (cVar2 != '\0') {
              bVar4 = CARRY1((byte)DAT_0022,DAT_002a);
              DAT_002a = (byte)DAT_0022 + DAT_002a;
              DAT_0022._0_1_ = DAT_0022._1_1_ + DAT_002b + bVar4;
              DAT_0020 = CONCAT11(DAT_002a,(undefined1)DAT_0020);
              DAT_0022._1_1_ = (&DAT_c048)[DAT_6f02];
              DAT_0024 = 0;
              bStack0000 = 0xc1;
              DAT_002b = (byte)DAT_0022;
              FUN_d40f();
              DAT_0022._1_1_ = DAT_0020._1_1_;
              bStack0000 = 0xc1;
              FUN_d105(DAT_6f5e);
              bVar1 = *(char *)(DAT_0020 + 0xb) + DAT_0022._1_1_;
              *(byte *)(DAT_0020 + 0xb) = bVar1;
              if (0x62 < bVar1) {
                *(undefined1 *)(DAT_0020 + 0xb) = 99;
              }
              bStack0000 = 0xc1;
              FUN_d152(5);
            }
          }
        }
        else {
          DAT_0022._0_1_ = 10;
          DAT_0022._1_1_ = 0;
          DAT_0024 = 10;
          bStack0000 = 0xc0;
          FUN_d36f(DAT_6f5e);
          if (cVar2 != '\0') {
            DAT_0020 = CONCAT11(DAT_0022._1_1_,(byte)DAT_0022);
            DAT_0022._0_1_ = 0;
            DAT_0022._1_1_ = (&DAT_c045)[DAT_6f02];
            bStack0000 = 0xc0;
            FUN_d438();
            DAT_0020 = CONCAT11(DAT_0026,(undefined1)DAT_0020);
            DAT_0022._0_1_ = DAT_0027;
            DAT_0022._1_1_ = 10;
            DAT_0024 = 0;
            bStack0000 = 0xc1;
            FUN_d40f();
            DAT_0022._1_1_ = DAT_0020._1_1_;
            bStack0000 = 0xc1;
            FUN_d105(DAT_6f5e);
            bVar1 = *(char *)(DAT_0020 + 10) + DAT_0022._1_1_;
            *(byte *)(DAT_0020 + 10) = bVar1;
            if (0x62 < bVar1) {
              *(undefined1 *)(DAT_0020 + 10) = 99;
            }
            bStack0000 = 0xc1;
            FUN_d152(5);
          }
        }
      }
      else {
        DAT_0022._0_1_ = 10;
        DAT_0022._1_1_ = 0;
        DAT_0024 = 0xe;
        bStack0000 = 0xc0;
        FUN_d36f(DAT_6f5e);
        if (cVar2 != '\0') {
          DAT_0020 = CONCAT11(DAT_0022._1_1_,(byte)DAT_0022);
          DAT_0022._0_1_ = 0;
          DAT_0022._1_1_ = (&DAT_c042)[DAT_6f02];
          bStack0000 = 0xc0;
          FUN_d438();
          DAT_0020 = CONCAT11(DAT_0026,(undefined1)DAT_0020);
          DAT_0022._0_1_ = DAT_0027;
          DAT_0022._1_1_ = 10;
          DAT_0024 = 0;
          bStack0000 = 0xc0;
          FUN_d40f();
          DAT_0022._1_1_ = (byte)DAT_0022 >> 1;
          DAT_0022._0_1_ = DAT_0020._1_1_ >> 1 | (byte)DAT_0022 << 7;
          bStack0000 = 0xc0;
          FUN_d105(DAT_6f5e);
          bStack0000 = 0xc0;
          FUN_c1c0();
          bVar4 = CARRY1(*(byte *)(DAT_0020 + 6),(byte)DAT_0022);
          *(byte *)(DAT_0020 + 6) = *(byte *)(DAT_0020 + 6) + (byte)DAT_0022;
          bVar1 = *(char *)(DAT_0020 + 7) + DAT_0022._1_1_ + bVar4 & 0x7f;
          *(byte *)(DAT_0020 + 7) = bVar1;
          if ((0x26 < bVar1) && (0xf < *(byte *)(DAT_0020 + 6))) {
            *(undefined1 *)(DAT_0020 + 6) = 0xf;
            *(undefined1 *)(DAT_0020 + 7) = 0x27;
          }
          bStack0000 = 0xc0;
          FUN_d152(5);
        }
      }
    }
    cVar2 = '\0';
    if (2 < DAT_6f01) {
      cVar3 = 7 < DAT_6f01;
      cVar2 = '\x01';
      if (!(bool)cVar3) {
        DAT_0022._0_1_ = 10;
        DAT_0022._1_1_ = 0;
        DAT_0024 = 0xe;
        bStack0000 = 0xbf;
        FUN_d36f(DAT_6f5e);
        if (cVar3 != '\0') {
          DAT_0020 = CONCAT11(DAT_0022._1_1_,(byte)DAT_0022);
          DAT_0022._0_1_ = 0;
          DAT_0022._1_1_ = (&DAT_c042)[DAT_6f02];
          bStack0000 = 0xbf;
          FUN_d438();
          DAT_0020 = CONCAT11(DAT_0026,(undefined1)DAT_0020);
          DAT_0022._0_1_ = DAT_0027;
          DAT_0022._1_1_ = 10;
          DAT_0024 = 0;
          bStack0000 = 0xbf;
          FUN_d40f();
          DAT_0022._1_1_ = (byte)DAT_0022;
          DAT_0022._0_1_ = DAT_0020._1_1_;
          bStack0000 = 0xbf;
          FUN_d105(DAT_6f5e);
          bStack0000 = 0xbf;
          FUN_c1a7((byte)DAT_0022);
          bVar4 = CARRY1(*(byte *)(DAT_0020 + 8),(byte)DAT_0022);
          *(byte *)(DAT_0020 + 8) = *(byte *)(DAT_0020 + 8) + (byte)DAT_0022;
          bVar1 = *(char *)(DAT_0020 + 9) + DAT_0022._1_1_ + bVar4 & 3;
          *(byte *)(DAT_0020 + 9) = bVar1;
          if ((2 < bVar1) && (0xe6 < *(byte *)(DAT_0020 + 8))) {
            *(undefined1 *)(DAT_0020 + 8) = 0xe7;
            *(undefined1 *)(DAT_0020 + 9) = 3;
          }
          bStack0000 = 0xbf;
          FUN_d152(5);
        }
        goto code_r0xbec7;
      }
    }
    DAT_0022._0_1_ = 10;
    DAT_0022._1_1_ = 0;
    DAT_0024 = 0xe;
    bStack0000 = 0xbf;
    FUN_d36f(DAT_6f5e);
    if (cVar2 != '\0') {
      DAT_0020 = CONCAT11(DAT_0022._1_1_,(byte)DAT_0022);
      DAT_0022._0_1_ = 0;
      DAT_0022._1_1_ = (&DAT_c042)[DAT_6f02];
      bStack0000 = 0xbf;
      FUN_d438();
      DAT_0020 = CONCAT11(DAT_0026,(undefined1)DAT_0020);
      DAT_0022._0_1_ = DAT_0027;
      DAT_0022._1_1_ = 10;
      DAT_0024 = 0;
      bStack0000 = 0xc0;
      FUN_d40f();
      DAT_0022._1_1_ = (byte)DAT_0022;
      DAT_0022._0_1_ = DAT_0020._1_1_;
      bStack0000 = 0xc0;
      FUN_d105(DAT_6f5e);
      bStack0000 = 0xc0;
      FUN_c1a7((byte)DAT_0022);
      bVar4 = CARRY1(*(byte *)(DAT_0020 + 0xe),(byte)DAT_0022);
      *(byte *)(DAT_0020 + 0xe) = *(byte *)(DAT_0020 + 0xe) + (byte)DAT_0022;
      bVar1 = *(char *)(DAT_0020 + 0xf) + DAT_0022._1_1_ + bVar4 & 3;
      *(byte *)(DAT_0020 + 0xf) = bVar1;
      if ((2 < bVar1) && (0xe6 < *(byte *)(DAT_0020 + 0xe))) {
        *(undefined1 *)(DAT_0020 + 0xe) = 0xe7;
        *(undefined1 *)(DAT_0020 + 0xf) = 3;
      }
      bStack0000 = 0xc0;
      FUN_d152(5);
    }
  } while( true );
}



/* 0xbee6 FUN_bee6 */

void FUN_bee6(void)

{
  byte bVar1;
  byte bVar2;
  
  do {
    bVar1 = DAT_6f03;
    (&DAT_6f83)[DAT_6f03] = (&DAT_6f83)[DAT_6f03] + '\x01';
    bVar2 = (&DAT_6f83)[bVar1];
    if (0x1d < bVar2) {
      DAT_6f62 = DAT_6f62 + '\x01';
      if (DAT_6f62 == '\x03') {
        DAT_6f62 = 0;
        FUN_d140();
        return;
      }
      bVar2 = 0;
    }
    (&DAT_6f83)[bVar1] = bVar2;
    DAT_6f5e = bVar2;
    bVar2 = FUN_d105();
  } while (bVar2 != DAT_6f03);
  return;
}



/* 0xc1a7 FUN_c1a7 */

void FUN_c1a7(byte param_1)

{
  byte bVar1;
  
  DAT_002a = '\x01';
  if (0x1e < param_1) {
    DAT_002a = '\x02';
  }
  bVar1 = *(char *)(DAT_0020 + 0xb) + DAT_002a;
  if (99 < bVar1) {
    bVar1 = 100;
  }
  *(byte *)(DAT_0020 + 0xb) = bVar1;
  return;
}



/* 0xc1c0 FUN_c1c0 */

void FUN_c1c0(void)

{
  byte bVar1;
  
  DAT_002a = '\x01';
  if (((DAT_0022._1_1_ - 0xb) -
       (((~(byte)DAT_0022 & 0xb8 | (byte)DAT_0022 + 0x48 & 0xb8 |
         (byte)DAT_0022 + 0x48 & ~(byte)DAT_0022) & 0x80) == 0) & ~DAT_0022._1_1_ & 0x80) != 0) {
    DAT_002a = '\x02';
  }
  bVar1 = *(char *)(DAT_0020 + 0xb) + DAT_002a;
  if (99 < bVar1) {
    bVar1 = 100;
  }
  *(byte *)(DAT_0020 + 0xb) = bVar1;
  return;
}



/* 0xc1e0 FUN_c1e0 */

void FUN_c1e0(void)

{
  byte bVar1;
  char cVar2;
  undefined1 uStack0000;
  
  bVar1 = 0xf;
  do {
    (&DAT_6f73)[bVar1] = 0xff;
    bVar1 = bVar1 - 1;
  } while (-1 < (char)bVar1);
  uStack0000 = 0xc1;
  bVar1 = FUN_d4bb(100);
  if (0x1d < bVar1) {
    FUN_c298();
    return;
  }
  do {
    uStack0000 = 0xc1;
    FUN_c248();
    if (DAT_0022._1_1_ == -1) {
      FUN_c337();
      return;
    }
    DAT_0036 = DAT_0022._1_1_;
    uStack0000 = 0xc2;
    bVar1 = FUN_d283(3);
    cVar2 = 0x45 < bVar1;
  } while ((bool)cVar2);
  DAT_0022._0_1_ = '\x14';
  DAT_0022._1_1_ = 0;
  DAT_0024 = 10;
  uStack0000 = 0xc2;
  FUN_d36f(DAT_6f5e);
  if (cVar2 != '\0') {
    uStack0000 = 0xc2;
    cVar2 = FUN_d4ad(5);
    DAT_0022._0_1_ = cVar2 + (&DAT_c04b)[DAT_6f02];
    bVar1 = 3;
    uStack0000 = 0xc2;
    cVar2 = FUN_d283(DAT_0036);
    *(char *)(DAT_0020 + (ushort)bVar1) = cVar2 + (char)DAT_0022;
    uStack0000 = 0xc2;
    FUN_d5e7();
    uStack0000 = 0xc2;
    FUN_d152(5);
  }
  FUN_bec7();
  return;
}



/* 0xc248 FUN_c248 */

void FUN_c248(void)

{
  byte bVar1;
  undefined1 uStack0000;
  
  DAT_0024 = 0x11;
  DAT_0022._0_1_ = 0xff;
  DAT_0022._1_1_ = 0xff;
  do {
    uStack0000 = 0xc2;
    FUN_d105(DAT_6f5e);
    DAT_0025 = *(char *)(DAT_0020 + (ushort)DAT_0024);
    if ((DAT_0025 != -1) && ((&DAT_6f62)[DAT_0024] != '\0')) {
      uStack0000 = 0xc2;
      bVar1 = FUN_d283(DAT_0025,3);
      if ((bVar1 != 100) && (bVar1 < (byte)DAT_0022)) {
        DAT_0022._1_1_ = DAT_0024;
        DAT_0022._0_1_ = bVar1;
      }
    }
    DAT_0024 = DAT_0024 + 1;
  } while (DAT_0024 < 0x1b);
  uStack0000 = 0xc2;
  FUN_d105(DAT_6f5e);
  if (-1 < (char)DAT_0022._1_1_) {
    (&DAT_6f62)[DAT_0022._1_1_] = 0;
    DAT_0022._1_1_ = *(byte *)(DAT_0020 + (ushort)DAT_0022._1_1_);
  }
  return;
}



/* 0xc298 FUN_c298 */

void FUN_c298(void)

{
  byte bVar1;
  char cVar2;
  undefined1 uStack0000;
  
  do {
    uStack0000 = 0xc2;
    FUN_c2eb();
    if (DAT_0022._1_1_ == -1) goto LAB_c2e8;
    DAT_0036 = DAT_0022._1_1_;
    uStack0000 = 0xc2;
    bVar1 = FUN_d283(2);
  } while ((bVar1 < 0x32) || (cVar2 = 0x4f < bVar1, (bool)cVar2));
  DAT_0022._0_1_ = '\x14';
  DAT_0022._1_1_ = '\0';
  DAT_0024 = 10;
  uStack0000 = 0xc2;
  FUN_d36f(DAT_6f5e);
  if (cVar2 != '\0') {
    uStack0000 = 0xc2;
    cVar2 = FUN_d4ad(5);
    DAT_0022._0_1_ = cVar2 + (&DAT_c04b)[DAT_6f02];
    bVar1 = 2;
    uStack0000 = 0xc2;
    cVar2 = FUN_d283(DAT_0036);
    *(char *)(DAT_0020 + (ushort)bVar1) = cVar2 + (char)DAT_0022;
    uStack0000 = 0xc2;
    FUN_d5e7();
    uStack0000 = 0xc2;
    FUN_d152(5);
  }
LAB_c2e8:
  FUN_bec7();
  return;
}



/* 0xc2eb FUN_c2eb */

void FUN_c2eb(void)

{
  byte bVar1;
  undefined1 uStack0000;
  
  DAT_0024 = 0x11;
  DAT_0022._0_1_ = 0xff;
  DAT_0022._1_1_ = 0xff;
  do {
    uStack0000 = 0xc2;
    FUN_d105(DAT_6f5e);
    DAT_0025 = *(char *)(DAT_0020 + (ushort)DAT_0024);
    if ((DAT_0025 != -1) && ((&DAT_6f62)[DAT_0024] != '\0')) {
      uStack0000 = 0xc3;
      bVar1 = FUN_d283(DAT_0025,2);
      if (bVar1 < (byte)DAT_0022) {
        DAT_0022._1_1_ = DAT_0024;
        DAT_0022._0_1_ = bVar1;
      }
    }
    DAT_0024 = DAT_0024 + 1;
  } while (DAT_0024 < 0x1b);
  uStack0000 = 0xc3;
  FUN_d105(DAT_6f5e);
  if (-1 < (char)DAT_0022._1_1_) {
    (&DAT_6f62)[DAT_0022._1_1_] = 0;
    DAT_0022._1_1_ = *(byte *)(DAT_0020 + (ushort)DAT_0022._1_1_);
  }
  return;
}



/* 0xc337 FUN_c337 */

void FUN_c337(void)

{
  byte bVar1;
  byte bVar2;
  char cVar3;
  undefined1 uStack0000;
  
  uStack0000 = 0xc3;
  FUN_f266(0x30);
  if ((*(byte *)(DAT_6f5e + 0x8ffc) & 1) != 0) {
    while( true ) {
      uStack0000 = 0xc3;
      FUN_c3ff();
      if (DAT_0038 == -1) break;
      uStack0000 = 0xc3;
      FUN_d105(DAT_6f5e);
      if ((DAT_003a & 0x1f) == 0) {
        cVar3 = '\0';
        uStack0000 = 0xc3;
        FUN_c3a4(0x18);
        if (cVar3 == '\0') break;
        bVar2 = 10;
        uStack0000 = 0xc3;
        bVar1 = FUN_d2ab(DAT_0038);
        *(byte *)(DAT_0022 + (ushort)bVar2) = bVar1 & 0x1f | DAT_003a;
        uStack0000 = 0xc3;
        FUN_d152(5);
      }
      else {
        cVar3 = '\0';
        uStack0000 = 0xc3;
        FUN_c3a4((DAT_003a & 0x1f) << 1);
        if (cVar3 == '\0') break;
        bVar2 = 10;
        uStack0000 = 0xc3;
        bVar1 = FUN_d2ab(DAT_0038);
        *(byte *)(DAT_0022 + (ushort)bVar2) = bVar1 & 0xe0 | DAT_003a;
        uStack0000 = 0xc3;
        FUN_d152(5);
      }
    }
  }
  FUN_bec7();
  return;
}



/* 0xc3a4 FUN_c3a4 */

void FUN_c3a4(byte param_1)

{
  byte bVar1;
  byte bVar2;
  
  DAT_0022._0_1_ = *(byte *)(DAT_0020 + 2) - (&DAT_c3bf)[param_1];
  bVar1 = ~*(byte *)(DAT_0020 + 2);
  bVar2 = (*(byte *)(DAT_0020 + 3) - (&DAT_c3c0)[param_1]) -
          ((((&DAT_c3bf)[param_1] & (bVar1 | (byte)DAT_0022) | (byte)DAT_0022 & bVar1) & 0x80) == 0)
  ;
  bVar1 = ~*(byte *)(DAT_0020 + 3);
  if ((((&DAT_c3c0)[param_1] & (bVar1 | bVar2) | bVar2 & bVar1) & 0x80) != 0) {
    *(byte *)(DAT_0020 + 3) = bVar2;
    *(byte *)(DAT_0020 + 2) = (byte)DAT_0022;
  }
  return;
}



/* 0xc3ff FUN_c3ff */

void FUN_c3ff(void)

{
  char cVar1;
  byte bVar2;
  undefined1 uStack0000;
  
  DAT_0037 = 0x11;
  DAT_0038 = -1;
  DAT_0039 = 0;
  do {
    uStack0000 = 0xc4;
    FUN_d105(DAT_6f5e);
    if (*(char *)(DAT_0020 + (ushort)DAT_0037) != -1) {
      uStack0000 = 0xc4;
      DAT_003b = *(char *)(DAT_0020 + (ushort)DAT_0037);
      cVar1 = FUN_c451();
      if (cVar1 != -1) {
        uStack0000 = 0xc4;
        DAT_003c = cVar1;
        bVar2 = FUN_d2ab(DAT_003b,1);
        if (DAT_0039 <= bVar2) {
          DAT_0038 = DAT_003b;
          DAT_003a = DAT_003c;
          DAT_0039 = bVar2;
        }
      }
    }
    DAT_0037 = DAT_0037 + 1;
  } while (DAT_0037 < 0x1b);
  return;
}



/* 0xc451 FUN_c451 */

char FUN_c451(void)

{
  byte bVar1;
  char cVar2;
  byte bVar3;
  byte bVar4;
  undefined1 uStack0000;
  
  uStack0000 = 0xc4;
  DAT_002a = FUN_d2ab(10);
  bVar3 = DAT_002a & 0x1f;
  DAT_002b = '\0';
  if ((7 < bVar3) && (DAT_002b = '\x04', 0xf < bVar3)) {
    DAT_002b = '\b';
  }
  bVar1 = (&DAT_c4d0)[DAT_6f5e] * '\x10' + DAT_002b;
  bVar4 = bVar1;
  if (((((byte)(&DAT_c4ee)[bVar1] <= bVar3) &&
       (bVar4 = bVar1 + 1, (byte)(&DAT_c4ee)[bVar4] <= bVar3)) &&
      (bVar4 = bVar1 + 2, (byte)(&DAT_c4ee)[bVar4] <= bVar3)) &&
     (bVar4 = bVar1 + 3, (byte)(&DAT_c4ee)[bVar4] <= bVar3)) {
    cVar2 = (&DAT_c4d0)[DAT_6f5e] * '\x10';
    bVar3 = cVar2 + 0xc;
    bVar1 = DAT_002a >> 5;
    if ((((byte)(&DAT_c4ee)[bVar3] <= bVar1) &&
        (bVar3 = cVar2 + 0xd, (byte)(&DAT_c4ee)[bVar3] <= bVar1)) &&
       ((bVar3 = cVar2 + 0xe, (byte)(&DAT_c4ee)[bVar3] <= bVar1 &&
        (bVar3 = cVar2 + 0xf, (byte)(&DAT_c4ee)[bVar3] <= bVar1)))) {
      return -1;
    }
    return (&DAT_c4ee)[bVar3] << 5;
  }
  return (&DAT_c4ee)[bVar4];
}



/* 0xc50e FUN_c50e */

void FUN_c50e(void)

{
  byte bVar1;
  char cVar2;
  undefined1 uStack0000;
  
  uStack0000 = 0xc5;
  DAT_0036 = FUN_d249();
  cVar2 = DAT_0036 == '\0';
  uStack0000 = 0xc5;
  DAT_0045 = DAT_0036;
  FUN_d1a4();
  if (cVar2 != '\0') {
    return;
  }
  DAT_003b = 0;
  DAT_003c = 0;
  DAT_003d = 0xff;
  do {
    DAT_0036 = DAT_003b;
    uStack0000 = 0xc5;
    bVar1 = FUN_d105();
    cVar2 = (bVar1 & 7) == DAT_6f03;
    if ((bool)cVar2) {
      uStack0000 = 0xc5;
      FUN_d1a4();
      if (cVar2 != '\0') {
        uStack0000 = 0xc5;
        cVar2 = FUN_d583(DAT_0045,DAT_0036);
        if (cVar2 == -1) {
          uStack0000 = 0xc5;
          bVar1 = FUN_d304(DAT_003b);
          if ((DAT_003c <= bVar1) && (bVar1 != 10)) {
            DAT_003d = DAT_003b;
            DAT_003c = bVar1;
          }
        }
      }
    }
    DAT_003b = DAT_003b + 1;
  } while (DAT_003b < 0x1e);
  if (DAT_003d != 0xff) {
    uStack0000 = 0xc5;
    FUN_d105(DAT_0045);
    DAT_002a = *DAT_00ee;
    for (bVar1 = 0x11; *(char *)(DAT_0020 + (ushort)bVar1) != DAT_002a; bVar1 = bVar1 + 1) {
    }
    *(undefined1 *)(DAT_0020 + (ushort)bVar1) = 0xff;
    uStack0000 = 0xc5;
    FUN_d105(DAT_003d);
    for (bVar1 = 0x11; *(char *)(DAT_0020 + (ushort)bVar1) != -1; bVar1 = bVar1 + 1) {
    }
    *(char *)(DAT_0020 + (ushort)bVar1) = DAT_002a;
    uStack0000 = 0xc5;
    FUN_d3dd(DAT_0045);
    uStack0000 = 0xc5;
    FUN_d165(2);
  }
  uStack0000 = 0xc5;
  FUN_d249();
  return;
}



/* 0xc5b9 FUN_c5b9 */

void FUN_c5b9(void)

{
  undefined1 uStack0000;
  
  DAT_0036 = 0;
  do {
    uStack0000 = 0xc5;
    FUN_c5d2();
    uStack0000 = 0xc5;
    FUN_c6cc();
    DAT_0036 = DAT_0036 + 1;
  } while (DAT_0036 < 0x1e);
  uStack0000 = 0xc5;
  FUN_d249();
  return;
}



/* 0xc5d2 FUN_c5d2 */

void FUN_c5d2(void)

{
  byte bVar1;
  undefined1 uStack0000;
  
  uStack0000 = 0xc5;
  FUN_f266(0x31);
  uStack0000 = 0xc5;
  bVar1 = FUN_d105(DAT_0036);
  if ((bVar1 & 7) == DAT_6f03) {
    uStack0000 = 0xc5;
    bVar1 = FUN_d4bb(100);
    if (bVar1 < 10) {
      uStack0000 = 0xc5;
      bVar1 = FUN_d304(DAT_0036);
      if (bVar1 < 10) {
        DAT_0020 = CONCAT11(0x14,DAT_0036);
        uStack0000 = 0xc6;
        FUN_d471();
        DAT_0037 = 0;
        DAT_0022 = CONCAT11(DAT_002b + -0x75 + (0xe3 < DAT_002a),DAT_002a + 0x1c);
        do {
          do {
            DAT_0024 = *(undefined1 *)(DAT_0022 + (ushort)DAT_0037);
            bVar1 = *(char *)(DAT_0022 + (ushort)(byte)(DAT_0037 + 1)) + 0x9c;
            DAT_0020 = CONCAT11(DAT_0020._1_1_,bVar1);
            if (DAT_6f00 < bVar1) {
              DAT_0037 = DAT_0037 + 2;
              return;
            }
            uStack0000 = 0xc6;
            DAT_0037 = DAT_0037 + 2;
            bVar1 = FUN_d283(DAT_0024,0xb);
          } while ((bVar1 & 3) != 1);
          uStack0000 = 0xc6;
          DAT_002a = FUN_c66f(DAT_0024);
          do {
            uStack0000 = 0xc6;
            bVar1 = FUN_e89a();
          } while (99 < bVar1);
        } while (DAT_002a <= bVar1);
        *(byte *)(DAT_0020 + 0xb) = *(byte *)(DAT_0020 + 0xb) & 0xfc | 2;
        uStack0000 = 0xc6;
        FUN_d105(DAT_0036);
        bVar1 = 0x10;
        do {
          bVar1 = bVar1 + 1;
        } while (*(char *)(DAT_0020 + (ushort)bVar1) != -1);
        *(undefined1 *)(DAT_0020 + (ushort)bVar1) = DAT_0024;
        return;
      }
    }
  }
  return;
}



/* 0xc66f FUN_c66f */

undefined1 FUN_c66f(char param_1)

{
  if (DAT_6f03 == '\x04') {
    if (param_1 == 'm') {
      return 0x5a;
    }
    if (param_1 == 'p') {
      return 0x5a;
    }
    if (param_1 == '7') {
      return 0x5a;
    }
    if (param_1 == -0x49) {
      return 0x5a;
    }
    if (param_1 == -0x70) {
      return 0x5a;
    }
  }
  else if (DAT_6f03 == '\x02') {
    if ((((param_1 == 'V') || (param_1 == 'c')) || (param_1 == '9')) ||
       ((param_1 == -0x5b || (param_1 == -100)))) {
      return 0x5a;
    }
  }
  else if (DAT_6f03 == '\x03') {
    if (param_1 == 'k') {
      return 0x5a;
    }
    if (param_1 == -0x16) {
      return 0x5a;
    }
    if (param_1 == -0x15) {
      return 0x5a;
    }
    if (param_1 == -0x2b) {
      return 0x5a;
    }
    if (param_1 == '/') {
      return 0x5a;
    }
  }
  return 10;
}



/* 0xc6cc FUN_c6cc */

/* WARNING: Globals starting with '_' overlap smaller symbols at the same address */

byte FUN_c6cc(void)

{
  byte bVar1;
  byte bVar2;
  undefined1 uStack0000;
  byte unaff_retaddr;
  
  uStack0000 = 0xc6;
  bVar1 = FUN_d105(DAT_0036);
  bVar1 = bVar1 & 7;
  if (bVar1 == DAT_6f03) {
    uStack0000 = 0xc6;
    bVar1 = FUN_d4bb(100);
    if (bVar1 < (byte)(&DAT_c795)[DAT_6f02]) {
      uStack0000 = 0xc6;
      bVar1 = FUN_d304(DAT_0036);
      if (bVar1 < 10) {
        DAT_0037 = 0;
        uStack0000 = 0xc6;
        FUN_f266(0x30);
        bVar1 = 0xf;
        do {
          (&DAT_6f73)[bVar1] = 0xff;
          bVar1 = bVar1 - 1;
        } while (-1 < (char)bVar1);
        bVar1 = DAT_0036 << 3;
        bVar2 = 0;
        do {
          (&DAT_6f73)[bVar2] = *(undefined1 *)(bVar1 + 0x9d72);
          bVar1 = bVar1 + 1;
          bVar2 = bVar2 + 1;
        } while (bVar2 < 8);
        DAT_0022 = 0x63c0;
        bVar1 = 0;
        do {
          if ((*(byte *)(DAT_0022 + 0xb) & 3) == 0) {
            uStack0000 = 199;
            DAT_002a = FUN_c66f(bVar1);
            do {
              uStack0000 = 199;
              bVar2 = FUN_e89a();
            } while (99 < bVar2);
            if (bVar2 < DAT_002a) {
              if (*(char *)(DAT_0022 + 5) == DAT_0036) {
LAB_c765:
                *(byte *)(DAT_0022 + 0xb) = *(byte *)(DAT_0022 + 0xb) & 0xfc | 2;
                uStack0000 = 199;
                FUN_d105(DAT_0036);
                bVar2 = 0x10;
                do {
                  bVar2 = bVar2 + 1;
                } while (*(char *)(DAT_0020 + (ushort)bVar2) != -1);
                *(byte *)(DAT_0020 + (ushort)bVar2) = bVar1;
                uStack0000 = 199;
                DAT_0031 = bVar1;
                FUN_d319(DAT_6f03);
                DAT_0030 = *_DAT_0024;
                uStack0000 = 199;
                FUN_cf3f();
                return unaff_retaddr;
              }
              bVar2 = 0;
              do {
                if (*(char *)(DAT_0022 + 5) == (&DAT_6f73)[bVar2]) goto LAB_c765;
                bVar2 = bVar2 + 1;
              } while (bVar2 < 8);
            }
          }
          bVar2 = DAT_0022._1_1_ + (0xf3 < (byte)DAT_0022);
          DAT_0022 = CONCAT11(bVar2,(byte)DAT_0022 + 0xc);
          bVar1 = bVar1 + 1;
          if (0xec < bVar1) {
            return bVar2;
          }
        } while( true );
      }
    }
  }
  return bVar1;
}



/* 0xc79a FUN_c79a */

void FUN_c79a(void)

{
  byte bVar1;
  char cVar2;
  undefined1 uStack0000;
  
  DAT_0036 = 0xff;
  do {
    do {
      DAT_0036 = DAT_0036 + 1;
      if (0x1d < DAT_0036) {
        return;
      }
      uStack0000 = 199;
      bVar1 = FUN_d105(DAT_0036);
    } while ((bVar1 & 7) != DAT_6f03);
    bVar1 = 0xf;
    do {
      (&DAT_0540)[bVar1] = 0xff;
      bVar1 = bVar1 - 1;
    } while (-1 < (char)bVar1);
    while( true ) {
      uStack0000 = 199;
      FUN_c917();
      if (((char)DAT_0022 != '\0') || (DAT_002b < 2)) break;
      uStack0000 = 199;
      bVar1 = FUN_e88a();
      cVar2 = DAT_0020._1_1_ <= bVar1;
      if ((bool)cVar2) {
        DAT_0022._0_1_ = '\x14';
        DAT_0022._1_1_ = 0;
        DAT_0024 = 0;
        uStack0000 = 199;
        FUN_d36f(DAT_0036);
        if (cVar2 == '\0') {
          return;
        }
        uStack0000 = 199;
        FUN_f266(0x30);
        if ((*(byte *)(DAT_0036 + 0x8ffc) & 8) == 0) {
          uStack0000 = 199;
          FUN_c80a();
        }
        else {
          uStack0000 = 200;
          FUN_c97a();
          uStack0000 = 200;
          FUN_d165(5);
        }
      }
    }
  } while( true );
}



/* 0xc80a FUN_c80a */

void FUN_c80a(void)

{
  byte bVar1;
  undefined1 uStack0000;
  
  bVar1 = 0xf;
  do {
    (&DAT_6f73)[bVar1] = 0xff;
    bVar1 = bVar1 - 1;
  } while (-1 < (char)bVar1);
  uStack0000 = 200;
  FUN_f266(0x30);
  DAT_0024 = DAT_0036 << 3;
  do {
    uStack0000 = 200;
    bVar1 = FUN_d4ad(8);
    if (((&DAT_6f73)[bVar1] != '\0') &&
       ((&DAT_6f73)[bVar1] = 0, -1 < *(char *)((byte)(bVar1 + DAT_0024) + 0x9d72))) {
      uStack0000 = 200;
      FUN_c84d();
    }
    bVar1 = 0;
    while ((&DAT_6f73)[bVar1] != -1) {
      bVar1 = bVar1 + 1;
      if (7 < bVar1) {
        return;
      }
    }
  } while( true );
}



/* 0xc84d FUN_c84d */

void FUN_c84d(undefined1 param_1)

{
  byte bVar1;
  char cVar2;
  undefined1 uStack0000;
  undefined1 unaff_retaddr;
  
  uStack0000 = 200;
  DAT_0037 = param_1;
  bVar1 = FUN_d105();
  cVar2 = DAT_6f03 <= bVar1;
  if (bVar1 != DAT_6f03) {
    return;
  }
  uStack0000 = 200;
  FUN_c86a(DAT_0037);
  if (cVar2 != '\0') {
    FUN_c8e6(unaff_retaddr);
    return;
  }
  uStack0000 = 200;
  FUN_c885();
  return;
}



/* 0xc86a FUN_c86a */

void FUN_c86a(byte param_1)

{
  byte bVar1;
  byte bStack0000;
  
  bStack0000 = param_1;
  FUN_f266(0x30);
  bVar1 = bStack0000;
  if ((*(byte *)(bStack0000 + 0x8ffc) & 8) != 0) {
    bStack0000 = 200;
    bVar1 = FUN_d304(bVar1);
    if (bVar1 < 10) {
      return;
    }
  }
  return;
}



/* 0xc885 FUN_c885 */

void FUN_c885(void)

{
  byte bVar1;
  undefined1 uStack0000;
  
  bVar1 = 8;
  do {
    (&DAT_6f7b)[bVar1] = 0xff;
    bVar1 = bVar1 - 1;
  } while (-1 < (char)bVar1);
  DAT_0028 = DAT_0037 << 3;
  do {
    do {
      uStack0000 = 200;
      bVar1 = FUN_d4ad(8);
    } while ((&DAT_6f7b)[bVar1] == '\0');
    (&DAT_6f7b)[bVar1] = 0;
    if (-1 < *(char *)((byte)(bVar1 + DAT_0028) + 0x9d72)) {
      uStack0000 = 200;
      FUN_c8c3();
    }
    bVar1 = 0;
    while ((&DAT_6f7b)[bVar1] != -1) {
      bVar1 = bVar1 + 1;
      if (7 < bVar1) {
        return;
      }
    }
  } while( true );
}



/* 0xc8c3 FUN_c8c3 */

void FUN_c8c3(undefined1 param_1)

{
  byte bVar1;
  char cVar2;
  undefined1 uStack0000;
  
  uStack0000 = 200;
  DAT_0038 = param_1;
  bVar1 = FUN_d105();
  cVar2 = DAT_6f03 <= bVar1;
  if (bVar1 == DAT_6f03) {
    uStack0000 = 200;
    FUN_c86a(DAT_0038);
    if (cVar2 != '\0') {
      DAT_0037 = DAT_0038;
      FUN_c8e6();
      return;
    }
  }
  return;
}



/* 0xc8e6 FUN_c8e6 */

void FUN_c8e6(void)

{
  byte bVar1;
  char cVar2;
  undefined1 uStack0000;
  
  uStack0000 = 200;
  FUN_d105(DAT_0036);
  bVar1 = 0x10;
  do {
    bVar1 = bVar1 + 1;
  } while (*(char *)(DAT_0020 + (ushort)bVar1) != DAT_0039);
  *(undefined1 *)(DAT_0020 + (ushort)bVar1) = 0xff;
  uStack0000 = 0xc9;
  FUN_d105(DAT_0037);
  bVar1 = 0x10;
  do {
    bVar1 = bVar1 + 1;
  } while (*(char *)(DAT_0020 + (ushort)bVar1) != -1);
  *(char *)(DAT_0020 + (ushort)bVar1) = DAT_0039;
  uStack0000 = 0xc9;
  FUN_d3dd(DAT_0036);
  do {
    uStack0000 = 200;
    FUN_c97a();
    uStack0000 = 200;
    FUN_d165(5);
    while( true ) {
      do {
        while( true ) {
          uStack0000 = 199;
          FUN_c917();
          if (((char)DAT_0022 == '\0') && (1 < DAT_002b)) break;
          do {
            DAT_0036 = DAT_0036 + 1;
            if (0x1d < DAT_0036) {
              return;
            }
            uStack0000 = 199;
            bVar1 = FUN_d105(DAT_0036);
          } while ((bVar1 & 7) != DAT_6f03);
          bVar1 = 0xf;
          do {
            (&DAT_0540)[bVar1] = 0xff;
            bVar1 = bVar1 - 1;
          } while (-1 < (char)bVar1);
        }
        uStack0000 = 199;
        bVar1 = FUN_e88a();
        cVar2 = DAT_0020._1_1_ <= bVar1;
      } while (!(bool)cVar2);
      DAT_0022._0_1_ = '\x14';
      DAT_0022._1_1_ = 0;
      DAT_0024 = 0;
      uStack0000 = 199;
      FUN_d36f(DAT_0036);
      if (cVar2 == '\0') {
        return;
      }
      uStack0000 = 199;
      FUN_f266(0x30);
      if ((*(byte *)(DAT_0036 + 0x8ffc) & 8) != 0) break;
      uStack0000 = 199;
      FUN_c80a();
    }
  } while( true );
}



/* 0xc917 FUN_c917 */

void FUN_c917(void)

{
  byte bVar1;
  undefined1 uStack0000;
  
  uStack0000 = 0xc9;
  FUN_d105(DAT_0036);
  DAT_0028 = 0x11;
  DAT_0029 = 0xff;
  DAT_002a = 0xff;
  DAT_002b = '\0';
  do {
    if ((*(char *)(DAT_0028 + 0x52f) != '\0') && (*(char *)(DAT_0020 + DAT_0028) != -1)) {
      DAT_002b = DAT_002b + '\x01';
      uStack0000 = 0xc9;
      bVar1 = FUN_d2ab(0);
      if (bVar1 < DAT_0029) {
        DAT_002a = DAT_0028;
        DAT_0029 = bVar1;
      }
    }
    bVar1 = DAT_002a;
    DAT_0028 = DAT_0028 + 1;
  } while (DAT_0028 < 0x1b);
  *(undefined1 *)(DAT_002a + 0x52f) = 0;
  DAT_0039 = *(undefined1 *)(DAT_0020 + bVar1);
  uStack0000 = 0xc9;
  uStack0000 = FUN_d2d3(0);
  DAT_0022._0_1_ = FUN_d2ab(DAT_0039,0);
  DAT_0022._1_1_ = uStack0000;
  DAT_0020 = DAT_0020 & 0xff;
  DAT_0024 = 0;
  uStack0000 = 0xc9;
  FUN_d40f();
  return;
}



/* 0xc97a FUN_c97a */

void FUN_c97a(void)

{
  byte bVar1;
  undefined1 uStack0000;
  
  uStack0000 = 0xc9;
  uStack0000 = FUN_d2d3(DAT_0039,0);
  bVar1 = 0;
  FUN_d2ab(DAT_0039);
  *(undefined1 *)(DAT_0022 + (ushort)bVar1) = uStack0000;
  return;
}



/* 0xc98f FUN_c98f */

void FUN_c98f(undefined1 param_1)

{
  undefined1 uStack0000;
  
  DAT_0036 = 0;
  DAT_0037 = param_1;
  do {
    uStack0000 = 0xc9;
    FUN_c9a5();
    DAT_0036 = DAT_0036 + 1;
  } while (DAT_0036 < 0x1e);
  return;
}



/* 0xc9a5 FUN_c9a5 */

void FUN_c9a5(void)

{
  undefined1 uVar1;
  byte bVar2;
  char cVar3;
  undefined1 uStack0000;
  
  uStack0000 = 0xc9;
  bVar2 = FUN_d105(DAT_0036);
  if ((bVar2 & 7) != DAT_0037) {
    return;
  }
  DAT_003a = 0x11;
  DAT_003b = 0;
  DAT_003c = 0xff;
  do {
    if (*(char *)(DAT_0020 + (ushort)DAT_003a) != -1) {
      uStack0000 = 0xc9;
      cVar3 = FUN_d2ab(3);
      if (cVar3 == 'd') {
        DAT_003c = DAT_003a;
        break;
      }
      bVar2 = cVar3 + *(char *)(DAT_0022 + 4);
      if (DAT_003b <= bVar2) {
        DAT_003c = DAT_003a;
        DAT_003b = bVar2;
      }
    }
    DAT_003a = DAT_003a + 1;
  } while (DAT_003a < 0x1b);
  if ((DAT_003c != 0xff) && (DAT_003c != 0x11)) {
    uVar1 = *(undefined1 *)(DAT_0020 + 0x11);
    *(undefined1 *)(DAT_0020 + 0x11) = *(undefined1 *)(DAT_0020 + (ushort)DAT_003c);
    *(undefined1 *)(DAT_0020 + (ushort)DAT_003c) = uVar1;
  }
  return;
}



/* 0xca19 FUN_ca19 */

/* WARNING: Globals starting with '_' overlap smaller symbols at the same address */

void FUN_ca19(void)

{
  char cVar1;
  byte bVar2;
  undefined1 uStack0000;
  
  DAT_0040 = 0;
  do {
    uStack0000 = 0xca;
    FUN_d319(DAT_0040);
    cVar1 = *_DAT_0024;
    if ((cVar1 != -1) && (DAT_0038 = cVar1, _DAT_0024[3] == '\x03')) {
      uStack0000 = 0xca;
      bVar2 = FUN_d2ab(cVar1,0xb);
      if ((bVar2 & 3) != 2) {
        *(byte *)(DAT_0022 + 0xb) = *(byte *)(DAT_0022 + 0xb) & 0xfc | 3;
        uStack0000 = 0xca;
        FUN_ca68();
      }
      uStack0000 = 0xca;
      FUN_c98f(DAT_0040);
    }
    DAT_0040 = DAT_0040 + 1;
  } while (DAT_0040 < 7);
  uStack0000 = 0xca;
  FUN_d249();
  FUN_bec7();
  return;
}



/* 0xca68 FUN_ca68 */

/* WARNING: Removing unreachable block (RAM,0xca86) */
/* WARNING: Globals starting with '_' overlap smaller symbols at the same address */

void FUN_ca68(void)

{
  undefined1 uStack0000;
  
  uStack0000 = 0xca;
  FUN_ca87();
  uStack0000 = 0xca;
  FUN_cb05();
  uStack0000 = 0xca;
  FUN_d319(DAT_0040);
  *_DAT_0024 = 0xff;
  do {
  } while( true );
}



/* 0xca87 FUN_ca87 */

/* WARNING: Globals starting with '_' overlap smaller symbols at the same address */

void FUN_ca87(void)

{
  undefined1 uStack0000;
  
  _DAT_0024 = CONCAT11((&DAT_cad9)[(byte)(DAT_0040 << 1)],(&DAT_cad8)[(byte)(DAT_0040 << 1)]);
  for (DAT_0026 = 0; *(char *)(_DAT_0024 + (ushort)DAT_0026) != -1; DAT_0026 = DAT_0026 + 1) {
    uStack0000 = 0xca;
    DAT_0027 = *(char *)(_DAT_0024 + (ushort)DAT_0026);
    FUN_caad();
  }
  return;
}



/* 0xcaad FUN_caad */

void FUN_caad(void)

{
  char cVar1;
  byte bVar2;
  undefined1 uStack0000;
  undefined1 in_stack_00000004;
  
  DAT_002a = 0;
  do {
    uStack0000 = 0xca;
    cVar1 = FUN_d105(DAT_002a);
    if (cVar1 == DAT_0040) {
      bVar2 = 0x11;
      do {
        if (*(char *)(DAT_0020 + (ushort)bVar2) == DAT_0027) {
          FUN_cb52(in_stack_00000004);
          return;
        }
        bVar2 = bVar2 + 1;
      } while (bVar2 < 0x1b);
    }
    DAT_002a = DAT_002a + 1;
  } while (DAT_002a < 0x1e);
  return;
}



/* 0xcb05 FUN_cb05 */

void FUN_cb05(void)

{
  char cVar1;
  byte bVar2;
  undefined1 uStack0000;
  undefined1 unaff_retaddr;
  
  DAT_002a = 0;
  DAT_002b = 0;
  DAT_0027 = -1;
  do {
    uStack0000 = 0xcb;
    cVar1 = FUN_d105(DAT_002a);
    if (cVar1 == DAT_0040) {
      DAT_0024 = 0x11;
      do {
        if (*(char *)(DAT_0020 + (ushort)DAT_0024) != -1) {
          uStack0000 = 0xcb;
          bVar2 = FUN_d2ab(4);
          if (DAT_002b <= bVar2) {
            DAT_0027 = *(char *)(DAT_0020 + (ushort)DAT_0024);
            DAT_002b = bVar2;
          }
        }
        DAT_0024 = DAT_0024 + 1;
      } while (DAT_0024 < 0x1b);
    }
    DAT_002a = DAT_002a + 1;
  } while (DAT_002a < 0x1e);
  if (DAT_0027 != -1) {
    FUN_cb52(unaff_retaddr);
    return;
  }
  return;
}



/* 0xcb52 FUN_cb52 */

/* WARNING: Removing unreachable block (RAM,0xcb80) */
/* WARNING: Globals starting with '_' overlap smaller symbols at the same address */

void FUN_cb52(void)

{
  byte bVar1;
  undefined1 uStack0000;
  
  uStack0000 = 0xcb;
  FUN_d319(DAT_0040);
  DAT_0033 = *_DAT_0024;
  *_DAT_0024 = DAT_0027;
  bVar1 = 3;
  uStack0000 = 0xcb;
  FUN_d2ab();
  *(undefined1 *)(DAT_0022 + (ushort)bVar1) = 100;
  uStack0000 = DAT_0027;
  FUN_cb81();
  do {
  } while( true );
}



/* 0xcb81 FUN_cb81 */

void FUN_cb81(void)

{
  char cVar1;
  undefined1 uStack0000;
  
  DAT_0030 = DAT_0027;
  DAT_0045 = 0;
  do {
    uStack0000 = 0xcb;
    cVar1 = FUN_d105(DAT_0045);
    if (cVar1 == DAT_0040) {
      uStack0000 = 0xcb;
      FUN_cba3();
    }
    DAT_0045 = DAT_0045 + 1;
  } while (DAT_0045 < 0x1e);
  return;
}



/* 0xcba3 FUN_cba3 */

void FUN_cba3(void)

{
  byte bVar1;
  char cVar2;
  byte bVar3;
  undefined1 uStack0000;
  
  DAT_0044 = 0x11;
  do {
    uStack0000 = 0xcb;
    FUN_d105(DAT_0045);
    cVar2 = DAT_0020[DAT_0044];
    if ((cVar2 == -1) || (cVar2 == DAT_0030)) {
      while (DAT_0045 = DAT_0045 + 1, DAT_0045 < 0x1e) {
        uStack0000 = 0xcb;
        cVar2 = FUN_d105(DAT_0045);
        if (cVar2 == DAT_0040) {
          uStack0000 = 0xcb;
          FUN_cba3();
        }
      }
      return;
    }
    DAT_0032 = DAT_0040;
    uStack0000 = 0xcb;
    DAT_0031 = cVar2;
    FUN_cf7c();
    uStack0000 = 0xcb;
    bVar1 = FUN_d2ab(DAT_0031,3);
    if (bVar1 < 0x1f) {
      uStack0000 = 0xcb;
      bVar1 = FUN_d4bb(100);
      if (bVar1 < 0x14) {
        bVar3 = 0xb;
        uStack0000 = 0xcb;
        bVar1 = FUN_d2ab(DAT_0031);
        *(byte *)(DAT_0022 + (ushort)bVar3) = bVar1 & 0xfc;
        *(byte *)(DAT_0022 + 5) = DAT_0045;
      }
    }
    DAT_0044 = DAT_0044 + 1;
  } while (DAT_0044 < 0x1b);
  uStack0000 = 0xcb;
  FUN_d3dd(DAT_0045);
  uStack0000 = 0xcc;
  cVar2 = FUN_d304(DAT_0045);
  if (cVar2 == '\0') {
    uStack0000 = 0xcc;
    FUN_d105(DAT_0045);
    *DAT_0020 = 7;
  }
  return;
}



/* 0xcc12 FUN_cc12 */

void FUN_cc12(void)

{
  byte bVar1;
  byte bVar2;
  byte bVar3;
  byte bVar4;
  bool bVar5;
  undefined1 uStack0000;
  
  DAT_0036 = 0xff;
  while (DAT_0036 = DAT_0036 + 1, DAT_0036 < 0x1e) {
    uStack0000 = 0xcc;
    bVar4 = FUN_d105(DAT_0036);
    if (((bVar4 & 7) == DAT_6f03) &&
       (bVar4 = *(byte *)(DAT_0020 + 3) -
                ((*(byte *)(DAT_0020 + 2) - 0x32 & ~*(byte *)(DAT_0020 + 2) & 0x80) == 0),
       (bVar4 & ~*(byte *)(DAT_0020 + 3) & 0x80) == 0)) {
      uStack0000 = 0xcc;
      FUN_f266(bVar4,0x30);
      if ((*(byte *)(DAT_0036 + 0x8ffc) & 4) != 0) {
        uStack0000 = 0xcc;
        FUN_ccf8();
        uStack0000 = 0xcc;
        FUN_d105(DAT_0036);
        bVar2 = *(byte *)(DAT_0020 + 4) - DAT_0039;
        bVar4 = ~*(byte *)(DAT_0020 + 4);
        bVar3 = (*(byte *)(DAT_0020 + 5) - DAT_003a) -
                (((DAT_0039 & (bVar4 | bVar2) | bVar2 & bVar4) & 0x80) == 0);
        bVar4 = ~*(byte *)(DAT_0020 + 5);
        bVar1 = DAT_003a & (bVar4 | bVar3);
        DAT_0039 = bVar2;
        DAT_003a = bVar3;
        if (((bVar1 | bVar3 & bVar4) & 0x80) != 0) {
          if (((bVar3 - 1) - ((bVar2 - 0x2c & ~bVar2 & 0x80) == 0) & ~bVar3 & 0x80) != 0) {
            DAT_0039 = 0x2c;
            DAT_003a = 1;
          }
          bVar2 = *(byte *)(DAT_0020 + 4) - DAT_0039;
          bVar4 = ~*(byte *)(DAT_0020 + 4);
          bVar1 = DAT_0039 & (bVar4 | bVar2);
          *(byte *)(DAT_0020 + 4) = bVar2;
          *(byte *)(DAT_0020 + 5) =
               (*(char *)(DAT_0020 + 5) - DAT_003a) - (((bVar1 | bVar2 & bVar4) & 0x80) == 0);
          uStack0000 = 0xcc;
          FUN_f266(0x30);
          DAT_0022._1_1_ = *(undefined1 *)((byte)(DAT_0036 << 1) + 0x8fc0);
          DAT_0020 = CONCAT11(DAT_003a,DAT_0039);
          DAT_0022._0_1_ = 0;
          uStack0000 = 0xcc;
          FUN_d438();
          DAT_0020 = CONCAT11(DAT_0027,DAT_0026);
          DAT_0022._0_1_ = DAT_0028;
          DAT_0022._1_1_ = 100;
          DAT_0024 = 0;
          uStack0000 = 0xcc;
          FUN_d336();
          DAT_0039 = (byte)DAT_0020;
          DAT_003a = DAT_0020._1_1_;
          uStack0000 = 0xcc;
          FUN_d105(DAT_0036);
          bVar5 = CARRY1(*(byte *)(DAT_0020 + 2),DAT_0039);
          *(byte *)(DAT_0020 + 2) = *(byte *)(DAT_0020 + 2) + DAT_0039;
          *(byte *)(DAT_0020 + 3) = *(char *)(DAT_0020 + 3) + DAT_003a + bVar5;
          uStack0000 = 0xcc;
          FUN_d69d();
          uStack0000 = 0xcc;
          FUN_d165(2);
        }
      }
    }
  }
  return;
}



/* 0xccf8 FUN_ccf8 */

void FUN_ccf8(void)

{
  byte bVar1;
  char cVar2;
  bool bVar3;
  undefined1 uStack0000;
  
  uStack0000 = 0xcc;
  FUN_d105(DAT_0036);
  DAT_0037 = 0x11;
  DAT_0038 = 0;
  DAT_0039 = '\0';
  do {
    if (*(char *)(DAT_0020 + (ushort)DAT_0037) != -1) {
      cVar2 = '\b';
      uStack0000 = 0xcd;
      bVar1 = FUN_d2ab();
      bVar3 = CARRY1(bVar1,DAT_0038);
      DAT_0038 = bVar1 + DAT_0038;
      DAT_0039 = DAT_0039 + *(char *)(DAT_0022 + (ushort)(byte)(cVar2 + 1)) + bVar3;
    }
    DAT_0037 = DAT_0037 + 1;
  } while (DAT_0037 < 0x1b);
  bVar1 = DAT_0039 << 1 | DAT_0038 >> 7;
  DAT_0020._1_1_ = DAT_0038 * '\x03';
  DAT_0022 = CONCAT11(0x19,bVar1 + DAT_0039 + CARRY1(DAT_0038 * '\x02',DAT_0038));
  DAT_0024 = 0;
  uStack0000 = 0xcd;
  DAT_0038 = DAT_0038 * '\x02';
  DAT_0039 = bVar1;
  FUN_d40f();
  DAT_0039 = DAT_0020._1_1_;
  DAT_003a = (undefined1)DAT_0022;
  return;
}



/* 0xcd68 FUN_cd68 */

void FUN_cd68(void)

{
  char cVar1;
  undefined1 uStack0000;
  
  uStack0000 = 0xcd;
  cVar1 = FUN_d4ad(10);
  DAT_0036 = 6;
  uStack0000 = 0xcd;
  FUN_cdb9(cVar1 + '\n');
  uStack0000 = 0xcd;
  FUN_cd9a();
  DAT_0036 = 8;
  uStack0000 = 0xcd;
  FUN_cdb9();
  uStack0000 = 0xcd;
  FUN_cd9a();
  DAT_0036 = 0xe;
  uStack0000 = 0xcd;
  FUN_cdb9();
  uStack0000 = 0xcd;
  FUN_cd9a();
  DAT_0036 = 0xb;
  uStack0000 = 0xcd;
  FUN_ce1b();
  return;
}



/* 0xcd9a FUN_cd9a */

undefined1 FUN_cd9a(void)

{
  undefined1 uVar1;
  
  uVar1 = 10;
  if ((((4 < DAT_6f8d) && (uVar1 = 0x14, 9 < DAT_6f8d)) && (uVar1 = 0x1e, 0xe < DAT_6f8d)) &&
     (uVar1 = 0x28, 0x13 < DAT_6f8d)) {
    uVar1 = 0x3c;
  }
  return uVar1;
}



/* 0xcdb9 FUN_cdb9 */

void FUN_cdb9(undefined1 param_1)

{
  byte bVar1;
  byte bVar2;
  byte bVar3;
  byte bVar4;
  byte bVar5;
  undefined1 uStack0000;
  
  uStack0000 = param_1;
  FUN_d105(DAT_0038);
  DAT_0020 = CONCAT11(*(undefined1 *)(DAT_0020 + (ushort)(byte)(DAT_0036 + 1)),
                      *(undefined1 *)(DAT_0020 + (ushort)DAT_0036));
  DAT_0022._1_1_ = uStack0000;
  DAT_0022._0_1_ = 0;
  uStack0000 = 0xcd;
  FUN_d438();
  DAT_0020 = CONCAT11(DAT_0027,DAT_0026);
  DAT_0022._0_1_ = DAT_0028;
  DAT_0022._1_1_ = 100;
  DAT_0024 = 0;
  uStack0000 = 0xcd;
  FUN_d336();
  DAT_002a = (byte)DAT_0020;
  DAT_002b = DAT_0020._1_1_;
  uStack0000 = 0xcd;
  FUN_d105(DAT_0038);
  bVar5 = DAT_0036;
  bVar4 = *(byte *)(DAT_0020 + (ushort)DAT_0036) - DAT_002a;
  bVar1 = ~*(byte *)(DAT_0020 + (ushort)DAT_0036);
  bVar2 = DAT_002a & (bVar1 | bVar4);
  *(byte *)(DAT_0020 + (ushort)DAT_0036) = bVar4;
  bVar3 = *(byte *)(DAT_0020 + (ushort)(byte)(bVar5 + 1));
  bVar2 = (bVar3 - DAT_002b) - (((bVar2 | bVar4 & bVar1) & 0x80) == 0);
  bVar3 = ~bVar3;
  bVar1 = DAT_002b & (bVar3 | bVar2);
  *(byte *)(DAT_0020 + (ushort)(byte)(bVar5 + 1)) = bVar2;
  bVar4 = DAT_0036;
  if (((bVar1 | bVar2 & bVar3) & 0x80) == 0) {
    *(undefined1 *)(DAT_0020 + (ushort)DAT_0036) = 0;
    *(undefined1 *)(DAT_0020 + (ushort)(byte)(bVar4 + 1)) = 0;
  }
  return;
}



/* 0xce1b FUN_ce1b */

void FUN_ce1b(undefined1 param_1)

{
  byte bVar1;
  byte bVar2;
  byte bVar3;
  byte bVar4;
  undefined1 uStack0000;
  
  uStack0000 = param_1;
  FUN_d105(DAT_0038);
  DAT_0022._1_1_ = uStack0000;
  DAT_0020 = (ushort)*(byte *)(DAT_0020 + DAT_0036);
  DAT_0022._0_1_ = 0;
  uStack0000 = 0xce;
  FUN_d438();
  DAT_0020 = CONCAT11(DAT_0027,DAT_0026);
  DAT_0022._0_1_ = DAT_0028;
  DAT_0022._1_1_ = 100;
  DAT_0024 = 0;
  uStack0000 = 0xce;
  FUN_d336();
  DAT_002a = (byte)DAT_0020;
  uStack0000 = 0xce;
  FUN_d105(DAT_0038);
  bVar4 = DAT_0036;
  bVar3 = *(byte *)(DAT_0020 + DAT_0036) - DAT_002a;
  bVar1 = ~*(byte *)(DAT_0020 + DAT_0036);
  bVar2 = DAT_002a & (bVar1 | bVar3);
  *(byte *)(DAT_0020 + DAT_0036) = bVar3;
  if (((bVar2 | bVar3 & bVar1) & 0x80) == 0) {
    *(undefined1 *)(DAT_0020 + bVar4) = 0;
  }
  return;
}



/* 0xce67 FUN_ce67 */

void FUN_ce67(void)

{
  byte bVar1;
  byte bVar2;
  byte bVar3;
  undefined1 uStack0000;
  
  bVar3 = 0xfe;
  do {
    bVar3 = bVar3 + 2;
    bVar1 = DAT_0522 - (&DAT_cec9)[bVar3];
    bVar1 = (DAT_0523 - (&DAT_ceca)[bVar3]) -
            ((((&DAT_cec9)[bVar3] & (~DAT_0522 | bVar1) | bVar1 & ~DAT_0522) & 0x80) == 0);
  } while ((((&DAT_ceca)[bVar3] & (~DAT_0523 | bVar1) | bVar1 & ~DAT_0523) & 0x80) != 0);
  DAT_0022._1_1_ = (&DAT_ced3)[bVar3 >> 1];
  DAT_0020._0_1_ = DAT_0522;
  DAT_0020._1_1_ = DAT_0523;
  DAT_0022._0_1_ = 0;
  uStack0000 = 0xce;
  FUN_d438();
  DAT_0020._0_1_ = DAT_0026;
  DAT_0020._1_1_ = DAT_0027;
  DAT_0022._0_1_ = DAT_0028;
  DAT_0022._1_1_ = 100;
  DAT_0024 = 0;
  uStack0000 = 0xce;
  FUN_d336();
  bVar1 = DAT_0522 - (byte)DAT_0020;
  bVar2 = (DAT_0523 - DAT_0020._1_1_) -
          ((((byte)DAT_0020 & (~DAT_0522 | bVar1) | bVar1 & ~DAT_0522) & 0x80) == 0);
  bVar3 = ~DAT_0523;
  DAT_0522 = bVar1;
  DAT_0523 = bVar2;
  if (((DAT_0020._1_1_ & (bVar3 | bVar2) | bVar2 & bVar3) & 0x80) == 0) {
    DAT_0522 = 0;
    DAT_0523 = 0;
  }
  return;
}



/* 0xcedd FUN_cedd */

void FUN_cedd(void)

{
  byte bVar1;
  byte bVar2;
  byte bVar3;
  undefined1 uStack0000;
  
  bVar3 = 0xfe;
  do {
    bVar3 = bVar3 + 2;
    bVar1 = DAT_0526 - (&DAT_cec9)[bVar3];
    bVar1 = (DAT_0527 - (&DAT_ceca)[bVar3]) -
            ((((&DAT_cec9)[bVar3] & (~DAT_0526 | bVar1) | bVar1 & ~DAT_0526) & 0x80) == 0);
  } while ((((&DAT_ceca)[bVar3] & (~DAT_0527 | bVar1) | bVar1 & ~DAT_0527) & 0x80) != 0);
  DAT_0022._1_1_ = (&DAT_ced3)[bVar3 >> 1];
  DAT_0020._0_1_ = DAT_0526;
  DAT_0020._1_1_ = DAT_0527;
  DAT_0022._0_1_ = 0;
  uStack0000 = 0xcf;
  FUN_d438();
  DAT_0020._0_1_ = DAT_0026;
  DAT_0020._1_1_ = DAT_0027;
  DAT_0022._0_1_ = DAT_0028;
  DAT_0022._1_1_ = 100;
  DAT_0024 = 0;
  uStack0000 = 0xcf;
  FUN_d336();
  bVar1 = DAT_0526 - (byte)DAT_0020;
  bVar2 = (DAT_0527 - DAT_0020._1_1_) -
          ((((byte)DAT_0020 & (~DAT_0526 | bVar1) | bVar1 & ~DAT_0526) & 0x80) == 0);
  bVar3 = ~DAT_0527;
  DAT_0526 = bVar1;
  DAT_0527 = bVar2;
  if (((DAT_0020._1_1_ & (bVar3 | bVar2) | bVar2 & bVar3) & 0x80) == 0) {
    DAT_0526 = 0;
    DAT_0527 = 0;
  }
  return;
}



/* 0xcf3f FUN_cf3f */

void FUN_cf3f(void)

{
  byte bVar1;
  char cStack0000;
  
  cStack0000 = 0xcf;
  DAT_0020._1_1_ = FUN_d2ab(DAT_0030,4);
  DAT_0022 = 0xa00;
  DAT_0024 = 0;
  cStack0000 = 0xcf;
  FUN_d40f();
  cStack0000 = DAT_0020._1_1_ + 'F';
  DAT_0020._0_1_ = FUN_d2ab(DAT_0031,3);
  bVar1 = cStack0000 - (char)DAT_0020;
  if (0x59 < bVar1) {
    bVar1 = 0x5a;
  }
  if (bVar1 < 10) {
    bVar1 = 10;
  }
  *(byte *)(DAT_0022 + 3) = bVar1;
  cStack0000 = 0xcf;
  FUN_d61e();
  return;
}



/* 0xcf7c FUN_cf7c */

/* WARNING: Globals starting with '_' overlap smaller symbols at the same address */

void FUN_cf7c(void)

{
  char cVar1;
  byte bVar2;
  byte bVar3;
  byte bStack0000;
  
  _DAT_0024 = CONCAT11((&DAT_cad9)[(byte)(DAT_0032 << 1)],(&DAT_cad8)[(byte)(DAT_0032 << 1)]);
  bVar3 = 0xff;
  do {
    bVar3 = bVar3 + 1;
    if (*(char *)(_DAT_0024 + bVar3) == -1) {
      bStack0000 = 0xcf;
      DAT_0020._1_1_ = FUN_d2ab(DAT_0030,4);
      DAT_0022 = &DAT_0500;
      _DAT_0024 = _DAT_0024 & 0xff00;
      bStack0000 = 0xcf;
      FUN_d40f();
      bStack0000 = DAT_0020._1_1_;
      DAT_0020._1_1_ = FUN_d2ab(DAT_0033,4);
      DAT_0022 = &DAT_0500;
      _DAT_0024 = _DAT_0024 & 0xff00;
      FUN_d40f();
      DAT_0020._0_1_ = bStack0000 - DAT_0020._1_1_;
      if (((DAT_0020._1_1_ & (~bStack0000 | (byte)DAT_0020) | (byte)DAT_0020 & ~bStack0000) & 0x80)
          == 0) {
        DAT_0020._0_1_ = ((byte)DAT_0020 ^ 0xff) + 1;
        bStack0000 = 0xcf;
        bVar2 = FUN_d2ab(DAT_0031,3);
        bVar3 = bVar2 - (byte)DAT_0020;
        if ((((byte)DAT_0020 & (~bVar2 | bVar3) | bVar3 & ~bVar2) & 0x80) == 0) {
          bVar3 = 0;
        }
      }
      else {
        bStack0000 = 0xcf;
        cVar1 = FUN_d2ab(DAT_0031,3);
        bVar3 = cVar1 + (byte)DAT_0020;
      }
      bVar2 = bVar3 - 10;
      if ((bVar2 & ~bVar3 & 0x80) == 0) {
        bVar2 = 0;
      }
      if (0x62 < bVar2) {
        bVar2 = 99;
      }
      if (bVar2 < 10) {
        bVar2 = 10;
      }
      DAT_0022[3] = bVar2;
      bStack0000 = 0xd0;
      FUN_d61e();
      return;
    }
  } while (*(char *)(_DAT_0024 + bVar3) != DAT_0030);
  return;
}



/* 0xd00c FUN_d00c */

void FUN_d00c(void)

{
  byte bVar1;
  undefined1 uStack0000;
  
  uStack0000 = 0xd0;
  bVar1 = FUN_d2ab((byte)DAT_0020,3);
  DAT_0020._0_1_ = 0x32 - bVar1;
  if (((bVar1 & ((byte)DAT_0020 | 0xcd) | (byte)DAT_0020 & 0xcd) & 0x80) == 0) {
    DAT_0020._0_1_ = ((byte)DAT_0020 ^ 0xff) + 1;
  }
  bVar1 = 0x33 - (byte)DAT_0020;
  if ((((byte)DAT_0020 & (bVar1 | 0xcc) | bVar1 & 0xcc) & 0x80) == 0) {
    bVar1 = 0;
  }
  if (bVar1 < 10) {
    bVar1 = 10;
  }
  *(byte *)(DAT_0022 + 3) = bVar1;
  uStack0000 = 0xd0;
  FUN_d61e();
  return;
}



/* 0xd105 FUN_d105 */

byte FUN_d105(byte param_1)

{
  undefined1 uStack0000;
  
  DAT_0020 = (byte *)CONCAT11((((((param_1 >> 7) << 1 | (param_1 & 0x7f) >> 6) << 1 |
                                (param_1 & 0x3f) >> 5) << 1 | (param_1 & 0x1f) >> 4) << 1 |
                              (param_1 & 0xf) >> 3) + 0x60,param_1 * ' ');
  uStack0000 = 0xd1;
  FUN_d69d();
  return *DAT_0020 & 7;
}



/* 0xd140 FUN_d140 */

void FUN_d140(void)

{
  DAT_6f5b = 2;
  DAT_6f8b = 0xff;
  DAT_6f8d = 0;
  return;
}



/* 0xd152 FUN_d152 */

void FUN_d152(byte param_1)

{
  byte bVar1;
  byte bVar2;
  
  DAT_0020._0_1_ = param_1;
  bVar2 = DAT_6f5d - param_1;
  bVar1 = ~DAT_6f5d;
  DAT_6f5d = bVar2;
  if ((bVar2 != 0) && (((param_1 & (bVar1 | bVar2) | bVar2 & bVar1) & 0x80) != 0)) {
    return;
  }
  FUN_d140();
  return;
}



/* 0xd165 FUN_d165 */

void FUN_d165(byte param_1)

{
  byte bVar1;
  byte bVar2;
  undefined1 unaff_retaddr;
  
  DAT_0020._0_1_ = param_1;
  bVar2 = DAT_6f5d - param_1;
  bVar1 = ~DAT_6f5d;
  DAT_6f5d = bVar2;
  if (((param_1 & (bVar1 | bVar2) | bVar2 & bVar1) & 0x80) == 0) {
    FUN_d140(unaff_retaddr);
    return;
  }
  return;
}



/* 0xd1a4 FUN_d1a4 */

byte FUN_d1a4(void)

{
  byte bVar1;
  undefined1 uStack0000;
  
  DAT_002a = DAT_6f03;
  uStack0000 = 0xd1;
  FUN_f266(0x30);
  bVar1 = 0xf;
  do {
    (&DAT_6f73)[bVar1] = 0xff;
    bVar1 = bVar1 - 1;
  } while (-1 < (char)bVar1);
  DAT_002b = 0;
  DAT_002c = 0;
  bVar1 = DAT_0036 << 3;
  do {
    if (*(char *)(bVar1 + 0x9d72) < '\0') {
      return DAT_002b;
    }
    uStack0000 = 0xd1;
    DAT_0022._1_1_ = *(char *)(bVar1 + 0x9d72);
    DAT_0024 = bVar1;
    bVar1 = FUN_d105();
    if (((bVar1 & 7) != 7) && ((bVar1 & 7) != DAT_002a)) {
      (&DAT_6f73)[DAT_002b] = DAT_0022._1_1_;
      DAT_002b = DAT_002b + 1;
    }
    bVar1 = DAT_0024 + 1;
    DAT_002c = DAT_002c + 1;
  } while (DAT_002c < 8);
  return DAT_002b;
}



/* 0xd249 FUN_d249 */

byte FUN_d249(void)

{
  byte bVar1;
  undefined1 uStack0000;
  
  uStack0000 = 0xd2;
  FUN_d6e5();
  DAT_0036 = 0;
  DAT_002a = *DAT_00ee;
  do {
    uStack0000 = 0xd2;
    bVar1 = FUN_d105(DAT_0036);
    if ((bVar1 & 7) == DAT_6f03) {
      bVar1 = 0x11;
      do {
        if (*(char *)(DAT_0020 + (ushort)bVar1) == DAT_002a) {
          return DAT_0036;
        }
        bVar1 = bVar1 + 1;
      } while (bVar1 < 0x1b);
    }
    DAT_0036 = DAT_0036 + 1;
  } while (DAT_0036 < 0x1e);
  return 0xff;
}



/* 0xd283 FUN_d283 */

undefined1 FUN_d283(byte param_1,byte param_2)

{
  DAT_0020 = CONCAT11((((CARRY1(param_1 * '\x02',param_1) - ((char)param_1 >> 7)) * '\x02' |
                       (byte)(param_1 * '\x03') >> 7) << 1 | (param_1 * '\x03' & 0x7f) >> 6) + 99 +
                      (0x3f < (byte)(param_1 * '\f')),param_1 * '\f' - 0x40);
  return *(undefined1 *)(DAT_0020 + (ushort)param_2);
}



/* 0xd2ab FUN_d2ab */

undefined1 FUN_d2ab(byte param_1,byte param_2)

{
  DAT_0022 = CONCAT11((((CARRY1(param_1 * '\x02',param_1) - ((char)param_1 >> 7)) * '\x02' |
                       (byte)(param_1 * '\x03') >> 7) << 1 | (param_1 * '\x03' & 0x7f) >> 6) + 99 +
                      (0x3f < (byte)(param_1 * '\f')),param_1 * '\f' - 0x40);
  return *(undefined1 *)(DAT_0022 + (ushort)param_2);
}



/* 0xd2d3 FUN_d2d3 */

/* WARNING: Globals starting with '_' overlap smaller symbols at the same address */

undefined1 FUN_d2d3(byte param_1)

{
  byte bVar1;
  undefined1 uStack0000;
  
  uStack0000 = 0xd2;
  DAT_0026 = param_1;
  bVar1 = FUN_f266(0x31);
  _DAT_0024 = CONCAT11((((CARRY1(bVar1 * '\x02',bVar1) - ((char)bVar1 >> 7)) * '\x02' |
                        (byte)(bVar1 * '\x03') >> 7) << 1 | (bVar1 * '\x03' & 0x7f) >> 6) + 0x80,
                       bVar1 * '\f');
  return *(undefined1 *)(_DAT_0024 + (ushort)DAT_0026);
}



/* 0xd304 FUN_d304 */

char FUN_d304(void)

{
  char cVar1;
  byte bVar2;
  undefined1 uStack0000;
  
  uStack0000 = 0xd3;
  FUN_d105();
  cVar1 = '\0';
  bVar2 = 0x11;
  do {
    if (*(char *)(DAT_0020 + (ushort)bVar2) == -1) {
      return cVar1;
    }
    cVar1 = cVar1 + '\x01';
    bVar2 = bVar2 + 1;
  } while (bVar2 < 0x1b);
  return cVar1;
}



/* 0xd307 FUN_d307 */

char FUN_d307(void)

{
  char cVar1;
  byte bVar2;
  
  cVar1 = '\0';
  bVar2 = 0x11;
  do {
    if (*(char *)(DAT_0020 + (ushort)bVar2) == -1) {
      return cVar1;
    }
    cVar1 = cVar1 + '\x01';
    bVar2 = bVar2 + 1;
  } while (bVar2 < 0x1b);
  return cVar1;
}



/* 0xd319 FUN_d319 */

void FUN_d319(byte param_1)

{
  byte bVar1;
  
  bVar1 = (param_1 & 0xf) << 1;
  DAT_0024 = (&DAT_d328)[bVar1];
  DAT_0025 = (&DAT_d329)[bVar1];
  return;
}



/* 0xd336 FUN_d336 */

void FUN_d336(void)

{
  byte bVar1;
  char cVar2;
  byte bVar3;
  byte bVar4;
  
  DAT_0025 = 0;
  DAT_0026 = 0;
  DAT_0027 = 0;
  cVar2 = '\x17';
  do {
    bVar3 = (byte)DAT_0020 >> 7;
    DAT_0020._0_1_ = (byte)DAT_0020 * '\x02';
    bVar4 = DAT_0020._1_1_ >> 7;
    DAT_0020._1_1_ = DAT_0020._1_1_ << 1 | bVar3;
    bVar3 = (byte)DAT_0022 >> 7;
    DAT_0022._0_1_ = (byte)DAT_0022 << 1 | bVar4;
    bVar3 = DAT_0025 << 1 | bVar3;
    bVar4 = DAT_0026 << 1 | DAT_0025 >> 7;
    DAT_0027 = DAT_0027 << 1 | DAT_0026 >> 7;
    DAT_0028 = bVar3 - DAT_0022._1_1_;
    DAT_0029 = (bVar4 - DAT_0024) -
               (((DAT_0022._1_1_ & (~bVar3 | DAT_0028) | DAT_0028 & ~bVar3) & 0x80) == 0);
    bVar1 = DAT_0027 - (((DAT_0024 & (~bVar4 | DAT_0029) | DAT_0029 & ~bVar4) & 0x80) == 0);
    DAT_0025 = bVar3;
    DAT_0026 = bVar4;
    if ((bVar1 & ~DAT_0027 & 0x80) != 0) {
      DAT_0020._0_1_ = (byte)DAT_0020 + 1;
      DAT_0025 = DAT_0028;
      DAT_0026 = DAT_0029;
      DAT_0027 = bVar1;
    }
    cVar2 = cVar2 + -1;
  } while (-1 < cVar2);
  return;
}



/* 0xd36f FUN_d36f */

byte FUN_d36f(undefined1 param_1)

{
  byte bVar1;
  byte bVar2;
  undefined1 uVar3;
  byte bVar4;
  bool bVar5;
  undefined1 uStack0000;
  
  uStack0000 = param_1;
  FUN_d105();
  if (DAT_0024 != '\0') {
    bVar4 = FUN_d4bb();
    bVar5 = CARRY1(bVar4,(byte)DAT_0022);
    DAT_0022._0_1_ = bVar4 + (byte)DAT_0022;
    DAT_0022._1_1_ = DAT_0022._1_1_ + bVar5;
  }
  uVar3 = uStack0000;
  uStack0000 = 0xd3;
  FUN_d105(uVar3);
  uStack0000 = 0xd3;
  FUN_d69d();
  bVar1 = *(byte *)(DAT_0020 + 2) - (byte)DAT_0022;
  bVar4 = ~*(byte *)(DAT_0020 + 2);
  bVar2 = (*(byte *)(DAT_0020 + 3) - DAT_0022._1_1_) -
          ((((byte)DAT_0022 & (bVar4 | bVar1) | bVar1 & bVar4) & 0x80) == 0);
  bVar4 = ~*(byte *)(DAT_0020 + 3);
  if (((DAT_0022._1_1_ & (bVar4 | bVar2) | bVar2 & bVar4) & 0x80) == 0) {
    return bVar1;
  }
  *(byte *)(DAT_0020 + 3) = bVar2;
  *(byte *)(DAT_0020 + 2) = bVar1;
  uStack0000 = 0xd3;
  bVar4 = FUN_d69d();
  return bVar4;
}



/* 0xd3a9 FUN_d3a9 */

byte FUN_d3a9(undefined1 param_1)

{
  byte bVar1;
  byte bVar2;
  undefined1 uVar3;
  byte bVar4;
  bool bVar5;
  undefined1 uStack0000;
  
  uStack0000 = param_1;
  FUN_d105();
  if (DAT_0024 != '\0') {
    bVar4 = FUN_d4bb();
    bVar5 = CARRY1(bVar4,(byte)DAT_0022);
    DAT_0022._0_1_ = bVar4 + (byte)DAT_0022;
    DAT_0022._1_1_ = DAT_0022._1_1_ + bVar5;
  }
  uVar3 = uStack0000;
  uStack0000 = 0xd3;
  FUN_d105(uVar3);
  bVar1 = *(byte *)(DAT_0020 + 4) - (byte)DAT_0022;
  bVar4 = ~*(byte *)(DAT_0020 + 4);
  bVar2 = (*(byte *)(DAT_0020 + 5) - DAT_0022._1_1_) -
          ((((byte)DAT_0022 & (bVar4 | bVar1) | bVar1 & bVar4) & 0x80) == 0);
  bVar4 = ~*(byte *)(DAT_0020 + 5);
  if (((DAT_0022._1_1_ & (bVar4 | bVar2) | bVar2 & bVar4) & 0x80) == 0) {
    return bVar1;
  }
  *(byte *)(DAT_0020 + 5) = bVar2;
  *(byte *)(DAT_0020 + 4) = bVar1;
  return bVar1;
}



/* 0xd3dd FUN_d3dd */

void FUN_d3dd(void)

{
  byte bVar1;
  byte bVar2;
  undefined1 uStack0000;
  
  uStack0000 = 0xd3;
  FUN_d105();
  bVar1 = 0;
  do {
    (&DAT_6f73)[bVar1] = 0xff;
    bVar1 = bVar1 + 1;
  } while (bVar1 < 0x10);
  bVar2 = 0x11;
  bVar1 = 0;
  do {
    if (*(char *)(DAT_0020 + (ushort)bVar2) != -1) {
      (&DAT_6f73)[bVar1] = *(char *)(DAT_0020 + (ushort)bVar2);
      bVar1 = bVar1 + 1;
    }
    bVar2 = bVar2 + 1;
  } while (bVar2 < 0x1b);
  bVar2 = 0x11;
  bVar1 = 0;
  do {
    *(undefined1 *)(DAT_0020 + (ushort)bVar2) = (&DAT_6f73)[bVar1];
    bVar2 = bVar2 + 1;
    bVar1 = bVar1 + 1;
  } while (bVar2 < 0x1b);
  return;
}



/* 0xd40f FUN_d40f */

void FUN_d40f(void)

{
  char cVar1;
  byte bVar2;
  byte bVar3;
  
  DAT_0025 = 0;
  DAT_0026 = 0;
  cVar1 = '\x0f';
  do {
    bVar2 = DAT_0020._1_1_ >> 7;
    DAT_0020._1_1_ = DAT_0020._1_1_ * '\x02';
    bVar3 = (byte)DAT_0022 >> 7;
    DAT_0022._0_1_ = (byte)DAT_0022 << 1 | bVar2;
    bVar3 = DAT_0025 << 1 | bVar3;
    DAT_0026 = DAT_0026 << 1 | DAT_0025 >> 7;
    DAT_0027 = bVar3 - DAT_0022._1_1_;
    bVar2 = (DAT_0026 - DAT_0024) -
            (((DAT_0022._1_1_ & (~bVar3 | DAT_0027) | DAT_0027 & ~bVar3) & 0x80) == 0);
    DAT_0025 = bVar3;
    if (((DAT_0024 & (~DAT_0026 | bVar2) | bVar2 & ~DAT_0026) & 0x80) != 0) {
      DAT_0020._1_1_ = DAT_0020._1_1_ + 1;
      DAT_0025 = DAT_0027;
      DAT_0026 = bVar2;
    }
    cVar1 = cVar1 + -1;
  } while (-1 < cVar1);
  return;
}



/* 0xd438 FUN_d438 */

void FUN_d438(void)

{
  char cVar1;
  byte bVar2;
  bool bVar3;
  bool bVar4;
  byte bVar5;
  
  cVar1 = '\a';
  DAT_0024 = 0;
  DAT_0025 = 0;
  DAT_0026 = 0;
  DAT_0027 = 0;
  DAT_0028 = 0;
  DAT_0029 = '\0';
  do {
    bVar2 = DAT_0022._1_1_ & 1;
    DAT_0022._1_1_ = DAT_0022._1_1_ >> 1;
    if (bVar2 != 0) {
      bVar3 = CARRY1((byte)DAT_0020,DAT_0026);
      DAT_0026 = (byte)DAT_0020 + DAT_0026;
      bVar4 = CARRY1(DAT_0020._1_1_,DAT_0027);
      DAT_0027 = DAT_0020._1_1_ + DAT_0027 + bVar3;
      bVar3 = CARRY1((byte)DAT_0022,DAT_0028);
      DAT_0028 = (byte)DAT_0022 + DAT_0028 + bVar4;
      DAT_0029 = DAT_0024 + DAT_0029 + bVar3;
    }
    bVar2 = (byte)DAT_0020 >> 7;
    DAT_0020._0_1_ = (byte)DAT_0020 << 1;
    bVar5 = DAT_0020._1_1_ >> 7;
    DAT_0020._1_1_ = DAT_0020._1_1_ << 1 | bVar2;
    bVar2 = (byte)DAT_0022 >> 7;
    DAT_0022._0_1_ = (byte)DAT_0022 << 1 | bVar5;
    DAT_0024 = DAT_0024 << 1 | bVar2;
    cVar1 = cVar1 + -1;
  } while (-1 < cVar1);
  return;
}



/* 0xd471 FUN_d471 */

void FUN_d471(void)

{
  char cVar1;
  byte bVar2;
  bool bVar3;
  
  cVar1 = '\a';
  DAT_002c = 0;
  DAT_002a = 0;
  DAT_002b = '\0';
  do {
    bVar2 = DAT_0020._1_1_ & 1;
    DAT_0020._1_1_ = DAT_0020._1_1_ >> 1;
    if (bVar2 != 0) {
      bVar3 = CARRY1((byte)DAT_0020,DAT_002a);
      DAT_002a = (byte)DAT_0020 + DAT_002a;
      DAT_002b = DAT_002c + DAT_002b + bVar3;
    }
    bVar2 = (byte)DAT_0020 >> 7;
    DAT_0020._0_1_ = (byte)DAT_0020 << 1;
    DAT_002c = DAT_002c << 1 | bVar2;
    cVar1 = cVar1 + -1;
  } while (-1 < cVar1);
  return;
}



/* 0xd494 FUN_d494 */

/* WARNING: Globals starting with '_' overlap smaller symbols at the same address */

void FUN_d494(char param_1,undefined1 param_2)

{
  undefined1 unaff_retaddr;
  undefined1 unaff_retaddr_00;
  
  RAM0x0021 = CONCAT11(unaff_retaddr_00,unaff_retaddr);
  RAM0x0023 = (code *)CONCAT11(*(undefined1 *)(RAM0x0021 + (ushort)(byte)(param_1 * '\x02' + 2)),
                               *(undefined1 *)(RAM0x0021 + (ushort)(byte)(param_1 * '\x02' + 1)));
  DAT_0020._0_1_ = param_2;
                    /* WARNING: Could not recover jumptable at 0xd4aa. Too many branches */
                    /* WARNING: Treating indirect jump as call */
  (*RAM0x0023)(param_2);
  return;
}



/* 0xd4ad FUN_d4ad */

void FUN_d4ad(byte param_1)

{
  byte bVar1;
  undefined1 uStack0000;
  
  DAT_0056 = param_1;
  do {
    uStack0000 = 0xd4;
    bVar1 = FUN_e88a();
  } while (DAT_0056 <= (bVar1 & 0xf));
  return;
}



/* 0xd4bb FUN_d4bb */

void FUN_d4bb(byte param_1)

{
  byte bVar1;
  undefined1 uStack0000;
  
  DAT_0056 = param_1;
  if (param_1 < 0xf) {
    do {
      uStack0000 = 0xd4;
      bVar1 = FUN_e88a();
    } while (DAT_0056 <= (bVar1 & 0xf));
    return;
  }
  do {
    uStack0000 = 0xd4;
    bVar1 = FUN_e88a();
  } while (DAT_0056 <= bVar1);
  return;
}



/* 0xd4cb FUN_d4cb */

void FUN_d4cb(void)

{
  byte bVar1;
  byte bVar2;
  undefined1 uStack0000;
  
  bVar1 = 0x7f;
  do {
    *(undefined1 *)(bVar1 + 0x580) = 0;
    bVar1 = bVar1 - 1;
  } while (-1 < (char)bVar1);
  uStack0000 = 0xd4;
  FUN_f266(0x30);
  DAT_0036 = '\x1d';
  do {
    uStack0000 = 0xd4;
    bVar1 = FUN_d105(DAT_0036);
    if ((bVar1 & 7) == DAT_6f03) {
      for (DAT_0024 = DAT_0036 << 3; -1 < (char)*(byte *)(DAT_0024 + 0x9d72);
          DAT_0024 = DAT_0024 + 1) {
        uStack0000 = 0xd5;
        DAT_0025 = *(byte *)(DAT_0024 + 0x9d72);
        bVar1 = FUN_d105();
        if ((bVar1 & 7) == DAT_6f03) {
          *(byte *)((byte)(DAT_0036 + (&DAT_d5bf)[DAT_0025]) + 0x580) =
               (&DAT_d5df)[DAT_0025 & 7] |
               *(byte *)((byte)(DAT_0036 + (&DAT_d5bf)[DAT_0025]) + 0x580);
        }
      }
    }
    DAT_0036 = DAT_0036 + -1;
  } while (-1 < DAT_0036);
  bVar2 = 1;
  bVar1 = 0;
  do {
    do {
      uStack0000 = 0xd5;
      FUN_d53e();
      bVar2 = bVar2 + 1;
    } while (bVar2 < 0x1e);
    bVar2 = bVar1 + 1;
    bVar1 = bVar1 + 2;
  } while (bVar1 < 0x1d);
  return;
}



/* 0xd53e FUN_d53e */

void FUN_d53e(byte param_1,byte param_2)

{
  if ((*(byte *)(param_1 + 0x580) & *(byte *)(param_2 + 0x580)) != 0) {
    *(byte *)(param_2 + 0x580) = *(byte *)(param_1 + 0x580) | *(byte *)(param_2 + 0x580);
  }
  if ((*(byte *)(param_1 + 0x5a0) & *(byte *)(param_2 + 0x5a0)) != 0) {
    *(byte *)(param_2 + 0x5a0) = *(byte *)(param_1 + 0x5a0) | *(byte *)(param_2 + 0x5a0);
  }
  if ((*(byte *)(param_1 + 0x5c0) & *(byte *)(param_2 + 0x5c0)) != 0) {
    *(byte *)(param_2 + 0x5c0) = *(byte *)(param_1 + 0x5c0) | *(byte *)(param_2 + 0x5c0);
  }
  if ((*(byte *)(param_1 + 0x5e0) & *(byte *)(param_2 + 0x5e0)) != 0) {
    *(byte *)(param_2 + 0x5e0) = *(byte *)(param_1 + 0x5e0) | *(byte *)(param_2 + 0x5e0);
  }
  return;
}



/* 0xd583 FUN_d583 */

undefined1 FUN_d583(byte param_1,byte param_2)

{
  DAT_0031 = param_2;
  DAT_0032 = param_1;
  DAT_0030 = 0x1d;
  while (((*(byte *)((DAT_0030 | (&DAT_d5bf)[param_2]) + 0x580) & (&DAT_d5df)[param_2 & 7]) == 0 ||
         ((*(byte *)((DAT_0030 | (&DAT_d5bf)[param_1]) + 0x580) & (&DAT_d5df)[param_1 & 7]) == 0)))
  {
    DAT_0030 = DAT_0030 - 1;
    if ((char)DAT_0030 < '\0') {
      return 0;
    }
  }
  return 0xff;
}



/* 0xd5e7 FUN_d5e7 */

void FUN_d5e7(void)

{
  return;
}



/* 0xd61e FUN_d61e */

void FUN_d61e(void)

{
  return;
}



/* 0xd69d FUN_d69d */

byte FUN_d69d(void)

{
  byte bVar1;
  
  if (((*(byte *)(DAT_0020 + 3) - 0x27) -
       ((*(byte *)(DAT_0020 + 2) - 0x10 & ~*(byte *)(DAT_0020 + 2) & 0x80) == 0) &
       ~*(byte *)(DAT_0020 + 3) & 0x80) != 0) {
    *(undefined1 *)(DAT_0020 + 2) = 0xf;
    *(undefined1 *)(DAT_0020 + 3) = 0x27;
  }
  bVar1 = (*(byte *)(DAT_0020 + 5) - 0x27) -
          ((*(byte *)(DAT_0020 + 4) - 0x10 & ~*(byte *)(DAT_0020 + 4) & 0x80) == 0);
  if ((bVar1 & ~*(byte *)(DAT_0020 + 5) & 0x80) != 0) {
    *(undefined1 *)(DAT_0020 + 4) = 0xf;
    bVar1 = 0x27;
    *(undefined1 *)(DAT_0020 + 5) = 0x27;
  }
  return bVar1;
}



/* 0xd6e5 FUN_d6e5 */

void FUN_d6e5(void)

{
  return;
}



/* 0xd717 FUN_d717 */

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



/* 0xdd34 FUN_dd34 */

void FUN_dd34(void)

{
  byte bVar1;
  byte bVar2;
  undefined1 uStack0000;
  
  uStack0000 = 0xdd;
  FUN_f25f(0x21);
  bVar1 = 0;
  DAT_0012 = DAT_0542;
  do {
    bVar2 = DAT_0012 & 1;
    DAT_0012 = DAT_0012 >> 1;
    if (bVar2 != 0) {
      uStack0000 = 0xdd;
      FUN_dd53();
    }
    bVar1 = bVar1 + 1;
  } while (bVar1 < 5);
  return;
}



/* 0xdd53 FUN_dd53 */

char FUN_dd53(char param_1)

{
  char cStack0000;
  
  DAT_0000 = *(undefined1 *)((byte)(param_1 * '\x02') + 0x970c);
  DAT_0001 = *(undefined1 *)((byte)(param_1 * '\x02' + 1) + 0x970c);
  DAT_000c = 0;
  DAT_000a = 0;
  DAT_0002 = 0;
  cStack0000 = param_1;
  FUN_f1ad();
  return cStack0000;
}



/* 0xe000 reset_dispatch */

/* WARNING: Globals starting with '_' overlap smaller symbols at the same address */

void reset_dispatch(void)

{
  byte bVar1;
  char cVar2;
  
  cVar2 = '\x02';
  do {
    do {
    } while (-1 < DAT_2002);
    do {
    } while (DAT_2002 < '\0');
    cVar2 = cVar2 + -1;
  } while (-1 < cVar2);
  DAT_4010 = 0;
  DAT_4015 = 0xf;
  DAT_4017 = 0xc0;
  DAT_2000 = 0;
  DAT_2001 = 0;
  cVar2 = '\x04';
  do {
    do {
    } while (-1 < DAT_2002);
    do {
    } while (DAT_2002 < '\0');
    cVar2 = cVar2 + -1;
  } while (-1 < cVar2);
  _DAT_0001 = &DAT_0004;
  do {
    do {
      *_DAT_0001 = 0;
      cVar2 = DAT_0001 + '\x01';
      _DAT_0001 = (undefined1 *)CONCAT11(DAT_0002,cVar2);
    } while (cVar2 != '\0');
    bVar1 = DAT_0002 + 1;
    _DAT_0001 = (undefined1 *)((ushort)bVar1 << 8);
  } while (bVar1 < 8);
  *(undefined2 *)(CONCAT11((char)((ushort)&stack0x0000 >> 8),0xff) + -1) = 0xe061;
  FUN_f3bd();
  DAT_007a = 0;
  DAT_004e = (code *)CONCAT11(DAT_e07d,DAT_e07c);
                    /* WARNING: Could not recover jumptable at 0xe079. Too many branches */
                    /* WARNING: Treating indirect jump as call */
  (*DAT_004e)();
  return;
}



/* 0xe370 FUN_e370 */

void FUN_e370(void)

{
  undefined1 uStack0000;
  
  uStack0000 = 0xe3;
  FUN_f237(0x3d);
  uStack0000 = 0xe3;
  thunk_FUN_a8d7();
  uStack0000 = 0xe3;
  FUN_f206();
  return;
}



/* 0xe4da FUN_e4da */

void FUN_e4da(void)

{
  undefined1 uStack0000;
  
  uStack0000 = 0xe4;
  FUN_e768();
  uStack0000 = 0xe4;
  DAT_2001 = FUN_e74d();
  uStack0000 = 0xe4;
  FUN_e57f();
  uStack0000 = 0xe4;
  FUN_e7df();
  DAT_0090 = 0;
  DAT_0091 = 0;
  DAT_008e = 0;
  DAT_008f = 0;
  DAT_0098 = 0;
  DAT_0099 = 0;
  DAT_0096 = 0;
  DAT_0097 = 0;
  DAT_007e = 0;
  DAT_005e = 0;
  DAT_005f = 0;
  switchD_f878::caseD_f = 0;
  DAT_00a4 = 0;
  DAT_0300 = 0xff;
  DAT_0304 = 0xff;
  FUN_e823();
  return;
}



/* 0xe51f FUN_e51f */

void FUN_e51f(char param_1)

{
  byte bVar1;
  
  bVar1 = param_1 * '\b';
  DAT_00e6 = (&DAT_e567)[bVar1];
                    /* WARNING: Read-only address (RAM,0xc000) is written */
  uRAMc000 = (&DAT_e567)[bVar1];
  DAT_00e7 = (&DAT_e567)[(byte)(bVar1 + 1)];
                    /* WARNING: Read-only address (RAM,0xc800) is written */
  uRAMc800 = (&DAT_e567)[(byte)(bVar1 + 1)];
  DAT_00e8 = (&DAT_e567)[(byte)(bVar1 + 2)];
                    /* WARNING: Read-only address (RAM,0xd000) is written */
  uRAMd000 = (&DAT_e567)[(byte)(bVar1 + 2)];
  DAT_00e9 = (&DAT_e567)[(byte)(bVar1 + 3)];
  DAT_d800 = (&DAT_e567)[(byte)(bVar1 + 3)];
  DAT_00ea = (&DAT_e567)[(byte)(bVar1 + 4)];
  DAT_00eb = (&DAT_e567)[(byte)(bVar1 + 5)];
  DAT_00ec = (&DAT_e567)[(byte)(bVar1 + 6)];
  DAT_00ed = (&DAT_e567)[(byte)(bVar1 + 7)];
  return;
}



/* 0xe57f FUN_e57f */

void FUN_e57f(void)

{
  undefined1 uStack0000;
  
  uStack0000 = 0xe5;
  FUN_e673(0);
  uStack0000 = 0xe5;
  FUN_e590();
  DAT_00a5 = 0x4c;
  LAB_f800 = 0x4c;
  return;
}



/* 0xe590 FUN_e590 */

void FUN_e590(void)

{
  byte bVar1;
  char cVar2;
  undefined1 uStack0000;
  
  DAT_4015 = 0;
  DAT_07f6 = 0;
  DAT_4000 = 0x10;
  DAT_4004 = 0x10;
  DAT_400c = 0x10;
  DAT_4001 = 8;
  DAT_4005 = 8;
  DAT_4008 = 0;
  DAT_07f2 = 0;
  bVar1 = 0;
  do {
    *(undefined1 *)(bVar1 + 0x700) = 0xff;
    *(undefined1 *)(bVar1 + 0x706) = 0;
    bVar1 = bVar1 + 0x16;
  } while (bVar1 != 0xf2);
  cVar2 = '?';
  do {
    cVar2 = cVar2 + -1;
  } while (-1 < cVar2);
  LAB_f800 = 0x80;
  bVar1 = 0;
  do {
    DAT_4800 = (&DAT_e6a6)[bVar1];
    bVar1 = bVar1 + 1;
  } while (bVar1 < 0x20);
  uStack0000 = 0xe5;
  FUN_e5fa(0xf0,100);
  LAB_f800 = 0x7f;
  DAT_4800 = 0x30;
  return;
}



/* 0xe5f3 FUN_e5f3 */

void FUN_e5f3(undefined1 param_1,undefined1 param_2)

{
  LAB_f800 = param_2;
  DAT_4800 = param_1;
  return;
}



/* 0xe5fa FUN_e5fa */

undefined1 FUN_e5fa(undefined1 param_1,char param_2)

{
  undefined1 uVar1;
  undefined1 uStack0000;
  
  uStack0000 = param_1;
  do {
    uVar1 = uStack0000;
    uStack0000 = 0xe5;
    uStack0000 = FUN_e5f3(uVar1);
    param_2 = param_2 + '\b';
  } while (-1 < param_2);
  return uStack0000;
}



/* 0xe609 FUN_e609 */

undefined1 FUN_e609(undefined1 param_1)

{
  byte bVar1;
  undefined1 uStack0000;
  
  uStack0000 = 0xe6;
  bVar1 = FUN_f25f(0x22);
  DAT_00f0 = (byte *)CONCAT11(((bVar1 >> 7) << 1 | (bVar1 & 0x7f) >> 6) + 0x80,bVar1 * '\x04');
  bVar1 = *DAT_00f0;
  if ((*(char *)(bVar1 + 0x700) != -1) && (*(byte *)(bVar1 + 0x701) < 4)) {
    DAT_07f6 = (&DAT_e667)[*(byte *)(bVar1 + 0x701)] & DAT_07f6;
    DAT_4015 = DAT_07f6;
  }
  *(byte *)(bVar1 + 0x701) = DAT_00f0[1];
  *(byte *)(bVar1 + 0x702) = DAT_00f0[2];
  *(byte *)(bVar1 + 0x703) = DAT_00f0[3] + 0x40;
  *(undefined1 *)(bVar1 + 0x700) = 0;
  return param_1;
}



/* 0xe673 FUN_e673 */

void FUN_e673(char param_1)

{
  char cStack0000;
  
  cStack0000 = param_1;
  FUN_e609();
  cStack0000 = cStack0000 + '\x01';
  FUN_e609();
  cStack0000 = cStack0000 + '\x01';
  FUN_e609();
  cStack0000 = cStack0000 + '\x01';
  FUN_e609();
  cStack0000 = cStack0000 + '\x01';
  FUN_e609();
  cStack0000 = cStack0000 + '\x01';
  FUN_e609();
  FUN_e609(cStack0000 + '\x01');
  return;
}



/* 0xe6c6 FUN_e6c6 */

void FUN_e6c6(void)

{
  byte bVar1;
  byte bVar2;
  char cVar3;
  
  bVar2 = DAT_0085;
  bVar1 = DAT_0083;
  DAT_0084 = DAT_0083;
  DAT_0086 = DAT_0085;
  DAT_4016 = 0;
  cVar3 = '\a';
  do {
    DAT_0083 = DAT_0083 >> 1;
    DAT_0085 = DAT_0085 >> 1 | ((DAT_4017 & 3) != 0) << 7;
    cVar3 = cVar3 + -1;
  } while (-1 < cVar3);
  DAT_0081 = (DAT_0083 ^ bVar1) & DAT_0083;
  DAT_0082 = (DAT_0085 ^ bVar2) & DAT_0085;
  return;
}



/* 0xe70e FUN_e70e */

void FUN_e70e(void)

{
  byte bVar1;
  
  DAT_2000 = DAT_008b & 0xfb;
  bVar1 = 0;
  DAT_007d = 0;
  do {
    DAT_2007 = (&DAT_0101)[bVar1];
    bVar1 = bVar1 + 2;
  } while (bVar1 < 0x20);
  DAT_2006 = 0;
  return;
}



/* 0xe749 FUN_e749 */

/* WARNING: Removing unreachable block (RAM,0xe74d) */

void FUN_e749(void)

{
  DAT_008c = 0x1e;
  return;
}



/* 0xe74d FUN_e74d */

void FUN_e74d(void)

{
  DAT_008c = 0;
  return;
}



/* 0xe753 FUN_e753 */

void FUN_e753(void)

{
  DAT_007b = 0;
  DAT_007e = 0;
  DAT_2000 = DAT_008b | 0x80;
  if (DAT_2000 == 0) {
    DAT_2000 = DAT_008b & 0x7f;
  }
  DAT_008b = DAT_2000;
  return;
}



/* 0xe768 FUN_e768 */

void FUN_e768(void)

{
  DAT_008b = DAT_008b & 0x7f;
  DAT_2000 = DAT_008b;
  return;
}



/* 0xe7b5 FUN_e7b5 */

void FUN_e7b5(void)

{
  char cVar1;
  byte bVar2;
  
  DAT_2006 = 0;
  cVar1 = '\0';
  DAT_0001 = '\x03';
  do {
    do {
      cVar1 = cVar1 + -1;
    } while (cVar1 != '\0');
    DAT_0001 = DAT_0001 + -1;
    bVar2 = 0;
  } while (DAT_0001 != '\0');
  do {
    bVar2 = bVar2 + 1;
  } while (bVar2 < 0xc0);
  do {
    DAT_2007 = DAT_0003;
    bVar2 = bVar2 + 1;
  } while (bVar2 != 0);
  return;
}



/* 0xe7df FUN_e7df */

void FUN_e7df(void)

{
  undefined1 uStack0000;
  
                    /* WARNING: Read-only address (RAM,0xc000) is written */
  uRAMc000 = 0xe0;
                    /* WARNING: Read-only address (RAM,0xc800) is written */
  uRAMc800 = 0xe1;
                    /* WARNING: Read-only address (RAM,0xd000) is written */
  uRAMd000 = 0xe0;
  DAT_d800 = 0xe1;
  DAT_0002 = 1;
  DAT_0003 = 0xaa;
  uStack0000 = 0xe8;
  FUN_e7b5(0x20);
  DAT_0002 = 1;
  DAT_0003 = 0xaa;
  uStack0000 = 0xe8;
  FUN_e7b5(0x24);
  DAT_0002 = 1;
  DAT_0003 = 0xaa;
  FUN_e7b5(0x28);
  return;
}



/* 0xe823 FUN_e823 */

void FUN_e823(void)

{
  byte bVar1;
  
  bVar1 = 0;
  do {
    *(undefined1 *)(bVar1 + 0x200) = 0xf0;
    bVar1 = bVar1 + 1;
  } while (bVar1 != 0);
  return;
}



/* 0xe830 FUN_e830 */

void FUN_e830(void)

{
  byte bVar1;
  
  bVar1 = DAT_007c;
  if (DAT_007c != 0xff) {
    do {
      *(undefined1 *)(bVar1 + 0x200) = 0xf0;
      bVar1 = bVar1 + 4;
    } while (bVar1 != 0);
  }
  return;
}



/* 0xe88a FUN_e88a */

undefined1 FUN_e88a(undefined1 param_1)

{
  ushort uVar1;
  
  DAT_0053 = param_1;
  uVar1 = (ushort)DAT_0052;
  DAT_0052 = DAT_0052 + 1;
  return (&DAT_e8ba)[uVar1];
}



/* 0xe89a FUN_e89a */

undefined1 FUN_e89a(undefined1 param_1)

{
  ushort uVar1;
  
  DAT_0053 = param_1;
  uVar1 = (ushort)DAT_0054;
  DAT_0054 = DAT_0054 + 1;
  return (&DAT_e8ba)[uVar1];
}



/* 0xeade tail_dispatch_inline_table */

/* WARNING: Globals starting with '_' overlap smaller symbols at the same address */

void tail_dispatch_inline_table(char param_1,undefined1 param_2)

{
  undefined1 unaff_retaddr;
  undefined1 unaff_retaddr_00;
  
  _DAT_0001 = CONCAT11(unaff_retaddr_00,unaff_retaddr);
  _DAT_0003 = (code *)CONCAT11(*(undefined1 *)(_DAT_0001 + (ushort)(byte)(param_1 * '\x02' + 2)),
                               *(undefined1 *)(_DAT_0001 + (ushort)(byte)(param_1 * '\x02' + 1)));
  DAT_0000 = param_2;
                    /* WARNING: Could not recover jumptable at 0xeaf4. Too many branches */
                    /* WARNING: Treating indirect jump as call */
  (*_DAT_0003)(param_2);
  return;
}



/* 0xeaf7 FUN_eaf7 */

void FUN_eaf7(void)

{
  DAT_2005 = DAT_0090;
  DAT_008b = DAT_008f & 1 | DAT_008b & 0xfe;
  DAT_2000 = DAT_008b;
  return;
}



/* 0xec67 FUN_ec67 */

/* WARNING: Globals starting with '_' overlap smaller symbols at the same address */

void FUN_ec67(void)

{
  char cVar1;
  byte bVar2;
  byte bVar3;
  
  if (DAT_0087 < '\0') {
    return;
  }
  if (-1 < (char)(DAT_008a + -1)) {
    DAT_008a = DAT_008a + -1;
    return;
  }
  DAT_008a = DAT_0089;
  DAT_007d = 1;
  if (DAT_0087 == '\0') {
    DAT_0088 = DAT_0088 - 1;
    if (DAT_0088 != 0) goto LAB_ec98;
  }
  else {
    DAT_0088 = DAT_0088 + 1;
    if (DAT_0088 < 4) goto LAB_ec98;
  }
  DAT_0087 = -1;
LAB_ec98:
  _DAT_0000 = 0x100;
  _DAT_0002 = &DAT_0120;
  bVar3 = 0x1f;
  do {
    cVar1 = _DAT_0002[bVar3];
    bVar2 = DAT_0088;
    do {
      bVar2 = bVar2 - 1;
      if ((char)bVar2 < '\0') goto LAB_ecb9;
      cVar1 = cVar1 + -0x10;
    } while (-1 < cVar1);
    cVar1 = '\x0f';
LAB_ecb9:
    *(char *)(_DAT_0000 + (ushort)bVar3) = cVar1;
    bVar3 = bVar3 - 1;
    if ((char)bVar3 < '\0') {
      return;
    }
  } while( true );
}



/* 0xecbf FUN_ecbf */

/* WARNING: Globals starting with '_' overlap smaller symbols at the same address */

void FUN_ecbf(void)

{
  byte bVar1;
  
  DAT_0087 = 0;
  DAT_0088 = 4;
  DAT_0089 = 4;
  _DAT_0000 = 0x100;
  _DAT_0002 = &DAT_0120;
  bVar1 = 0;
  do {
    _DAT_0002[bVar1] = *(undefined1 *)(_DAT_0000 + (ushort)bVar1);
    *(undefined1 *)(_DAT_0000 + (ushort)bVar1) = 0xf;
    bVar1 = bVar1 + 1;
  } while (bVar1 < 0x20);
  return;
}



/* 0xee07 far_call_inline_word */

/* WARNING: Globals starting with '_' overlap smaller symbols at the same address */

void far_call_inline_word(undefined1 param_1)

{
  undefined1 uStack0000;
  byte bStack0001;
  char cStack0002;
  
  DAT_0058 = DAT_00e2;
  _DAT_0059 = (undefined2 *)CONCAT11(cStack0002 + (0xfe < bStack0001),bStack0001 + 1);
  DAT_005b = (code *)*_DAT_0059;
  DAT_005d = param_1;
  FUN_f237(param_1);
  if ((char)(DAT_0059 + '\x01') == '\0') {
    DAT_005a = DAT_005a + '\x01';
  }
  uStack0000 = DAT_0058;
  DAT_0059 = DAT_0059 + '\x01';
                    /* WARNING: Could not recover jumptable at 0xee4a. Too many branches */
                    /* WARNING: Treating indirect jump as call */
  (*DAT_005b)();
  return;
}



/* 0xee53 FUN_ee53 */

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



/* 0xef0b FUN_ef0b */

void FUN_ef0b(void)

{
  byte bVar1;
  
  DAT_0001 = (((DAT_0140 & 3) << 1 | DAT_0141 >> 7) << 1 | (DAT_0141 & 0x7f) >> 6) << 1 |
             (DAT_0141 & 0x3f) >> 5;
  DAT_0000 = 0x1e - DAT_0001;
  DAT_2000 = DAT_008b | 4;
  bVar1 = 0;
  do {
    DAT_2007 = (&DAT_0142)[bVar1];
    bVar1 = bVar1 + 1;
  } while (bVar1 < DAT_0000);
  DAT_2006 = DAT_0141 & 0x1f;
  do {
    if (0x1d < bVar1) {
      return;
    }
    DAT_2007 = (&DAT_0142)[bVar1];
    bVar1 = bVar1 + 1;
  } while (bVar1 != 0);
  return;
}



/* 0xef71 FUN_ef71 */

void FUN_ef71(void)

{
  byte bVar1;
  
  DAT_2000 = DAT_008b & 0xfb;
  DAT_0000 = 0x20 - (DAT_0165 & 0x1f);
  bVar1 = 0;
  do {
    DAT_2007 = (&DAT_0166)[bVar1];
    bVar1 = bVar1 + 1;
  } while (bVar1 < DAT_0000);
  DAT_2006 = DAT_0165 & 0xe0;
  do {
    if (0x1f < bVar1) {
      return;
    }
    DAT_2007 = (&DAT_0166)[bVar1];
    bVar1 = bVar1 + 1;
  } while (bVar1 != 0);
  return;
}



/* 0xefc0 FUN_efc0 */

void FUN_efc0(void)

{
  byte bVar1;
  byte bVar2;
  
  DAT_0001 = DAT_0189;
  DAT_0000 = 8 - ((DAT_0189 & 0x38) >> 3);
  bVar2 = 0;
  do {
    DAT_2006 = DAT_0001;
    DAT_2007 = (&DAT_018a)[bVar2];
    DAT_0001 = DAT_0001 + 8;
    bVar2 = bVar2 + 1;
  } while (bVar2 < DAT_0000);
  bVar1 = DAT_0189 & 199;
  do {
    DAT_0001 = bVar1;
    if (7 < bVar2) {
      return;
    }
    DAT_2006 = DAT_0001;
    DAT_2007 = (&DAT_018a)[bVar2];
    bVar2 = bVar2 + 1;
    bVar1 = DAT_0001 + 8;
  } while (bVar2 != 0);
  DAT_0001 = DAT_0001 + 8;
  return;
}



/* 0xf028 FUN_f028 */

void FUN_f028(void)

{
  byte bVar1;
  
  DAT_2000 = DAT_008b & 0xfb;
  DAT_0000 = 8 - (DAT_019d & 7);
  bVar1 = 0;
  do {
    DAT_2007 = (&DAT_019e)[bVar1];
    bVar1 = bVar1 + 1;
  } while (bVar1 < DAT_0000);
  DAT_2006 = DAT_019d & 0xf8;
  do {
    if (7 < bVar1) {
      return;
    }
    DAT_2007 = (&DAT_019e)[bVar1];
    bVar1 = bVar1 + 1;
  } while (bVar1 != 0);
  return;
}



/* 0xf077 FUN_f077 */

void FUN_f077(void)

{
  if (((DAT_009c ^ DAT_009d) & 0xc0) != 0) {
    DAT_0095 = 0xff;
  }
  if (((DAT_009c ^ DAT_009d) & 0x30) != 0) {
    DAT_0094 = 0xff;
  }
  return;
}



/* 0xf1ad FUN_f1ad */

/* WARNING: Globals starting with '_' overlap smaller symbols at the same address */

void FUN_f1ad(void)

{
  byte bVar1;
  byte bVar2;
  
  DAT_0003 = '\0';
  DAT_0004 = 0;
  bVar2 = 0;
  do {
    if (DAT_007c == 0xff) {
      return;
    }
    while( true ) {
      if (*(char *)(_DAT_0000 + (ushort)bVar2) == -0x80) {
        return;
      }
      bVar1 = *(char *)(_DAT_0000 + (ushort)bVar2) + DAT_000a;
      if (DAT_0004 <= bVar1) break;
      bVar2 = bVar2 + 4;
    }
    *(byte *)(DAT_007c + 0x200) = bVar1;
    *(char *)(DAT_007c + 0x201) = *(char *)(_DAT_0000 + (ushort)(byte)(bVar2 + 1)) + DAT_0003;
    *(byte *)(DAT_007c + 0x202) = *(byte *)(_DAT_0000 + (ushort)(byte)(bVar2 + 2)) ^ DAT_0002;
    *(char *)(DAT_007c + 0x203) = *(char *)(_DAT_0000 + (ushort)(byte)(bVar2 + 3)) + DAT_000c;
    bVar2 = bVar2 + 4;
    DAT_007c = DAT_007c + 4;
  } while (DAT_007c != 0);
  DAT_007c = 0xff;
  return;
}



/* 0xf206 FUN_f206 */

void FUN_f206(void)

{
  DAT_8000 = DAT_00ae;
  DAT_8800 = DAT_00af;
  DAT_9000 = DAT_00b0;
  DAT_9800 = DAT_00b1;
  bank10_entry_00 = DAT_00b2;
  DAT_a800 = DAT_00b3;
                    /* WARNING: Read-only address (RAM,0xb000) is written */
  uRAMb000 = DAT_00b4;
  DAT_b800 = DAT_00b5;
  return;
}



/* 0xf237 FUN_f237 */

undefined1 FUN_f237(undefined1 param_1,byte param_2)

{
  DAT_00e2 = param_2;
  DAT_00e3 = param_2 + 1;
                    /* WARNING: Read-only address (RAM,0xf000) is written */
  cRAMf000 = param_2 + 1;
                    /* WARNING: Read-only address (RAM,0xe800) is written */
  bRAMe800 = param_2 | 0xc0;
  return param_1;
}



/* 0xf25f FUN_f25f */

void FUN_f25f(code param_1)

{
  DAT_00e1 = param_1;
  reset_dispatch = param_1;
  return;
}



/* 0xf266 FUN_f266 */

void FUN_f266(code param_1)

{
  DAT_00de = param_1;
  reset_dispatch = param_1;
  return;
}



/* 0xf2af region_address */

void region_address(byte param_1)

{
  DAT_0000 = param_1 * ' ';
  DAT_0001 = (((((param_1 >> 7) << 1 | (param_1 & 0x7f) >> 6) << 1 | (param_1 & 0x3f) >> 5) << 1 |
              (param_1 & 0x1f) >> 4) << 1 | (param_1 & 0xf) >> 3) + 0x60;
  return;
}



/* 0xf2d7 officer_address */

void officer_address(byte param_1)

{
  DAT_0000 = param_1 * '\f' - 0x40;
  DAT_0001 = (((CARRY1(param_1 * '\x02',param_1) - ((char)param_1 >> 7)) * '\x02' |
              (byte)(param_1 * '\x03') >> 7) << 1 | (param_1 * '\x03' & 0x7f) >> 6) + 99 +
             (0x3f < (byte)(param_1 * '\f'));
  return;
}



/* 0xf3bd FUN_f3bd */

void FUN_f3bd(void)

{
  byte bVar1;
  char cVar2;
  bool bVar3;
  undefined1 uStack0000;
  
  DAT_5000 = 0;
  DAT_5800 = 0;
                    /* WARNING: Read-only address (RAM,0xc000) is written */
  uRAMc000 = 0xe0;
                    /* WARNING: Read-only address (RAM,0xd000) is written */
  uRAMd000 = 0xe0;
                    /* WARNING: Read-only address (RAM,0xc800) is written */
  uRAMc800 = 0xe1;
  DAT_d800 = 0xe1;
  bVar1 = 0;
  do {
    DAT_0001 = (byte)FUN_f3bd[bVar1] & 1;
    DAT_4016 = DAT_0001;
    if (((DAT_4017 >> 1 ^ 0xff) & 1) != DAT_0001) {
      return;
    }
    bVar1 = bVar1 + 1;
  } while (bVar1 != 0x46);
  LAB_f800 = 0x40;
  bVar3 = false;
  uStack0000 = 0xf3;
  FUN_f422();
  if (!bVar3) {
    uStack0000 = 0xf4;
    FUN_f43f();
    uStack0000 = 0xf4;
    FUN_f422();
  }
  cVar2 = '\0';
  do {
    cVar2 = cVar2 + '\x01';
  } while (cVar2 != ' ');
  do {
                    /* WARNING: Do nothing block with infinite loop */
  } while( true );
}



/* 0xf422 FUN_f422 */

/* WARNING: Globals starting with '_' overlap smaller symbols at the same address */

char FUN_f422(byte param_1)

{
  char cVar1;
  undefined1 uStack0000;
  
  uStack0000 = 0xf4;
  FUN_f458();
  do {
    do {
      if (*(char *)(_DAT_0002 + (ushort)param_1) != DAT_0000) {
        return *(char *)(_DAT_0002 + (ushort)param_1);
      }
      uStack0000 = 0xf4;
      FUN_f468();
      param_1 = param_1 + 1;
    } while (param_1 != 0);
    cVar1 = DAT_0003 + '\x01';
    _DAT_0002 = CONCAT11(cVar1,DAT_0002);
  } while (cVar1 != -0x80);
  return '\0';
}



/* 0xf43f FUN_f43f */

/* WARNING: Globals starting with '_' overlap smaller symbols at the same address */

void FUN_f43f(byte param_1)

{
  char cVar1;
  undefined1 uStack0000;
  
  uStack0000 = 0xf4;
  FUN_f458();
  do {
    do {
      *(undefined1 *)(_DAT_0002 + (ushort)param_1) = DAT_0000;
      uStack0000 = 0xf4;
      FUN_f468();
      param_1 = param_1 + 1;
    } while (param_1 != 0);
    cVar1 = DAT_0003 + '\x01';
    _DAT_0002 = CONCAT11(cVar1,DAT_0002);
  } while (cVar1 != -0x80);
  return;
}



/* 0xf458 FUN_f458 */

void FUN_f458(void)

{
  DAT_0002 = 0;
  DAT_0003 = 0x60;
  DAT_0000 = 0xaa;
  return;
}



/* 0xf468 FUN_f468 */

void FUN_f468(void)

{
  do {
    DAT_0000 = DAT_0000 * '\x05' + '\x01';
  } while (DAT_0000 == '\0');
  return;
}



/* 0xf8af FUN_f8af */

undefined1 FUN_f8af(void)

{
  undefined1 in_stack_00000003;
  
  return in_stack_00000003;
}



/* 0xfa97 switchD_f878::caseD_0 */

undefined1 switchD_f878::caseD_0(void)

{
  undefined1 uStack0000;
  undefined1 in_stack_00000003;
  
  uStack0000 = 0xfa;
  FUN_fb0b();
  uStack0000 = 0xfa;
  FUN_f206();
  uStack0000 = 0xfa;
  FUN_e6c6();
  uStack0000 = 0xfa;
  FUN_ff62();
  uStack0000 = 0xfa;
  FUN_fb28();
  DAT_007b = DAT_007b + -1;
  reset_dispatch = DAT_00de;
                    /* WARNING: Read-only address (RAM,0xe800) is written */
  bRAMe800 = bRAM00df | 0xc0;
                    /* WARNING: Read-only address (RAM,0xf000) is written */
  uRAMf000 = uRAM00e0;
  cRAM0050 = cRAM0050 + '\x01';
  DAT_0052 = DAT_0052 + '\x01';
  DAT_0054 = DAT_0054 + '\x01';
  cRAM0055 = cRAM0055 + '\x01';
  DAT_005e = DAT_005e + '\x01';
  if (DAT_005e == '\0') {
    DAT_005f = DAT_005f + '\x01';
  }
  return in_stack_00000003;
}



/* 0xfaa9 FUN_faa9 */

void FUN_faa9(void)

{
  undefined1 uVar1;
  undefined1 uVar2;
  
  uVar2 = DAT_0083;
  uVar1 = DAT_0081;
  if (DAT_6f44 != '\0') {
    DAT_0081 = DAT_0082;
    DAT_0082 = uVar1;
    DAT_0083 = DAT_0085;
    DAT_0085 = uVar2;
  }
  return;
}



/* 0xfabf FUN_fabf */

void FUN_fabf(void)

{
  undefined1 uVar1;
  undefined1 uVar2;
  
  uVar2 = DAT_0085;
  uVar1 = DAT_0082;
  if (DAT_6f44 != '\0') {
    DAT_0082 = DAT_0081;
    DAT_0081 = uVar1;
    DAT_0085 = DAT_0083;
    DAT_0083 = uVar2;
  }
  return;
}



/* 0xfad5 FUN_fad5 */

void FUN_fad5(void)

{
  code cVar1;
  byte bVar2;
  undefined1 uStack0000;
  
  uStack0000 = 0xfa;
  FUN_f206();
  uStack0000 = 0xfa;
  FUN_fb0b();
  bVar2 = DAT_00e2;
  cVar1 = DAT_00e1;
  uStack0000 = DAT_00e3;
  FUN_f237(0x2e);
  thunk_FUN_d717();
  LAB_f800 = DAT_00a5;
  reset_dispatch = cVar1;
  bRAMe800 = bVar2 | 0xc0;
                    /* WARNING: Read-only address (RAM,0xe800) is written */
  DAT_00e3 = uStack0000;
                    /* WARNING: Read-only address (RAM,0xf000) is written */
  uRAMf000 = uStack0000;
  uStack0000 = 0xfb;
  DAT_00e1 = cVar1;
  DAT_00e2 = bVar2;
  FUN_fb28();
  FUN_f8af();
  return;
}



/* 0xfb0b FUN_fb0b */

void FUN_fb0b(void)

{
  undefined1 uStack0000;
  
  uStack0000 = 0xfb;
  FUN_eaf7();
                    /* WARNING: Read-only address (RAM,0xc000) is written */
  uRAMc000 = DAT_00e6;
                    /* WARNING: Read-only address (RAM,0xc800) is written */
  uRAMc800 = DAT_00e7;
                    /* WARNING: Read-only address (RAM,0xd000) is written */
  uRAMd000 = DAT_00e8;
  DAT_d800 = DAT_00e9;
  do {
  } while ((DAT_2002 & 0x40) == 0x40);
  return;
}



/* 0xfb28 FUN_fb28 */

void FUN_fb28(void)

{
  do {
  } while (DAT_0062 != '\0');
  return;
}



/* 0xfb2d FUN_fb2d */

undefined1 FUN_fb2d(undefined1 param_1)

{
  byte bVar1;
  char cVar2;
  char cVar3;
  
  if ((DAT_5800 & 0x7f) != 0x7f) {
    do {
                    /* WARNING: Do nothing block with infinite loop */
    } while( true );
  }
  if (DAT_0060 == '\0') {
    DAT_0062 = 0;
    DAT_5000 = 0;
    DAT_5800 = 0;
    uRAMb000 = 0xad;
    uRAMc000 = 0xd4;
    uRAMc700 = 0x73;
    uRAMc800 = 0x7a;
    uRAMd000 = 0xb0;
    return param_1;
  }
  if (DAT_0060 != '\x01') {
    if (DAT_0060 == '\x02') {
      cVar2 = '\b';
      do {
        cVar2 = cVar2 + -1;
      } while (-1 < cVar2);
      bVar1 = (DAT_0099 & 7) << 1;
      DAT_0046 = (&DAT_fd1a)[bVar1];
      DAT_0047 = (&DAT_fd1b)[bVar1];
                    /* WARNING: Read-only address (RAM,0xb000) is written */
      do {
        DAT_0046 = DAT_0046 + -1;
      } while (DAT_0046 != '\0');
      do {
        DAT_0047 = DAT_0047 + -1;
      } while (DAT_0047 != '\0');
                    /* WARNING: Read-only address (RAM,0xb000) is written */
      cVar2 = '\x1b';
      do {
        cVar2 = cVar2 + -1;
      } while (cVar2 != '\0');
      DAT_0046 = 0;
      DAT_0047 = 0;
      DAT_0062 = 0;
      DAT_2005 = DAT_0096;
      DAT_2006 = DAT_009a;
      DAT_5000 = 0;
      DAT_5800 = 0;
      DAT_8000 = DAT_00b6;
      DAT_8800 = DAT_00b7;
      DAT_9000 = DAT_00b8;
      DAT_9800 = DAT_00b9;
      bank10_entry_00 = DAT_00ba;
      DAT_a800 = DAT_00bb;
      uRAMb000 = DAT_00bc;
      DAT_b800 = DAT_00bd;
      uRAMc000 = 0xd4;
      uRAMc700 = DAT_00ea;
      uRAMc800 = 0x7a;
      uRAMd000 = 0xb0;
      return param_1;
    }
    if (DAT_0060 != '\x03') {
      cVar2 = DAT_0072;
      if (DAT_0060 == '\x04') {
        do {
          cVar2 = cVar2 + -1;
          cVar3 = DAT_0073;
        } while (-1 < cVar2);
        do {
          cVar3 = cVar3 + -1;
          cVar2 = DAT_0074;
        } while (-1 < cVar3);
        do {
          cVar2 = cVar2 + -1;
        } while (-1 < cVar2);
        DAT_0062 = 0;
        DAT_2005 = DAT_0096;
        DAT_2006 = DAT_009a;
        DAT_5000 = 0;
        DAT_5800 = 0;
        DAT_8000 = DAT_00b6;
        DAT_8800 = DAT_00b7;
        DAT_9000 = DAT_00b8;
        DAT_9800 = DAT_00b9;
        bank10_entry_00 = DAT_00ba;
        DAT_a800 = DAT_00bb;
        uRAMb000 = DAT_00bc;
        DAT_b800 = DAT_00bd;
        uRAMc000 = 0xd4;
        uRAMc700 = DAT_00ea;
        uRAMc800 = 0x7a;
        uRAMd000 = 0xb0;
        return param_1;
      }
      if (DAT_0060 == '\x05') {
LAB_fd95:
                    /* WARNING: Read-only address (RAM,0xc700) is written */
                    /* WARNING: Read-only address (RAM,0xd000) is written */
                    /* WARNING: Read-only address (RAM,0xc800) is written */
                    /* WARNING: Read-only address (RAM,0xb000) is written */
        cVar2 = '0';
        do {
          cVar2 = cVar2 + -1;
        } while (-1 < cVar2);
        DAT_0062 = 0;
        DAT_2005 = DAT_0096;
        DAT_2006 = DAT_009a;
        DAT_5000 = 0;
        DAT_5800 = 0;
        DAT_8000 = DAT_00b6;
        DAT_8800 = DAT_00b7;
        DAT_9000 = DAT_00b8;
        DAT_9800 = DAT_00b9;
        bank10_entry_00 = DAT_00ba;
        DAT_a800 = DAT_00bb;
        uRAMb000 = DAT_00bc;
        DAT_b800 = DAT_00bd;
        uRAMc000 = 0xd4;
        uRAMc700 = 0xe1;
        uRAMc800 = 0xe1;
        uRAMd000 = 0xe1;
        DAT_d800 = 0xe1;
        return param_1;
      }
      if (DAT_0060 == '\x06') {
        DAT_0062 = 0;
        DAT_5000 = 0;
        DAT_5800 = 0;
        uRAMb000 = 0xad;
        uRAMc000 = 0xd4;
        uRAMc700 = 0x73;
        uRAMc800 = 0x7a;
        uRAMd000 = 0xb0;
        return param_1;
      }
      if (DAT_0060 == '\a') {
        DAT_5000 = *(undefined1 *)((byte)(DAT_0063 << 1) + 0x6a);
        DAT_5800 = *(undefined1 *)((byte)(DAT_0063 << 1) + 0x6b);
        if (DAT_0063 == '\0') {
                    /* WARNING: Read-only address (RAM,0xc700) is written */
          uRAMc700 = 0xe1;
                    /* WARNING: Read-only address (RAM,0xd000) is written */
          uRAMd000 = 0xe1;
                    /* WARNING: Read-only address (RAM,0xc800) is written */
          uRAMc800 = 0xe1;
          DAT_d800 = 0xe1;
          DAT_2006 = 0xb8;
                    /* WARNING: Read-only address (RAM,0xb000) is written */
          DAT_2005 = 0;
          goto LAB_fbce;
        }
        if (DAT_0063 == '\x01') goto LAB_fbfc;
        if (DAT_0063 != '\x02') {
          DAT_0063 = '\0';
          goto LAB_fd95;
        }
        goto LAB_fc2a;
      }
      if (DAT_0060 == '\b') {
        DAT_5000 = *(undefined1 *)((byte)(DAT_0063 << 1) + 0x6a);
        DAT_5800 = *(undefined1 *)((byte)(DAT_0063 << 1) + 0x6b);
        if (DAT_0063 == '\0') goto LAB_fbce;
        if (DAT_0063 == '\x01') goto LAB_fbfc;
        if (DAT_0063 == '\x02') goto LAB_fc2a;
        goto LAB_fc58;
      }
      if (DAT_0060 == '\t') {
        DAT_0062 = 0;
        DAT_5000 = 0;
        DAT_5800 = 0;
        DAT_8000 = DAT_00b6;
        DAT_8800 = DAT_00b7;
        DAT_9000 = DAT_00b8;
        DAT_9800 = DAT_00b9;
        bank10_entry_00 = DAT_00ba;
        DAT_a800 = DAT_00bb;
        uRAMb000 = DAT_00bc;
        DAT_b800 = DAT_00bd;
        uRAMc000 = 0xd4;
        uRAMc700 = 0x73;
        uRAMc800 = 0x7a;
        uRAMd000 = 0xb0;
        return param_1;
      }
      if (DAT_0060 == '\n') {
                    /* WARNING: Read-only address (RAM,0xc000) is written */
                    /* WARNING: Read-only address (RAM,0xb000) is written */
        cVar2 = '\x10';
        do {
          cVar2 = cVar2 + -1;
        } while (-1 < cVar2);
        DAT_0062 = 0;
        DAT_2005 = 0;
        DAT_2006 = DAT_009a;
        DAT_5000 = 0;
        DAT_5800 = 0;
        DAT_8000 = DAT_00b6;
        DAT_8800 = DAT_00b7;
        DAT_9000 = DAT_00b8;
        DAT_9800 = DAT_00b9;
        bank10_entry_00 = DAT_00ba;
        DAT_a800 = DAT_00bb;
        uRAMb000 = DAT_00bc;
        DAT_b800 = DAT_00bd;
        uRAMc000 = DAT_00ea;
        uRAMc700 = 0x73;
        uRAMc800 = 0x7a;
        uRAMd000 = 0xb0;
        return param_1;
      }
      if (DAT_0060 == '\v') {
        DAT_5000 = DAT_006a;
        DAT_5800 = DAT_006b;
        DAT_0060 = '\f';
        goto LAB_fbce;
      }
      if (DAT_0060 != '\f') {
        DAT_0062 = 0;
        DAT_5000 = 0;
        DAT_5800 = 0;
        uRAMb000 = 0xad;
        uRAMc000 = 0xd4;
        uRAMc700 = 0x73;
        uRAMc800 = 0x7a;
        uRAMd000 = 0xb0;
        return param_1;
      }
      DAT_5000 = DAT_006c;
      DAT_5800 = DAT_006d;
      DAT_0060 = '\n';
      goto LAB_fbfc;
    }
  }
  DAT_5000 = *(undefined1 *)((byte)(DAT_0063 << 1) + 0x6a);
  DAT_5800 = *(undefined1 *)((byte)(DAT_0063 << 1) + 0x6b);
  if (DAT_0063 == '\0') {
LAB_fbce:
                    /* WARNING: Read-only address (RAM,0xb000) is written */
    DAT_0063 = DAT_0063 + '\x01';
    DAT_8000 = DAT_00be;
    DAT_8800 = DAT_00bf;
    DAT_9000 = DAT_00c0;
    DAT_9800 = DAT_00c1;
    bank10_entry_00 = DAT_00c2;
    DAT_a800 = DAT_00c3;
    uRAMb000 = DAT_00c4;
    DAT_b800 = DAT_00c5;
    uRAMc000 = 0xd4;
    return param_1;
  }
  if (DAT_0063 != '\x01') {
    if (DAT_0063 != '\x02') {
LAB_fc58:
                    /* WARNING: Read-only address (RAM,0xb000) is written */
      DAT_0060 = DAT_0060 + '\x01';
      DAT_0063 = 0;
      DAT_8000 = DAT_00d6;
      DAT_8800 = DAT_00d7;
      DAT_9000 = DAT_00d8;
      DAT_9800 = DAT_00d9;
      bank10_entry_00 = DAT_00da;
      DAT_a800 = DAT_00db;
      uRAMb000 = DAT_00dc;
      DAT_b800 = DAT_00dd;
      uRAMc000 = 0xd4;
      uRAMc700 = 0x73;
      uRAMc800 = 0x7a;
      uRAMd000 = 0xb0;
      return param_1;
    }
LAB_fc2a:
                    /* WARNING: Read-only address (RAM,0xb000) is written */
    DAT_0063 = DAT_0063 + '\x01';
    DAT_8000 = DAT_00ce;
    DAT_8800 = DAT_00cf;
    DAT_9000 = DAT_00d0;
    DAT_9800 = DAT_00d1;
    bank10_entry_00 = DAT_00d2;
    DAT_a800 = DAT_00d3;
    uRAMb000 = DAT_00d4;
    DAT_b800 = DAT_00d5;
    uRAMc000 = 0xd4;
    uRAMc700 = 0x73;
    uRAMc800 = 0x7a;
    uRAMd000 = 0xb0;
    return param_1;
  }
LAB_fbfc:
                    /* WARNING: Read-only address (RAM,0xb000) is written */
  uRAMd000 = 0xb0;
  uRAMc800 = 0x7a;
  uRAMc700 = 0x73;
  uRAMc000 = 0xd4;
  DAT_b800 = DAT_00cd;
  uRAMb000 = DAT_00cc;
  DAT_a800 = DAT_00cb;
  bank10_entry_00 = DAT_00ca;
  DAT_9800 = DAT_00c9;
  DAT_9000 = DAT_00c8;
  DAT_8800 = DAT_00c7;
  DAT_8000 = DAT_00c6;
  DAT_0063 = DAT_0063 + '\x01';
                    /* WARNING: Read-only address (RAM,0xb000) is written */
                    /* WARNING: Read-only address (RAM,0xc000) is written */
                    /* WARNING: Read-only address (RAM,0xc700) is written */
                    /* WARNING: Read-only address (RAM,0xc800) is written */
                    /* WARNING: Read-only address (RAM,0xd000) is written */
  return param_1;
}



/* 0xff62 FUN_ff62 */

void FUN_ff62(void)

{
  DAT_0099 = DAT_0098;
  DAT_0047 = (DAT_0098 >> 7) << 1 | (DAT_0098 & 0x78) >> 6;
  DAT_009a = (DAT_0098 & 0xf8) << 2;
  DAT_009b = DAT_0047 + 0x20;
  DAT_00ea = 0xe0;
  DAT_00ec = 0xe0;
  if ((DAT_0097 & 1) != 0) {
    DAT_00ea = 0xe1;
    DAT_00ec = 0xe1;
  }
  return;
}



/* 0xff9b FUN_ff9b */

void FUN_ff9b(void)

{
  DAT_0099 = DAT_0098;
  DAT_0047 = (DAT_0098 >> 7) << 1 | (DAT_0098 & 0x78) >> 6;
  DAT_009a = (DAT_0098 & 0xf8) << 2;
  DAT_009b = DAT_0047 + 0x20;
  DAT_00ea = 0xe0;
  if ((DAT_0097 & 1) != 0) {
    DAT_009b = DAT_0047 + 0x24;
    DAT_00ea = 0xe1;
  }
  return;
}



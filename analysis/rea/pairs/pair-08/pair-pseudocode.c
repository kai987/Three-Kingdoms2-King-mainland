// Ghidra-generated fixed-bank-pair pseudocode. Bank switching and inline pointer dispatch need manual correction. Not original source.

/* 0xa000 bank8_entry_00 */

void bank8_entry_00(void)

{
  byte bVar1;
  byte bVar2;
  bool bVar3;
  
  if (DAT_6f8b == -1) {
    return;
  }
  if (DAT_6f8b == '\x01') {
    FUN_b933();
    return;
  }
  do {
    if (0x13 < DAT_6f94) break;
    bVar3 = (char)((&DAT_6fa1)[DAT_6f94] + '\x01') < '\0';
    bVar1 = DAT_6f94 + 1;
    if ((((&DAT_6fa1)[DAT_6f94] != -1) &&
        (bVar2 = DAT_6f94, DAT_6f94 = DAT_6f94 + 1, FUN_a944(), bVar1 = DAT_6f94, !bVar3)) &&
       ((&DAT_0664)[bVar2] != -1)) {
      DAT_6f96 = DAT_6f96 + '\x01';
      DAT_6f8c = bVar2;
      FUN_a099();
      if (DAT_6f8f != '\x03') {
        DAT_6f8b = 0xff;
        return;
      }
      DAT_6f95 = DAT_6f95 + '\x01';
      bVar1 = DAT_6f94;
    }
    DAT_6f94 = bVar1;
  } while (DAT_6f94 < 0x14);
  if (DAT_6f96 == DAT_6f95) {
    DAT_6f94 = 0;
    DAT_6f8f = 3;
    DAT_6f8b = 0xff;
    return;
  }
  DAT_6f94 = 0;
  DAT_6f95 = 0;
  DAT_6f96 = 0;
  FUN_a03c();
  return;
}



/* 0xa003 thunk_FUN_b130 */

/* WARNING: Globals starting with '_' overlap smaller symbols at the same address */

void thunk_FUN_b130(void)

{
  byte bVar1;
  undefined1 uStack0000;
  
  bVar1 = 0;
  do {
    (&DAT_6fa1)[bVar1] = 0xff;
    bVar1 = bVar1 + 1;
  } while (bVar1 < 0x40);
  bVar1 = 0;
  do {
    *(undefined1 *)(bVar1 + 0x6fc9) = 0;
    bVar1 = bVar1 + 1;
  } while (bVar1 < 0x14);
  DAT_0022 = DAT_0507 & 0xf;
  uStack0000 = 0xb1;
  FUN_b4c2();
  if (*(char *)(_DAT_0020 + 3) == '\x03') {
    DAT_6f91 = 0;
    DAT_6fa1 = 0;
    uStack0000 = 0xb1;
    FUN_b371();
    _DAT_0020 = _DAT_0020 & 0xff00;
    uStack0000 = 0xb1;
    FUN_b1b0();
  }
  DAT_0022 = DAT_0507 >> 4;
  uStack0000 = 0xb1;
  FUN_b4c2();
  if (*(char *)(_DAT_0020 + 3) == '\x03') {
    DAT_6f91 = 10;
    DAT_6fab = 0;
    uStack0000 = 0xb1;
    FUN_b371();
    _DAT_0020 = CONCAT11(DAT_0021,0x36);
    uStack0000 = 0xb1;
    FUN_b1b0();
  }
  bVar1 = 0;
  do {
    (&DAT_04d8)[bVar1] = 0xff;
    bVar1 = bVar1 + 1;
  } while (bVar1 < 8);
  DAT_6f94 = 0;
  DAT_6f95 = 0;
  DAT_6f96 = 0;
  return;
}



/* 0xa006 thunk_FUN_bab3 */

void thunk_FUN_bab3(void)

{
  undefined1 uStack0000;
  
  uStack0000 = 0xba;
                    /* WARNING: Subroutine does not return */
  tail_dispatch_inline_table(DAT_0501);
}



/* 0xa009 thunk_FUN_c0bb */

void thunk_FUN_c0bb(void)

{
  undefined1 uStack0000;
  
  uStack0000 = 0xc0;
                    /* WARNING: Subroutine does not return */
  tail_dispatch_inline_table(DAT_0501);
}



/* 0xa00c thunk_FUN_c983 */

void thunk_FUN_c983(byte param_1)

{
  byte bVar1;
  byte bVar2;
  byte bVar3;
  bool bVar4;
  undefined1 uStack0000;
  
FUN_c983:
  bVar4 = false;
  DAT_0010 = 0;
  DAT_0011 = 0;
  bVar2 = 0;
  do {
    uStack0000 = 0xc9;
    FUN_cc92();
    if (!bVar4) {
      bVar1 = (&DAT_6fa1)[bVar2] & 0xf;
      if (bVar1 == 7) {
        (&DAT_6fa1)[bVar2] = (byte)(&DAT_6fa1)[bVar2] >> 4;
      }
      else if (4 < bVar1) {
        if (bVar1 == 5) {
          bVar1 = 100;
        }
        else {
          bVar1 = 0x32;
        }
        bVar4 = CARRY1(bVar1,DAT_0010);
        DAT_0010 = bVar1 + DAT_0010;
        DAT_0011 = DAT_0011 + bVar4;
      }
    }
    bVar1 = bVar2 + 1;
    bVar4 = (char)(bVar2 - 0x13) < '\0';
    bVar2 = bVar1;
  } while (bVar1 < 0x14);
  uStack0000 = 0xc9;
  FUN_c93e();
  bVar1 = *(byte *)(param_1 + 0x526) - DAT_0010;
  bVar2 = ~*(byte *)(param_1 + 0x526);
  bVar1 = (*(byte *)(param_1 + 0x527) - DAT_0011) -
          (((DAT_0010 & (bVar2 | bVar1) | bVar1 & bVar2) & 0x80) == 0);
  bVar2 = ~*(byte *)(param_1 + 0x527);
  if (((DAT_0011 & (bVar2 | bVar1) | bVar1 & bVar2) & 0x80) == 0) {
    DAT_0010 = 6;
    do {
      bVar4 = false;
      bVar2 = 0;
      do {
        uStack0000 = 0xc9;
        FUN_cc92();
        if ((!bVar4) && (((&DAT_6fa1)[bVar2] & 0xf) == DAT_0010)) {
          (&DAT_6fa1)[bVar2] = (byte)(&DAT_6fa1)[bVar2] >> 4;
          goto FUN_c983;
        }
        bVar1 = bVar2 + 1;
        bVar4 = (char)(bVar2 - 0x13) < '\0';
        bVar2 = bVar1;
      } while (bVar1 < 0x14);
      bVar1 = DAT_0010 - 1;
      DAT_0010 = bVar1;
    } while (4 < bVar1);
  }
  uStack0000 = 0xca;
  FUN_cd00(bVar1);
  uStack0000 = 0xca;
  FUN_c93e();
  bVar1 = (&DAT_0522)[param_1] - DAT_001a;
  bVar2 = ~(&DAT_0522)[param_1];
  bVar1 = ((&DAT_0523)[param_1] - DAT_001b) -
          (((DAT_001a & (bVar2 | bVar1) | bVar1 & bVar2) & 0x80) == 0);
  bVar2 = ~(&DAT_0523)[param_1];
  if (((DAT_001b & (bVar2 | bVar1) | bVar1 & bVar2) & 0x80) == 0) {
    uStack0000 = 0xca;
    FUN_f25f(0x31);
    DAT_0000 = DAT_050e * '\x02';
    if (*(char *)((byte)(DAT_050e * '\x06') + 0x9ba4) != -1) {
      uStack0000 = 0xca;
      FUN_c93e();
      if ((*(char *)(param_1 + 0x527) != '\0') || (99 < *(byte *)(param_1 + 0x526))) {
        bVar4 = false;
        bVar2 = 0;
        do {
          uStack0000 = 0xca;
          FUN_cc92();
          if ((!bVar4) && (bVar1 = (&DAT_6fa1)[bVar2] & 0xf, bVar1 == 5)) goto LAB_cac2;
          bVar1 = bVar2 + 1;
          bVar4 = (char)(bVar2 - 0x13) < '\0';
          bVar2 = bVar1;
        } while (bVar1 < 0x14);
        uStack0000 = 0xca;
        bVar1 = FUN_cb6a();
        goto LAB_cac2;
      }
    }
    uStack0000 = 0xca;
    FUN_cd06(10);
    uStack0000 = 0xca;
    FUN_c93e();
    bVar1 = (&DAT_0522)[param_1] - DAT_001a;
    bVar2 = ~(&DAT_0522)[param_1];
    bVar1 = ((&DAT_0523)[param_1] - DAT_001b) -
            (((DAT_001a & (bVar2 | bVar1) | bVar1 & bVar2) & 0x80) == 0);
    bVar2 = ~(&DAT_0523)[param_1];
    if (((DAT_001b & (bVar2 | bVar1) | bVar1 & bVar2) & 0x80) == 0) {
      uStack0000 = 0xca;
      bVar1 = FUN_cbfe(bVar1);
    }
  }
  else {
    uStack0000 = 0xca;
    FUN_c93e(bVar1);
    param_1 = param_1 ^ 2;
    bVar1 = (&DAT_0522)[param_1] - DAT_001c;
    bVar2 = ~(&DAT_0522)[param_1];
    bVar1 = ((&DAT_0523)[param_1] - DAT_001d) -
            (((DAT_001c & (bVar2 | bVar1) | bVar1 & bVar2) & 0x80) == 0);
    bVar2 = ~(&DAT_0523)[param_1];
    if (((DAT_001d & (bVar2 | bVar1) | bVar1 & bVar2) & 0x80) == 0) {
      uStack0000 = 0xca;
      FUN_cd06(5);
      uStack0000 = 0xca;
      FUN_c93e();
      param_1 = param_1 ^ 2;
      bVar1 = (&DAT_0522)[param_1] - DAT_001c;
      bVar2 = ~(&DAT_0522)[param_1];
      bVar1 = ((&DAT_0523)[param_1] - DAT_001d) -
              (((DAT_001c & (bVar2 | bVar1) | bVar1 & bVar2) & 0x80) == 0);
      bVar2 = ~(&DAT_0523)[param_1];
      if (((DAT_001d & (bVar2 | bVar1) | bVar1 & bVar2) & 0x80) == 0) {
        uStack0000 = 0xca;
        bVar1 = FUN_cb4d(bVar1);
      }
    }
  }
LAB_cac2:
  uStack0000 = 0xca;
  FUN_f25f(bVar1,0x31);
  DAT_0000 = DAT_050e * '\x02';
  if (*(char *)((byte)(DAT_050e * '\x06' + 4) + 0x9ba4) != -1) {
    uStack0000 = 0xca;
    FUN_c93e();
    if ((*(char *)(param_1 + 0x527) != '\0') || (0x31 < *(byte *)(param_1 + 0x526))) {
      bVar1 = 0;
      bVar4 = false;
      bVar2 = 0;
      do {
        uStack0000 = 0xca;
        FUN_cc92();
        if ((!bVar4) && (((&DAT_6fa1)[bVar2] & 0xf) == 6)) {
          bVar1 = bVar1 + 1;
        }
        bVar3 = bVar2 + 1;
        bVar4 = (char)(bVar2 - 0x13) < '\0';
        bVar2 = bVar3;
      } while (bVar3 < 0x14);
      if (bVar1 < 2) {
        bVar4 = false;
        bVar2 = 0;
        DAT_0010 = bVar1;
        do {
          uStack0000 = 0xcb;
          FUN_cc92();
          if (((!bVar4) && ((&DAT_6fa1)[bVar2] != 0)) && ((byte)(&DAT_6fa1)[bVar2] < 5)) {
            uStack0000 = 0xcb;
            FUN_cc19();
          }
          bVar1 = bVar2 + 1;
          bVar4 = (char)(bVar2 - 0x13) < '\0';
          bVar2 = bVar1;
        } while (bVar1 < 0x14);
      }
    }
  }
  uStack0000 = 0xcb;
  FUN_ccaa();
  bVar2 = (DAT_001d - 3) -
          (((~DAT_001c & 0xe8 | DAT_001c + 0x18 & 0xe8 | DAT_001c + 0x18 & ~DAT_001c) & 0x80) == 0);
  if ((bVar2 & ~DAT_001d & 0x80) == 0) {
    bVar2 = (DAT_001b - 0x13) -
            (((~DAT_001a & 0x88 | DAT_001a + 0x78 & 0x88 | DAT_001a + 0x78 & ~DAT_001a) & 0x80) == 0
            );
    if ((bVar2 & ~DAT_001b & 0x80) != 0) {
      FUN_cbfe(bVar2);
      return;
    }
    FUN_cb9a();
    return;
  }
  FUN_cb9a(bVar2);
  return;
}



/* 0xa00f thunk_FUN_cd78 */

void thunk_FUN_cd78(void)

{
  byte bVar1;
  char cVar2;
  byte bVar3;
  byte bVar4;
  byte bVar5;
  undefined1 uStack0000;
  
  DAT_050a = 0;
  if (0x1e < DAT_0506) {
    DAT_0000 = 0;
    FUN_ceab();
    return;
  }
  uStack0000 = 0xcd;
  FUN_cd06(1);
  bVar5 = DAT_0524 - DAT_001a;
  bVar3 = (DAT_0525 - DAT_001b) -
          (((DAT_001a & (~DAT_0524 | bVar5) | bVar5 & ~DAT_0524) & 0x80) == 0);
  if ((((DAT_001b & (~DAT_0525 | bVar3) | bVar3 & ~DAT_0525) & 0x80) != 0) &&
     ((bVar5 != 0 || (bVar3 != 0)))) {
    bVar1 = DAT_0522 - DAT_001c;
    bVar4 = (DAT_0523 - DAT_001d) -
            (((DAT_001c & (~DAT_0522 | bVar1) | bVar1 & ~DAT_0522) & 0x80) == 0);
    DAT_0524 = bVar5;
    DAT_0525 = bVar3;
    if ((((DAT_001d & (~DAT_0523 | bVar4) | bVar4 & ~DAT_0523) & 0x80) != 0) &&
       ((bVar1 != 0 || (bVar4 != 0)))) {
      DAT_0010 = 0xf;
      DAT_0011 = 1;
      uStack0000 = 0xcd;
      DAT_0522 = bVar1;
      DAT_0523 = bVar4;
      FUN_ce40();
      uStack0000 = 0xcd;
      FUN_cf60();
      if (DAT_052e != '\0') {
        DAT_0010 = 0xf0;
        DAT_0011 = 0x10;
        DAT_000b = 0;
        DAT_000c = 0;
        uStack0000 = 0xce;
        FUN_ce40();
        DAT_000a = 0x6d;
        uStack0000 = 0xce;
        far_call_inline_word(0x2e);
        DAT_00a0 = DAT_00a0 << 1;
      }
      bVar5 = 0;
      while( true ) {
        if ((*(char *)(bVar5 + 0x4db) != -1) &&
           (cVar2 = *(char *)(bVar5 + 0x4db) + -1, *(char *)(bVar5 + 0x4db) = cVar2, cVar2 == '\0'))
        {
          (&DAT_04d8)[bVar5] = 0xff;
        }
        if (bVar5 == 4) break;
        bVar5 = 4;
      }
      return;
    }
    DAT_0522 = 0;
    DAT_0523 = 0;
    FUN_cf06();
    return;
  }
  DAT_0524 = 0;
  DAT_0525 = 0;
  DAT_0000 = 0x80;
  FUN_ceab();
  return;
}



/* 0xa012 thunk_FUN_cfa2 */

void thunk_FUN_cfa2(void)

{
  byte bVar1;
  undefined1 uStack0000;
  
  if ((((DAT_008f == '\0') && (DAT_04c8 == '\0')) && (DAT_0500 < 0xc)) && ((DAT_005e & 0x20) != 0))
  {
    DAT_000a = 0x20;
    DAT_000c = 0xb0;
    DAT_0000 = 0x3c;
    DAT_0001 = 0xd1;
    DAT_0002 = 0;
    uStack0000 = 0xcf;
    FUN_f1ad();
    DAT_0000 = 0x5d;
    if ((DAT_005e & 0x40) == 0) {
      DAT_0000 = 0x6e;
    }
    DAT_0001 = 0xd1;
    uStack0000 = 0xcf;
    FUN_f1ad();
    DAT_0001 = DAT_0505;
    DAT_0002 = 0;
    DAT_0003 = 0;
    uStack0000 = 0xd0;
    FUN_e9ba();
    if (DAT_0007 >> 4 != 0) {
      DAT_000a = 0x20;
      DAT_000c = 0xe0;
      uStack0000 = 0xd0;
      FUN_d126(DAT_0007 >> 4);
    }
    DAT_000a = 0x20;
    DAT_000c = 0xe8;
    uStack0000 = 0xd0;
    FUN_d126(DAT_0007 & 0xf);
    DAT_0001 = DAT_0506;
    DAT_0002 = 0;
    DAT_0003 = 0;
    uStack0000 = 0xd0;
    FUN_e9ba();
    if (DAT_0007 >> 4 != 0) {
      DAT_000a = 0x10;
      DAT_000c = 0xd0;
      uStack0000 = 0xd0;
      FUN_d126(DAT_0007 >> 4);
    }
    DAT_000a = 0x10;
    DAT_000c = 0xd8;
    uStack0000 = 0xd0;
    FUN_d126(DAT_0007 & 0xf);
    if ((DAT_005e & 0x40) == 0) {
      bVar1 = 0;
      if (DAT_0504 < '\0') {
        bVar1 = 2;
      }
      DAT_0001 = (&DAT_0522)[bVar1];
      DAT_0002 = (&DAT_0523)[bVar1];
      DAT_0003 = 0;
      uStack0000 = 0xd0;
      FUN_e9ba();
    }
    else {
      bVar1 = 0;
      if (DAT_0504 < '\0') {
        bVar1 = 2;
      }
      DAT_0001 = *(undefined1 *)(bVar1 + 0x526);
      DAT_0002 = *(undefined1 *)(bVar1 + 0x527);
      DAT_0003 = 0;
      uStack0000 = 0xd0;
      FUN_e9ba();
    }
    DAT_0011 = '\0';
    DAT_0010 = 0x40;
    if (DAT_0008 >> 4 != 0) {
      DAT_0011 = '\x01';
      DAT_000a = 0x40;
      DAT_000c = 0xd0;
      uStack0000 = 0xd0;
      FUN_d126(DAT_0008 >> 4);
    }
    if (((DAT_0008 & 0xf) != 0) || (DAT_0011 != '\0')) {
      DAT_0011 = DAT_0011 + '\x01';
      DAT_000a = DAT_0010;
      DAT_000c = 0xd8;
      uStack0000 = 0xd0;
      FUN_d126();
    }
    if ((DAT_0007 >> 4 != 0) || (DAT_0011 != '\0')) {
      DAT_000a = DAT_0010;
      DAT_000c = 0xe0;
      uStack0000 = 0xd1;
      FUN_d126(DAT_0007 >> 4);
    }
    DAT_000a = DAT_0010;
    DAT_000c = 0xe8;
    uStack0000 = 0xd1;
    FUN_d126(DAT_0007 & 0xf);
    return;
  }
  return;
}



/* 0xa015 thunk_FUN_d1ed */

void thunk_FUN_d1ed(void)

{
  ushort uVar1;
  byte bVar2;
  byte bVar3;
  byte bStack0000;
  
  if ((DAT_008f == '\0') && (DAT_0500 < 0xc)) {
    bStack0000 = 0xd1;
    FUN_d2f5();
    if (DAT_0061 != '\a') {
      bStack0000 = 0xd2;
      FUN_f25f(0x31);
      bVar3 = (DAT_050e & 0x7f) >> 6;
      bVar2 = DAT_050e << 2;
      DAT_000a = *(undefined1 *)(bVar2 + 0x9d58);
      DAT_000b = *(undefined1 *)(bVar2 + 0x9d59);
      DAT_000c = *(char *)(bVar2 + 0x9d5a);
      DAT_000d = *(undefined1 *)(bVar2 + 0x9d5b);
      bStack0000 = 0xd2;
      FUN_d337();
      if (bVar3 != 0) {
        DAT_0000 = 0x15;
        DAT_0001 = 0xd3;
        DAT_0002 = 0;
        DAT_0003 = 0;
        DAT_0004 = 0x9c;
        bStack0000 = 0xd2;
        FUN_f09c();
      }
      bStack0000 = 0xd2;
      FUN_f25f(0x31);
      bStack0000 = DAT_050e * '\x06';
      if (-1 < *(char *)(bStack0000 + 0x9ba4)) {
        DAT_000a = *(undefined1 *)(bStack0000 + 0x9ba5);
        DAT_000c = *(char *)(bStack0000 + 0x9ba4);
        FUN_d296();
      }
      if (-1 < *(char *)(bStack0000 + 0x9ba6)) {
        DAT_000a = *(undefined1 *)(bStack0000 + 0x9ba7);
        DAT_000c = *(char *)(bStack0000 + 0x9ba6);
        FUN_d296();
      }
      uVar1 = (ushort)bStack0000;
      if (-1 < *(char *)(uVar1 + 0x9ba8)) {
        DAT_000a = *(undefined1 *)(bStack0000 + 0x9ba9);
        bStack0000 = 0xd2;
        DAT_000c = *(char *)(uVar1 + 0x9ba8);
        FUN_d296();
      }
      return;
    }
  }
  return;
}



/* 0xa018 thunk_FUN_d390 */

/* WARNING: Globals starting with '_' overlap smaller symbols at the same address */

void thunk_FUN_d390(void)

{
  byte bVar1;
  undefined1 uStack0000;
  
  uStack0000 = 0xd3;
  officer_address(DAT_042c);
  bVar1 = *(byte *)(_DAT_0000 + 0xb) >> 4;
  if (bVar1 == 3) {
    bVar1 = 0;
  }
  else if (bVar1 == 4) {
    bVar1 = 0xb;
  }
  else if (bVar1 == 5) {
    bVar1 = 0x11;
  }
  else {
    if (bVar1 != 6) {
      DAT_042d = 0xff;
      return;
    }
    bVar1 = 0x14;
  }
  while( true ) {
    if ((&DAT_d3d8)[bVar1] == -1) {
      DAT_042d = 0xff;
      return;
    }
    if ((&DAT_d3d8)[bVar1] == DAT_042c) break;
    bVar1 = bVar1 + 1;
  }
  return;
}



/* 0xa01b thunk_FUN_d3ee */

/* WARNING: Globals starting with '_' overlap smaller symbols at the same address */

void thunk_FUN_d3ee(void)

{
  byte bVar1;
  char cVar2;
  undefined1 uStack0000;
  
  bVar1 = 0xf;
  do {
    *(undefined1 *)(bVar1 + 0x580) = 0xff;
    bVar1 = bVar1 - 1;
  } while (-1 < (char)bVar1);
  DAT_0010 = (&DAT_0664)[DAT_050a];
  uStack0000 = 0xd4;
  officer_address();
  DAT_0011 = *(byte *)(_DAT_0000 + 0xb) >> 4;
  if (((((DAT_0010 == -0x5f) || (DAT_0010 == 'c')) || (DAT_0010 == -0x59)) ||
      (((((DAT_0010 == '\x16' || (DAT_0010 == -0x3c)) ||
         ((DAT_0010 == -0x25 || ((DAT_0010 == -0x16 || (DAT_0010 == 'k')))))) || (DAT_0010 == -0x32)
        ) || ((DAT_0010 == -0x15 || (DAT_0010 == -0x49)))))) && (2 < DAT_0011)) {
    cVar2 = '\x05';
    goto LAB_d4e6;
  }
  if (((((DAT_0010 == '\x18') || (DAT_0010 == '7')) || (DAT_0010 == 'p')) ||
      ((DAT_0010 == -0x2b || (DAT_0010 == 'n')))) || (DAT_0010 == 'g')) {
    if (3 < DAT_0011) {
      cVar2 = '\x06';
      goto LAB_d4e6;
    }
    if (2 < DAT_0011) {
      cVar2 = '\x05';
      goto LAB_d4e6;
    }
  }
  if (((DAT_0010 == -0x3b) || (DAT_0010 == 'V')) || (DAT_0010 == ']')) {
    if (4 < DAT_0011) {
      cVar2 = '\a';
      goto LAB_d4e6;
    }
    if (3 < DAT_0011) {
      cVar2 = '\x06';
      goto LAB_d4e6;
    }
    if (2 < DAT_0011) {
      cVar2 = '\x05';
      goto LAB_d4e6;
    }
  }
  if (DAT_0010 == 'm') {
    cVar2 = '\b';
    if ((((5 < DAT_0011) || (cVar2 = '\a', 4 < DAT_0011)) || (cVar2 = '\x06', 3 < DAT_0011)) ||
       (cVar2 = '\x05', 2 < DAT_0011)) goto LAB_d4e6;
  }
  uStack0000 = 0xd4;
  officer_address(DAT_0010);
  bVar1 = *(byte *)(_DAT_0000 + 2);
  cVar2 = '\0';
  if (((0x27 < bVar1) && (cVar2 = '\x01', 0x3b < bVar1)) &&
     ((cVar2 = '\x02', 0x4a < bVar1 && (cVar2 = '\x03', 0x54 < bVar1)))) {
    cVar2 = '\x04';
  }
LAB_d4e6:
  _DAT_0000 = CONCAT11((&DAT_d50a)[(byte)(cVar2 << 1)],(&DAT_d509)[(byte)(cVar2 << 1)]);
  for (bVar1 = 0; *(char *)(_DAT_0000 + (ushort)bVar1) != -1; bVar1 = bVar1 + 1) {
    *(char *)(bVar1 + 0x580) = *(char *)(_DAT_0000 + (ushort)bVar1);
  }
  DAT_0542 = bVar1 - 1;
  return;
}



/* 0xa01e thunk_FUN_c851 */

void thunk_FUN_c851(void)

{
  char cVar1;
  byte bVar2;
  byte bVar3;
  byte bVar4;
  byte bVar5;
  
  bVar5 = DAT_0012 * '\x04' + DAT_0000 * '\x10';
  bVar4 = 0;
  do {
    cVar1 = (&DAT_c8de)[bVar5];
    *(char *)(bVar4 + 0x44c) = cVar1;
    bVar2 = cVar1 * '\x02';
    bVar3 = bVar4 * '\x03';
    DAT_0000 = bVar2;
    DAT_0001 = bVar4;
    (&DAT_042c)[bVar3] = (&DAT_c89e)[bVar2];
    (&DAT_042d)[bVar3] = (&DAT_c89e)[(byte)(bVar2 + 1)];
    (&DAT_042e)[bVar3] = 0;
    bVar5 = bVar5 + 1;
    bVar4 = DAT_0001 + 1;
  } while (bVar4 < 4);
  return;
}



/* 0xa021 thunk_FUN_d57b */

void thunk_FUN_d57b(void)

{
  byte bVar1;
  byte bVar2;
  
  if (0xb < DAT_0500) {
    return;
  }
  DAT_0000 = 0;
  bVar2 = DAT_0508;
  if ((char)DAT_0508 < '\0') {
    bVar1 = DAT_008e + 2;
    if ((0xfd < DAT_008e) ||
       (DAT_009c = DAT_009c & 0xbf | 0x80, DAT_008e = bVar1, bVar2 = DAT_0508 | 0x80,
       (bVar1 & 0xe) == 0)) {
      bVar2 = DAT_0508 & 0x7f;
    }
  }
  DAT_0508 = bVar2;
  bVar2 = DAT_0508;
  if ((char)(DAT_0508 << 1) < '\0') {
    bVar1 = DAT_008e - 2;
    if (((bVar1 & ~DAT_008e & 0x80) == 0) ||
       (DAT_009c = DAT_009c & 0x7f | 0x40, DAT_008e = bVar1, bVar2 = DAT_0508 | 0x40,
       (bVar1 & 0xe) == 0)) {
      bVar2 = DAT_0508 & 0xbf;
    }
  }
  DAT_0508 = bVar2;
  bVar2 = DAT_0508;
  if ((char)(DAT_0508 << 2) < '\0') {
    bVar1 = DAT_0090 - 2;
    if (((bVar1 & ~DAT_0090 & 0x80) == 0) ||
       (DAT_009c = DAT_009c & 0xdf | 0x10, DAT_0090 = bVar1, bVar2 = DAT_0508 | 0x20,
       (bVar1 & 0xe) == 0)) {
      bVar2 = DAT_0508 & 0xdf;
    }
  }
  DAT_0508 = bVar2;
  bVar2 = DAT_0508;
  if ((char)(DAT_0508 << 3) < '\0') {
    bVar1 = DAT_0090 + 2;
    if ((0x8f < bVar1) ||
       (DAT_009c = DAT_009c & 0xef | 0x20, DAT_0090 = bVar1, bVar2 = DAT_0508 | 0x10,
       (bVar1 & 0xe) == 0)) {
      bVar2 = DAT_0508 & 0xef;
    }
  }
  DAT_0508 = bVar2;
  return;
}



/* 0xa024 thunk_FUN_d70f */

void thunk_FUN_d70f(void)

{
  undefined1 uStack0000;
  
  uStack0000 = 0xd7;
  FUN_db10();
  uStack0000 = 0xd7;
  FUN_db62();
  uStack0000 = 0xd7;
  FUN_dbb4();
  uStack0000 = 0xd7;
  FUN_dbff();
  uStack0000 = 0xd7;
                    /* WARNING: Subroutine does not return */
  tail_dispatch_inline_table(DAT_0540);
}



/* 0xa027 thunk_FUN_d66e */

/* WARNING: Globals starting with '_' overlap smaller symbols at the same address */

void thunk_FUN_d66e(void)

{
  undefined1 uStack0000;
  
  DAT_0514 = 0;
  DAT_052b = DAT_0664;
  if (DAT_050f == '\x03') {
    uStack0000 = 0xd6;
    FUN_f368(DAT_0507 & 0xf);
    DAT_6f44 = *(char *)(_DAT_0000 + 3);
    DAT_0509 = 0;
    DAT_042c = DAT_0507 & 0xf;
    DAT_00a4 = 4;
    DAT_050a = 0x51;
  }
  else {
    DAT_6f44 = DAT_050f;
    DAT_042c = DAT_0507 >> 4;
    DAT_00a4 = 3;
    DAT_050a = 0x50;
  }
  DAT_0500 = 7;
  DAT_0501 = 2;
  return;
}



/* 0xa02a thunk_FUN_d6cd */

void thunk_FUN_d6cd(void)

{
  byte bVar1;
  
  bVar1 = DAT_0000;
  *(undefined1 *)(DAT_0000 + 0x600) = 0xff;
  *(undefined1 *)(bVar1 + 0x614) = 0xff;
  *(undefined1 *)(bVar1 + 0x628) = 0xff;
  *(undefined1 *)(bVar1 + 0x63c) = 0xff;
  *(undefined1 *)(bVar1 + 0x650) = 0xff;
  (&DAT_0664)[bVar1] = 0xff;
  (&DAT_6fa1)[bVar1] = 0xff;
  bVar1 = 0;
  if ((DAT_04d8 != DAT_0000) && (bVar1 = 4, DAT_04dc != DAT_0000)) {
    return;
  }
  DAT_0001 = bVar1 + 4;
  do {
    (&DAT_04d8)[bVar1] = 0xff;
    bVar1 = bVar1 + 1;
  } while (bVar1 < DAT_0001);
  return;
}



/* 0xa02d FUN_a02d */

void FUN_a02d(void)

{
  byte bVar1;
  byte bVar2;
  bool bVar3;
  
  if (DAT_6f8b == -1) {
    return;
  }
  if (DAT_6f8b == '\x01') {
    FUN_b933();
    return;
  }
  do {
    if (0x13 < DAT_6f94) break;
    bVar3 = (char)((&DAT_6fa1)[DAT_6f94] + '\x01') < '\0';
    bVar1 = DAT_6f94 + 1;
    if ((((&DAT_6fa1)[DAT_6f94] != -1) &&
        (bVar2 = DAT_6f94, DAT_6f94 = DAT_6f94 + 1, FUN_a944(), bVar1 = DAT_6f94, !bVar3)) &&
       ((&DAT_0664)[bVar2] != -1)) {
      DAT_6f96 = DAT_6f96 + '\x01';
      DAT_6f8c = bVar2;
      FUN_a099();
      if (DAT_6f8f != '\x03') {
        DAT_6f8b = 0xff;
        return;
      }
      DAT_6f95 = DAT_6f95 + '\x01';
      bVar1 = DAT_6f94;
    }
    DAT_6f94 = bVar1;
  } while (DAT_6f94 < 0x14);
  if (DAT_6f96 == DAT_6f95) {
    DAT_6f94 = 0;
    DAT_6f8f = 3;
    DAT_6f8b = 0xff;
    return;
  }
  DAT_6f94 = 0;
  DAT_6f95 = 0;
  DAT_6f96 = 0;
  FUN_a03c();
  return;
}



/* 0xa03c FUN_a03c */

void FUN_a03c(void)

{
  byte bVar1;
  byte bVar2;
  bool bVar3;
  
  do {
    if (0x13 < DAT_6f94) break;
    bVar3 = (char)((&DAT_6fa1)[DAT_6f94] + '\x01') < '\0';
    bVar1 = DAT_6f94 + 1;
    if ((((&DAT_6fa1)[DAT_6f94] != -1) &&
        (bVar2 = DAT_6f94, DAT_6f94 = DAT_6f94 + 1, FUN_a944(), bVar1 = DAT_6f94, !bVar3)) &&
       ((&DAT_0664)[bVar2] != -1)) {
      DAT_6f96 = DAT_6f96 + '\x01';
      DAT_6f8c = bVar2;
      FUN_a099();
      if (DAT_6f8f != '\x03') {
        DAT_6f8b = 0xff;
        return;
      }
      DAT_6f95 = DAT_6f95 + '\x01';
      bVar1 = DAT_6f94;
    }
    DAT_6f94 = bVar1;
  } while (DAT_6f94 < 0x14);
  if (DAT_6f96 == DAT_6f95) {
    DAT_6f94 = 0;
    DAT_6f8f = 3;
    DAT_6f8b = 0xff;
    return;
  }
  DAT_6f94 = 0;
  DAT_6f95 = 0;
  DAT_6f96 = 0;
  FUN_a03c();
  return;
}



/* 0xa03f FUN_a03f */

void FUN_a03f(byte param_1)

{
  bool bVar1;
  
  do {
    if (0x13 < param_1) break;
    DAT_6f94 = DAT_6f94 + 1;
    bVar1 = (char)((&DAT_6fa1)[param_1] + '\x01') < '\0';
    if ((((&DAT_6fa1)[param_1] != -1) && (FUN_a944(), !bVar1)) && ((&DAT_0664)[param_1] != -1)) {
      DAT_6f96 = DAT_6f96 + '\x01';
      DAT_6f8c = param_1;
      FUN_a099();
      if (DAT_6f8f != '\x03') {
        DAT_6f8b = 0xff;
        return;
      }
      DAT_6f95 = DAT_6f95 + '\x01';
    }
    param_1 = DAT_6f94;
  } while (DAT_6f94 < 0x14);
  if (DAT_6f96 == DAT_6f95) {
    DAT_6f94 = 0;
    DAT_6f8f = 3;
    DAT_6f8b = 0xff;
    return;
  }
  DAT_6f94 = 0;
  DAT_6f95 = 0;
  DAT_6f96 = 0;
  FUN_a03c();
  return;
}



/* 0xa099 FUN_a099 */

/* WARNING: Control flow encountered bad instruction data */
/* WARNING: Globals starting with '_' overlap smaller symbols at the same address */

void FUN_a099(byte param_1)

{
  byte bVar1;
  byte bVar2;
  bool bVar3;
  bool bVar4;
  char in_C;
  undefined1 uStack0000;
  
  uStack0000 = 0xa0;
  FUN_b517((&DAT_6fa1)[param_1] & 0xf);
  bVar2 = *(byte *)(_DAT_00a0 + (ushort)param_1) | DAT_00a1;
  bVar1 = DAT_00a1 >> 1 | in_C << 7;
  _DAT_00a0 = CONCAT11(bVar1,DAT_00a0);
  bVar4 = bVar1 == 0;
  bVar3 = false;
  if ((byte)(in_C << 7) != 0) {
                    /* WARNING: Bad instruction - Truncating control flow here */
    halt_baddata();
  }
  while( true ) {
    if (!bVar4) {
      uStack0000 = 0xa0;
      FUN_a944(bVar2);
      if ((!bVar3) && ((&DAT_0664)[param_1] != -1)) {
        DAT_6f96 = DAT_6f96 + '\x01';
        uStack0000 = 0xa0;
        DAT_6f8c = param_1;
        FUN_a099();
        if (DAT_6f8f != '\x03') {
          DAT_6f8b = 0xff;
          return;
        }
        DAT_6f95 = DAT_6f95 + '\x01';
      }
    }
    if ((0x13 < DAT_6f94) || (0x13 < DAT_6f94)) break;
    bVar2 = (&DAT_6fa1)[DAT_6f94];
    bVar4 = bVar2 == 0xff;
    bVar3 = (char)(bVar2 + 1) < '\0';
    param_1 = DAT_6f94;
    DAT_6f94 = DAT_6f94 + 1;
  }
  if (DAT_6f96 == DAT_6f95) {
    DAT_6f94 = 0;
    DAT_6f8f = 3;
    DAT_6f8b = 0xff;
    return;
  }
  DAT_6f94 = 0;
  DAT_6f95 = 0;
  DAT_6f96 = 0;
  FUN_a03c();
  return;
}



/* 0xa8e8 FUN_a8e8 */

void FUN_a8e8(void)

{
  byte bVar1;
  byte bVar2;
  byte bVar3;
  undefined1 uStack0000;
  
  bVar3 = 0;
  do {
    *(undefined1 *)(bVar3 + 0x6fc9) = 0;
    if ((&DAT_0664)[bVar3] != -1) {
      bVar2 = *(char *)(bVar3 + 0x600) - DAT_0020;
      if ((char)bVar2 < '\0') {
        bVar2 = (bVar2 ^ 0xff) + 1;
      }
      if ((bVar2 == DAT_0022) || (bVar2 < DAT_0022)) {
        bVar1 = *(byte *)(bVar3 + 0x614);
        if (0xf < bVar1) {
          bVar1 = bVar1 - 1;
        }
        bVar1 = bVar1 - DAT_0021;
        if ((char)bVar1 < '\0') {
          bVar1 = (bVar1 ^ 0xff) + 1;
        }
        if ((bVar1 == DAT_0022) || (DAT_0023._0_1_ = bVar2, DAT_0022 > bVar1)) {
          DAT_0023._0_1_ = bVar1 + bVar2 + (DAT_0022 <= bVar1);
          uStack0000 = 0xa9;
          bVar2 = FUN_a944();
          *(byte *)(bVar3 + 0x6fc9) = bVar2 | (byte)DAT_0023;
        }
      }
    }
    bVar3 = bVar3 + 1;
  } while (bVar3 < 0x14);
  return;
}



/* 0xa944 FUN_a944 */

undefined1 FUN_a944(byte param_1)

{
  if (DAT_0504 < '\0') {
    if (*(char *)(param_1 + 0x628) < '\0') {
      return 0;
    }
  }
  else if (-1 < *(char *)(param_1 + 0x628)) {
    return 0;
  }
  return 0x80;
}



/* 0xb130 FUN_b130 */

/* WARNING: Globals starting with '_' overlap smaller symbols at the same address */

void FUN_b130(void)

{
  byte bVar1;
  undefined1 uStack0000;
  
  bVar1 = 0;
  do {
    (&DAT_6fa1)[bVar1] = 0xff;
    bVar1 = bVar1 + 1;
  } while (bVar1 < 0x40);
  bVar1 = 0;
  do {
    *(undefined1 *)(bVar1 + 0x6fc9) = 0;
    bVar1 = bVar1 + 1;
  } while (bVar1 < 0x14);
  DAT_0022 = DAT_0507 & 0xf;
  uStack0000 = 0xb1;
  FUN_b4c2();
  if (*(char *)(_DAT_0020 + 3) == '\x03') {
    DAT_6f91 = 0;
    DAT_6fa1 = 0;
    uStack0000 = 0xb1;
    FUN_b371();
    _DAT_0020 = _DAT_0020 & 0xff00;
    uStack0000 = 0xb1;
    FUN_b1b0();
  }
  DAT_0022 = DAT_0507 >> 4;
  uStack0000 = 0xb1;
  FUN_b4c2();
  if (*(char *)(_DAT_0020 + 3) == '\x03') {
    DAT_6f91 = 10;
    DAT_6fab = 0;
    uStack0000 = 0xb1;
    FUN_b371();
    _DAT_0020 = CONCAT11(DAT_0021,0x36);
    uStack0000 = 0xb1;
    FUN_b1b0();
  }
  bVar1 = 0;
  do {
    (&DAT_04d8)[bVar1] = 0xff;
    bVar1 = bVar1 + 1;
  } while (bVar1 < 8);
  DAT_6f94 = 0;
  DAT_6f95 = 0;
  DAT_6f96 = 0;
  return;
}



/* 0xb1b0 FUN_b1b0 */

/* WARNING: Globals starting with '_' overlap smaller symbols at the same address */

void FUN_b1b0(void)

{
  char cVar1;
  byte bVar2;
  byte bVar3;
  undefined1 uStack0000;
  
  if ((DAT_0022 == 1) || (DAT_0022 == 5)) {
    cVar1 = '\x12';
  }
  else if ((DAT_0022 == 2) || (DAT_0022 == 4)) {
    cVar1 = '$';
  }
  else {
    cVar1 = '\0';
  }
  cVar1 = cVar1 + DAT_0020;
  _DAT_0020 = (undefined1 *)CONCAT11(DAT_0021,cVar1);
  if (DAT_6f94 != '\0') {
    bVar2 = (DAT_6f94 + -1) * '\x02' + cVar1;
    _DAT_0020 = (undefined1 *)CONCAT11((2 < bVar2) + -0x4d,bVar2 - 3);
    bVar2 = 0;
    if (DAT_6f91 != 0) {
      bVar2 = 4;
    }
    bVar3 = 0;
    do {
      DAT_0022 = *(byte *)((short)_DAT_0020 + (ushort)bVar3);
      (&DAT_6f99)[bVar2] = DAT_0022 >> 4;
      *(byte *)(bVar2 + 0x6f9a) = DAT_0022 & 0xf;
      bVar2 = bVar2 + 2;
      bVar3 = bVar3 + 1;
    } while (bVar3 < 2);
    bVar2 = 0;
    if (DAT_6f91 != 0) {
      bVar2 = 4;
    }
    DAT_0022 = bVar2 + 4;
    _DAT_0020 = (undefined1 *)CONCAT11(DAT_0021,1);
    bVar3 = DAT_6f91 + 1;
    do {
      if ((&DAT_6f99)[bVar2] != '\0') {
        _DAT_0020 = (undefined1 *)CONCAT11((&DAT_6f99)[bVar2],DAT_0020);
        do {
          (&DAT_6fa1)[bVar3] = DAT_0020;
          bVar3 = bVar3 + 1;
          cVar1 = DAT_0021 + -1;
          _DAT_0020 = (undefined1 *)CONCAT11(cVar1,DAT_0020);
        } while (cVar1 != '\0');
      }
      _DAT_0020 = (undefined1 *)CONCAT11(DAT_0021,DAT_0020 + '\x01');
      bVar2 = bVar2 + 1;
    } while (bVar2 < DAT_0022);
  }
  if (DAT_6f91 == 0) {
    uStack0000 = 0xb2;
    FUN_b2ae();
  }
  else {
    uStack0000 = 0xb2;
    FUN_b312();
  }
  bVar2 = DAT_6f91;
  DAT_002a = DAT_6f91 + 10;
  *(undefined1 *)(DAT_6f91 + 0x614) = *_DAT_0020;
  *(undefined1 *)(bVar2 + 0x600) = _DAT_0020[1];
  bVar2 = bVar2 + 1;
  do {
    if ((&DAT_6fa1)[bVar2] == -1) {
      return;
    }
    DAT_002b = (&DAT_6fa1)[bVar2] - 1;
    bVar3 = *(byte *)(DAT_002b + 0x22);
    *(undefined1 *)(bVar2 + 0x614) = _DAT_0020[bVar3];
    *(undefined1 *)(bVar2 + 0x600) = _DAT_0020[(byte)(bVar3 + 1)];
    *(char *)(DAT_002b + 0x22) = *(char *)(DAT_002b + 0x22) + '\x02';
    bVar2 = bVar2 + 1;
  } while (bVar2 < DAT_002a);
  return;
}



/* 0xb2ae FUN_b2ae */

void FUN_b2ae(void)

{
  char cVar1;
  byte bVar2;
  bool bVar3;
  byte bStack0000;
  
  bStack0000 = 0xb2;
  FUN_f266(0x30);
  bStack0000 = DAT_050e << 3;
  do {
    if (*(char *)(bStack0000 + 0x9d72) < '\0') {
      cVar1 = '\0';
LAB_b2d9:
      DAT_0020 = cVar1 << 5;
      bStack0000 = 0xb2;
      FUN_f266(0x26);
      bVar2 = *(byte *)((byte)(DAT_050e << 1) + 0x8c52);
      bVar3 = CARRY1(bVar2,DAT_0020);
      DAT_0020 = bVar2 + DAT_0020;
      DAT_0021 = *(char *)((byte)(DAT_050e << 1) + 0x8c53) + bVar3;
      bVar2 = 0;
      do {
        *(undefined1 *)(bVar2 + 0x22) = (&DAT_b30e)[bVar2];
        bVar2 = bVar2 + 1;
      } while (bVar2 < 4);
      return;
    }
    if (*(char *)(bStack0000 + 0x9d72) == DAT_052a) {
      FUN_f266(0x31);
      cVar1 = *(char *)(bStack0000 + 0x9ab4);
      goto LAB_b2d9;
    }
    bStack0000 = bStack0000 + 1;
  } while( true );
}



/* 0xb312 FUN_b312 */

void FUN_b312(void)

{
  char cVar1;
  byte bVar2;
  bool bVar3;
  undefined1 uStack0000;
  
  uStack0000 = 0xb3;
  FUN_f266(0x30);
  bVar2 = DAT_050e << 3;
  do {
    if (*(char *)(bVar2 + 0x9d72) < '\0') {
      cVar1 = '\0';
LAB_b334:
      DAT_0020 = cVar1 * '\"';
      uStack0000 = 0xb3;
      FUN_f266(0x26);
      bVar2 = *(byte *)((byte)(DAT_050e << 1) + 0x8000);
      bVar3 = CARRY1(bVar2,DAT_0020);
      DAT_0020 = bVar2 + DAT_0020;
      DAT_0021 = *(char *)((byte)(DAT_050e << 1) + 0x8001) + bVar3;
      bVar2 = 0;
      do {
        *(undefined1 *)(bVar2 + 0x22) = (&DAT_b36d)[bVar2];
        bVar2 = bVar2 + 1;
      } while (bVar2 < 4);
      return;
    }
    if (*(char *)(bVar2 + 0x9d72) == DAT_052a) {
      cVar1 = *(char *)(bVar2 + 0x9e62);
      goto LAB_b334;
    }
    bVar2 = bVar2 + 1;
  } while( true );
}



/* 0xb371 FUN_b371 */

/* WARNING: Globals starting with '_' overlap smaller symbols at the same address */

void FUN_b371(void)

{
  char cVar1;
  byte bVar2;
  byte bStack0000;
  
  DAT_002a = DAT_6f91 + 10;
  cVar1 = '\0';
  bVar2 = DAT_6f91;
  do {
    if ((&DAT_0664)[bVar2] != -1) {
      cVar1 = cVar1 + '\x01';
    }
    bVar2 = bVar2 + 1;
  } while (bVar2 < DAT_002a);
  DAT_6f94 = cVar1 - 1;
  if (DAT_6f94 < 2) {
    return;
  }
  bStack0000 = 1;
  do {
    DAT_002b = DAT_6f91 + DAT_6f94;
    bVar2 = DAT_6f91 + 1;
    do {
      FUN_b491((&DAT_0664)[bVar2]);
      DAT_002a = *(byte *)(_DAT_0020 + 1);
      FUN_b491(*(undefined1 *)(bVar2 + 0x665));
      if (DAT_002a <= *(byte *)(_DAT_0020 + 1)) {
        FUN_b3d2();
      }
      bVar2 = bVar2 + 1;
    } while (bVar2 < DAT_002b);
    bStack0000 = bStack0000 + 1;
  } while (bStack0000 < DAT_6f94);
  return;
}



/* 0xb3d2 FUN_b3d2 */

void FUN_b3d2(byte param_1)

{
  undefined1 uVar1;
  
  uVar1 = (&DAT_0664)[param_1];
  (&DAT_0664)[param_1] = *(undefined1 *)(param_1 + 0x665);
  *(undefined1 *)(param_1 + 0x665) = uVar1;
  uVar1 = *(undefined1 *)(param_1 + 0x628);
  *(undefined1 *)(param_1 + 0x628) = *(undefined1 *)(param_1 + 0x629);
  *(undefined1 *)(param_1 + 0x629) = uVar1;
  uVar1 = *(undefined1 *)(param_1 + 0x63c);
  *(undefined1 *)(param_1 + 0x63c) = *(undefined1 *)(param_1 + 0x63d);
  *(undefined1 *)(param_1 + 0x63d) = uVar1;
  return;
}



/* 0xb491 FUN_b491 */

void FUN_b491(byte param_1)

{
  DAT_0020 = param_1 * '\f' - 0x40;
  DAT_0021 = (((CARRY1(param_1 * '\x02',param_1) - ((char)param_1 >> 7)) * '\x02' |
              (byte)(param_1 * '\x03') >> 7) << 1 | (param_1 * '\x03' & 0x7f) >> 6) + 99 +
             (0x3f < (byte)(param_1 * '\f'));
  return;
}



/* 0xb4c2 FUN_b4c2 */

void FUN_b4c2(byte param_1)

{
  byte bVar1;
  
  bVar1 = (param_1 & 0xf) << 1;
  DAT_0020 = (&DAT_b4d3)[bVar1];
  DAT_0021 = (&DAT_b4d4)[bVar1];
  return;
}



/* 0xb517 FUN_b517 */

/* WARNING: Globals starting with '_' overlap smaller symbols at the same address */

void FUN_b517(char param_1,undefined1 param_2)

{
  undefined1 unaff_retaddr;
  undefined1 unaff_retaddr_00;
  
  _DAT_0021 = CONCAT11(unaff_retaddr_00,unaff_retaddr);
  DAT_0023 = (code *)CONCAT11(*(undefined1 *)(_DAT_0021 + (ushort)(byte)(param_1 * '\x02' + 2)),
                              *(undefined1 *)(_DAT_0021 + (ushort)(byte)(param_1 * '\x02' + 1)));
  DAT_0020 = param_2;
                    /* WARNING: Could not recover jumptable at 0xb533. Too many branches */
                    /* WARNING: Treating indirect jump as call */
  (*DAT_0023)(param_2);
  return;
}



/* 0xb536 FUN_b536 */

void FUN_b536(void)

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
    bVar3 = DAT_0020 >> 7;
    DAT_0020 = DAT_0020 * '\x02';
    bVar4 = DAT_0021 >> 7;
    DAT_0021 = DAT_0021 << 1 | bVar3;
    bVar3 = DAT_0022 >> 7;
    DAT_0022 = DAT_0022 << 1 | bVar4;
    bVar3 = DAT_0025 << 1 | bVar3;
    bVar4 = DAT_0026 << 1 | DAT_0025 >> 7;
    DAT_0027 = DAT_0027 << 1 | DAT_0026 >> 7;
    DAT_0028 = bVar3 - (byte)DAT_0023;
    DAT_0029 = (bVar4 - DAT_0023._1_1_) -
               ((((byte)DAT_0023 & (~bVar3 | DAT_0028) | DAT_0028 & ~bVar3) & 0x80) == 0);
    bVar1 = DAT_0027 - (((DAT_0023._1_1_ & (~bVar4 | DAT_0029) | DAT_0029 & ~bVar4) & 0x80) == 0);
    DAT_0025 = bVar3;
    DAT_0026 = bVar4;
    if ((bVar1 & ~DAT_0027 & 0x80) != 0) {
      DAT_0020 = DAT_0020 + 1;
      DAT_0025 = DAT_0028;
      DAT_0026 = DAT_0029;
      DAT_0027 = bVar1;
    }
    cVar2 = cVar2 + -1;
  } while (-1 < cVar2);
  return;
}



/* 0xb585 FUN_b585 */

void FUN_b585(void)

{
  char cVar1;
  byte bVar2;
  bool bVar3;
  bool bVar4;
  byte bVar5;
  
  cVar1 = '\a';
  DAT_0023._1_1_ = 0;
  DAT_0025 = 0;
  DAT_0026 = 0;
  DAT_0027 = 0;
  DAT_0028 = 0;
  DAT_0029 = '\0';
  do {
    bVar2 = (byte)DAT_0023 & 1;
    DAT_0023._0_1_ = (byte)DAT_0023 >> 1;
    if (bVar2 != 0) {
      bVar3 = CARRY1(DAT_0020,DAT_0026);
      DAT_0026 = DAT_0020 + DAT_0026;
      bVar4 = CARRY1(DAT_0021,DAT_0027);
      DAT_0027 = DAT_0021 + DAT_0027 + bVar3;
      bVar3 = CARRY1(DAT_0022,DAT_0028);
      DAT_0028 = DAT_0022 + DAT_0028 + bVar4;
      DAT_0029 = DAT_0023._1_1_ + DAT_0029 + bVar3;
    }
    bVar2 = DAT_0020 >> 7;
    DAT_0020 = DAT_0020 << 1;
    bVar5 = DAT_0021 >> 7;
    DAT_0021 = DAT_0021 << 1 | bVar2;
    bVar2 = DAT_0022 >> 7;
    DAT_0022 = DAT_0022 << 1 | bVar5;
    DAT_0023._1_1_ = DAT_0023._1_1_ << 1 | bVar2;
    cVar1 = cVar1 + -1;
  } while (-1 < cVar1);
  return;
}



/* 0xb5d5 FUN_b5d5 */

undefined1 FUN_b5d5(undefined1 param_1)

{
  ushort uVar1;
  
  DAT_6f93 = param_1;
  uVar1 = (ushort)DAT_6f92;
  DAT_6f92 = DAT_6f92 + 1;
  return (&DAT_b5e5)[uVar1];
}



/* 0xb6e5 FUN_b6e5 */

byte FUN_b6e5(void)

{
  byte bVar1;
  undefined1 uStack0000;
  
  uStack0000 = 0xb6;
  bVar1 = FUN_b6ef();
  if (5 < bVar1) {
    bVar1 = 2;
  }
  return bVar1;
}



/* 0xb6ef FUN_b6ef */

/* WARNING: Globals starting with '_' overlap smaller symbols at the same address */

undefined1 FUN_b6ef(void)

{
  byte bVar1;
  byte bVar2;
  undefined1 uStack0000;
  
  bVar2 = 0xf < DAT_0020;
  if (0xf < DAT_0021) {
    bVar2 = bVar2 | 2;
  }
  bVar1 = *(byte *)(DAT_00a8 + (ushort)bVar2) << 1;
  _DAT_0022 = CONCAT11((&DAT_b7cc)[bVar1],(&DAT_b7cb)[bVar1]);
  uStack0000 = 0xb7;
  FUN_f266((&DAT_b8bb)[*(byte *)(DAT_00a8 + (ushort)bVar2)]);
  RAM0x0024 = &DAT_b74b;
  DAT_0026 = DAT_0020 & 0xf;
  bVar2 = *(byte *)(_DAT_0022 + (ushort)(byte)(DAT_0021 << 4 | DAT_0020 & 0xf));
  if (0x7f < bVar2) {
    return 0;
  }
  return (&DAT_b74b)[bVar2];
}



/* 0xb933 FUN_b933 */

/* WARNING: Globals starting with '_' overlap smaller symbols at the same address */

void FUN_b933(void)

{
  char cVar1;
  byte bVar2;
  undefined1 uStack0000;
  
  DAT_6f8f = 0xff;
  DAT_002a = 4;
  if (DAT_0504 < '\0') {
    DAT_002a = 0;
  }
  if ((&DAT_04d8)[DAT_002a] != -1) {
    bVar2 = *(byte *)(DAT_002a + 0x4da);
    if ((*(char *)(DAT_6f8c + 0x600) != *(char *)(DAT_002a + 0x4d9)) ||
       (*(byte *)(DAT_002a + 0x614) != bVar2)) {
      if (0xf < bVar2) {
        bVar2 = bVar2 - 1;
      }
      _DAT_0020 = CONCAT11(bVar2,*(char *)(DAT_002a + 0x4d9));
      DAT_0022 = 2;
      uStack0000 = 0xb9;
      FUN_a8e8();
      if (*(char *)(DAT_6f8c + 0x6fc9) == '\0') {
        DAT_6f8b = 0xff;
        return;
      }
    }
    _DAT_0020 = CONCAT11(*(undefined1 *)(DAT_6f8c + 0x614),*(undefined1 *)(DAT_6f8c + 0x600));
    uStack0000 = 0xb9;
    cVar1 = FUN_b6e5();
    if (cVar1 == '\0') {
      uStack0000 = 0xb9;
      FUN_b491((&DAT_0664)[(byte)(&DAT_04d8)[DAT_002a]]);
      DAT_0023._0_1_ = *(byte *)(_DAT_0020 + 2);
      DAT_0023._1_1_ = *(byte *)(_DAT_0020 + 0xb);
      uStack0000 = 0xb9;
      FUN_b491((&DAT_0664)[DAT_6f8c]);
      DAT_0022 = *(char *)(_DAT_0020 + 2);
      cVar1 = (byte)DAT_0023 - DAT_0022;
      if (cVar1 < '\0') {
        cVar1 = '\0';
      }
      _DAT_0020 = CONCAT11(DAT_0021,cVar1 + '\n');
      do {
        uStack0000 = 0xb9;
        bVar2 = FUN_b5d5();
      } while (100 < bVar2);
      DAT_002a = DAT_0023._1_1_ * '\n' + CARRY1(DAT_0023._1_1_ * '\b',DAT_0023._1_1_);
      _DAT_0020 = (ushort)(byte)DAT_0023;
      DAT_0022 = 0;
      do {
        uStack0000 = 0xba;
        bVar2 = FUN_b5d5();
      } while (10 < bVar2);
      DAT_0023._0_1_ = bVar2 + 0x1e;
      uStack0000 = 0xba;
      FUN_b585();
      _DAT_0020 = CONCAT11(DAT_0027,DAT_0026);
      DAT_0023._0_1_ = 10;
      DAT_0022 = 0;
      DAT_0023._1_1_ = 0;
      uStack0000 = 0xba;
      FUN_b536();
      DAT_0022 = DAT_0020 + DAT_002a;
      DAT_0023._0_1_ = DAT_0021 + CARRY1(DAT_0020,DAT_002a);
      uStack0000 = 0xba;
      FUN_b491((&DAT_0664)[DAT_6f8c]);
      DAT_0023._1_1_ = *(byte *)(_DAT_0020 + 8);
      DAT_0025 = *(byte *)(_DAT_0020 + 9) & 3;
      DAT_0026 = DAT_0023._1_1_ - DAT_0022;
      DAT_0027 = (DAT_0025 - (byte)DAT_0023) -
                 (((DAT_0022 & (~DAT_0023._1_1_ | DAT_0026) | DAT_0026 & ~DAT_0023._1_1_) & 0x80) ==
                 0);
      if ((((byte)DAT_0023 & (~DAT_0025 | DAT_0027) | DAT_0027 & ~DAT_0025) & 0x80) == 0) {
        DAT_0026 = 0;
        DAT_0027 = 0;
        DAT_0022 = DAT_0023._1_1_;
        DAT_0023._0_1_ = DAT_0025;
      }
      *(byte *)(_DAT_0020 + 8) = DAT_0026;
      *(byte *)(_DAT_0020 + 9) = *(byte *)(_DAT_0020 + 9) & 0xfc | DAT_0027;
      DAT_042c = DAT_0022;
      DAT_042d = (byte)DAT_0023;
      DAT_042e = 0;
      DAT_6f8f = 0;
    }
  }
  DAT_6f8b = 0xff;
  return;
}



/* 0xbab3 FUN_bab3 */

void FUN_bab3(void)

{
  undefined1 uStack0000;
  
  uStack0000 = 0xba;
                    /* WARNING: Subroutine does not return */
  tail_dispatch_inline_table(DAT_0501);
}



/* 0xc0bb FUN_c0bb */

void FUN_c0bb(void)

{
  undefined1 uStack0000;
  
  uStack0000 = 0xc0;
                    /* WARNING: Subroutine does not return */
  tail_dispatch_inline_table(DAT_0501);
}



/* 0xc851 FUN_c851 */

void FUN_c851(void)

{
  char cVar1;
  byte bVar2;
  byte bVar3;
  byte bVar4;
  byte bVar5;
  
  bVar5 = DAT_0012 * '\x04' + DAT_0000 * '\x10';
  bVar4 = 0;
  do {
    cVar1 = (&DAT_c8de)[bVar5];
    *(char *)(bVar4 + 0x44c) = cVar1;
    bVar2 = cVar1 * '\x02';
    bVar3 = bVar4 * '\x03';
    DAT_0000 = bVar2;
    DAT_0001 = bVar4;
    (&DAT_042c)[bVar3] = (&DAT_c89e)[bVar2];
    (&DAT_042d)[bVar3] = (&DAT_c89e)[(byte)(bVar2 + 1)];
    (&DAT_042e)[bVar3] = 0;
    bVar5 = bVar5 + 1;
    bVar4 = DAT_0001 + 1;
  } while (bVar4 < 4);
  return;
}



/* 0xc93e FUN_c93e */

void FUN_c93e(void)

{
  return;
}



/* 0xc983 FUN_c983 */

void FUN_c983(byte param_1)

{
  byte bVar1;
  byte bVar2;
  byte bVar3;
  bool bVar4;
  undefined1 uStack0000;
  
code_r0xc983:
  bVar4 = false;
  DAT_0010 = 0;
  DAT_0011 = 0;
  bVar2 = 0;
  do {
    uStack0000 = 0xc9;
    FUN_cc92();
    if (!bVar4) {
      bVar1 = (&DAT_6fa1)[bVar2] & 0xf;
      if (bVar1 == 7) {
        (&DAT_6fa1)[bVar2] = (byte)(&DAT_6fa1)[bVar2] >> 4;
      }
      else if (4 < bVar1) {
        if (bVar1 == 5) {
          bVar1 = 100;
        }
        else {
          bVar1 = 0x32;
        }
        bVar4 = CARRY1(bVar1,DAT_0010);
        DAT_0010 = bVar1 + DAT_0010;
        DAT_0011 = DAT_0011 + bVar4;
      }
    }
    bVar1 = bVar2 + 1;
    bVar4 = (char)(bVar2 - 0x13) < '\0';
    bVar2 = bVar1;
  } while (bVar1 < 0x14);
  uStack0000 = 0xc9;
  FUN_c93e();
  bVar1 = *(byte *)(param_1 + 0x526) - DAT_0010;
  bVar2 = ~*(byte *)(param_1 + 0x526);
  bVar1 = (*(byte *)(param_1 + 0x527) - DAT_0011) -
          (((DAT_0010 & (bVar2 | bVar1) | bVar1 & bVar2) & 0x80) == 0);
  bVar2 = ~*(byte *)(param_1 + 0x527);
  if (((DAT_0011 & (bVar2 | bVar1) | bVar1 & bVar2) & 0x80) == 0) {
    DAT_0010 = 6;
    do {
      bVar4 = false;
      bVar2 = 0;
      do {
        uStack0000 = 0xc9;
        FUN_cc92();
        if ((!bVar4) && (((&DAT_6fa1)[bVar2] & 0xf) == DAT_0010)) {
          (&DAT_6fa1)[bVar2] = (byte)(&DAT_6fa1)[bVar2] >> 4;
          goto code_r0xc983;
        }
        bVar1 = bVar2 + 1;
        bVar4 = (char)(bVar2 - 0x13) < '\0';
        bVar2 = bVar1;
      } while (bVar1 < 0x14);
      bVar1 = DAT_0010 - 1;
      DAT_0010 = bVar1;
    } while (4 < bVar1);
  }
  uStack0000 = 0xca;
  FUN_cd00(bVar1);
  uStack0000 = 0xca;
  FUN_c93e();
  bVar1 = (&DAT_0522)[param_1] - DAT_001a;
  bVar2 = ~(&DAT_0522)[param_1];
  bVar1 = ((&DAT_0523)[param_1] - DAT_001b) -
          (((DAT_001a & (bVar2 | bVar1) | bVar1 & bVar2) & 0x80) == 0);
  bVar2 = ~(&DAT_0523)[param_1];
  if (((DAT_001b & (bVar2 | bVar1) | bVar1 & bVar2) & 0x80) == 0) {
    uStack0000 = 0xca;
    FUN_f25f(0x31);
    DAT_0000 = DAT_050e * '\x02';
    if (*(char *)((byte)(DAT_050e * '\x06') + 0x9ba4) != -1) {
      uStack0000 = 0xca;
      FUN_c93e();
      if ((*(char *)(param_1 + 0x527) != '\0') || (99 < *(byte *)(param_1 + 0x526))) {
        bVar4 = false;
        bVar2 = 0;
        do {
          uStack0000 = 0xca;
          FUN_cc92();
          if ((!bVar4) && (bVar1 = (&DAT_6fa1)[bVar2] & 0xf, bVar1 == 5)) goto LAB_cac2;
          bVar1 = bVar2 + 1;
          bVar4 = (char)(bVar2 - 0x13) < '\0';
          bVar2 = bVar1;
        } while (bVar1 < 0x14);
        uStack0000 = 0xca;
        bVar1 = FUN_cb6a();
        goto LAB_cac2;
      }
    }
    uStack0000 = 0xca;
    FUN_cd06(10);
    uStack0000 = 0xca;
    FUN_c93e();
    bVar1 = (&DAT_0522)[param_1] - DAT_001a;
    bVar2 = ~(&DAT_0522)[param_1];
    bVar1 = ((&DAT_0523)[param_1] - DAT_001b) -
            (((DAT_001a & (bVar2 | bVar1) | bVar1 & bVar2) & 0x80) == 0);
    bVar2 = ~(&DAT_0523)[param_1];
    if (((DAT_001b & (bVar2 | bVar1) | bVar1 & bVar2) & 0x80) == 0) {
      uStack0000 = 0xca;
      bVar1 = FUN_cbfe(bVar1);
    }
  }
  else {
    uStack0000 = 0xca;
    FUN_c93e(bVar1);
    param_1 = param_1 ^ 2;
    bVar1 = (&DAT_0522)[param_1] - DAT_001c;
    bVar2 = ~(&DAT_0522)[param_1];
    bVar1 = ((&DAT_0523)[param_1] - DAT_001d) -
            (((DAT_001c & (bVar2 | bVar1) | bVar1 & bVar2) & 0x80) == 0);
    bVar2 = ~(&DAT_0523)[param_1];
    if (((DAT_001d & (bVar2 | bVar1) | bVar1 & bVar2) & 0x80) == 0) {
      uStack0000 = 0xca;
      FUN_cd06(5);
      uStack0000 = 0xca;
      FUN_c93e();
      param_1 = param_1 ^ 2;
      bVar1 = (&DAT_0522)[param_1] - DAT_001c;
      bVar2 = ~(&DAT_0522)[param_1];
      bVar1 = ((&DAT_0523)[param_1] - DAT_001d) -
              (((DAT_001c & (bVar2 | bVar1) | bVar1 & bVar2) & 0x80) == 0);
      bVar2 = ~(&DAT_0523)[param_1];
      if (((DAT_001d & (bVar2 | bVar1) | bVar1 & bVar2) & 0x80) == 0) {
        uStack0000 = 0xca;
        bVar1 = FUN_cb4d(bVar1);
      }
    }
  }
LAB_cac2:
  uStack0000 = 0xca;
  FUN_f25f(bVar1,0x31);
  DAT_0000 = DAT_050e * '\x02';
  if (*(char *)((byte)(DAT_050e * '\x06' + 4) + 0x9ba4) != -1) {
    uStack0000 = 0xca;
    FUN_c93e();
    if ((*(char *)(param_1 + 0x527) != '\0') || (0x31 < *(byte *)(param_1 + 0x526))) {
      bVar1 = 0;
      bVar4 = false;
      bVar2 = 0;
      do {
        uStack0000 = 0xca;
        FUN_cc92();
        if ((!bVar4) && (((&DAT_6fa1)[bVar2] & 0xf) == 6)) {
          bVar1 = bVar1 + 1;
        }
        bVar3 = bVar2 + 1;
        bVar4 = (char)(bVar2 - 0x13) < '\0';
        bVar2 = bVar3;
      } while (bVar3 < 0x14);
      if (bVar1 < 2) {
        bVar4 = false;
        bVar2 = 0;
        DAT_0010 = bVar1;
        do {
          uStack0000 = 0xcb;
          FUN_cc92();
          if (((!bVar4) && ((&DAT_6fa1)[bVar2] != 0)) && ((byte)(&DAT_6fa1)[bVar2] < 5)) {
            uStack0000 = 0xcb;
            FUN_cc19();
          }
          bVar1 = bVar2 + 1;
          bVar4 = (char)(bVar2 - 0x13) < '\0';
          bVar2 = bVar1;
        } while (bVar1 < 0x14);
      }
    }
  }
  uStack0000 = 0xcb;
  FUN_ccaa();
  bVar2 = (DAT_001d - 3) -
          (((~DAT_001c & 0xe8 | DAT_001c + 0x18 & 0xe8 | DAT_001c + 0x18 & ~DAT_001c) & 0x80) == 0);
  if ((bVar2 & ~DAT_001d & 0x80) == 0) {
    bVar2 = (DAT_001b - 0x13) -
            (((~DAT_001a & 0x88 | DAT_001a + 0x78 & 0x88 | DAT_001a + 0x78 & ~DAT_001a) & 0x80) == 0
            );
    if ((bVar2 & ~DAT_001b & 0x80) != 0) {
      FUN_cbfe(bVar2);
      return;
    }
    FUN_cb9a();
    return;
  }
  FUN_cb9a(bVar2);
  return;
}



/* 0xcb4d FUN_cb4d */

void FUN_cb4d(void)

{
  byte bVar1;
  byte bVar2;
  bool bVar3;
  undefined1 uStack0000;
  
  bVar3 = false;
  bVar1 = 0;
  do {
    uStack0000 = 0xcb;
    FUN_cc92();
    if ((!bVar3) && (((&DAT_6fa1)[bVar1] == '\x01' || ((&DAT_6fa1)[bVar1] == '\x02')))) {
      (&DAT_6fa1)[bVar1] = 4;
    }
    bVar2 = bVar1 + 1;
    bVar3 = (char)(bVar1 - 0x13) < '\0';
    bVar1 = bVar2;
  } while (bVar2 < 0x14);
  return;
}



/* 0xcb6a FUN_cb6a */

void FUN_cb6a(void)

{
  byte bVar1;
  byte bVar2;
  byte bVar3;
  bool bVar4;
  undefined1 uStack0000;
  
  bVar1 = 0;
  do {
    DAT_001a = (&DAT_cb96)[bVar1];
    bVar4 = false;
    bVar2 = 0;
    do {
      uStack0000 = 0xcb;
      FUN_a944();
      if ((!bVar4) && ((&DAT_6fa1)[bVar2] == DAT_001a)) {
        (&DAT_6fa1)[bVar2] = (&DAT_6fa1)[bVar2] << 4 | 5;
        return;
      }
      bVar3 = bVar2 + 1;
      bVar4 = (char)(bVar2 - 0x13) < '\0';
      bVar2 = bVar3;
    } while (bVar3 < 0x14);
    bVar1 = bVar1 + 1;
    if (3 < bVar1) {
      return;
    }
  } while( true );
}



/* 0xcb9a FUN_cb9a */

void FUN_cb9a(void)

{
  byte bVar1;
  undefined1 uStack0000;
  
  bVar1 = 0;
  DAT_0010 = 0;
  DAT_0011 = 0;
  do {
    uStack0000 = 0xcb;
    FUN_cc92();
    if ((&DAT_6fa1)[bVar1] == '\x01') {
      DAT_0010 = DAT_0010 + 1;
    }
    else if ((&DAT_6fa1)[bVar1] == '\x03') {
      DAT_0011 = DAT_0011 + 1;
    }
    bVar1 = bVar1 + 1;
  } while (bVar1 < 0x14);
  if (DAT_0010 < DAT_6f99) {
    DAT_0000 = 2;
    uStack0000 = 0xcb;
    FUN_cbdf();
  }
  if (DAT_0011 < DAT_6f9b) {
    DAT_0000 = 4;
    uStack0000 = 0xcb;
    FUN_cbdf();
  }
  return;
}



/* 0xcbdf FUN_cbdf */

void FUN_cbdf(void)

{
  byte bVar1;
  byte bVar2;
  bool bVar3;
  undefined1 uStack0000;
  
  bVar3 = false;
  bVar1 = 0;
  while( true ) {
    uStack0000 = 0xcb;
    FUN_cc92();
    if ((!bVar3) && ((&DAT_6fa1)[bVar1] == DAT_0000)) break;
    bVar2 = bVar1 + 1;
    bVar3 = (char)(bVar1 - 0x13) < '\0';
    bVar1 = bVar2;
    if (0x13 < bVar2) {
      return;
    }
  }
  DAT_0000 = DAT_0000 + -1;
  (&DAT_6fa1)[bVar1] = DAT_0000;
  return;
}



/* 0xcbfe FUN_cbfe */

void FUN_cbfe(void)

{
  byte bVar1;
  byte bVar2;
  bool bVar3;
  undefined1 uStack0000;
  
  bVar3 = false;
  bVar1 = 0;
  do {
    uStack0000 = 0xcc;
    FUN_cc92();
    if (((!bVar3) && ((&DAT_6fa1)[bVar1] != 0)) && ((byte)(&DAT_6fa1)[bVar1] < 5)) {
      (&DAT_6fa1)[bVar1] = 1;
    }
    bVar2 = bVar1 + 1;
    bVar3 = (char)(bVar1 - 0x13) < '\0';
    bVar1 = bVar2;
  } while (bVar2 < 0x14);
  return;
}



/* 0xcc19 FUN_cc19 */

/* WARNING: Globals starting with '_' overlap smaller symbols at the same address */

void FUN_cc19(byte param_1)

{
  char cVar1;
  byte bStack0000;
  
  cVar1 = (&DAT_0664)[param_1];
  if (cVar1 != -1) {
    DAT_0011 = cVar1;
    bStack0000 = param_1;
    FUN_f387(cVar1);
    _DAT_0000 = (byte *)(ushort)*_DAT_0000;
    DAT_0002 = 0;
    DAT_0003 = 6;
    FUN_ebe9();
    _DAT_0000 = (byte *)CONCAT11(DAT_0006,DAT_0000);
    DAT_0002 = DAT_0007;
    DAT_0003 = 10;
    DAT_0004 = 0;
    FUN_ea7c();
    DAT_0012 = DAT_0001;
    officer_address(DAT_0011);
    DAT_0011 = *_DAT_0000;
    if (DAT_0011 < DAT_0012) {
      (&DAT_6fa1)[bStack0000] = (&DAT_6fa1)[bStack0000] << 4 | 6;
      DAT_0010 = DAT_0010 + '\x01';
    }
    return;
  }
  return;
}



/* 0xcc92 FUN_cc92 */

undefined1 FUN_cc92(byte param_1)

{
  if (DAT_0504 < '\0') {
    if (*(char *)(param_1 + 0x628) < '\0') {
      return 0;
    }
  }
  else if (-1 < *(char *)(param_1 + 0x628)) {
    return 0;
  }
  return 0x80;
}



/* 0xccaa FUN_ccaa */

/* WARNING: Globals starting with '_' overlap smaller symbols at the same address */

void FUN_ccaa(void)

{
  byte bVar1;
  byte bVar2;
  char cVar3;
  bool bVar4;
  byte bStack0000;
  
  bStack0000 = 0xcc;
  FUN_f25f(0x31);
  bVar2 = 0;
  DAT_001a = 0;
  DAT_001b = 0;
  DAT_001c = 0;
  DAT_001d = 0;
  do {
    cVar3 = (&DAT_0664)[bVar2];
    if (cVar3 != -1) {
      DAT_0002 = cVar3;
      bStack0000 = bVar2;
      officer_address(cVar3);
      bVar2 = bStack0000;
      DAT_0002 = *(byte *)(_DAT_0000 + 8);
      DAT_0003 = *(char *)(_DAT_0000 + 9);
      bVar1 = 0;
      cVar3 = '\0';
      bStack0000 = 0xcc;
      FUN_cc92();
      if (cVar3 != '\0') {
        bVar1 = 2;
      }
      bVar4 = CARRY1(*(byte *)(bVar1 + 0x1a),DAT_0002);
      *(byte *)(bVar1 + 0x1a) = *(byte *)(bVar1 + 0x1a) + DAT_0002;
      *(char *)(bVar1 + 0x1b) = *(char *)(bVar1 + 0x1b) + DAT_0003 + bVar4;
    }
    bVar2 = bVar2 + 1;
  } while (bVar2 < 0x14);
  return;
}



/* 0xcd00 FUN_cd00 */

void FUN_cd00(void)

{
  undefined1 uStack0000;
  
  DAT_001e = '\x1e' - DAT_0506;
  uStack0000 = 0xcd;
  FUN_ccaa();
  DAT_0000 = DAT_001a;
  DAT_0001 = DAT_001b;
  uStack0000 = 0xcd;
  FUN_cd43();
  DAT_001a = DAT_0006;
  DAT_001b = DAT_0007;
  DAT_0000 = DAT_001c;
  DAT_0001 = DAT_001d;
  uStack0000 = 0xcd;
  FUN_cd43();
  DAT_001c = DAT_0006;
  DAT_001d = DAT_0007;
  return;
}



/* 0xcd06 FUN_cd06 */

void FUN_cd06(undefined1 param_1)

{
  undefined1 uStack0000;
  
  uStack0000 = 0xcd;
  DAT_001e = param_1;
  FUN_ccaa();
  DAT_0000 = DAT_001a;
  DAT_0001 = DAT_001b;
  uStack0000 = 0xcd;
  FUN_cd43();
  DAT_001a = DAT_0006;
  DAT_001b = DAT_0007;
  DAT_0000 = DAT_001c;
  DAT_0001 = DAT_001d;
  uStack0000 = 0xcd;
  FUN_cd43();
  DAT_001c = DAT_0006;
  DAT_001d = DAT_0007;
  return;
}



/* 0xcd43 FUN_cd43 */

void FUN_cd43(void)

{
  undefined1 uStack0000;
  
  DAT_0002 = 0;
  DAT_0003 = 4;
  uStack0000 = 0xcd;
  FUN_ebe9();
  DAT_0000 = DAT_0006;
  DAT_0001 = DAT_0007;
  DAT_0002 = DAT_0008;
  DAT_0003 = 0xe8;
  DAT_0004 = 3;
  uStack0000 = 0xcd;
  FUN_eaa5();
  DAT_0003 = DAT_001e;
  FUN_ebe9();
  return;
}



/* 0xcd78 FUN_cd78 */

void FUN_cd78(void)

{
  byte bVar1;
  char cVar2;
  byte bVar3;
  byte bVar4;
  byte bVar5;
  undefined1 uStack0000;
  
  DAT_050a = 0;
  if (0x1e < DAT_0506) {
    DAT_0000 = 0;
    FUN_ceab();
    return;
  }
  uStack0000 = 0xcd;
  FUN_cd06(1);
  bVar5 = DAT_0524 - DAT_001a;
  bVar3 = (DAT_0525 - DAT_001b) -
          (((DAT_001a & (~DAT_0524 | bVar5) | bVar5 & ~DAT_0524) & 0x80) == 0);
  if ((((DAT_001b & (~DAT_0525 | bVar3) | bVar3 & ~DAT_0525) & 0x80) != 0) &&
     ((bVar5 != 0 || (bVar3 != 0)))) {
    bVar1 = DAT_0522 - DAT_001c;
    bVar4 = (DAT_0523 - DAT_001d) -
            (((DAT_001c & (~DAT_0522 | bVar1) | bVar1 & ~DAT_0522) & 0x80) == 0);
    DAT_0524 = bVar5;
    DAT_0525 = bVar3;
    if ((((DAT_001d & (~DAT_0523 | bVar4) | bVar4 & ~DAT_0523) & 0x80) != 0) &&
       ((bVar1 != 0 || (bVar4 != 0)))) {
      DAT_0010 = 0xf;
      DAT_0011 = 1;
      uStack0000 = 0xcd;
      DAT_0522 = bVar1;
      DAT_0523 = bVar4;
      FUN_ce40();
      uStack0000 = 0xcd;
      FUN_cf60();
      if (DAT_052e != '\0') {
        DAT_0010 = 0xf0;
        DAT_0011 = 0x10;
        DAT_000b = 0;
        DAT_000c = 0;
        uStack0000 = 0xce;
        FUN_ce40();
        DAT_000a = 0x6d;
        uStack0000 = 0xce;
        far_call_inline_word(0x2e);
        DAT_00a0 = DAT_00a0 << 1;
      }
      bVar5 = 0;
      while( true ) {
        if ((*(char *)(bVar5 + 0x4db) != -1) &&
           (cVar2 = *(char *)(bVar5 + 0x4db) + -1, *(char *)(bVar5 + 0x4db) = cVar2, cVar2 == '\0'))
        {
          (&DAT_04d8)[bVar5] = 0xff;
        }
        if (bVar5 == 4) break;
        bVar5 = 4;
      }
      return;
    }
    DAT_0522 = 0;
    DAT_0523 = 0;
    FUN_cf06();
    return;
  }
  DAT_0524 = 0;
  DAT_0525 = 0;
  DAT_0000 = 0x80;
  FUN_ceab();
  return;
}



/* 0xce40 FUN_ce40 */

/* WARNING: Globals starting with '_' overlap smaller symbols at the same address */

void FUN_ce40(void)

{
  byte bVar1;
  byte bVar2;
  char cVar3;
  bool bVar4;
  byte bStack0000;
  
  bStack0000 = 0;
  do {
    if (((*(byte *)(bStack0000 + 0x650) != 0) &&
        (bVar2 = *(byte *)(bStack0000 + 0x650) & DAT_0010, bVar2 != 0)) &&
       (*(byte *)(bStack0000 + 0x650) = bVar2 - DAT_0011, DAT_0011 == '\x10')) {
      officer_address((&DAT_0664)[bStack0000]);
      do {
        bVar2 = FUN_e87a();
      } while (0x46 < bVar2);
      DAT_0002 = *(byte *)(_DAT_0000 + 8) - (bVar2 + 0x50);
      bVar1 = ~*(byte *)(_DAT_0000 + 8);
      cVar3 = *(char *)(_DAT_0000 + 9) -
              (((bVar2 + 0x50 & (bVar1 | DAT_0002) | DAT_0002 & bVar1) & 0x80) == 0);
      if (cVar3 < '\0') {
        cVar3 = '\0';
        DAT_0002 = 0;
      }
      *(char *)(_DAT_0000 + 9) = cVar3;
      *(byte *)(_DAT_0000 + 8) = DAT_0002;
      bVar4 = CARRY1(DAT_0002,DAT_000b);
      DAT_000b = DAT_0002 + DAT_000b;
      DAT_000c = DAT_000c + bVar4;
    }
    bStack0000 = bStack0000 + 1;
  } while (bStack0000 < 0x14);
  return;
}



/* 0xceab FUN_ceab */

void FUN_ceab(void)

{
  undefined1 uStack0000;
  
  DAT_052b = DAT_066e;
  if (DAT_050f == '\x03') {
    uStack0000 = 0xce;
    FUN_cf92();
    DAT_0509 = 0;
    DAT_042c = DAT_0507 & 0xf;
    DAT_00a4 = 3;
    DAT_050a = 0xb5;
  }
  else {
    DAT_6f44 = DAT_050f;
    DAT_0509 = 10;
    DAT_042c = DAT_0507 >> 4;
    DAT_00a4 = 4;
    if (DAT_0000 < '\0') {
      DAT_050a = 0xbf;
    }
    else {
      DAT_050a = 0xbe;
    }
  }
  DAT_0514 = 1;
  return;
}



/* 0xcf06 FUN_cf06 */

/* WARNING: Globals starting with '_' overlap smaller symbols at the same address */

void FUN_cf06(void)

{
  undefined1 uStack0000;
  
  DAT_052b = DAT_0664;
  uStack0000 = 0xcf;
  FUN_f368(DAT_0507 & 0xf);
  if (*(char *)(_DAT_0000 + 3) == '\x03') {
    DAT_6f44 = DAT_050f;
    DAT_0509 = 10;
    DAT_042c = DAT_0507 >> 4;
    DAT_00a4 = 3;
    DAT_050a = 0xb5;
  }
  else {
    uStack0000 = 0xcf;
    FUN_cf92();
    DAT_0509 = 0;
    DAT_042c = DAT_0507 & 0xf;
    DAT_00a4 = 4;
    DAT_050a = 0xbf;
  }
  DAT_0514 = 0;
  return;
}



/* 0xcf60 FUN_cf60 */

/* WARNING: Globals starting with '_' overlap smaller symbols at the same address */

void FUN_cf60(void)

{
  byte bVar1;
  undefined1 uStack0000;
  
  bVar1 = 0;
  do {
    if ((&DAT_0664)[bVar1] == 'm') {
      uStack0000 = 0xcf;
      DAT_052f = bVar1;
      officer_address(0x6d);
      if ((*(byte *)(_DAT_0000 + 0xb) & 3) != 3) {
        DAT_052c = *(byte *)(_DAT_0000 + 0xb) & 0xf0;
        DAT_052e = *(undefined1 *)(_DAT_0000 + 1);
      }
      return;
    }
    bVar1 = bVar1 + 1;
  } while (bVar1 < 0x14);
  return;
}



/* 0xcf92 FUN_cf92 */

/* WARNING: Globals starting with '_' overlap smaller symbols at the same address */

void FUN_cf92(void)

{
  undefined1 uStack0000;
  
  uStack0000 = 0xcf;
  FUN_f368(DAT_0507 & 0xf);
  DAT_6f44 = *(undefined1 *)(_DAT_0000 + 3);
  return;
}



/* 0xcfa2 FUN_cfa2 */

void FUN_cfa2(void)

{
  byte bVar1;
  undefined1 uStack0000;
  
  if ((((DAT_008f == '\0') && (DAT_04c8 == '\0')) && (DAT_0500 < 0xc)) && ((DAT_005e & 0x20) != 0))
  {
    DAT_000a = 0x20;
    DAT_000c = 0xb0;
    DAT_0000 = 0x3c;
    DAT_0001 = 0xd1;
    DAT_0002 = 0;
    uStack0000 = 0xcf;
    FUN_f1ad();
    DAT_0000 = 0x5d;
    if ((DAT_005e & 0x40) == 0) {
      DAT_0000 = 0x6e;
    }
    DAT_0001 = 0xd1;
    uStack0000 = 0xcf;
    FUN_f1ad();
    DAT_0001 = DAT_0505;
    DAT_0002 = 0;
    DAT_0003 = 0;
    uStack0000 = 0xd0;
    FUN_e9ba();
    if (DAT_0007 >> 4 != 0) {
      DAT_000a = 0x20;
      DAT_000c = 0xe0;
      uStack0000 = 0xd0;
      FUN_d126(DAT_0007 >> 4);
    }
    DAT_000a = 0x20;
    DAT_000c = 0xe8;
    uStack0000 = 0xd0;
    FUN_d126(DAT_0007 & 0xf);
    DAT_0001 = DAT_0506;
    DAT_0002 = 0;
    DAT_0003 = 0;
    uStack0000 = 0xd0;
    FUN_e9ba();
    if (DAT_0007 >> 4 != 0) {
      DAT_000a = 0x10;
      DAT_000c = 0xd0;
      uStack0000 = 0xd0;
      FUN_d126(DAT_0007 >> 4);
    }
    DAT_000a = 0x10;
    DAT_000c = 0xd8;
    uStack0000 = 0xd0;
    FUN_d126(DAT_0007 & 0xf);
    if ((DAT_005e & 0x40) == 0) {
      bVar1 = 0;
      if (DAT_0504 < '\0') {
        bVar1 = 2;
      }
      DAT_0001 = (&DAT_0522)[bVar1];
      DAT_0002 = (&DAT_0523)[bVar1];
      DAT_0003 = 0;
      uStack0000 = 0xd0;
      FUN_e9ba();
    }
    else {
      bVar1 = 0;
      if (DAT_0504 < '\0') {
        bVar1 = 2;
      }
      DAT_0001 = *(undefined1 *)(bVar1 + 0x526);
      DAT_0002 = *(undefined1 *)(bVar1 + 0x527);
      DAT_0003 = 0;
      uStack0000 = 0xd0;
      FUN_e9ba();
    }
    DAT_0011 = '\0';
    DAT_0010 = 0x40;
    if (DAT_0008 >> 4 != 0) {
      DAT_0011 = '\x01';
      DAT_000a = 0x40;
      DAT_000c = 0xd0;
      uStack0000 = 0xd0;
      FUN_d126(DAT_0008 >> 4);
    }
    if (((DAT_0008 & 0xf) != 0) || (DAT_0011 != '\0')) {
      DAT_0011 = DAT_0011 + '\x01';
      DAT_000a = DAT_0010;
      DAT_000c = 0xd8;
      uStack0000 = 0xd0;
      FUN_d126();
    }
    if ((DAT_0007 >> 4 != 0) || (DAT_0011 != '\0')) {
      DAT_000a = DAT_0010;
      DAT_000c = 0xe0;
      uStack0000 = 0xd1;
      FUN_d126(DAT_0007 >> 4);
    }
    DAT_000a = DAT_0010;
    DAT_000c = 0xe8;
    uStack0000 = 0xd1;
    FUN_d126(DAT_0007 & 0xf);
    return;
  }
  return;
}



/* 0xd126 FUN_d126 */

void FUN_d126(char param_1)

{
  DAT_0000 = (&DAT_d17f)[(byte)(param_1 << 1)];
  DAT_0001 = (&DAT_d180)[(byte)(param_1 << 1)];
  DAT_0002 = 0;
  FUN_f1ad();
  return;
}



/* 0xd1ed FUN_d1ed */

void FUN_d1ed(void)

{
  ushort uVar1;
  byte bVar2;
  byte bVar3;
  byte bStack0000;
  
  if ((DAT_008f == '\0') && (DAT_0500 < 0xc)) {
    bStack0000 = 0xd1;
    FUN_d2f5();
    if (DAT_0061 != '\a') {
      bStack0000 = 0xd2;
      FUN_f25f(0x31);
      bVar3 = (DAT_050e & 0x7f) >> 6;
      bVar2 = DAT_050e << 2;
      DAT_000a = *(undefined1 *)(bVar2 + 0x9d58);
      DAT_000b = *(undefined1 *)(bVar2 + 0x9d59);
      DAT_000c = *(char *)(bVar2 + 0x9d5a);
      DAT_000d = *(undefined1 *)(bVar2 + 0x9d5b);
      bStack0000 = 0xd2;
      FUN_d337();
      if (bVar3 != 0) {
        DAT_0000 = 0x15;
        DAT_0001 = 0xd3;
        DAT_0002 = 0;
        DAT_0003 = 0;
        DAT_0004 = 0x9c;
        bStack0000 = 0xd2;
        FUN_f09c();
      }
      bStack0000 = 0xd2;
      FUN_f25f(0x31);
      bStack0000 = DAT_050e * '\x06';
      if (-1 < *(char *)(bStack0000 + 0x9ba4)) {
        DAT_000a = *(undefined1 *)(bStack0000 + 0x9ba5);
        DAT_000c = *(char *)(bStack0000 + 0x9ba4);
        FUN_d296();
      }
      if (-1 < *(char *)(bStack0000 + 0x9ba6)) {
        DAT_000a = *(undefined1 *)(bStack0000 + 0x9ba7);
        DAT_000c = *(char *)(bStack0000 + 0x9ba6);
        FUN_d296();
      }
      uVar1 = (ushort)bStack0000;
      if (-1 < *(char *)(uVar1 + 0x9ba8)) {
        DAT_000a = *(undefined1 *)(bStack0000 + 0x9ba9);
        bStack0000 = 0xd2;
        DAT_000c = *(char *)(uVar1 + 0x9ba8);
        FUN_d296();
      }
      return;
    }
  }
  return;
}



/* 0xd296 FUN_d296 */

void FUN_d296(void)

{
  byte bVar1;
  byte bVar2;
  byte bVar3;
  byte bVar4;
  char cVar5;
  undefined1 uStack0000;
  
  bVar4 = DAT_000a >> 7;
  bVar1 = DAT_000a & 0x7f;
  bVar2 = DAT_000a & 0x3f;
  bVar3 = DAT_000a & 0x1f;
  DAT_000a = DAT_000a << 4;
  DAT_000b = ((bVar4 << 1 | bVar1 >> 6) << 1 | bVar2 >> 5) << 1 | bVar3 >> 4;
  bVar4 = DAT_000c >> 7;
  bVar1 = DAT_000c & 0x7f;
  bVar2 = DAT_000c & 0x3f;
  bVar3 = DAT_000c & 0x1f;
  DAT_000c = DAT_000c << 4;
  cVar5 = '\0';
  DAT_000d = ((bVar4 << 1 | bVar1 >> 6) << 1 | bVar2 >> 5) << 1 | bVar3 >> 4;
  uStack0000 = 0xd2;
  FUN_d337();
  if (cVar5 != '\0') {
    DAT_0000 = 0x26;
    DAT_0001 = 0xd3;
    DAT_0002 = 0;
    DAT_0003 = 0;
    DAT_0004 = 0x9c;
    FUN_f09c();
    return;
  }
  return;
}



/* 0xd2f5 FUN_d2f5 */

void FUN_d2f5(void)

{
  DAT_00b2 = 0x88;
  if ((DAT_005e & 0x10) != 0) {
    DAT_00b2 = 0x8b;
  }
  DAT_00d6 = DAT_00b2;
  if (DAT_04c8 == '\0') {
    DAT_00c2 = DAT_00b2;
    DAT_00c6 = DAT_00b2;
    DAT_00d2 = DAT_00b2;
  }
  return;
}



/* 0xd337 FUN_d337 */

void FUN_d337(void)

{
  byte bVar1;
  
  DAT_0001 = DAT_000b >> 1;
  DAT_0000 = (byte)(DAT_000a >> 1 | DAT_000b << 7) >> 3;
  DAT_0003 = DAT_000d >> 1;
  DAT_0002 = (byte)(DAT_000c >> 1 | DAT_000d << 7) >> 3;
  bVar1 = 0;
  while ((*(byte *)(bVar1 + 0x600) != DAT_0002 || (*(byte *)(bVar1 + 0x614) != DAT_0000))) {
    bVar1 = bVar1 + 1;
    if (0x13 < bVar1) {
      return;
    }
  }
  if ((DAT_005e & 0x40) == 0) {
    return;
  }
  return;
}



/* 0xd390 FUN_d390 */

/* WARNING: Globals starting with '_' overlap smaller symbols at the same address */

void FUN_d390(void)

{
  byte bVar1;
  undefined1 uStack0000;
  
  uStack0000 = 0xd3;
  officer_address(DAT_042c);
  bVar1 = *(byte *)(_DAT_0000 + 0xb) >> 4;
  if (bVar1 == 3) {
    bVar1 = 0;
  }
  else if (bVar1 == 4) {
    bVar1 = 0xb;
  }
  else if (bVar1 == 5) {
    bVar1 = 0x11;
  }
  else {
    if (bVar1 != 6) {
      DAT_042d = 0xff;
      return;
    }
    bVar1 = 0x14;
  }
  while( true ) {
    if ((&DAT_d3d8)[bVar1] == -1) {
      DAT_042d = 0xff;
      return;
    }
    if ((&DAT_d3d8)[bVar1] == DAT_042c) break;
    bVar1 = bVar1 + 1;
  }
  return;
}



/* 0xd3ee FUN_d3ee */

/* WARNING: Globals starting with '_' overlap smaller symbols at the same address */

void FUN_d3ee(void)

{
  byte bVar1;
  char cVar2;
  undefined1 uStack0000;
  
  bVar1 = 0xf;
  do {
    *(undefined1 *)(bVar1 + 0x580) = 0xff;
    bVar1 = bVar1 - 1;
  } while (-1 < (char)bVar1);
  DAT_0010 = (&DAT_0664)[DAT_050a];
  uStack0000 = 0xd4;
  officer_address();
  DAT_0011 = *(byte *)(_DAT_0000 + 0xb) >> 4;
  if (((((DAT_0010 == -0x5f) || (DAT_0010 == 'c')) || (DAT_0010 == -0x59)) ||
      (((((DAT_0010 == '\x16' || (DAT_0010 == -0x3c)) ||
         ((DAT_0010 == -0x25 || ((DAT_0010 == -0x16 || (DAT_0010 == 'k')))))) || (DAT_0010 == -0x32)
        ) || ((DAT_0010 == -0x15 || (DAT_0010 == -0x49)))))) && (2 < DAT_0011)) {
    cVar2 = '\x05';
    goto LAB_d4e6;
  }
  if (((((DAT_0010 == '\x18') || (DAT_0010 == '7')) || (DAT_0010 == 'p')) ||
      ((DAT_0010 == -0x2b || (DAT_0010 == 'n')))) || (DAT_0010 == 'g')) {
    if (3 < DAT_0011) {
      cVar2 = '\x06';
      goto LAB_d4e6;
    }
    if (2 < DAT_0011) {
      cVar2 = '\x05';
      goto LAB_d4e6;
    }
  }
  if (((DAT_0010 == -0x3b) || (DAT_0010 == 'V')) || (DAT_0010 == ']')) {
    if (4 < DAT_0011) {
      cVar2 = '\a';
      goto LAB_d4e6;
    }
    if (3 < DAT_0011) {
      cVar2 = '\x06';
      goto LAB_d4e6;
    }
    if (2 < DAT_0011) {
      cVar2 = '\x05';
      goto LAB_d4e6;
    }
  }
  if (DAT_0010 == 'm') {
    cVar2 = '\b';
    if ((((5 < DAT_0011) || (cVar2 = '\a', 4 < DAT_0011)) || (cVar2 = '\x06', 3 < DAT_0011)) ||
       (cVar2 = '\x05', 2 < DAT_0011)) goto LAB_d4e6;
  }
  uStack0000 = 0xd4;
  officer_address(DAT_0010);
  bVar1 = *(byte *)(_DAT_0000 + 2);
  cVar2 = '\0';
  if (((0x27 < bVar1) && (cVar2 = '\x01', 0x3b < bVar1)) &&
     ((cVar2 = '\x02', 0x4a < bVar1 && (cVar2 = '\x03', 0x54 < bVar1)))) {
    cVar2 = '\x04';
  }
LAB_d4e6:
  _DAT_0000 = CONCAT11((&DAT_d50a)[(byte)(cVar2 << 1)],(&DAT_d509)[(byte)(cVar2 << 1)]);
  for (bVar1 = 0; *(char *)(_DAT_0000 + (ushort)bVar1) != -1; bVar1 = bVar1 + 1) {
    *(char *)(bVar1 + 0x580) = *(char *)(_DAT_0000 + (ushort)bVar1);
  }
  DAT_0542 = bVar1 - 1;
  return;
}



/* 0xd57b FUN_d57b */

void FUN_d57b(void)

{
  byte bVar1;
  byte bVar2;
  
  if (0xb < DAT_0500) {
    return;
  }
  DAT_0000 = 0;
  bVar2 = DAT_0508;
  if ((char)DAT_0508 < '\0') {
    bVar1 = DAT_008e + 2;
    if ((0xfd < DAT_008e) ||
       (DAT_009c = DAT_009c & 0xbf | 0x80, DAT_008e = bVar1, bVar2 = DAT_0508 | 0x80,
       (bVar1 & 0xe) == 0)) {
      bVar2 = DAT_0508 & 0x7f;
    }
  }
  DAT_0508 = bVar2;
  bVar2 = DAT_0508;
  if ((char)(DAT_0508 << 1) < '\0') {
    bVar1 = DAT_008e - 2;
    if (((bVar1 & ~DAT_008e & 0x80) == 0) ||
       (DAT_009c = DAT_009c & 0x7f | 0x40, DAT_008e = bVar1, bVar2 = DAT_0508 | 0x40,
       (bVar1 & 0xe) == 0)) {
      bVar2 = DAT_0508 & 0xbf;
    }
  }
  DAT_0508 = bVar2;
  bVar2 = DAT_0508;
  if ((char)(DAT_0508 << 2) < '\0') {
    bVar1 = DAT_0090 - 2;
    if (((bVar1 & ~DAT_0090 & 0x80) == 0) ||
       (DAT_009c = DAT_009c & 0xdf | 0x10, DAT_0090 = bVar1, bVar2 = DAT_0508 | 0x20,
       (bVar1 & 0xe) == 0)) {
      bVar2 = DAT_0508 & 0xdf;
    }
  }
  DAT_0508 = bVar2;
  bVar2 = DAT_0508;
  if ((char)(DAT_0508 << 3) < '\0') {
    bVar1 = DAT_0090 + 2;
    if ((0x8f < bVar1) ||
       (DAT_009c = DAT_009c & 0xef | 0x20, DAT_0090 = bVar1, bVar2 = DAT_0508 | 0x10,
       (bVar1 & 0xe) == 0)) {
      bVar2 = DAT_0508 & 0xef;
    }
  }
  DAT_0508 = bVar2;
  return;
}



/* 0xd66e FUN_d66e */

/* WARNING: Globals starting with '_' overlap smaller symbols at the same address */

void FUN_d66e(void)

{
  undefined1 uStack0000;
  
  DAT_0514 = 0;
  DAT_052b = DAT_0664;
  if (DAT_050f == '\x03') {
    uStack0000 = 0xd6;
    FUN_f368(DAT_0507 & 0xf);
    DAT_6f44 = *(char *)(_DAT_0000 + 3);
    DAT_0509 = 0;
    DAT_042c = DAT_0507 & 0xf;
    DAT_00a4 = 4;
    DAT_050a = 0x51;
  }
  else {
    DAT_6f44 = DAT_050f;
    DAT_042c = DAT_0507 >> 4;
    DAT_00a4 = 3;
    DAT_050a = 0x50;
  }
  DAT_0500 = 7;
  DAT_0501 = 2;
  return;
}



/* 0xd6cd FUN_d6cd */

void FUN_d6cd(void)

{
  byte bVar1;
  
  bVar1 = DAT_0000;
  *(undefined1 *)(DAT_0000 + 0x600) = 0xff;
  *(undefined1 *)(bVar1 + 0x614) = 0xff;
  *(undefined1 *)(bVar1 + 0x628) = 0xff;
  *(undefined1 *)(bVar1 + 0x63c) = 0xff;
  *(undefined1 *)(bVar1 + 0x650) = 0xff;
  (&DAT_0664)[bVar1] = 0xff;
  (&DAT_6fa1)[bVar1] = 0xff;
  bVar1 = 0;
  if ((DAT_04d8 != DAT_0000) && (bVar1 = 4, DAT_04dc != DAT_0000)) {
    return;
  }
  DAT_0001 = bVar1 + 4;
  do {
    (&DAT_04d8)[bVar1] = 0xff;
    bVar1 = bVar1 + 1;
  } while (bVar1 < DAT_0001);
  return;
}



/* 0xd70f FUN_d70f */

void FUN_d70f(void)

{
  undefined1 uStack0000;
  
  uStack0000 = 0xd7;
  FUN_db10();
  uStack0000 = 0xd7;
  FUN_db62();
  uStack0000 = 0xd7;
  FUN_dbb4();
  uStack0000 = 0xd7;
  FUN_dbff();
  uStack0000 = 0xd7;
                    /* WARNING: Subroutine does not return */
  tail_dispatch_inline_table(DAT_0540);
}



/* 0xdb10 FUN_db10 */

void FUN_db10(void)

{
  undefined1 uStack0000;
  
  if (DAT_0541 == '\x01') {
    if ((char)(&DAT_db51)[DAT_0545] < '\0') {
      if ((DAT_6fea & 1) == 0) {
        DAT_6fea = DAT_6fea | 1;
        uStack0000 = 0xdb;
        FUN_e693(0x62);
      }
      return;
    }
    if ((DAT_0083 & (&DAT_db51)[DAT_0545]) == 0) {
      DAT_0545 = 0;
      return;
    }
    if ((DAT_0081 & (&DAT_db5a)[DAT_0545]) != 0) {
      DAT_0545 = DAT_0545 + 1;
    }
  }
  return;
}



/* 0xdb62 FUN_db62 */

void FUN_db62(void)

{
  undefined1 uStack0000;
  
  if (DAT_0541 == '\x03') {
    if ((char)(&DAT_dba3)[DAT_0546] < '\0') {
      if ((DAT_6fea & 2) == 0) {
        DAT_6fea = DAT_6fea | 2;
        uStack0000 = 0xdb;
        FUN_e693(0x62);
      }
      return;
    }
    if ((DAT_0085 & (&DAT_dba3)[DAT_0546]) == 0) {
      DAT_0546 = 0;
      return;
    }
    if ((DAT_0082 & (&DAT_dbac)[DAT_0546]) != 0) {
      DAT_0546 = DAT_0546 + 1;
    }
  }
  return;
}



/* 0xdbb4 FUN_dbb4 */

void FUN_dbb4(void)

{
  undefined1 uStack0000;
  
  if ((char)(&DAT_dbee)[DAT_0547] < '\0') {
    if ((DAT_6fea & 4) == 0) {
      DAT_6fea = DAT_6fea | 4;
      uStack0000 = 0xdb;
      FUN_e693(0x62);
    }
    return;
  }
  if ((DAT_0083 & (&DAT_dbee)[DAT_0547]) == 0) {
    DAT_0547 = 0;
    return;
  }
  if ((DAT_0081 & (&DAT_dbf7)[DAT_0547]) != 0) {
    DAT_0547 = DAT_0547 + 1;
  }
  return;
}



/* 0xdbff FUN_dbff */

void FUN_dbff(void)

{
  undefined1 uStack0000;
  
  if ((char)(&DAT_dc39)[DAT_0548] < '\0') {
    if ((DAT_6fea & 8) == 0) {
      DAT_6fea = DAT_6fea | 8;
      uStack0000 = 0xdc;
      FUN_e693(0x62);
    }
    return;
  }
  if ((DAT_0083 & (&DAT_dc39)[DAT_0548]) == 0) {
    DAT_0548 = 0;
    return;
  }
  if ((DAT_0081 & (&DAT_dc42)[DAT_0548]) != 0) {
    DAT_0548 = DAT_0548 + 1;
  }
  return;
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
  thunk_FUN_d3ee();
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
  LAB_c000 = (&DAT_e567)[bVar1];
  DAT_00e7 = (&DAT_e567)[(byte)(bVar1 + 1)];
  DAT_c800 = (&DAT_e567)[(byte)(bVar1 + 1)];
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



/* 0xe693 FUN_e693 */

void FUN_e693(char param_1)

{
  char cStack0000;
  
  cStack0000 = param_1;
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
  
  LAB_c000 = 0xe0;
  DAT_c800 = 0xe1;
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



/* 0xe87a FUN_e87a */

undefined1 FUN_e87a(undefined1 param_1)

{
  ushort uVar1;
  
  DAT_0051 = param_1;
  uVar1 = (ushort)DAT_0050;
  DAT_0050 = DAT_0050 + 1;
  return (&DAT_e8ba)[uVar1];
}



/* 0xe9ba FUN_e9ba */

void FUN_e9ba(void)

{
  byte bVar1;
  byte bVar2;
  byte bVar3;
  bool bVar4;
  
  DAT_0007 = 0;
  DAT_0008 = '\0';
  DAT_0009 = '\0';
  bVar3 = DAT_0001;
  bVar1 = DAT_0002;
  bVar2 = DAT_0003;
  do {
    DAT_0003 = bVar2;
    DAT_0002 = bVar1;
    DAT_0001 = bVar3;
    bVar1 = (DAT_0002 + 0xbe) - ((DAT_0001 - 0x40 & ~DAT_0001 & 0x80) == 0);
    bVar2 = (DAT_0003 - 0xf) - ((bVar1 & ~DAT_0002 & 0x80) == 0);
    bVar3 = DAT_0001 - 0x40;
  } while ((bVar2 & ~DAT_0003 & 0x80) != 0);
  do {
    bVar1 = DAT_0001 + 0x60;
    bVar2 = (DAT_0002 + 0x7a) -
            (((~DAT_0001 & 0xa0 | bVar1 & 0xa0 | bVar1 & ~DAT_0001) & 0x80) == 0);
    bVar3 = (DAT_0003 - 1) - (((~DAT_0002 & 0x86 | bVar2 & 0x86 | bVar2 & ~DAT_0002) & 0x80) == 0);
    bVar4 = (bVar3 & ~DAT_0003 & 0x80) != 0;
    if (!bVar4) break;
    DAT_0009 = DAT_0009 + '\x0f' + bVar4;
    DAT_0001 = bVar1;
    DAT_0002 = bVar2;
    DAT_0003 = bVar3;
  } while (DAT_0009 != '\0');
  do {
    bVar1 = DAT_0001 - 0x10;
    DAT_0005 = (DAT_0002 - 0x27) - ((bVar1 & ~DAT_0001 & 0x80) == 0);
    bVar2 = DAT_0003 - ((DAT_0005 & ~DAT_0002 & 0x80) == 0);
    if ((bVar2 & ~DAT_0003 & 0x80) == 0) break;
    DAT_0009 = DAT_0009 + '\x01';
    DAT_0001 = bVar1;
    DAT_0002 = DAT_0005;
    DAT_0003 = bVar2;
  } while (DAT_0009 != '\0');
  do {
    bVar1 = DAT_0001 + 0x18;
    bVar2 = (DAT_0002 - 3) - (((~DAT_0001 & 0xe8 | bVar1 & 0xe8 | bVar1 & ~DAT_0001) & 0x80) == 0);
    bVar4 = (bVar2 & ~DAT_0002 & 0x80) != 0;
    if (!bVar4) break;
    DAT_0008 = DAT_0008 + '\x0f' + bVar4;
    DAT_0001 = bVar1;
    DAT_0002 = bVar2;
  } while (DAT_0008 != '\0');
  do {
    bVar1 = DAT_0001 + 0x9c;
    bVar2 = DAT_0002 - ((bVar1 & ~DAT_0001 & 0x80) == 0);
    if ((bVar2 & ~DAT_0002 & 0x80) == 0) break;
    DAT_0008 = DAT_0008 + '\x01';
    DAT_0001 = bVar1;
    DAT_0002 = bVar2;
  } while (DAT_0008 != '\0');
  do {
    DAT_0004 = DAT_0001 - 10;
    bVar1 = DAT_0002 - ((DAT_0004 & ~DAT_0001 & 0x80) == 0);
    bVar4 = (bVar1 & ~DAT_0002 & 0x80) != 0;
    if (!bVar4) break;
    DAT_0007 = DAT_0007 + 0xf + bVar4;
    DAT_0001 = DAT_0004;
    DAT_0002 = bVar1;
  } while (DAT_0007 != 0);
  DAT_0007 = DAT_0001 | DAT_0007;
  return;
}



/* 0xea7c FUN_ea7c */

void FUN_ea7c(void)

{
  char cVar1;
  byte bVar2;
  byte bVar3;
  
  DAT_0005 = 0;
  DAT_0006 = 0;
  cVar1 = '\x0f';
  do {
    bVar2 = DAT_0001 >> 7;
    DAT_0001 = DAT_0001 * '\x02';
    bVar3 = DAT_0002 >> 7;
    DAT_0002 = DAT_0002 << 1 | bVar2;
    bVar3 = DAT_0005 << 1 | bVar3;
    DAT_0006 = DAT_0006 << 1 | DAT_0005 >> 7;
    DAT_0007 = bVar3 - DAT_0003;
    bVar2 = (DAT_0006 - DAT_0004) -
            (((DAT_0003 & (~bVar3 | DAT_0007) | DAT_0007 & ~bVar3) & 0x80) == 0);
    DAT_0005 = bVar3;
    if (((DAT_0004 & (~DAT_0006 | bVar2) | bVar2 & ~DAT_0006) & 0x80) != 0) {
      DAT_0001 = DAT_0001 + 1;
      DAT_0005 = DAT_0007;
      DAT_0006 = bVar2;
    }
    cVar1 = cVar1 + -1;
  } while (-1 < cVar1);
  return;
}



/* 0xeaa5 FUN_eaa5 */

void FUN_eaa5(void)

{
  byte bVar1;
  char cVar2;
  byte bVar3;
  byte bVar4;
  
  DAT_0005 = 0;
  DAT_0006 = 0;
  DAT_0007 = 0;
  cVar2 = '\x17';
  do {
    bVar3 = DAT_0000 >> 7;
    DAT_0000 = DAT_0000 * '\x02';
    bVar4 = DAT_0001 >> 7;
    DAT_0001 = DAT_0001 << 1 | bVar3;
    bVar3 = DAT_0002 >> 7;
    DAT_0002 = DAT_0002 << 1 | bVar4;
    bVar3 = DAT_0005 << 1 | bVar3;
    bVar4 = DAT_0006 << 1 | DAT_0005 >> 7;
    DAT_0007 = DAT_0007 << 1 | DAT_0006 >> 7;
    DAT_0008 = bVar3 - DAT_0003;
    DAT_0009 = (bVar4 - DAT_0004) -
               (((DAT_0003 & (~bVar3 | DAT_0008) | DAT_0008 & ~bVar3) & 0x80) == 0);
    bVar1 = DAT_0007 - (((DAT_0004 & (~bVar4 | DAT_0009) | DAT_0009 & ~bVar4) & 0x80) == 0);
    DAT_0005 = bVar3;
    DAT_0006 = bVar4;
    if ((bVar1 & ~DAT_0007 & 0x80) != 0) {
      DAT_0000 = DAT_0000 + 1;
      DAT_0005 = DAT_0008;
      DAT_0006 = DAT_0009;
      DAT_0007 = bVar1;
    }
    cVar2 = cVar2 + -1;
  } while (-1 < cVar2);
  return;
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



/* 0xebe9 FUN_ebe9 */

void FUN_ebe9(void)

{
  char cVar1;
  byte bVar2;
  bool bVar3;
  bool bVar4;
  byte bVar5;
  
  cVar1 = '\a';
  DAT_0004 = 0;
  DAT_0005 = 0;
  DAT_0006 = 0;
  DAT_0007 = 0;
  DAT_0008 = 0;
  DAT_0009 = '\0';
  do {
    bVar2 = DAT_0003 & 1;
    DAT_0003 = DAT_0003 >> 1;
    if (bVar2 != 0) {
      bVar3 = CARRY1(DAT_0000,DAT_0006);
      DAT_0006 = DAT_0000 + DAT_0006;
      bVar4 = CARRY1(DAT_0001,DAT_0007);
      DAT_0007 = DAT_0001 + DAT_0007 + bVar3;
      bVar3 = CARRY1(DAT_0002,DAT_0008);
      DAT_0008 = DAT_0002 + DAT_0008 + bVar4;
      DAT_0009 = DAT_0004 + DAT_0009 + bVar3;
    }
    bVar2 = DAT_0000 >> 7;
    DAT_0000 = DAT_0000 << 1;
    bVar5 = DAT_0001 >> 7;
    DAT_0001 = DAT_0001 << 1 | bVar2;
    bVar2 = DAT_0002 >> 7;
    DAT_0002 = DAT_0002 << 1 | bVar5;
    DAT_0004 = DAT_0004 << 1 | bVar2;
    cVar1 = cVar1 + -1;
  } while (-1 < cVar1);
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



/* 0xf09c FUN_f09c */

/* WARNING: Globals starting with '_' overlap smaller symbols at the same address */

byte FUN_f09c(void)

{
  byte bVar1;
  byte bVar2;
  byte bVar3;
  byte bVar4;
  bool bVar5;
  char cVar6;
  
  bVar2 = DAT_000a;
  if (((DAT_0002 & 0x80) == 0x80) && (bVar2 = DAT_000a - 8, 0xef < (byte)(DAT_000a - 8))) {
    DAT_000b = DAT_000b + -1;
    bVar2 = DAT_000a - 0x18;
  }
  DAT_000a = bVar2;
  if (((DAT_0002 & 0x40) == 0x40) &&
     (bVar1 = DAT_000c - 0x10, bVar2 = ~DAT_000c, DAT_000c = bVar1, (bVar1 & bVar2 & 0x80) == 0)) {
    DAT_000d = DAT_000d + -1;
  }
  bVar2 = DAT_000a - DAT_0090;
  bVar5 = ((DAT_0090 & (~DAT_000a | bVar2) | bVar2 & ~DAT_000a) & 0x80) == 0;
  if (bVar5) {
    bVar2 = bVar2 - 0x10;
  }
  DAT_000b = (DAT_000b - DAT_0091) - bVar5;
  bVar1 = DAT_000c - DAT_008e;
  bVar3 = (DAT_000d - DAT_008f) -
          (((DAT_008e & (~DAT_000c | bVar1) | bVar1 & ~DAT_000c) & 0x80) == 0);
  bVar4 = 0;
  DAT_000a = bVar2;
  DAT_000c = bVar1;
  DAT_000d = bVar3;
  while( true ) {
    if (DAT_007c == 0xff) {
      return bVar3;
    }
    DAT_000f = DAT_000b;
    bVar2 = *(byte *)(_DAT_0000 + (ushort)bVar4);
    if (bVar2 == 0x80) break;
    if ((DAT_0002 & 0x80) == 0x80) {
      bVar2 = 8 - *(char *)(_DAT_0000 + (ushort)bVar4);
    }
    if (bVar2 < 0x80) {
      cVar6 = CARRY1(bVar2,DAT_000a);
      DAT_000e = bVar2 + DAT_000a;
    }
    else {
      bVar2 = (bVar2 ^ 0xff) + 1;
      DAT_000e = DAT_000a - bVar2;
      cVar6 = -(((bVar2 & (~DAT_000a | DAT_000e) | DAT_000e & ~DAT_000a) & 0x80) == 0);
    }
    bVar3 = DAT_000b + cVar6;
    if ((bVar3 == 0) && (bVar3 = DAT_000e - 1, bVar3 < DAT_0004)) {
      *(byte *)(DAT_007c + 0x200) = bVar3;
      *(char *)(DAT_007c + 0x201) = *(char *)(_DAT_0000 + (ushort)(byte)(bVar4 + 1)) + DAT_0003;
      *(byte *)(DAT_007c + 0x202) = *(byte *)(_DAT_0000 + (ushort)(byte)(bVar4 + 2)) ^ DAT_0002;
      bVar2 = *(byte *)(_DAT_0000 + (ushort)(byte)(bVar4 + 3));
      if ((DAT_0002 & 0x40) == 0x40) {
        bVar2 = 8 - *(char *)(_DAT_0000 + (ushort)(byte)(bVar4 + 3));
      }
      if ((char)bVar2 < '\0') {
        DAT_000e = bVar2 ^ 0xff;
        bVar3 = DAT_000c - DAT_000e;
        bVar2 = ~DAT_000c;
        bVar1 = DAT_000e & (bVar2 | bVar3);
        *(byte *)(DAT_007c + 0x203) = bVar3;
        bVar3 = DAT_000d - (((bVar1 | bVar3 & bVar2) & 0x80) == 0);
      }
      else {
        bVar5 = CARRY1(bVar2,DAT_000c);
        *(byte *)(DAT_007c + 0x203) = bVar2 + DAT_000c;
        bVar3 = DAT_000d + bVar5;
      }
      if (bVar3 == 0) {
        bVar4 = bVar4 + 4;
        DAT_007c = DAT_007c + 4;
        if (DAT_007c == 0) {
          DAT_007c = 0xff;
        }
      }
      else {
        bVar4 = bVar4 + 4;
      }
    }
    else {
      bVar4 = bVar4 + 4;
    }
  }
  DAT_000f = DAT_000b;
  return 0x80;
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
  bank8_entry_00 = DAT_00b2;
  DAT_a800 = DAT_00b3;
  DAT_b000 = DAT_00b4;
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



/* 0xf368 FUN_f368 */

void FUN_f368(byte param_1)

{
  byte bVar1;
  
  bVar1 = (param_1 & 0xf) << 1;
  DAT_0000 = (&DAT_f379)[bVar1];
  DAT_0001 = (&DAT_f37a)[bVar1];
  return;
}



/* 0xf387 FUN_f387 */

void FUN_f387(void)

{
  byte bVar1;
  undefined1 uStack0000;
  
  uStack0000 = 0xf3;
  bVar1 = FUN_f25f(0x31);
  DAT_0000 = bVar1 * '\f';
  DAT_0001 = (((CARRY1(bVar1 * '\x02',bVar1) - ((char)bVar1 >> 7)) * '\x02' |
              (byte)(bVar1 * '\x03') >> 7) << 1 | (bVar1 * '\x03' & 0x7f) >> 6) + 0x80;
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
  LAB_c000 = 0xe0;
                    /* WARNING: Read-only address (RAM,0xd000) is written */
  uRAMd000 = 0xe0;
  DAT_c800 = 0xe1;
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
  DAT_0050 = DAT_0050 + '\x01';
  cRAM0052 = cRAM0052 + '\x01';
  cRAM0054 = cRAM0054 + '\x01';
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
  thunk_FUN_b130();
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
  LAB_c000 = DAT_00e6;
  DAT_c800 = DAT_00e7;
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



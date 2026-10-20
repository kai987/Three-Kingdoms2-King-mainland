// Ghidra-generated fixed-bank-pair pseudocode. Bank switching and inline pointer dispatch need manual correction. Not original source.

/* 0xa000 bank25_entry_00 */

void bank25_entry_00(byte param_1)

{
  byte bStack0000;
  
  if ((DAT_6fea & 4) != 0) {
    DAT_00a4 = 3;
  }
  if ((DAT_6fea & 8) != 0) {
    DAT_00a4 = 4;
  }
  bStack0000 = 0xce;
  FUN_f25f(0x21);
  if ((param_1 & 1) == 0) {
    DAT_0003 = 0;
    DAT_00b8 = (&DAT_ced6)[DAT_0000];
  }
  else {
    DAT_0003 = 0x40;
    DAT_00b9 = (&DAT_ced6)[DAT_0000];
  }
  DAT_0005 = 0;
  bStack0000 = ((DAT_00a4 & 7) + *(char *)(DAT_0000 + 0x99a0)) * '\x02';
  DAT_0000 = *(undefined1 *)(bStack0000 + 0x9aa0);
  DAT_0001 = *(undefined1 *)(bStack0000 + 0x9aa1);
  DAT_000c = DAT_04bc;
  if (DAT_04bc == '\0') {
    DAT_000c = '\x10';
  }
  DAT_0002 = 0;
  DAT_0004 = 0xa0;
  FUN_f1b7();
  DAT_04bc = 0;
  if ((((-1 < (char)DAT_00a4) && ((DAT_007e & 1) != 0)) && (DAT_0304 != -1)) &&
     ((DAT_0303 == '\0' && ((DAT_005e & 8) != 0)))) {
    DAT_0000 = *(undefined1 *)(bStack0000 + 0x9d64);
    DAT_0001 = *(undefined1 *)(bStack0000 + 0x9d65);
    FUN_f1b7();
    return;
  }
  DAT_0000 = *(undefined1 *)(bStack0000 + 0x9bac);
  DAT_0001 = *(undefined1 *)(bStack0000 + 0x9bad);
  FUN_f1b7();
  return;
}



/* 0xa003 thunk_FUN_a033 */

void thunk_FUN_a033(void)

{
  undefined1 uStack0000;
  
  uStack0000 = 0xa0;
                    /* WARNING: Subroutine does not return */
  tail_dispatch_inline_table(DAT_0401);
}



/* 0xa006 thunk_FUN_c773 */

void thunk_FUN_c773(void)

{
  undefined1 uStack0000;
  
  uStack0000 = 199;
                    /* WARNING: Subroutine does not return */
  tail_dispatch_inline_table(DAT_0401);
}



/* 0xa009 thunk_FUN_a296 */

void thunk_FUN_a296(void)

{
  undefined1 uStack0000;
  
  uStack0000 = 0xa2;
                    /* WARNING: Subroutine does not return */
  tail_dispatch_inline_table(DAT_0401);
}



/* 0xa00c thunk_FUN_ad81 */

void thunk_FUN_ad81(void)

{
  undefined1 uStack0000;
  
  uStack0000 = 0xad;
                    /* WARNING: Subroutine does not return */
  tail_dispatch_inline_table(DAT_0401);
}



/* 0xa00f thunk_FUN_cfd6 */

void thunk_FUN_cfd6(void)

{
  undefined1 uStack0000;
  
  if (((DAT_04c8 != 0) && (DAT_0300 == -1)) && (DAT_0304 == -1)) {
    if (-1 < (char)DAT_04c8) {
      DAT_04c9 = DAT_04c8 - 1;
      DAT_04ca = 0;
      DAT_04c8 = 0x80;
      DAT_04d1 = 7;
      uStack0000 = 0xd4;
                    /* WARNING: Subroutine does not return */
      tail_dispatch_inline_table(0);
    }
    uStack0000 = 0xd0;
                    /* WARNING: Subroutine does not return */
    tail_dispatch_inline_table(DAT_04c8 & 0xf);
  }
  return;
}



/* 0xa012 thunk_FUN_b2d7 */

/* WARNING: Globals starting with '_' overlap smaller symbols at the same address */

void thunk_FUN_b2d7(void)

{
  ushort uVar1;
  byte bVar2;
  bool bVar3;
  byte bStack0000;
  
  uVar1 = _DAT_0000;
  if ((DAT_007e & 4) == 0) {
    _DAT_0000 = _DAT_0000 & 0xff;
    if (-1 < (char)DAT_040d) {
      bStack0000 = DAT_040d;
      DAT_0382 = DAT_040d << 5;
      DAT_0381 = ((((DAT_040d >> 7) << 1 | (DAT_040d & 0x7f) >> 6) << 1 | (DAT_040d & 0x3f) >> 5) <<
                  1 | (DAT_040d & 0x1f) >> 4) << 1 | (DAT_040d & 0xf) >> 3;
      DAT_0380 = 0x20;
      _DAT_0000 = CONCAT11(DAT_040c,(char)uVar1);
      DAT_0002 = 0;
      DAT_0004 = 0;
      DAT_0003 = 3;
      FUN_ea7c();
      bVar3 = CARRY1((&DAT_b4b9)[(byte)(DAT_0005 << 1)],DAT_0382);
      DAT_0382 = (&DAT_b4b9)[(byte)(DAT_0005 << 1)] + DAT_0382;
      DAT_0381 = (&DAT_b4ba)[(byte)(DAT_0005 << 1)] + DAT_0381 + bVar3;
      if (*(char *)(DAT_040c + 0x410) == -2) {
        bStack0000 = 0x10;
      }
      else {
        bStack0000 = bStack0000 << 1;
      }
      _DAT_0000 = CONCAT11((&DAT_b386)[bStack0000],(&DAT_b385)[bStack0000]);
      bVar2 = 0;
      do {
        *(undefined1 *)(bVar2 + 899) = *(undefined1 *)(_DAT_0000 + bVar2);
        bVar2 = bVar2 + 1;
      } while (bVar2 < 0x20);
      bStack0000 = 0xb3;
      FUN_b4bf();
      DAT_03a3 = 0xff;
      DAT_007e = DAT_007e | 4;
      DAT_040d = DAT_040d + 1;
      if (9 < DAT_040d) {
        DAT_040d = 0xff;
      }
      return;
    }
  }
  return;
}



/* 0xa015 thunk_FUN_b7d9 */

/* WARNING: Globals starting with '_' overlap smaller symbols at the same address */

void thunk_FUN_b7d9(void)

{
  byte bVar1;
  char cVar2;
  byte bVar3;
  byte bVar4;
  undefined1 uStack0000;
  
  uStack0000 = 0xb7;
  region_address(DAT_0471);
  bVar4 = 2;
  bVar3 = 0x26;
  do {
    (&DAT_0500)[bVar3] = _DAT_0000[bVar4];
    _DAT_0000[bVar4] = 0;
    bVar4 = bVar4 + 1;
    bVar3 = bVar3 + 1;
    if (bVar3 == 0x28) {
      bVar3 = 0x22;
    }
  } while (bVar4 < 6);
  DAT_0507 = *_DAT_0000;
  _DAT_0000 = (byte *)CONCAT11(DAT_0001 + (0xee < DAT_0000),DAT_0000 + 0x11);
  bVar3 = 9;
  do {
    *(byte *)(bVar3 + 0x664) = _DAT_0000[bVar3];
    _DAT_0000[bVar3] = -1;
    bVar3 = bVar3 - 1;
  } while (-1 < (char)bVar3);
  DAT_066e = DAT_0481;
  bVar4 = 0xb;
  bVar3 = 0;
  do {
    if (bVar3 < 10) {
      cVar2 = (&DAT_0151)[bVar3];
      if (cVar2 != DAT_0481) goto LAB_b83a;
    }
    else {
      cVar2 = -1;
LAB_b83a:
      *(char *)(bVar4 + 0x664) = cVar2;
      bVar4 = bVar4 + 1;
    }
    bVar3 = bVar3 + 1;
  } while (bVar4 < 0x14);
  uStack0000 = 0xb8;
  region_address(DAT_0402);
  DAT_0507 = *_DAT_0000 << 4 | DAT_0507;
  bVar3 = 0;
  do {
    if ((&DAT_0151)[bVar3] == -1) break;
    for (bVar4 = 0x11; _DAT_0000[bVar4] != (&DAT_0151)[bVar3]; bVar4 = bVar4 + 1) {
    }
    _DAT_0000[bVar4] = -1;
    bVar3 = bVar3 + 1;
  } while (bVar3 < 10);
  bVar3 = 0x11;
  DAT_0003 = 0x10;
  do {
    DAT_0002 = _DAT_0000[bVar3];
    _DAT_0000[bVar3] = -1;
    if (DAT_0002 != -1) {
      DAT_0003 = DAT_0003 + 1;
      _DAT_0000[DAT_0003] = DAT_0002;
    }
    bVar3 = bVar3 + 1;
  } while (bVar3 < 0x1b);
  if (_DAT_0000[0x11] == -1) {
    *_DAT_0000 = '\a';
  }
  bVar1 = _DAT_0000[2] - DAT_042f;
  bVar3 = ~_DAT_0000[2];
  bVar4 = DAT_042f & (bVar3 | bVar1);
  _DAT_0000[2] = bVar1;
  _DAT_0000[3] = (_DAT_0000[3] - DAT_0430) - (((bVar4 | bVar1 & bVar3) & 0x80) == 0);
  bVar1 = _DAT_0000[4] - DAT_0432;
  bVar3 = ~_DAT_0000[4];
  bVar4 = DAT_0432 & (bVar3 | bVar1);
  _DAT_0000[4] = bVar1;
  _DAT_0000[5] = (_DAT_0000[5] - DAT_0433) - (((bVar4 | bVar1 & bVar3) & 0x80) == 0);
  return;
}



/* 0xa018 thunk_FUN_b8d7 */

/* WARNING: Globals starting with '_' overlap smaller symbols at the same address */

byte thunk_FUN_b8d7(void)

{
  byte bVar1;
  undefined1 uStack0000;
  
  uStack0000 = 0xb8;
  region_address(DAT_0470);
  DAT_0498 = *(undefined1 *)(_DAT_0000 + 2);
  DAT_0499 = *(undefined1 *)(_DAT_0000 + 3);
  DAT_049a = *(undefined1 *)(_DAT_0000 + 4);
  DAT_049b = *(undefined1 *)(_DAT_0000 + 5);
  DAT_049c = *(byte *)(_DAT_0000 + 0x10);
  DAT_049d = 0;
  uStack0000 = 0xb9;
  region_address(DAT_0471);
  DAT_0010._0_1_ = 0xf - *(byte *)(_DAT_0000 + 2);
  DAT_0010._1_1_ =
       ('\'' - *(char *)(_DAT_0000 + 3)) -
       (((*(byte *)(_DAT_0000 + 2) & ((byte)DAT_0010 | 0xf0) | (byte)DAT_0010 & 0xf0) & 0x80) == 0);
  uStack0000 = 0xb9;
  FUN_b948(0);
  DAT_0010._0_1_ = 0xf - *(byte *)(_DAT_0000 + 4);
  DAT_0010._1_1_ =
       ('\'' - *(char *)(_DAT_0000 + 5)) -
       (((*(byte *)(_DAT_0000 + 4) & ((byte)DAT_0010 | 0xf0) | (byte)DAT_0010 & 0xf0) & 0x80) == 0);
  uStack0000 = 0xb9;
  FUN_b948(2);
  DAT_0010._0_1_ = 99 - *(char *)(_DAT_0000 + 0x10);
  DAT_0010._1_1_ = 0;
  bVar1 = -(((DAT_049c & (~(byte)DAT_0010 | (byte)DAT_0010 - DAT_049c) |
             (byte)DAT_0010 - DAT_049c & ~(byte)DAT_0010) & 0x80) == 0) - DAT_049d;
  if (((DAT_049d | bVar1) & 0x80) == 0) {
    bVar1 = 0;
    DAT_049d = 0;
    DAT_049c = (byte)DAT_0010;
  }
  return bVar1;
}



/* 0xa01b thunk_FUN_b964 */

/* WARNING: Globals starting with '_' overlap smaller symbols at the same address */

void thunk_FUN_b964(void)

{
  byte bVar1;
  byte bVar2;
  undefined1 uStack0000;
  
  uStack0000 = 0xb9;
  FUN_f25f(0x31);
  _DAT_0000 = (ushort)DAT_0402;
  _DAT_0002 = 0x1400;
  uStack0000 = 0xb9;
  FUN_ebe9();
  _DAT_0002 = CONCAT11(DAT_0007 + -0x75 + (0xe3 < DAT_0006),DAT_0006 + 0x1c);
  DAT_0004 = 0;
  do {
    DAT_0472 = *(byte *)(_DAT_0002 + (ushort)DAT_0004);
    if (DAT_0472 == 0xff) {
LAB_b9ea:
      uStack0000 = 0xb9;
      FUN_f25f(0x30);
      bVar2 = DAT_0402 << 3;
      bVar1 = 0;
      do {
        (&DAT_0160)[bVar1] = *(undefined1 *)(bVar2 + 0x9d72);
        bVar2 = bVar2 + 1;
        bVar1 = bVar1 + 1;
      } while (bVar1 < 8);
      uStack0000 = 0xba;
      FUN_f25f(0x31);
      DAT_0004 = 0;
      do {
        uStack0000 = 0xba;
        officer_address(DAT_0004);
        if ((*(byte *)(_DAT_0000 + 0xb) & 3) == 0) {
          DAT_0472 = DAT_0004;
          bVar2 = *(byte *)(_DAT_0000 + 5);
          if (bVar2 == DAT_0402) {
            DAT_0472 = DAT_0004;
            return;
          }
          bVar1 = 0;
          do {
            if ((&DAT_0160)[bVar1] == bVar2) {
              DAT_0005 = bVar2;
              DAT_0472 = DAT_0004;
              return;
            }
            bVar1 = bVar1 + 1;
            DAT_0005 = bVar2;
          } while (bVar1 < 8);
        }
        DAT_0004 = DAT_0004 + 1;
      } while (DAT_0004 < 0xed);
      DAT_0010._1_1_ = 0x80;
      return;
    }
    uStack0000 = 0xb9;
    officer_address();
    if ((*(byte *)(_DAT_0000 + 0xb) & 3) == 1) {
      DAT_0004 = DAT_0004 + 1;
      bVar2 = *(char *)(_DAT_0002 + (ushort)DAT_0004) + 0x9c;
      if ((bVar2 == DAT_6f00) || (bVar2 < DAT_6f00)) {
        bVar2 = 0;
        do {
          if ((&DAT_ba50)[bVar2] == DAT_0472) {
            DAT_0473 = (&DAT_ba50)[(byte)(bVar2 + 1)];
            DAT_0470 = 7;
            return;
          }
          bVar2 = bVar2 + 2;
        } while (bVar2 < 0x24);
        return;
      }
      goto LAB_b9ea;
    }
    DAT_0004 = DAT_0004 + 2;
  } while( true );
}



/* 0xa01e thunk_FUN_c435 */

void thunk_FUN_c435(void)

{
  undefined1 uStack0000;
  
  uStack0000 = 0xc4;
                    /* WARNING: Subroutine does not return */
  tail_dispatch_inline_table(DAT_0401);
}



/* 0xa021 thunk_FUN_afe5 */

void thunk_FUN_afe5(void)

{
  undefined1 uStack0000;
  
  uStack0000 = 0xaf;
                    /* WARNING: Subroutine does not return */
  tail_dispatch_inline_table(DAT_0401);
}



/* 0xa024 thunk_FUN_ba70 */

/* WARNING: Globals starting with '_' overlap smaller symbols at the same address */

void thunk_FUN_ba70(void)

{
  byte bVar1;
  undefined1 uStack0000;
  
  DAT_0471 = '\x7f';
  if ((DAT_0470 != '\0') && (DAT_0471 = -0x78, DAT_0470 != '\x01')) {
    DAT_0471 = -0x6f;
  }
  do {
    uStack0000 = 0xba;
    bVar1 = FUN_e856();
  } while (4 < bVar1);
  uStack0000 = 0xba;
  DAT_0010._0_1_ = bVar1;
  officer_address(DAT_0481);
  if (*(byte *)(_DAT_0000 + 2) < 0x51) {
    if (0x32 < *(byte *)(_DAT_0000 + 2)) {
      DAT_0010._0_1_ = (byte)DAT_0010 + 2;
    }
  }
  else {
    DAT_0010._0_1_ = (byte)DAT_0010 + 4;
  }
  DAT_0471 = (byte)DAT_0010 + DAT_0471;
  DAT_0472 = (&DAT_badf)[(byte)DAT_0010];
  DAT_04a2 = (&DAT_bae8)[(byte)(DAT_0470 * '\t' + (byte)DAT_0010)];
  return;
}



/* 0xa027 thunk_FUN_bb03 */

/* WARNING: Globals starting with '_' overlap smaller symbols at the same address */

void thunk_FUN_bb03(void)

{
  byte bVar1;
  char cVar2;
  undefined1 uStack0000;
  
  uStack0000 = 0xbb;
  region_address(DAT_0402);
  DAT_042d = 2;
  do {
    *(undefined1 *)(ushort)DAT_042d = *(undefined1 *)(_DAT_0000 + DAT_042d);
    DAT_042d = DAT_042d + 1;
  } while (DAT_042d < 5);
  DAT_0006 = DAT_0002 - DAT_0004;
  bVar1 = (DAT_0003 - DAT_0005) -
          (((DAT_0004 & (~DAT_0002 | DAT_0006) | DAT_0006 & ~DAT_0002) & 0x80) == 0);
  if (((DAT_0005 & (~DAT_0003 | bVar1) | bVar1 & ~DAT_0003) & 0x80) == 0) {
    DAT_042d = 7;
  }
  else if ((bVar1 != 0) || (DAT_0006 != 0)) {
    DAT_042d = 3;
  }
  cVar2 = -0x10;
  uStack0000 = 0xbb;
  bVar1 = FUN_e862(10);
  if (DAT_042d <= bVar1) {
    cVar2 = cVar2 + '\x01';
  }
  _DAT_0000 = (ushort)(byte)(100 - DAT_042f);
  DAT_0002 = 0;
  DAT_0003 = 4;
  uStack0000 = 0xbb;
  DAT_042d = cVar2;
  FUN_ebe9();
  DAT_042f = DAT_0006;
  DAT_0430 = DAT_0007;
  DAT_0431 = 0;
  return;
}



/* 0xa02a thunk_FUN_bbde */

void thunk_FUN_bbde(void)

{
  if (DAT_04e4 == '\0') {
    return;
  }
  *(byte *)((DAT_0402 >> 3) + 0x4e0) =
       *(byte *)((DAT_0402 >> 3) + 0x4e0) | (&DAT_bbfa)[DAT_0402 & 7];
  return;
}



/* 0xa02d thunk_FUN_bc02 */

/* WARNING: Globals starting with '_' overlap smaller symbols at the same address */

void thunk_FUN_bc02(void)

{
  byte bVar1;
  byte bVar2;
  bool bVar3;
  
  DAT_6ffc = 0x49;
  DAT_6ffd = 0x44;
  DAT_0004 = 0;
  DAT_0005 = '\0';
  _DAT_0000 = 0x6000;
  _DAT_0002 = 0x7000;
  do {
    bVar2 = 0;
    do {
      bVar1 = *(byte *)(_DAT_0000 + (ushort)bVar2);
      *(byte *)(_DAT_0002 + (ushort)bVar2) = bVar1;
      bVar3 = CARRY1(bVar1,DAT_0004);
      DAT_0004 = bVar1 + DAT_0004;
      DAT_0005 = DAT_0005 + bVar3;
      bVar2 = bVar2 + 1;
    } while (bVar2 != 0);
    bVar2 = DAT_0001 + 1;
    _DAT_0000 = CONCAT11(bVar2,DAT_0000);
    _DAT_0002 = CONCAT11(DAT_0003 + '\x01',DAT_0002);
  } while (bVar2 < 0x6f);
  bVar2 = 0;
  do {
    bVar1 = *(byte *)(_DAT_0000 + (ushort)bVar2);
    *(byte *)(_DAT_0002 + (ushort)bVar2) = bVar1;
    bVar3 = CARRY1(bVar1,DAT_0004);
    DAT_0004 = bVar1 + DAT_0004;
    DAT_0005 = DAT_0005 + bVar3;
    bVar2 = bVar2 + 1;
  } while (bVar2 != 0xfe);
  DAT_7ffe = DAT_0004;
  DAT_7fff = DAT_0005;
  DAT_00a5 = 0x4c;
  LAB_f800 = 0x4c;
  return;
}



/* 0xa030 thunk_FUN_bb73 */

/* WARNING: Globals starting with '_' overlap smaller symbols at the same address */

void thunk_FUN_bb73(void)

{
  byte bVar1;
  byte bVar2;
  byte bVar3;
  bool bVar4;
  undefined1 uStack0000;
  
  uStack0000 = 0xbb;
  region_address(DAT_0402);
  bVar3 = 2;
  if (DAT_042d != -0x10) {
    bVar3 = 4;
  }
  DAT_0002 = *(byte *)(_DAT_0000 + (ushort)bVar3) - DAT_042f;
  bVar1 = ~*(byte *)(_DAT_0000 + (ushort)bVar3);
  bVar2 = *(byte *)(_DAT_0000 + (ushort)(byte)(bVar3 + 1));
  bVar1 = (bVar2 - DAT_0430) - (((DAT_042f & (bVar1 | DAT_0002) | DAT_0002 & bVar1) & 0x80) == 0);
  bVar2 = ~bVar2;
  if (((DAT_0430 & (bVar2 | bVar1) | bVar1 & bVar2) & 0x80) == 0) {
    DAT_042e = DAT_042d;
    DAT_042d = 0;
    return;
  }
  *(byte *)(_DAT_0000 + (ushort)(byte)(bVar3 + 1)) = bVar1;
  *(byte *)(_DAT_0000 + (ushort)bVar3) = DAT_0002;
  DAT_000a = DAT_042c;
  uStack0000 = 0xbb;
  FUN_a1eb();
  bVar3 = 2;
  if (DAT_042d != -0x10) {
    bVar3 = 4;
  }
  bVar4 = CARRY1(*(byte *)(_DAT_0000 + (ushort)bVar3),DAT_042f);
  *(byte *)(_DAT_0000 + (ushort)bVar3) = *(byte *)(_DAT_0000 + (ushort)bVar3) + DAT_042f;
  *(byte *)(_DAT_0000 + (ushort)(byte)(bVar3 + 1)) =
       *(char *)(_DAT_0000 + (ushort)(byte)(bVar3 + 1)) + DAT_0430 + bVar4;
  DAT_0010._0_1_ = DAT_0000;
  DAT_0010._1_1_ = DAT_0001;
  uStack0000 = 0xbb;
  FUN_a52a(bVar3);
  return;
}



/* 0xa033 FUN_a033 */

void FUN_a033(void)

{
  undefined1 uStack0000;
  
  uStack0000 = 0xa0;
                    /* WARNING: Subroutine does not return */
  tail_dispatch_inline_table(DAT_0401);
}



/* 0xa03f FUN_a03f */

void FUN_a03f(byte param_1)

{
  undefined1 uStack0000;
  
  DAT_00a1 = param_1;
  do {
    DAT_6f41 = 0xf0;
    DAT_6f04 = DAT_6f04 + 1;
    if (6 < DAT_6f04) {
      DAT_6f04 = 0;
      DAT_6f06 = 0;
      DAT_6f01 = DAT_6f01 + 1;
      if (0xb < DAT_6f01) {
        DAT_6f01 = 0;
        DAT_6f00 = DAT_6f00 + '\x01';
      }
      uStack0000 = 0xa0;
      FUN_a209();
    }
    DAT_6f03 = (&DAT_a104)[(byte)(DAT_6f45 << 3 | DAT_6f04)];
    DAT_00ee = (char *)CONCAT11((&DAT_a0d7)[(byte)(DAT_6f03 << 1)],
                                (&DAT_a0d6)[(byte)(DAT_6f03 << 1)]);
  } while (*DAT_00ee == -1);
  uStack0000 = 0xa0;
  FUN_a240();
  if (DAT_0010._1_1_ < 0x1e) {
    DAT_0401 = 3;
    FUN_f28b(0xd5);
    return;
  }
  uStack0000 = 0xa0;
  FUN_a19f(DAT_6f03 & 7);
  DAT_6f05 = (&DAT_a0e4)[DAT_0003];
  uStack0000 = 0xa0;
  far_call_inline_word(0x3d);
  *(char *)(param_1 + 0xa0a0) = *(char *)(param_1 + 0xa0a0) << 1;
  uStack0000 = 0xa0;
  (*(code *)IRQ)();
  return;
}



/* 0xa19f FUN_a19f */

/* WARNING: Globals starting with '_' overlap smaller symbols at the same address */

void FUN_a19f(byte param_1)

{
  char cStack0000;
  
  DAT_0003 = '\0';
  cStack0000 = '\x1d';
  DAT_0002 = param_1;
  do {
    region_address();
    if ((*_DAT_0000 & 0xf) == DAT_0002) {
      DAT_0003 = DAT_0003 + '\x01';
    }
    cStack0000 = cStack0000 + -1;
  } while (-1 < cStack0000);
  return;
}



/* 0xa1eb FUN_a1eb */

/* WARNING: Globals starting with '_' overlap smaller symbols at the same address */

byte FUN_a1eb(void)

{
  byte bVar1;
  byte bVar2;
  undefined1 uStack0000;
  
  bVar1 = 0;
  do {
    uStack0000 = 0xa1;
    region_address(bVar1);
    bVar2 = 0x11;
    do {
      if (*(char *)(_DAT_0000 + (ushort)bVar2) == DAT_000a) {
        return bVar1;
      }
      bVar2 = bVar2 + 1;
    } while (bVar2 < 0x1b);
    bVar1 = bVar1 + 1;
  } while (bVar1 < 0x1e);
  return 0;
}



/* 0xa209 FUN_a209 */

/* WARNING: Globals starting with '_' overlap smaller symbols at the same address */

void FUN_a209(void)

{
  byte bVar1;
  undefined1 uStack0000;
  
  DAT_0002 = 0;
  do {
    uStack0000 = 0xa2;
    FUN_f368(DAT_0002);
    bVar1 = 4;
    do {
      if ((*(byte *)(_DAT_0000 + (ushort)bVar1) & 0xf) != 0) {
        *(char *)(_DAT_0000 + (ushort)bVar1) = *(char *)(_DAT_0000 + (ushort)bVar1) + -1;
      }
      if ((*(byte *)(_DAT_0000 + (ushort)bVar1) & 0xf0) != 0) {
        *(char *)(_DAT_0000 + (ushort)bVar1) = *(char *)(_DAT_0000 + (ushort)bVar1) + -0x10;
      }
      bVar1 = bVar1 + 1;
    } while (bVar1 < 8);
    DAT_0002 = DAT_0002 + 1;
  } while (DAT_0002 < 7);
  return;
}



/* 0xa240 FUN_a240 */

/* WARNING: Globals starting with '_' overlap smaller symbols at the same address */

void FUN_a240(void)

{
  byte bVar1;
  byte bVar2;
  undefined1 uStack0000;
  
  uStack0000 = 0xa2;
  FUN_f25f(0x31);
  bVar2 = 0;
  bVar1 = 0;
  do {
    (&DAT_042c)[bVar1] = *(undefined1 *)(bVar2 + 0x6f07);
    bVar1 = bVar1 + 1;
    bVar2 = bVar1 * '\b';
  } while (bVar1 < 7);
  (&DAT_042c)[DAT_6f03] = 0xff;
  DAT_0010._0_1_ = 0;
  DAT_0010._1_1_ = '\0';
  do {
    bVar2 = 0;
    do {
      if ((&DAT_042c)[bVar2] == (byte)DAT_0010) goto LAB_a28b;
      bVar2 = bVar2 + 1;
    } while (bVar2 < 7);
    uStack0000 = 0xa2;
    officer_address((byte)DAT_0010);
    if ((*(byte *)(_DAT_0000 + 0xb) & 3) != 3) {
      DAT_0010._1_1_ = DAT_0010._1_1_ + '\x01';
    }
LAB_a28b:
    DAT_0010._0_1_ = (byte)DAT_0010 + 1;
    if (0xec < (byte)DAT_0010) {
      return;
    }
  } while( true );
}



/* 0xa296 FUN_a296 */

void FUN_a296(void)

{
  undefined1 uStack0000;
  
  uStack0000 = 0xa2;
                    /* WARNING: Subroutine does not return */
  tail_dispatch_inline_table(DAT_0401);
}



/* 0xa52a FUN_a52a */

byte FUN_a52a(byte param_1)

{
  byte bVar1;
  byte bVar2;
  
  bVar1 = *(byte *)(DAT_0010 + (ushort)(byte)(param_1 + 1));
  bVar2 = (bVar1 - 0x27) -
          ((*(byte *)(DAT_0010 + (ushort)param_1) - 0x10 & ~*(byte *)(DAT_0010 + (ushort)param_1) &
           0x80) == 0);
  if ((bVar2 & ~bVar1 & 0x80) != 0) {
    *(undefined1 *)(DAT_0010 + (ushort)(byte)(param_1 + 1)) = 0x27;
    bVar2 = 0xf;
    *(undefined1 *)(DAT_0010 + (ushort)param_1) = 0xf;
  }
  return bVar2;
}



/* 0xa540 FUN_a540 */

void FUN_a540(void)

{
  return;
}



/* 0xa582 FUN_a582 */

void FUN_a582(void)

{
  return;
}



/* 0xad81 FUN_ad81 */

void FUN_ad81(void)

{
  undefined1 uStack0000;
  
  uStack0000 = 0xad;
                    /* WARNING: Subroutine does not return */
  tail_dispatch_inline_table(DAT_0401);
}



/* 0xafe5 FUN_afe5 */

void FUN_afe5(void)

{
  undefined1 uStack0000;
  
  uStack0000 = 0xaf;
                    /* WARNING: Subroutine does not return */
  tail_dispatch_inline_table(DAT_0401);
}



/* 0xb2d7 FUN_b2d7 */

/* WARNING: Globals starting with '_' overlap smaller symbols at the same address */

void FUN_b2d7(void)

{
  ushort uVar1;
  byte bVar2;
  bool bVar3;
  byte bStack0000;
  
  uVar1 = _DAT_0000;
  if ((DAT_007e & 4) == 0) {
    _DAT_0000 = _DAT_0000 & 0xff;
    if (-1 < (char)DAT_040d) {
      bStack0000 = DAT_040d;
      DAT_0382 = DAT_040d << 5;
      DAT_0381 = ((((DAT_040d >> 7) << 1 | (DAT_040d & 0x7f) >> 6) << 1 | (DAT_040d & 0x3f) >> 5) <<
                  1 | (DAT_040d & 0x1f) >> 4) << 1 | (DAT_040d & 0xf) >> 3;
      DAT_0380 = 0x20;
      _DAT_0000 = CONCAT11(DAT_040c,(char)uVar1);
      DAT_0002 = 0;
      DAT_0004 = 0;
      DAT_0003 = 3;
      FUN_ea7c();
      bVar3 = CARRY1((&DAT_b4b9)[(byte)(DAT_0005 << 1)],DAT_0382);
      DAT_0382 = (&DAT_b4b9)[(byte)(DAT_0005 << 1)] + DAT_0382;
      DAT_0381 = (&DAT_b4ba)[(byte)(DAT_0005 << 1)] + DAT_0381 + bVar3;
      if (*(char *)(DAT_040c + 0x410) == -2) {
        bStack0000 = 0x10;
      }
      else {
        bStack0000 = bStack0000 << 1;
      }
      _DAT_0000 = CONCAT11((&DAT_b386)[bStack0000],(&DAT_b385)[bStack0000]);
      bVar2 = 0;
      do {
        *(undefined1 *)(bVar2 + 899) = *(undefined1 *)(_DAT_0000 + bVar2);
        bVar2 = bVar2 + 1;
      } while (bVar2 < 0x20);
      bStack0000 = 0xb3;
      FUN_b4bf();
      DAT_03a3 = 0xff;
      DAT_007e = DAT_007e | 4;
      DAT_040d = DAT_040d + 1;
      if (9 < DAT_040d) {
        DAT_040d = 0xff;
      }
      return;
    }
  }
  return;
}



/* 0xb4bf FUN_b4bf */

void FUN_b4bf(void)

{
  undefined1 uStack0000;
  
  if (0xec < *(byte *)(DAT_040c + 0x410)) {
    return;
  }
  uStack0000 = 0xb4;
  officer_address();
  DAT_0010._0_1_ = DAT_0000;
  DAT_0010._1_1_ = DAT_0001;
  uStack0000 = 0xb4;
                    /* WARNING: Subroutine does not return */
  tail_dispatch_inline_table(DAT_040d);
}



/* 0xb7d9 FUN_b7d9 */

/* WARNING: Globals starting with '_' overlap smaller symbols at the same address */

void FUN_b7d9(void)

{
  byte bVar1;
  char cVar2;
  byte bVar3;
  byte bVar4;
  undefined1 uStack0000;
  
  uStack0000 = 0xb7;
  region_address(DAT_0471);
  bVar4 = 2;
  bVar3 = 0x26;
  do {
    (&DAT_0500)[bVar3] = _DAT_0000[bVar4];
    _DAT_0000[bVar4] = 0;
    bVar4 = bVar4 + 1;
    bVar3 = bVar3 + 1;
    if (bVar3 == 0x28) {
      bVar3 = 0x22;
    }
  } while (bVar4 < 6);
  DAT_0507 = *_DAT_0000;
  _DAT_0000 = (byte *)CONCAT11(DAT_0001 + (0xee < DAT_0000),DAT_0000 + 0x11);
  bVar3 = 9;
  do {
    *(byte *)(bVar3 + 0x664) = _DAT_0000[bVar3];
    _DAT_0000[bVar3] = -1;
    bVar3 = bVar3 - 1;
  } while (-1 < (char)bVar3);
  DAT_066e = DAT_0481;
  bVar4 = 0xb;
  bVar3 = 0;
  do {
    if (bVar3 < 10) {
      cVar2 = (&DAT_0151)[bVar3];
      if (cVar2 != DAT_0481) goto LAB_b83a;
    }
    else {
      cVar2 = -1;
LAB_b83a:
      *(char *)(bVar4 + 0x664) = cVar2;
      bVar4 = bVar4 + 1;
    }
    bVar3 = bVar3 + 1;
  } while (bVar4 < 0x14);
  uStack0000 = 0xb8;
  region_address(DAT_0402);
  DAT_0507 = *_DAT_0000 << 4 | DAT_0507;
  bVar3 = 0;
  do {
    if ((&DAT_0151)[bVar3] == -1) break;
    for (bVar4 = 0x11; _DAT_0000[bVar4] != (&DAT_0151)[bVar3]; bVar4 = bVar4 + 1) {
    }
    _DAT_0000[bVar4] = -1;
    bVar3 = bVar3 + 1;
  } while (bVar3 < 10);
  bVar3 = 0x11;
  DAT_0003 = 0x10;
  do {
    DAT_0002 = _DAT_0000[bVar3];
    _DAT_0000[bVar3] = -1;
    if (DAT_0002 != -1) {
      DAT_0003 = DAT_0003 + 1;
      _DAT_0000[DAT_0003] = DAT_0002;
    }
    bVar3 = bVar3 + 1;
  } while (bVar3 < 0x1b);
  if (_DAT_0000[0x11] == -1) {
    *_DAT_0000 = '\a';
  }
  bVar1 = _DAT_0000[2] - DAT_042f;
  bVar3 = ~_DAT_0000[2];
  bVar4 = DAT_042f & (bVar3 | bVar1);
  _DAT_0000[2] = bVar1;
  _DAT_0000[3] = (_DAT_0000[3] - DAT_0430) - (((bVar4 | bVar1 & bVar3) & 0x80) == 0);
  bVar1 = _DAT_0000[4] - DAT_0432;
  bVar3 = ~_DAT_0000[4];
  bVar4 = DAT_0432 & (bVar3 | bVar1);
  _DAT_0000[4] = bVar1;
  _DAT_0000[5] = (_DAT_0000[5] - DAT_0433) - (((bVar4 | bVar1 & bVar3) & 0x80) == 0);
  return;
}



/* 0xb8d7 FUN_b8d7 */

/* WARNING: Globals starting with '_' overlap smaller symbols at the same address */

byte FUN_b8d7(void)

{
  byte bVar1;
  undefined1 uStack0000;
  
  uStack0000 = 0xb8;
  region_address(DAT_0470);
  DAT_0498 = *(undefined1 *)(_DAT_0000 + 2);
  DAT_0499 = *(undefined1 *)(_DAT_0000 + 3);
  DAT_049a = *(undefined1 *)(_DAT_0000 + 4);
  DAT_049b = *(undefined1 *)(_DAT_0000 + 5);
  DAT_049c = *(byte *)(_DAT_0000 + 0x10);
  DAT_049d = 0;
  uStack0000 = 0xb9;
  region_address(DAT_0471);
  DAT_0010._0_1_ = 0xf - *(byte *)(_DAT_0000 + 2);
  DAT_0010._1_1_ =
       ('\'' - *(char *)(_DAT_0000 + 3)) -
       (((*(byte *)(_DAT_0000 + 2) & ((byte)DAT_0010 | 0xf0) | (byte)DAT_0010 & 0xf0) & 0x80) == 0);
  uStack0000 = 0xb9;
  FUN_b948(0);
  DAT_0010._0_1_ = 0xf - *(byte *)(_DAT_0000 + 4);
  DAT_0010._1_1_ =
       ('\'' - *(char *)(_DAT_0000 + 5)) -
       (((*(byte *)(_DAT_0000 + 4) & ((byte)DAT_0010 | 0xf0) | (byte)DAT_0010 & 0xf0) & 0x80) == 0);
  uStack0000 = 0xb9;
  FUN_b948(2);
  DAT_0010._0_1_ = 99 - *(char *)(_DAT_0000 + 0x10);
  DAT_0010._1_1_ = 0;
  bVar1 = -(((DAT_049c & (~(byte)DAT_0010 | (byte)DAT_0010 - DAT_049c) |
             (byte)DAT_0010 - DAT_049c & ~(byte)DAT_0010) & 0x80) == 0) - DAT_049d;
  if (((DAT_049d | bVar1) & 0x80) == 0) {
    bVar1 = 0;
    DAT_049d = 0;
    DAT_049c = (byte)DAT_0010;
  }
  return bVar1;
}



/* 0xb948 FUN_b948 */

byte FUN_b948(byte param_1)

{
  byte bVar1;
  
  bVar1 = (byte)DAT_0010 - (&DAT_0498)[param_1];
  bVar1 = (DAT_0010._1_1_ - (&DAT_0499)[param_1]) -
          ((((&DAT_0498)[param_1] & (~(byte)DAT_0010 | bVar1) | bVar1 & ~(byte)DAT_0010) & 0x80) ==
          0);
  if ((((&DAT_0499)[param_1] & (~DAT_0010._1_1_ | bVar1) | bVar1 & ~DAT_0010._1_1_) & 0x80) == 0) {
    (&DAT_0498)[param_1] = (byte)DAT_0010;
    bVar1 = DAT_0010._1_1_;
    (&DAT_0499)[param_1] = DAT_0010._1_1_;
  }
  return bVar1;
}



/* 0xb964 FUN_b964 */

/* WARNING: Globals starting with '_' overlap smaller symbols at the same address */

void FUN_b964(void)

{
  byte bVar1;
  byte bVar2;
  undefined1 uStack0000;
  
  uStack0000 = 0xb9;
  FUN_f25f(0x31);
  _DAT_0000 = (ushort)DAT_0402;
  _DAT_0002 = 0x1400;
  uStack0000 = 0xb9;
  FUN_ebe9();
  _DAT_0002 = CONCAT11(DAT_0007 + -0x75 + (0xe3 < DAT_0006),DAT_0006 + 0x1c);
  DAT_0004 = 0;
  do {
    DAT_0472 = *(byte *)(_DAT_0002 + (ushort)DAT_0004);
    if (DAT_0472 == 0xff) {
LAB_b9ea:
      uStack0000 = 0xb9;
      FUN_f25f(0x30);
      bVar2 = DAT_0402 << 3;
      bVar1 = 0;
      do {
        (&DAT_0160)[bVar1] = *(undefined1 *)(bVar2 + 0x9d72);
        bVar2 = bVar2 + 1;
        bVar1 = bVar1 + 1;
      } while (bVar1 < 8);
      uStack0000 = 0xba;
      FUN_f25f(0x31);
      DAT_0004 = 0;
      do {
        uStack0000 = 0xba;
        officer_address(DAT_0004);
        if ((*(byte *)(_DAT_0000 + 0xb) & 3) == 0) {
          DAT_0472 = DAT_0004;
          bVar2 = *(byte *)(_DAT_0000 + 5);
          if (bVar2 == DAT_0402) {
            DAT_0472 = DAT_0004;
            return;
          }
          bVar1 = 0;
          do {
            if ((&DAT_0160)[bVar1] == bVar2) {
              DAT_0005 = bVar2;
              DAT_0472 = DAT_0004;
              return;
            }
            bVar1 = bVar1 + 1;
            DAT_0005 = bVar2;
          } while (bVar1 < 8);
        }
        DAT_0004 = DAT_0004 + 1;
      } while (DAT_0004 < 0xed);
      DAT_0010._1_1_ = 0x80;
      return;
    }
    uStack0000 = 0xb9;
    officer_address();
    if ((*(byte *)(_DAT_0000 + 0xb) & 3) == 1) {
      DAT_0004 = DAT_0004 + 1;
      bVar2 = *(char *)(_DAT_0002 + (ushort)DAT_0004) + 0x9c;
      if ((bVar2 == DAT_6f00) || (bVar2 < DAT_6f00)) {
        bVar2 = 0;
        do {
          if ((&DAT_ba50)[bVar2] == DAT_0472) {
            DAT_0473 = (&DAT_ba50)[(byte)(bVar2 + 1)];
            DAT_0470 = 7;
            return;
          }
          bVar2 = bVar2 + 2;
        } while (bVar2 < 0x24);
        return;
      }
      goto LAB_b9ea;
    }
    DAT_0004 = DAT_0004 + 2;
  } while( true );
}



/* 0xba70 FUN_ba70 */

/* WARNING: Globals starting with '_' overlap smaller symbols at the same address */

void FUN_ba70(void)

{
  byte bVar1;
  undefined1 uStack0000;
  
  DAT_0471 = '\x7f';
  if ((DAT_0470 != '\0') && (DAT_0471 = -0x78, DAT_0470 != '\x01')) {
    DAT_0471 = -0x6f;
  }
  do {
    uStack0000 = 0xba;
    bVar1 = FUN_e856();
  } while (4 < bVar1);
  uStack0000 = 0xba;
  DAT_0010._0_1_ = bVar1;
  officer_address(DAT_0481);
  if (*(byte *)(_DAT_0000 + 2) < 0x51) {
    if (0x32 < *(byte *)(_DAT_0000 + 2)) {
      DAT_0010._0_1_ = (byte)DAT_0010 + 2;
    }
  }
  else {
    DAT_0010._0_1_ = (byte)DAT_0010 + 4;
  }
  DAT_0471 = (byte)DAT_0010 + DAT_0471;
  DAT_0472 = (&DAT_badf)[(byte)DAT_0010];
  DAT_04a2 = (&DAT_bae8)[(byte)(DAT_0470 * '\t' + (byte)DAT_0010)];
  return;
}



/* 0xbb03 FUN_bb03 */

/* WARNING: Globals starting with '_' overlap smaller symbols at the same address */

void FUN_bb03(void)

{
  byte bVar1;
  char cVar2;
  undefined1 uStack0000;
  
  uStack0000 = 0xbb;
  region_address(DAT_0402);
  DAT_042d = 2;
  do {
    *(undefined1 *)(ushort)DAT_042d = *(undefined1 *)(_DAT_0000 + DAT_042d);
    DAT_042d = DAT_042d + 1;
  } while (DAT_042d < 5);
  DAT_0006 = DAT_0002 - DAT_0004;
  bVar1 = (DAT_0003 - DAT_0005) -
          (((DAT_0004 & (~DAT_0002 | DAT_0006) | DAT_0006 & ~DAT_0002) & 0x80) == 0);
  if (((DAT_0005 & (~DAT_0003 | bVar1) | bVar1 & ~DAT_0003) & 0x80) == 0) {
    DAT_042d = 7;
  }
  else if ((bVar1 != 0) || (DAT_0006 != 0)) {
    DAT_042d = 3;
  }
  cVar2 = -0x10;
  uStack0000 = 0xbb;
  bVar1 = FUN_e862(10);
  if (DAT_042d <= bVar1) {
    cVar2 = cVar2 + '\x01';
  }
  _DAT_0000 = (ushort)(byte)(100 - DAT_042f);
  DAT_0002 = 0;
  DAT_0003 = 4;
  uStack0000 = 0xbb;
  DAT_042d = cVar2;
  FUN_ebe9();
  DAT_042f = DAT_0006;
  DAT_0430 = DAT_0007;
  DAT_0431 = 0;
  return;
}



/* 0xbb73 FUN_bb73 */

/* WARNING: Globals starting with '_' overlap smaller symbols at the same address */

void FUN_bb73(void)

{
  byte bVar1;
  byte bVar2;
  byte bVar3;
  bool bVar4;
  undefined1 uStack0000;
  
  uStack0000 = 0xbb;
  region_address(DAT_0402);
  bVar3 = 2;
  if (DAT_042d != -0x10) {
    bVar3 = 4;
  }
  DAT_0002 = *(byte *)(_DAT_0000 + (ushort)bVar3) - DAT_042f;
  bVar1 = ~*(byte *)(_DAT_0000 + (ushort)bVar3);
  bVar2 = *(byte *)(_DAT_0000 + (ushort)(byte)(bVar3 + 1));
  bVar1 = (bVar2 - DAT_0430) - (((DAT_042f & (bVar1 | DAT_0002) | DAT_0002 & bVar1) & 0x80) == 0);
  bVar2 = ~bVar2;
  if (((DAT_0430 & (bVar2 | bVar1) | bVar1 & bVar2) & 0x80) == 0) {
    DAT_042e = DAT_042d;
    DAT_042d = 0;
    return;
  }
  *(byte *)(_DAT_0000 + (ushort)(byte)(bVar3 + 1)) = bVar1;
  *(byte *)(_DAT_0000 + (ushort)bVar3) = DAT_0002;
  DAT_000a = DAT_042c;
  uStack0000 = 0xbb;
  FUN_a1eb();
  bVar3 = 2;
  if (DAT_042d != -0x10) {
    bVar3 = 4;
  }
  bVar4 = CARRY1(*(byte *)(_DAT_0000 + (ushort)bVar3),DAT_042f);
  *(byte *)(_DAT_0000 + (ushort)bVar3) = *(byte *)(_DAT_0000 + (ushort)bVar3) + DAT_042f;
  *(byte *)(_DAT_0000 + (ushort)(byte)(bVar3 + 1)) =
       *(char *)(_DAT_0000 + (ushort)(byte)(bVar3 + 1)) + DAT_0430 + bVar4;
  DAT_0010._0_1_ = DAT_0000;
  DAT_0010._1_1_ = DAT_0001;
  uStack0000 = 0xbb;
  FUN_a52a(bVar3);
  return;
}



/* 0xbbde FUN_bbde */

void FUN_bbde(void)

{
  if (DAT_04e4 == '\0') {
    return;
  }
  *(byte *)((DAT_0402 >> 3) + 0x4e0) =
       *(byte *)((DAT_0402 >> 3) + 0x4e0) | (&DAT_bbfa)[DAT_0402 & 7];
  return;
}



/* 0xbc02 FUN_bc02 */

/* WARNING: Globals starting with '_' overlap smaller symbols at the same address */

void FUN_bc02(void)

{
  byte bVar1;
  byte bVar2;
  bool bVar3;
  
  DAT_6ffc = 0x49;
  DAT_6ffd = 0x44;
  DAT_0004 = 0;
  DAT_0005 = '\0';
  _DAT_0000 = 0x6000;
  _DAT_0002 = 0x7000;
  do {
    bVar2 = 0;
    do {
      bVar1 = *(byte *)(_DAT_0000 + (ushort)bVar2);
      *(byte *)(_DAT_0002 + (ushort)bVar2) = bVar1;
      bVar3 = CARRY1(bVar1,DAT_0004);
      DAT_0004 = bVar1 + DAT_0004;
      DAT_0005 = DAT_0005 + bVar3;
      bVar2 = bVar2 + 1;
    } while (bVar2 != 0);
    bVar2 = DAT_0001 + 1;
    _DAT_0000 = CONCAT11(bVar2,DAT_0000);
    _DAT_0002 = CONCAT11(DAT_0003 + '\x01',DAT_0002);
  } while (bVar2 < 0x6f);
  bVar2 = 0;
  do {
    bVar1 = *(byte *)(_DAT_0000 + (ushort)bVar2);
    *(byte *)(_DAT_0002 + (ushort)bVar2) = bVar1;
    bVar3 = CARRY1(bVar1,DAT_0004);
    DAT_0004 = bVar1 + DAT_0004;
    DAT_0005 = DAT_0005 + bVar3;
    bVar2 = bVar2 + 1;
  } while (bVar2 != 0xfe);
  DAT_7ffe = DAT_0004;
  DAT_7fff = DAT_0005;
  DAT_00a5 = 0x4c;
  LAB_f800 = 0x4c;
  return;
}



/* 0xc435 FUN_c435 */

void FUN_c435(void)

{
  undefined1 uStack0000;
  
  uStack0000 = 0xc4;
                    /* WARNING: Subroutine does not return */
  tail_dispatch_inline_table(DAT_0401);
}



/* 0xc773 FUN_c773 */

void FUN_c773(void)

{
  undefined1 uStack0000;
  
  uStack0000 = 199;
                    /* WARNING: Subroutine does not return */
  tail_dispatch_inline_table(DAT_0401);
}



/* 0xce1f FUN_ce1f */

void FUN_ce1f(byte param_1)

{
  byte bStack0000;
  
  if ((DAT_6fea & 4) != 0) {
    DAT_00a4 = 3;
  }
  if ((DAT_6fea & 8) != 0) {
    DAT_00a4 = 4;
  }
  bStack0000 = 0xce;
  FUN_f25f(0x21);
  if ((param_1 & 1) == 0) {
    DAT_0003 = 0;
    DAT_00b8 = (&DAT_ced6)[DAT_0000];
  }
  else {
    DAT_0003 = 0x40;
    DAT_00b9 = (&DAT_ced6)[DAT_0000];
  }
  DAT_0005 = 0;
  bStack0000 = ((DAT_00a4 & 7) + *(char *)(DAT_0000 + 0x99a0)) * '\x02';
  DAT_0000 = *(undefined1 *)(bStack0000 + 0x9aa0);
  DAT_0001 = *(undefined1 *)(bStack0000 + 0x9aa1);
  DAT_000c = DAT_04bc;
  if (DAT_04bc == '\0') {
    DAT_000c = '\x10';
  }
  DAT_0002 = 0;
  DAT_0004 = 0xa0;
  FUN_f1b7();
  DAT_04bc = 0;
  if ((((-1 < (char)DAT_00a4) && ((DAT_007e & 1) != 0)) && (DAT_0304 != -1)) &&
     ((DAT_0303 == '\0' && ((DAT_005e & 8) != 0)))) {
    DAT_0000 = *(undefined1 *)(bStack0000 + 0x9d64);
    DAT_0001 = *(undefined1 *)(bStack0000 + 0x9d65);
    FUN_f1b7();
    return;
  }
  DAT_0000 = *(undefined1 *)(bStack0000 + 0x9bac);
  DAT_0001 = *(undefined1 *)(bStack0000 + 0x9bad);
  FUN_f1b7();
  return;
}



/* 0xcfd6 FUN_cfd6 */

void FUN_cfd6(void)

{
  undefined1 uStack0000;
  
  if (((DAT_04c8 != 0) && (DAT_0300 == -1)) && (DAT_0304 == -1)) {
    if (-1 < (char)DAT_04c8) {
      DAT_04c9 = DAT_04c8 - 1;
      DAT_04ca = 0;
      DAT_04c8 = 0x80;
      DAT_04d1 = 7;
      uStack0000 = 0xd4;
                    /* WARNING: Subroutine does not return */
      tail_dispatch_inline_table(0);
    }
    uStack0000 = 0xd0;
                    /* WARNING: Subroutine does not return */
    tail_dispatch_inline_table(DAT_04c8 & 0xf);
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
  thunk_FUN_b964();
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
  DAT_c000 = (&DAT_e567)[bVar1];
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
  
  DAT_c000 = 0xe0;
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



/* 0xe856 FUN_e856 */

byte FUN_e856(void)

{
  byte bVar1;
  undefined1 uStack0000;
  
  uStack0000 = 0xe8;
  bVar1 = FUN_e87a();
  return bVar1 & 7;
}



/* 0xe862 FUN_e862 */

void FUN_e862(byte param_1)

{
  byte bVar1;
  undefined1 uStack0000;
  
  DAT_0010._0_1_ = param_1;
  if (param_1 < 0xf) {
    do {
      uStack0000 = 0xe8;
      bVar1 = FUN_e87a();
    } while ((byte)DAT_0010 <= (bVar1 & 0xf));
    return;
  }
  do {
    uStack0000 = 0xe8;
    bVar1 = FUN_e87a();
  } while ((byte)DAT_0010 <= bVar1);
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



/* 0xec22 FUN_ec22 */

void FUN_ec22(void)

{
  char cVar1;
  byte bVar2;
  bool bVar3;
  bool bVar4;
  byte bVar5;
  
  cVar1 = '\x0f';
  DAT_0006 = 0;
  DAT_0007 = 0;
  DAT_0008 = 0;
  DAT_0009 = 0;
  DAT_000a = '\0';
  DAT_000b = 0;
  DAT_000c = 0;
  do {
    bVar5 = DAT_0004;
    DAT_0004 = DAT_0004 >> 1;
    bVar2 = DAT_0003 & 1;
    DAT_0003 = DAT_0003 >> 1 | bVar5 << 7;
    if (bVar2 != 0) {
      bVar3 = CARRY1(DAT_0000,DAT_0006);
      DAT_0006 = DAT_0000 + DAT_0006;
      bVar4 = CARRY1(DAT_0001,DAT_0007);
      DAT_0007 = DAT_0001 + DAT_0007 + bVar3;
      bVar3 = CARRY1(DAT_0002,DAT_0008);
      DAT_0008 = DAT_0002 + DAT_0008 + bVar4;
      bVar4 = CARRY1(DAT_000b,DAT_0009);
      DAT_0009 = DAT_000b + DAT_0009 + bVar3;
      DAT_000a = DAT_000c + DAT_000a + bVar4;
    }
    bVar5 = DAT_0000 >> 7;
    DAT_0000 = DAT_0000 << 1;
    bVar2 = DAT_0001 >> 7;
    DAT_0001 = DAT_0001 << 1 | bVar5;
    bVar5 = DAT_0002 >> 7;
    DAT_0002 = DAT_0002 << 1 | bVar2;
    bVar2 = DAT_000b >> 7;
    DAT_000b = DAT_000b << 1 | bVar5;
    DAT_000c = DAT_000c << 1 | bVar2;
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
      bVar1 = thunk_FUN_ad81();
      return bVar1;
    }
    if ((char)(DAT_007e << 5) < '\0') {
      DAT_007e = DAT_007e & 0xfb;
      bStack0000 = 0xee;
      FUN_f237(0x3d);
      bVar1 = thunk_FUN_c773();
      return bVar1;
    }
    if ((char)(DAT_007e << 6) < '\0') {
      DAT_007e = DAT_007e & 0xfd;
      bStack0000 = 0xee;
      FUN_f237(0x3d);
      bVar1 = thunk_FUN_b2d7();
      return bVar1;
    }
    if ((char)(DAT_007e << 7) < '\0') {
      bStack0000 = 0xee;
      FUN_f237(DAT_007e << 7,0x3d);
      bVar1 = bank25_entry_00();
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



/* 0xf1b7 FUN_f1b7 */

/* WARNING: Globals starting with '_' overlap smaller symbols at the same address */

void FUN_f1b7(void)

{
  byte bVar1;
  byte bVar2;
  
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
  bank25_entry_00 = DAT_00b2;
  DAT_a800 = DAT_00b3;
  DAT_b000 = DAT_00b4;
                    /* WARNING: Read-only address (RAM,0xb800) is written */
  uRAMb800 = DAT_00b5;
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



/* 0xf28b FUN_f28b */

void FUN_f28b(undefined1 param_1)

{
  DAT_0311 = param_1;
  DAT_0310 = 4;
  DAT_0312 = 0xff;
  DAT_0313 = 0xff;
  DAT_0300 = 0;
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



/* 0xf3bd FUN_f3bd */

void FUN_f3bd(void)

{
  byte bVar1;
  char cVar2;
  bool bVar3;
  undefined1 uStack0000;
  
  DAT_5000 = 0;
  DAT_5800 = 0;
  DAT_c000 = 0xe0;
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
  reset_dispatch = cRAM00de;
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
  thunk_FUN_a033();
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
  DAT_c000 = DAT_00e6;
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
    uRAMb800 = 0;
    uRAMd000 = 7;
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
                    /* WARNING: Read-only address (RAM,0xb800) is written */
      do {
        DAT_0046 = DAT_0046 + -1;
      } while (DAT_0046 != '\0');
      do {
        DAT_0047 = DAT_0047 + -1;
      } while (DAT_0047 != '\0');
                    /* WARNING: Read-only address (RAM,0xb800) is written */
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
      bank25_entry_00 = DAT_00ba;
      DAT_a800 = DAT_00bb;
      DAT_b000 = DAT_00bc;
      uRAMb800 = DAT_00bd;
      DAT_c700 = DAT_00ea;
      uRAMd000 = 7;
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
        bank25_entry_00 = DAT_00ba;
        DAT_a800 = DAT_00bb;
        DAT_b000 = DAT_00bc;
        uRAMb800 = DAT_00bd;
        DAT_c700 = DAT_00ea;
        uRAMd000 = 7;
        return param_1;
      }
      if (DAT_0060 == '\x05') {
LAB_fd95:
                    /* WARNING: Read-only address (RAM,0xd000) is written */
                    /* WARNING: Read-only address (RAM,0xb800) is written */
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
        bank25_entry_00 = DAT_00ba;
        DAT_a800 = DAT_00bb;
        DAT_b000 = DAT_00bc;
        uRAMb800 = DAT_00bd;
        DAT_c700 = 0xe1;
        DAT_c800 = 0xe1;
        uRAMd000 = 0xe1;
        DAT_d800 = 0xe1;
        return param_1;
      }
      if (DAT_0060 == '\x06') {
        DAT_0062 = 0;
        DAT_5000 = 0;
        DAT_5800 = 0;
        uRAMb800 = 0;
        uRAMd000 = 7;
        return param_1;
      }
      if (DAT_0060 == '\a') {
        DAT_5000 = *(undefined1 *)((byte)(DAT_0063 << 1) + 0x6a);
        DAT_5800 = *(undefined1 *)((byte)(DAT_0063 << 1) + 0x6b);
        if (DAT_0063 == '\0') {
          DAT_c700 = 0xe1;
                    /* WARNING: Read-only address (RAM,0xd000) is written */
          uRAMd000 = 0xe1;
          DAT_c800 = 0xe1;
          DAT_d800 = 0xe1;
          DAT_2006 = 0xb8;
                    /* WARNING: Read-only address (RAM,0xb800) is written */
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
        bank25_entry_00 = DAT_00ba;
        DAT_a800 = DAT_00bb;
        DAT_b000 = DAT_00bc;
        uRAMb800 = DAT_00bd;
        uRAMd000 = 7;
        return param_1;
      }
      if (DAT_0060 == '\n') {
                    /* WARNING: Read-only address (RAM,0xb800) is written */
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
        bank25_entry_00 = DAT_00ba;
        DAT_a800 = DAT_00bb;
        DAT_b000 = DAT_00bc;
        uRAMb800 = DAT_00bd;
        DAT_c000 = DAT_00ea;
        uRAMd000 = 7;
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
        uRAMb800 = 0;
        uRAMd000 = 7;
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
                    /* WARNING: Read-only address (RAM,0xb800) is written */
    DAT_0063 = DAT_0063 + '\x01';
    DAT_8000 = DAT_00be;
    DAT_8800 = DAT_00bf;
    DAT_9000 = DAT_00c0;
    DAT_9800 = DAT_00c1;
    bank25_entry_00 = DAT_00c2;
    DAT_a800 = DAT_00c3;
    DAT_b000 = DAT_00c4;
    uRAMb800 = DAT_00c5;
    return param_1;
  }
  if (DAT_0063 != '\x01') {
    if (DAT_0063 != '\x02') {
LAB_fc58:
                    /* WARNING: Read-only address (RAM,0xb800) is written */
      DAT_0060 = DAT_0060 + '\x01';
      DAT_0063 = 0;
      DAT_8000 = DAT_00d6;
      DAT_8800 = DAT_00d7;
      DAT_9000 = DAT_00d8;
      DAT_9800 = DAT_00d9;
      bank25_entry_00 = DAT_00da;
      DAT_a800 = DAT_00db;
      DAT_b000 = DAT_00dc;
      uRAMb800 = DAT_00dd;
      uRAMd000 = 7;
      return param_1;
    }
LAB_fc2a:
                    /* WARNING: Read-only address (RAM,0xb800) is written */
    DAT_0063 = DAT_0063 + '\x01';
    DAT_8000 = DAT_00ce;
    DAT_8800 = DAT_00cf;
    DAT_9000 = DAT_00d0;
    DAT_9800 = DAT_00d1;
    bank25_entry_00 = DAT_00d2;
    DAT_a800 = DAT_00d3;
    DAT_b000 = DAT_00d4;
    uRAMb800 = DAT_00d5;
    uRAMd000 = 7;
    return param_1;
  }
LAB_fbfc:
                    /* WARNING: Read-only address (RAM,0xb800) is written */
  uRAMd000 = 7;
  uRAMb800 = DAT_00cd;
  DAT_b000 = DAT_00cc;
  DAT_a800 = DAT_00cb;
  bank25_entry_00 = DAT_00ca;
  DAT_9800 = DAT_00c9;
  DAT_9000 = DAT_00c8;
  DAT_8800 = DAT_00c7;
  DAT_8000 = DAT_00c6;
  DAT_0063 = DAT_0063 + '\x01';
                    /* WARNING: Read-only address (RAM,0xb800) is written */
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



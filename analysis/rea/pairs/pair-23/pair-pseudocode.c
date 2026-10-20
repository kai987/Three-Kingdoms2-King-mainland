// Ghidra-generated fixed-bank-pair pseudocode. Bank switching and inline pointer dispatch need manual correction. Not original source.

/* 0xa000 bank23_entry_00 */

void bank23_entry_00(void)

{
  char cVar1;
  byte bVar2;
  undefined1 uStack0000;
  
  DAT_2000 = DAT_008b & 0xfb;
  DAT_2006 = DAT_0000;
  bVar2 = 0;
  DAT_0002 = *DAT_000a;
  uStack0000 = 0xa0;
  FUN_a0d2();
  while( true ) {
    while (DAT_000a[bVar2] != DAT_0002) {
      uStack0000 = 0xa0;
      DAT_2007 = DAT_000a[bVar2];
      FUN_a0d2();
    }
    uStack0000 = 0xa0;
    FUN_a0d2();
    cVar1 = DAT_000a[bVar2];
    if (cVar1 == '\0') break;
    uStack0000 = 0xa0;
    FUN_a0d2();
    DAT_2007 = DAT_000a[bVar2];
    do {
      cVar1 = cVar1 + -1;
    } while (cVar1 != '\0');
    uStack0000 = 0xa0;
    FUN_a0d2();
  }
  return;
}



/* 0xa003 thunk_FUN_a212 */

void thunk_FUN_a212(void)

{
  DAT_2000 = DAT_008b & 0xfb;
  DAT_2006 = DAT_0000;
  DAT_000c = '\0';
  DAT_000d = 0;
  do {
    DAT_2007 = *DAT_000a;
    if ((char)((char)DAT_000a + '\x01') == '\0') {
      DAT_000a._1_1_ = DAT_000a._1_1_ + '\x01';
    }
    DAT_000a = (undefined1 *)CONCAT11(DAT_000a._1_1_,(char)DAT_000a + '\x01');
    DAT_000c = DAT_000c + '\x01';
    if (DAT_000c == '\0') {
      DAT_000d = DAT_000d + 1;
    }
  } while (DAT_000d < 4);
  return;
}



/* 0xa006 thunk_FUN_a24e */

/* WARNING: Globals starting with '_' overlap smaller symbols at the same address */

void thunk_FUN_a24e(void)

{
  char cVar1;
  char cVar2;
  byte bVar3;
  byte bStack0000;
  
  DAT_2000 = DAT_008b & 0xfb;
  DAT_2006 = DAT_0000;
  bStack0000 = (byte)DAT_000a - 0x40;
  cVar1 = DAT_000a._1_1_ - ((bStack0000 & ~(byte)DAT_000a & 0x80) == 0);
  DAT_0002 = 0;
  DAT_0003 = 0;
  do {
    cVar2 = '\0';
    bVar3 = *DAT_000a;
    _DAT_0000 = CONCAT11(((bVar3 >> 7) << 1 | (bVar3 & 0x7f) >> 6) + DAT_000d +
                         CARRY1(bVar3 * '\x04',DAT_000c),bVar3 * '\x04' + DAT_000c);
    if ((DAT_0002 & 0x10) != 0) {
      cVar2 = '\x02';
    }
    DAT_2007 = *(undefined1 *)(_DAT_0000 + (ushort)(byte)(cVar2 + 1));
    FUN_a2e4();
    DAT_0002 = DAT_0002 + 1;
    if (((DAT_0002 & 0xf) == 0) && (DAT_0003 = DAT_0003 + 1, (DAT_0003 & 1) != 0)) {
      FUN_a2ed();
    }
  } while (DAT_0003 < 0x1e);
  DAT_000a = (byte *)CONCAT11(cVar1,bStack0000);
  cVar1 = '@';
  bVar3 = 0;
  do {
    DAT_2007 = *(undefined1 *)((short)DAT_000a + (ushort)bVar3);
    bVar3 = bVar3 + 1;
    cVar1 = cVar1 + -1;
  } while (cVar1 != '\0');
  return;
}



/* 0xa009 thunk_FUN_a2ff */

void thunk_FUN_a2ff(void)

{
  undefined1 uVar1;
  byte bVar2;
  char cVar3;
  byte bVar4;
  char cVar5;
  byte bStack0000;
  
  cVar3 = DAT_0091;
  bVar2 = DAT_0090;
  uVar1 = DAT_008f;
  bStack0000 = DAT_008e;
  DAT_001e = DAT_0090;
  DAT_001f = DAT_0091;
  DAT_0091 = DAT_0091 + '\x01';
  cVar5 = '\x1e';
  do {
    FUN_a485();
    FUN_ad9f();
    do {
      FUN_eee6();
    } while (DAT_007e != '\0');
    bVar4 = DAT_0090 - 8;
    if ((DAT_0090 - 8 & ~DAT_0090 & 0x80) == 0) {
      DAT_0091 = DAT_0091 + -1;
      bVar4 = DAT_0090 - 0x18;
    }
    DAT_0090 = bVar4;
    cVar5 = cVar5 + -1;
  } while (-1 < cVar5);
  DAT_0091 = cVar3;
  DAT_0090 = bVar2;
  DAT_008f = uVar1;
  DAT_008e = bStack0000;
  DAT_0092 = bVar2 >> 3;
  DAT_0094 = (byte)(bVar2 + 8) >> 4;
  DAT_0095 = (byte)(bStack0000 - 6) >> 3;
  DAT_0093 = bStack0000 >> 3;
  DAT_009c = 0x90;
  DAT_009d = 0x90;
  return;
}



/* 0xa00c thunk_FUN_a387 */

void thunk_FUN_a387(void)

{
  byte bVar1;
  undefined1 uStack0000;
  
  bVar1 = DAT_008e;
  if (0xfd < DAT_008e) {
    bVar1 = DAT_008e + 2;
  }
  if (bVar1 >> 3 != DAT_0093) {
    uStack0000 = 0xa3;
    DAT_0093 = bVar1 >> 3;
    FUN_a3b1();
  }
  if (DAT_0090 >> 3 != DAT_0092) {
    uStack0000 = 0xa3;
    DAT_0092 = DAT_0090 >> 3;
    FUN_a3bc();
  }
  return;
}



/* 0xa00f thunk_FUN_ab53 */

void thunk_FUN_ab53(void)

{
  byte bVar1;
  undefined1 uStack0000;
  
  bVar1 = (byte)(DAT_008e - 6U) >> 3;
  if (bVar1 != DAT_0095) {
    uStack0000 = 0xab;
    DAT_0095 = bVar1;
    FUN_ab7b();
    return;
  }
  if (DAT_0090 >> 4 != DAT_0094) {
    uStack0000 = 0xab;
    DAT_0094 = DAT_0090 >> 4;
    FUN_ab87();
  }
  return;
}



/* 0xa012 thunk_FUN_a61c */

void thunk_FUN_a61c(void)

{
  ushort uVar1;
  undefined1 uStack0000;
  
  DAT_0001 = (&DAT_a643)[(byte)(DAT_0000 << 1)];
  DAT_0002 = 0x77;
  DAT_0003 = 0xf4;
  uVar1 = (ushort)DAT_0000;
  uStack0000 = 0xa6;
  DAT_0000 = (&DAT_a642)[(byte)(DAT_0000 << 1)];
  FUN_f25f((&DAT_a822)[uVar1]);
  return;
}



/* 0xa015 thunk_FUN_aef0 */

void thunk_FUN_aef0(void)

{
  ushort uVar1;
  undefined1 uStack0000;
  
  DAT_0001 = (&DAT_a733)[(byte)(DAT_0000 << 1)];
  uVar1 = (ushort)DAT_0000;
  uStack0000 = 0xaf;
  DAT_0000 = (&DAT_a732)[(byte)(DAT_0000 << 1)];
  FUN_f25f((&DAT_a822)[uVar1]);
  return;
}



/* 0xa018 thunk_FUN_a983 */

void thunk_FUN_a983(void)

{
  char cVar1;
  byte bStack0000;
  byte bStack_1;
  
  bStack0000 = DAT_0000;
  bStack_1 = DAT_0507;
  if (*(char *)(DAT_0000 + 0x628) < '\0') {
    bStack_1 = DAT_0507 >> 4;
  }
  cVar1 = FUN_a9a8(bStack_1 & 0xf);
  if (cVar1 != '\0') {
    if (cVar1 != '\x01') {
      FUN_aa84();
      return;
    }
    DAT_01b0 = (&DAT_aafa)[*(byte *)(bStack0000 + 0x63c)];
    DAT_01b1 = (&DAT_ab05)[*(byte *)(bStack0000 + 0x63c)];
    if (((bStack0000 == 0) || (bStack0000 == 10)) &&
       (DAT_01b0 = 0xb1, *(char *)(bStack0000 + 0x63c) == '\n')) {
      DAT_01b0 = 0xb0;
      DAT_01b1 = 0x8b;
    }
    DAT_01b2 = 0x8c;
    DAT_01b3 = 0x8d;
    if ((*(byte *)(bStack0000 + 0x628) & 3) == 0) {
      DAT_01b2 = 0xb3;
      DAT_01b3 = 0xb4;
    }
    if ((*(byte *)(bStack0000 + 0x628) & 3) == 2) {
      DAT_01b2 = 0x8e;
      DAT_01b3 = 0x8f;
    }
    return;
  }
  DAT_01b0 = (&DAT_aae4)[*(byte *)(bStack0000 + 0x63c)];
  DAT_01b1 = (&DAT_aaef)[*(byte *)(bStack0000 + 0x63c)];
  if (((bStack0000 == 0) || (bStack0000 == 10)) &&
     (DAT_01b0 = 0xbb, *(char *)(bStack0000 + 0x63c) == '\n')) {
    DAT_01b0 = 0xba;
    DAT_01b1 = 0xab;
  }
  DAT_01b2 = 0xae;
  DAT_01b3 = 0xaf;
  if ((*(byte *)(bStack0000 + 0x628) & 3) == 0) {
    DAT_01b2 = 0xbd;
    DAT_01b3 = 0xbe;
  }
  if ((*(byte *)(bStack0000 + 0x628) & 3) == 1) {
    DAT_01b2 = 0xac;
    DAT_01b3 = 0xad;
  }
  return;
}



/* 0xa01b thunk_FUN_b100 */

void thunk_FUN_b100(void)

{
  undefined1 uStack0000;
  
  DAT_6f44 = *(char *)(DAT_04aa + 0x4ab);
  if (DAT_6f44 < '\0') {
    DAT_6f44 = *(char *)((DAT_04aa ^ 1) + 0x4ab);
  }
  uStack0000 = 0xb1;
                    /* WARNING: Subroutine does not return */
  tail_dispatch_inline_table(DAT_04a8);
}



/* 0xa01e thunk_FUN_d693 */

void thunk_FUN_d693(void)

{
  undefined1 uStack0000;
  
  uStack0000 = 0xd6;
  FUN_f25f(0x26);
  uStack0000 = 0xd6;
                    /* WARNING: Subroutine does not return */
  tail_dispatch_inline_table(DAT_0541);
}



/* 0xa021 thunk_FUN_de25 */

void thunk_FUN_de25(void)

{
  undefined1 uStack0000;
  
  if ((DAT_0081 & 8) != 0) {
    DAT_0541 = 4;
    DAT_0115 = 0xf;
    DAT_0116 = 0xf;
    DAT_0117 = 0xf;
    return;
  }
  uStack0000 = 0xde;
                    /* WARNING: Subroutine does not return */
  tail_dispatch_inline_table(DAT_0541);
}



/* 0xa024 thunk_FUN_a02a */

void thunk_FUN_a02a(void)

{
  undefined1 uStack0000;
  
  uStack0000 = 0xa0;
  FUN_f25f(0x21);
  DAT_0000 = 0;
  DAT_0001 = 0x20;
  uStack0000 = 0xa0;
  FUN_a04a();
  DAT_0000 = 0;
  DAT_0001 = 0x24;
  uStack0000 = 0xa0;
  FUN_a04a();
  return;
}



/* 0xa027 thunk_FUN_df15 */

/* WARNING: Globals starting with '_' overlap smaller symbols at the same address */

void thunk_FUN_df15(void)

{
  _DAT_0000 = (undefined1 *)
              CONCAT11((&DAT_df4b)[(byte)(DAT_050e << 1)],(&DAT_df4a)[(byte)(DAT_050e << 1)]);
  DAT_00aa = *_DAT_0000;
  DAT_00ab = _DAT_0000[1];
  DAT_00ac = _DAT_0000[2];
  DAT_00ad = _DAT_0000[3];
  DAT_00a8._0_1_ = 0xaa;
  DAT_00a8._1_1_ = 0;
  return;
}



/* 0xa02a FUN_a02a */

void FUN_a02a(void)

{
  undefined1 uStack0000;
  
  uStack0000 = 0xa0;
  FUN_f25f(0x21);
  DAT_0000 = 0;
  DAT_0001 = 0x20;
  uStack0000 = 0xa0;
  FUN_a04a();
  DAT_0000 = 0;
  DAT_0001 = 0x24;
  uStack0000 = 0xa0;
  FUN_a04a();
  return;
}



/* 0xa04a FUN_a04a */

void FUN_a04a(void)

{
  byte bVar1;
  undefined1 uStack0000;
  
  bVar1 = DAT_0544 << 1;
  DAT_000a._0_1_ = (&DAT_a06b)[bVar1];
  DAT_000a._1_1_ = (&DAT_a06c)[bVar1];
  DAT_000c = (&DAT_a079)[bVar1];
  DAT_000d = (&DAT_a07a)[bVar1];
  uStack0000 = 0xa0;
  FUN_a24e();
  return;
}



/* 0xa087 FUN_a087 */

void FUN_a087(void)

{
  char cVar1;
  byte bVar2;
  undefined1 uStack0000;
  
  DAT_2000 = DAT_008b & 0xfb;
  DAT_2006 = DAT_0000;
  bVar2 = 0;
  DAT_0002 = *DAT_000a;
  uStack0000 = 0xa0;
  FUN_a0d2();
  while( true ) {
    while (DAT_000a[bVar2] != DAT_0002) {
      uStack0000 = 0xa0;
      DAT_2007 = DAT_000a[bVar2];
      FUN_a0d2();
    }
    uStack0000 = 0xa0;
    FUN_a0d2();
    cVar1 = DAT_000a[bVar2];
    if (cVar1 == '\0') break;
    uStack0000 = 0xa0;
    FUN_a0d2();
    DAT_2007 = DAT_000a[bVar2];
    do {
      cVar1 = cVar1 + -1;
    } while (cVar1 != '\0');
    uStack0000 = 0xa0;
    FUN_a0d2();
  }
  return;
}



/* 0xa0d2 FUN_a0d2 */

void FUN_a0d2(void)

{
  bool bVar1;
  
  bVar1 = 0xfe < (byte)DAT_000a;
  DAT_000a._0_1_ = (byte)DAT_000a + 1;
  DAT_000a._1_1_ = DAT_000a._1_1_ + bVar1;
  return;
}



/* 0xa212 FUN_a212 */

void FUN_a212(void)

{
  DAT_2000 = DAT_008b & 0xfb;
  DAT_2006 = DAT_0000;
  DAT_000c = '\0';
  DAT_000d = 0;
  do {
    DAT_2007 = *DAT_000a;
    if ((char)((char)DAT_000a + '\x01') == '\0') {
      DAT_000a._1_1_ = DAT_000a._1_1_ + '\x01';
    }
    DAT_000a = (undefined1 *)CONCAT11(DAT_000a._1_1_,(char)DAT_000a + '\x01');
    DAT_000c = DAT_000c + '\x01';
    if (DAT_000c == '\0') {
      DAT_000d = DAT_000d + 1;
    }
  } while (DAT_000d < 4);
  return;
}



/* 0xa24e FUN_a24e */

/* WARNING: Globals starting with '_' overlap smaller symbols at the same address */

void FUN_a24e(void)

{
  char cVar1;
  char cVar2;
  byte bVar3;
  byte bStack0000;
  
  DAT_2000 = DAT_008b & 0xfb;
  DAT_2006 = DAT_0000;
  bStack0000 = (byte)DAT_000a - 0x40;
  cVar1 = DAT_000a._1_1_ - ((bStack0000 & ~(byte)DAT_000a & 0x80) == 0);
  DAT_0002 = 0;
  DAT_0003 = 0;
  do {
    cVar2 = '\0';
    bVar3 = *DAT_000a;
    _DAT_0000 = CONCAT11(((bVar3 >> 7) << 1 | (bVar3 & 0x7f) >> 6) + DAT_000d +
                         CARRY1(bVar3 * '\x04',DAT_000c),bVar3 * '\x04' + DAT_000c);
    if ((DAT_0002 & 0x10) != 0) {
      cVar2 = '\x02';
    }
    DAT_2007 = *(undefined1 *)(_DAT_0000 + (ushort)(byte)(cVar2 + 1));
    FUN_a2e4();
    DAT_0002 = DAT_0002 + 1;
    if (((DAT_0002 & 0xf) == 0) && (DAT_0003 = DAT_0003 + 1, (DAT_0003 & 1) != 0)) {
      FUN_a2ed();
    }
  } while (DAT_0003 < 0x1e);
  DAT_000a = (byte *)CONCAT11(cVar1,bStack0000);
  cVar1 = '@';
  bVar3 = 0;
  do {
    DAT_2007 = *(undefined1 *)((short)DAT_000a + (ushort)bVar3);
    bVar3 = bVar3 + 1;
    cVar1 = cVar1 + -1;
  } while (cVar1 != '\0');
  return;
}



/* 0xa2e4 FUN_a2e4 */

void FUN_a2e4(void)

{
  DAT_000a._0_1_ = (char)DAT_000a + '\x01';
  if ((char)DAT_000a == '\0') {
    DAT_000a._1_1_ = DAT_000a._1_1_ + '\x01';
  }
  return;
}



/* 0xa2ed FUN_a2ed */

void FUN_a2ed(void)

{
  byte bVar1;
  byte bVar2;
  
  bVar2 = (byte)DAT_000a - 0x10;
  bVar1 = ~(byte)DAT_000a;
  DAT_000a._0_1_ = bVar2;
  DAT_000a._1_1_ = DAT_000a._1_1_ - ((bVar2 & bVar1 & 0x80) == 0);
  return;
}



/* 0xa2ff FUN_a2ff */

void FUN_a2ff(void)

{
  undefined1 uVar1;
  byte bVar2;
  char cVar3;
  byte bVar4;
  char cVar5;
  byte bStack0000;
  
  cVar3 = DAT_0091;
  bVar2 = DAT_0090;
  uVar1 = DAT_008f;
  bStack0000 = DAT_008e;
  DAT_001e = DAT_0090;
  DAT_001f = DAT_0091;
  DAT_0091 = DAT_0091 + '\x01';
  cVar5 = '\x1e';
  do {
    FUN_a485();
    FUN_ad9f();
    do {
      FUN_eee6();
    } while (DAT_007e != '\0');
    bVar4 = DAT_0090 - 8;
    if ((DAT_0090 - 8 & ~DAT_0090 & 0x80) == 0) {
      DAT_0091 = DAT_0091 + -1;
      bVar4 = DAT_0090 - 0x18;
    }
    DAT_0090 = bVar4;
    cVar5 = cVar5 + -1;
  } while (-1 < cVar5);
  DAT_0091 = cVar3;
  DAT_0090 = bVar2;
  DAT_008f = uVar1;
  DAT_008e = bStack0000;
  DAT_0092 = bVar2 >> 3;
  DAT_0094 = (byte)(bVar2 + 8) >> 4;
  DAT_0095 = (byte)(bStack0000 - 6) >> 3;
  DAT_0093 = bStack0000 >> 3;
  DAT_009c = 0x90;
  DAT_009d = 0x90;
  return;
}



/* 0xa387 FUN_a387 */

void FUN_a387(void)

{
  byte bVar1;
  undefined1 uStack0000;
  
  bVar1 = DAT_008e;
  if (0xfd < DAT_008e) {
    bVar1 = DAT_008e + 2;
  }
  if (bVar1 >> 3 != DAT_0093) {
    uStack0000 = 0xa3;
    DAT_0093 = bVar1 >> 3;
    FUN_a3b1();
  }
  if (DAT_0090 >> 3 != DAT_0092) {
    uStack0000 = 0xa3;
    DAT_0092 = DAT_0090 >> 3;
    FUN_a3bc();
  }
  return;
}



/* 0xa3b1 FUN_a3b1 */

void FUN_a3b1(void)

{
  if (DAT_009c < '\0') {
    FUN_a465();
    return;
  }
  FUN_a3c9();
  return;
}



/* 0xa3bc FUN_a3bc */

void FUN_a3bc(void)

{
  if ((DAT_009c & 0x20) == 0) {
    FUN_a485();
    return;
  }
  FUN_a51c();
  return;
}



/* 0xa3c9 FUN_a3c9 */

/* WARNING: Globals starting with '_' overlap smaller symbols at the same address */

void FUN_a3c9(char param_1)

{
  byte bStack0000;
  
  DAT_000c = DAT_008e;
  DAT_000d = DAT_008f;
  DAT_000e = DAT_0090;
  DAT_000f = DAT_0091;
  if ((char)DAT_007e < '\0') {
    return;
  }
  bStack0000 = 0xa3;
  FUN_a604();
  bStack0000 = 0xa3;
  DAT_001a = param_1;
  FUN_a61f();
  DAT_0010 = *(undefined1 *)(DAT_00a8 + (ushort)(byte)(DAT_001a + 2));
  bStack0000 = 0xa3;
  FUN_a93f();
  DAT_0006 = 0;
  DAT_0007 = '\0';
  DAT_0008._0_1_ = DAT_000c >> 4;
  DAT_0005 = (DAT_000e & 0xf0) + (byte)DAT_0008;
  do {
    bStack0000 = 0xa4;
    FUN_a545(*(undefined1 *)((short)_DAT_0000 + (ushort)DAT_0005));
    DAT_0019 = DAT_0019 + '\x01';
    bStack0000 = DAT_0005 + 0x10;
    if (0xef < bStack0000) {
      bStack0000 = bStack0000 & 0xf;
      FUN_a61f(DAT_0010);
      DAT_0007 = DAT_0007 + '\x01';
      DAT_0019 = DAT_0019 + '\x01';
    }
    DAT_0006 = DAT_0006 + 1;
    DAT_0005 = bStack0000;
  } while (DAT_0006 < 0x10);
  _DAT_0000 = &DAT_0140;
  bStack0000 = 0xa4;
  FUN_a89a();
  DAT_007e = DAT_007e | 0x80;
  return;
}



/* 0xa465 FUN_a465 */

/* WARNING: Globals starting with '_' overlap smaller symbols at the same address */

void FUN_a465(char param_1)

{
  byte bStack0000;
  
  DAT_000c = DAT_008e - 8;
  DAT_000d = DAT_008f + (7 < DAT_008e);
  DAT_000e = DAT_0090;
  DAT_000f = DAT_0091;
  if ((char)DAT_007e < '\0') {
    return;
  }
  bStack0000 = 0xa3;
  FUN_a604();
  bStack0000 = 0xa3;
  DAT_001a = param_1;
  FUN_a61f();
  DAT_0010 = *(undefined1 *)(DAT_00a8 + (ushort)(byte)(DAT_001a + 2));
  bStack0000 = 0xa3;
  FUN_a93f();
  DAT_0006 = 0;
  DAT_0007 = '\0';
  DAT_0008._0_1_ = DAT_000c >> 4;
  DAT_0005 = (DAT_000e & 0xf0) + (byte)DAT_0008;
  do {
    bStack0000 = 0xa4;
    FUN_a545(*(undefined1 *)((short)_DAT_0000 + (ushort)DAT_0005));
    DAT_0019 = DAT_0019 + '\x01';
    bStack0000 = DAT_0005 + 0x10;
    if (0xef < bStack0000) {
      bStack0000 = bStack0000 & 0xf;
      FUN_a61f(DAT_0010);
      DAT_0007 = DAT_0007 + '\x01';
      DAT_0019 = DAT_0019 + '\x01';
    }
    DAT_0006 = DAT_0006 + 1;
    DAT_0005 = bStack0000;
  } while (DAT_0006 < 0x10);
  _DAT_0000 = &DAT_0140;
  bStack0000 = 0xa4;
  FUN_a89a();
  DAT_007e = DAT_007e | 0x80;
  return;
}



/* 0xa485 FUN_a485 */

/* WARNING: Globals starting with '_' overlap smaller symbols at the same address */

void FUN_a485(char param_1)

{
  byte bVar1;
  byte bVar2;
  undefined1 uStack0000;
  
  DAT_000c = DAT_008e;
  DAT_000d = DAT_008f;
  DAT_000f = DAT_0091;
  DAT_000e = DAT_0090;
  if ((char)(DAT_007e << 1) < '\0') {
    return;
  }
  uStack0000 = 0xa4;
  FUN_a604(DAT_007e << 1);
  uStack0000 = 0xa4;
  DAT_001a = param_1;
  FUN_a61f();
  DAT_0010 = *(undefined1 *)(DAT_00a8 + (ushort)(byte)(DAT_001a + 1));
  uStack0000 = 0xa4;
  FUN_a961();
  DAT_0008._0_1_ = DAT_000c >> 4;
  DAT_0005 = (DAT_000e & 0xf0) + (byte)DAT_0008;
  DAT_0006 = 0;
  do {
    uStack0000 = 0xa4;
    FUN_a5a5(*(undefined1 *)((short)_DAT_0000 + (ushort)DAT_0005));
    DAT_0018 = DAT_0018 + '\x01';
    bVar1 = DAT_0005 + 1;
    bVar2 = DAT_0005 & 0xf;
    DAT_0005 = bVar1;
    if (bVar2 == 0xf) {
      uStack0000 = 0xa4;
      FUN_a61f(DAT_0010);
      DAT_0005 = DAT_0005 - 1 & 0xf0;
    }
    DAT_0006 = DAT_0006 + 1;
  } while (DAT_0006 < 0x11);
  _DAT_0000 = &DAT_0164;
  uStack0000 = 0xa5;
  FUN_a89a();
  DAT_007e = DAT_007e | 0x40;
  return;
}



/* 0xa51c FUN_a51c */

/* WARNING: Globals starting with '_' overlap smaller symbols at the same address */

void FUN_a51c(char param_1)

{
  byte bVar1;
  byte bVar2;
  undefined1 uStack0000;
  
  DAT_000c = DAT_008e;
  DAT_000d = DAT_008f;
  DAT_000f = DAT_0091 + '\x01';
  DAT_000e = DAT_0090 - 0x10;
  if (DAT_0090 < 0x10) {
    DAT_000e = DAT_0090 - 0x20;
    DAT_000f = DAT_0091;
  }
  if ((char)(DAT_007e << 1) < '\0') {
    return;
  }
  uStack0000 = 0xa4;
  FUN_a604(DAT_007e << 1);
  uStack0000 = 0xa4;
  DAT_001a = param_1;
  FUN_a61f();
  DAT_0010 = *(undefined1 *)(DAT_00a8 + (ushort)(byte)(DAT_001a + 1));
  uStack0000 = 0xa4;
  FUN_a961();
  DAT_0008._0_1_ = DAT_000c >> 4;
  DAT_0005 = (DAT_000e & 0xf0) + (byte)DAT_0008;
  DAT_0006 = 0;
  do {
    uStack0000 = 0xa4;
    FUN_a5a5(*(undefined1 *)((short)_DAT_0000 + (ushort)DAT_0005));
    DAT_0018 = DAT_0018 + '\x01';
    bVar1 = DAT_0005 + 1;
    bVar2 = DAT_0005 & 0xf;
    DAT_0005 = bVar1;
    if (bVar2 == 0xf) {
      uStack0000 = 0xa4;
      FUN_a61f(DAT_0010);
      DAT_0005 = DAT_0005 - 1 & 0xf0;
    }
    DAT_0006 = DAT_0006 + 1;
  } while (DAT_0006 < 0x11);
  _DAT_0000 = &DAT_0164;
  uStack0000 = 0xa5;
  FUN_a89a();
  DAT_007e = DAT_007e | 0x40;
  return;
}



/* 0xa545 FUN_a545 */

void FUN_a545(byte param_1)

{
  byte bVar1;
  undefined1 uStack0000;
  
  uStack0000 = 0xa5;
  bVar1 = FUN_a8fd();
  DAT_0008 = (undefined1 *)
             CONCAT11(((bVar1 >> 7) << 1 | (bVar1 & 0x7f) >> 6) + DAT_0003 +
                      CARRY1(bVar1 * '\x04',DAT_0002),bVar1 * '\x04' + DAT_0002);
  if ((DAT_000c & 8) == 0) {
    if ((DAT_0006 != '\0') || ((DAT_000e & 8) == 0)) {
      (&DAT_0142)[param_1] = *DAT_0008;
      param_1 = param_1 + 1;
    }
    (&DAT_0142)[param_1] = DAT_0008[2];
    return;
  }
  if ((DAT_0006 != '\0') || ((DAT_000e & 8) == 0)) {
    (&DAT_0142)[param_1] = DAT_0008[1];
    param_1 = param_1 + 1;
  }
  (&DAT_0142)[param_1] = DAT_0008[3];
  return;
}



/* 0xa5a5 FUN_a5a5 */

void FUN_a5a5(byte param_1)

{
  byte bVar1;
  undefined1 uStack0000;
  
  uStack0000 = 0xa5;
  bVar1 = FUN_a91e();
  DAT_0008 = (undefined1 *)
             CONCAT11(((bVar1 >> 7) << 1 | (bVar1 & 0x7f) >> 6) + DAT_0003 +
                      CARRY1(bVar1 * '\x04',DAT_0002),bVar1 * '\x04' + DAT_0002);
  if ((DAT_000e & 8) == 0) {
    if ((DAT_0006 != '\0') || ((DAT_000c & 8) == 0)) {
      (&DAT_0166)[param_1] = *DAT_0008;
      param_1 = param_1 + 1;
    }
    (&DAT_0166)[param_1] = DAT_0008[1];
    return;
  }
  if ((DAT_0006 != '\0') || ((DAT_000c & 8) == 0)) {
    (&DAT_0166)[param_1] = DAT_0008[2];
    param_1 = param_1 + 1;
  }
  (&DAT_0166)[param_1] = DAT_0008[3];
  return;
}



/* 0xa604 FUN_a604 */

undefined1 FUN_a604(void)

{
  return *(undefined1 *)(DAT_00a8 + (ushort)(byte)(DAT_000f * '\x02' + DAT_000d));
}



/* 0xa610 FUN_a610 */

undefined1 FUN_a610(void)

{
  return *(undefined1 *)(DAT_00a8 + (ushort)(byte)(DAT_001f * '\x02' + DAT_001d));
}



/* 0xa61c FUN_a61c */

void FUN_a61c(void)

{
  ushort uVar1;
  undefined1 uStack0000;
  
  DAT_0001 = (&DAT_a643)[(byte)(DAT_0000 << 1)];
  DAT_0002 = 0x77;
  DAT_0003 = 0xf4;
  uVar1 = (ushort)DAT_0000;
  uStack0000 = 0xa6;
  DAT_0000 = (&DAT_a642)[(byte)(DAT_0000 << 1)];
  FUN_f25f((&DAT_a822)[uVar1]);
  return;
}



/* 0xa61f FUN_a61f */

void FUN_a61f(byte param_1)

{
  undefined1 uStack0000;
  
  DAT_0000 = (&DAT_a642)[(byte)(param_1 << 1)];
  DAT_0001 = (&DAT_a643)[(byte)(param_1 << 1)];
  DAT_0002 = 0x77;
  DAT_0003 = 0xf4;
  uStack0000 = 0xa6;
  FUN_f25f((&DAT_a822)[param_1]);
  return;
}



/* 0xa89a FUN_a89a */

/* WARNING: Globals starting with '_' overlap smaller symbols at the same address */

void FUN_a89a(void)

{
  *_DAT_0000 = ' ';
  _DAT_0000[1] = DAT_000c >> 3;
  DAT_000f = (DAT_000e >> 7) << 1 | (DAT_000e & 0x78) >> 6;
  _DAT_0000[1] = (DAT_000e & 0xf8) * '\x04' + _DAT_0000[1];
  *_DAT_0000 = *_DAT_0000 + DAT_000f;
  return;
}



/* 0xa8d3 FUN_a8d3 */

/* WARNING: Globals starting with '_' overlap smaller symbols at the same address */

void FUN_a8d3(void)

{
  *_DAT_0000 = 0x23;
  _DAT_0000[1] = (DAT_000c >> 5) - 0x40;
  _DAT_0000[1] = ((DAT_000e & 0xe0) >> 2) + _DAT_0000[1];
  return;
}



/* 0xa8fd FUN_a8fd */

undefined1 FUN_a8fd(undefined1 param_1,byte param_2)

{
  undefined1 uVar1;
  undefined1 uStack0000;
  undefined2 unaff_retaddr;
  
  if (*(char *)(DAT_0019 + 0x680) == -1) {
    return param_1;
  }
  uStack0000 = param_1;
  FUN_a986(unaff_retaddr._1_1_,*(char *)(DAT_0019 + 0x680));
  DAT_0008 = &DAT_01b0;
  if ((DAT_000c & 8) == 0) {
    if ((DAT_0006 != '\0') || ((DAT_000e & 8) == 0)) {
      (&DAT_0142)[param_2] = DAT_01b0;
      param_2 = param_2 + 1;
    }
    uVar1 = DAT_0008[2];
    (&DAT_0142)[param_2] = uVar1;
    return uVar1;
  }
  if ((DAT_0006 != '\0') || ((DAT_000e & 8) == 0)) {
    (&DAT_0142)[param_2] = DAT_01b1;
    param_2 = param_2 + 1;
  }
  uVar1 = DAT_0008[3];
  (&DAT_0142)[param_2] = uVar1;
  return uVar1;
}



/* 0xa91e FUN_a91e */

undefined1 FUN_a91e(undefined1 param_1,byte param_2)

{
  undefined1 uVar1;
  undefined1 uStack0000;
  undefined2 unaff_retaddr;
  
  if (*(char *)(DAT_0018 + 0x680) == -1) {
    return param_1;
  }
  uStack0000 = param_1;
  FUN_a986(unaff_retaddr._1_1_,*(char *)(DAT_0018 + 0x680));
  DAT_0008 = &DAT_01b0;
  if ((DAT_000e & 8) == 0) {
    if ((DAT_0006 != '\0') || ((DAT_000c & 8) == 0)) {
      (&DAT_0166)[param_2] = DAT_01b0;
      param_2 = param_2 + 1;
    }
    uVar1 = DAT_0008[1];
    (&DAT_0166)[param_2] = uVar1;
    return uVar1;
  }
  if ((DAT_0006 != '\0') || ((DAT_000c & 8) == 0)) {
    (&DAT_0166)[param_2] = DAT_01b2;
    param_2 = param_2 + 1;
  }
  uVar1 = DAT_0008[3];
  (&DAT_0166)[param_2] = uVar1;
  return uVar1;
}



/* 0xa93f FUN_a93f */

void FUN_a93f(void)

{
  byte bVar1;
  undefined1 uStack0000;
  
  uStack0000 = 0xa9;
  FUN_ab26();
  bVar1 = 0x3f;
  do {
    *(undefined1 *)(bVar1 + 0x680) = 0xff;
    bVar1 = bVar1 - 1;
  } while (-1 < (char)bVar1);
  bVar1 = 0x13;
  do {
    if (*(char *)(bVar1 + 0x600) == DAT_0018) {
      *(byte *)(*(byte *)(bVar1 + 0x614) + 0x680) = bVar1;
    }
    bVar1 = bVar1 - 1;
  } while (-1 < (char)bVar1);
  return;
}



/* 0xa961 FUN_a961 */

void FUN_a961(void)

{
  byte bVar1;
  undefined1 uStack0000;
  
  uStack0000 = 0xa9;
  FUN_ab26();
  bVar1 = 0x3f;
  do {
    *(undefined1 *)(bVar1 + 0x680) = 0xff;
    bVar1 = bVar1 - 1;
  } while (-1 < (char)bVar1);
  bVar1 = 0x13;
  do {
    if (*(char *)(bVar1 + 0x614) == DAT_0019) {
      *(byte *)(*(byte *)(bVar1 + 0x600) + 0x680) = bVar1;
    }
    bVar1 = bVar1 - 1;
  } while (-1 < (char)bVar1);
  return;
}



/* 0xa983 FUN_a983 */

void FUN_a983(void)

{
  char cVar1;
  byte bStack0000;
  byte bStack_1;
  
  bStack0000 = DAT_0000;
  bStack_1 = DAT_0507;
  if (*(char *)(DAT_0000 + 0x628) < '\0') {
    bStack_1 = DAT_0507 >> 4;
  }
  cVar1 = FUN_a9a8(bStack_1 & 0xf);
  if (cVar1 != '\0') {
    if (cVar1 != '\x01') {
      FUN_aa84();
      return;
    }
    DAT_01b0 = (&DAT_aafa)[*(byte *)(bStack0000 + 0x63c)];
    DAT_01b1 = (&DAT_ab05)[*(byte *)(bStack0000 + 0x63c)];
    if (((bStack0000 == 0) || (bStack0000 == 10)) &&
       (DAT_01b0 = 0xb1, *(char *)(bStack0000 + 0x63c) == '\n')) {
      DAT_01b0 = 0xb0;
      DAT_01b1 = 0x8b;
    }
    DAT_01b2 = 0x8c;
    DAT_01b3 = 0x8d;
    if ((*(byte *)(bStack0000 + 0x628) & 3) == 0) {
      DAT_01b2 = 0xb3;
      DAT_01b3 = 0xb4;
    }
    if ((*(byte *)(bStack0000 + 0x628) & 3) == 2) {
      DAT_01b2 = 0x8e;
      DAT_01b3 = 0x8f;
    }
    return;
  }
  DAT_01b0 = (&DAT_aae4)[*(byte *)(bStack0000 + 0x63c)];
  DAT_01b1 = (&DAT_aaef)[*(byte *)(bStack0000 + 0x63c)];
  if (((bStack0000 == 0) || (bStack0000 == 10)) &&
     (DAT_01b0 = 0xbb, *(char *)(bStack0000 + 0x63c) == '\n')) {
    DAT_01b0 = 0xba;
    DAT_01b1 = 0xab;
  }
  DAT_01b2 = 0xae;
  DAT_01b3 = 0xaf;
  if ((*(byte *)(bStack0000 + 0x628) & 3) == 0) {
    DAT_01b2 = 0xbd;
    DAT_01b3 = 0xbe;
  }
  if ((*(byte *)(bStack0000 + 0x628) & 3) == 1) {
    DAT_01b2 = 0xac;
    DAT_01b3 = 0xad;
  }
  return;
}



/* 0xa986 FUN_a986 */

void FUN_a986(byte param_1)

{
  char cVar1;
  byte bStack0000;
  byte bStack_1;
  
  bStack_1 = DAT_0507;
  if (*(char *)(param_1 + 0x628) < '\0') {
    bStack_1 = DAT_0507 >> 4;
  }
  bStack0000 = param_1;
  cVar1 = FUN_a9a8(bStack_1 & 0xf);
  if (cVar1 != '\0') {
    if (cVar1 != '\x01') {
      FUN_aa84();
      return;
    }
    DAT_01b0 = (&DAT_aafa)[*(byte *)(bStack0000 + 0x63c)];
    DAT_01b1 = (&DAT_ab05)[*(byte *)(bStack0000 + 0x63c)];
    if (((bStack0000 == 0) || (bStack0000 == 10)) &&
       (DAT_01b0 = 0xb1, *(char *)(bStack0000 + 0x63c) == '\n')) {
      DAT_01b0 = 0xb0;
      DAT_01b1 = 0x8b;
    }
    DAT_01b2 = 0x8c;
    DAT_01b3 = 0x8d;
    if ((*(byte *)(bStack0000 + 0x628) & 3) == 0) {
      DAT_01b2 = 0xb3;
      DAT_01b3 = 0xb4;
    }
    if ((*(byte *)(bStack0000 + 0x628) & 3) == 2) {
      DAT_01b2 = 0x8e;
      DAT_01b3 = 0x8f;
    }
    return;
  }
  DAT_01b0 = (&DAT_aae4)[*(byte *)(bStack0000 + 0x63c)];
  DAT_01b1 = (&DAT_aaef)[*(byte *)(bStack0000 + 0x63c)];
  if (((bStack0000 == 0) || (bStack0000 == 10)) &&
     (DAT_01b0 = 0xbb, *(char *)(bStack0000 + 0x63c) == '\n')) {
    DAT_01b0 = 0xba;
    DAT_01b1 = 0xab;
  }
  DAT_01b2 = 0xae;
  DAT_01b3 = 0xaf;
  if ((*(byte *)(bStack0000 + 0x628) & 3) == 0) {
    DAT_01b2 = 0xbd;
    DAT_01b3 = 0xbe;
  }
  if ((*(byte *)(bStack0000 + 0x628) & 3) == 1) {
    DAT_01b2 = 0xac;
    DAT_01b3 = 0xad;
  }
  return;
}



/* 0xa9a8 FUN_a9a8 */

/* WARNING: Globals starting with '_' overlap smaller symbols at the same address */

undefined1 FUN_a9a8(undefined1 param_1)

{
  undefined1 *puVar1;
  short sVar2;
  undefined1 uStack0000;
  
  sVar2 = _DAT_0000;
  uStack0000 = DAT_0000;
  FUN_f368(param_1);
  puVar1 = (undefined1 *)(_DAT_0000 + 3);
  _DAT_0000 = CONCAT11((char)((ushort)sVar2 >> 8),uStack0000);
  return *puVar1;
}



/* 0xaa84 FUN_aa84 */

void FUN_aa84(void)

{
  byte unaff_retaddr;
  
  DAT_01b0 = (&DAT_ab10)[*(byte *)(unaff_retaddr + 0x63c)];
  DAT_01b1 = (&DAT_ab1b)[*(byte *)(unaff_retaddr + 0x63c)];
  if (((unaff_retaddr == 0) || (unaff_retaddr == 10)) &&
     (DAT_01b0 = 0xb6, *(char *)(unaff_retaddr + 0x63c) == '\n')) {
    DAT_01b0 = 0xb5;
    DAT_01b1 = 0x9b;
  }
  DAT_01b2 = 0x9c;
  DAT_01b3 = 0x9d;
  if ((*(byte *)(unaff_retaddr + 0x628) & 3) == 0) {
    DAT_01b2 = 0xb8;
    DAT_01b3 = 0xb9;
  }
  if ((*(byte *)(unaff_retaddr + 0x628) & 3) == 2) {
    DAT_01b2 = 0x9e;
    DAT_01b3 = 0x9f;
  }
  return;
}



/* 0xab26 FUN_ab26 */

byte FUN_ab26(void)

{
  DAT_0018 = (byte)(DAT_000c >> 1 | DAT_000d << 7) >> 3;
  DAT_0019 = (byte)(DAT_000e >> 1 | DAT_000f << 7) >> 3;
  return DAT_000f >> 1;
}



/* 0xab53 FUN_ab53 */

void FUN_ab53(void)

{
  byte bVar1;
  undefined1 uStack0000;
  
  bVar1 = (byte)(DAT_008e - 6U) >> 3;
  if (bVar1 != DAT_0095) {
    uStack0000 = 0xab;
    DAT_0095 = bVar1;
    FUN_ab7b();
    return;
  }
  if (DAT_0090 >> 4 != DAT_0094) {
    uStack0000 = 0xab;
    DAT_0094 = DAT_0090 >> 4;
    FUN_ab87();
  }
  return;
}



/* 0xab7b FUN_ab7b */

void FUN_ab7b(void)

{
  if (-1 < (char)(DAT_009c << 1)) {
    FUN_ad69();
    return;
  }
  FUN_ab94(DAT_009c << 1);
  return;
}



/* 0xab87 FUN_ab87 */

void FUN_ab87(void)

{
  if ((DAT_009c & 0x10) != 0) {
    FUN_ad9f();
    return;
  }
  FUN_aeb5();
  return;
}



/* 0xab94 FUN_ab94 */

/* WARNING: Globals starting with '_' overlap smaller symbols at the same address */

void FUN_ab94(char param_1)

{
  byte bVar1;
  byte bStack0000;
  
  DAT_000c = DAT_008e;
  DAT_000d = DAT_008f;
  DAT_000e = DAT_0090;
  DAT_000f = DAT_0091;
  DAT_001c = DAT_008e;
  DAT_001d = DAT_008f + '\x01';
  DAT_001e = DAT_0090;
  DAT_001f = DAT_0091;
  bStack0000 = 0xab;
  FUN_a604();
  bStack0000 = 0xab;
  DAT_000a._0_1_ = param_1;
  FUN_aef3();
  bVar1 = (char)DAT_000a + 2;
  DAT_000a._0_1_ = *(undefined1 *)(DAT_00a8 + (ushort)bVar1);
  bStack0000 = 0xab;
  FUN_a610();
  bStack0000 = 0xab;
  DAT_001a = bVar1;
  FUN_af0c();
  DAT_001a = *(undefined1 *)(DAT_00a8 + (ushort)(byte)(DAT_001a + 2));
  DAT_0006 = 0;
  DAT_0008._0_1_ = DAT_000c >> 5;
  DAT_0005 = ((DAT_000e & 0xe0) >> 2) + (byte)DAT_0008;
  bStack0000 = 0xac;
  FUN_aff9();
  DAT_0007 = 8;
  if ((DAT_000e & 0x10) != 0) {
    DAT_0007 = 9;
  }
  do {
    DAT_0002 = *(undefined1 *)((short)_DAT_0000 + (ushort)DAT_0005);
    DAT_0003 = *(undefined1 *)(_DAT_0010 + (ushort)DAT_0005);
    bStack0000 = 0xac;
    FUN_af1b();
    DAT_0017 = DAT_0017 + '\x02';
    DAT_0019 = DAT_0019 + '\x02';
    bStack0000 = 0xac;
    FUN_ac80();
    bStack0000 = DAT_0005 + 8;
    if (0x3f < bStack0000) {
      bStack0000 = bStack0000 & 7;
      FUN_aef3((char)DAT_000a);
      FUN_af0c(DAT_001a);
    }
    DAT_0006 = DAT_0006 + 1;
    DAT_0005 = bStack0000;
  } while (DAT_0006 < DAT_0007);
  _DAT_0000 = &DAT_0188;
  bStack0000 = 0xac;
  FUN_a8d3();
  DAT_007e = DAT_007e | 0x20;
  return;
}



/* 0xac80 FUN_ac80 */

void FUN_ac80(byte param_1)

{
  if ((char)(DAT_009c << 1) < '\0') {
    if ((DAT_000c & 0x10) != 0) {
      if (DAT_0006 == '\b') {
        DAT_0002 = DAT_0002 & 0xc;
        DAT_018a = DAT_0003 & 3 | DAT_0002 | DAT_018a & 0xf0;
        return;
      }
      DAT_0002 = DAT_0002 & 0xcc;
      (&DAT_018a)[param_1] = DAT_0003 & 0x33 | DAT_0002;
      return;
    }
    if ((DAT_0006 == '\b') && ((DAT_000e & 0x10) != 0)) {
      DAT_018a = DAT_0002 & 0xf | DAT_018a & 0xf0;
      return;
    }
    (&DAT_018a)[param_1] = DAT_0002;
    return;
  }
  if ((DAT_000c & 0x10) == 0) {
    if ((DAT_0006 == '\b') && ((DAT_000e & 0x10) != 0)) {
      DAT_0002 = DAT_0002 & 3;
      DAT_018a = DAT_0003 & 0xc | DAT_0002 | DAT_018a & 0xf0;
      return;
    }
    DAT_0002 = DAT_0002 & 0x33;
    (&DAT_018a)[param_1] = DAT_0003 & 0xcc | DAT_0002;
    return;
  }
  if ((DAT_0006 == '\b') && ((DAT_000e & 0x10) != 0)) {
    DAT_018a = DAT_0002 & 0xf | DAT_018a & 0xf0;
    return;
  }
  (&DAT_018a)[param_1] = DAT_0002;
  return;
}



/* 0xad69 FUN_ad69 */

/* WARNING: Globals starting with '_' overlap smaller symbols at the same address */

void FUN_ad69(char param_1)

{
  byte bVar1;
  byte bStack0000;
  
  DAT_000c = DAT_008e;
  DAT_000d = DAT_008f + '\x01';
  DAT_000e = DAT_0090;
  DAT_000f = DAT_0091;
  DAT_001c = DAT_008e;
  DAT_001d = DAT_008f;
  DAT_001e = DAT_0090;
  DAT_001f = DAT_0091;
  bStack0000 = 0xab;
  FUN_a604();
  bStack0000 = 0xab;
  DAT_000a._0_1_ = param_1;
  FUN_aef3();
  bVar1 = (char)DAT_000a + 2;
  DAT_000a._0_1_ = *(undefined1 *)(DAT_00a8 + (ushort)bVar1);
  bStack0000 = 0xab;
  FUN_a610();
  bStack0000 = 0xab;
  DAT_001a = bVar1;
  FUN_af0c();
  DAT_001a = *(undefined1 *)(DAT_00a8 + (ushort)(byte)(DAT_001a + 2));
  DAT_0006 = 0;
  DAT_0008._0_1_ = DAT_000c >> 5;
  DAT_0005 = ((DAT_000e & 0xe0) >> 2) + (byte)DAT_0008;
  bStack0000 = 0xac;
  FUN_aff9();
  DAT_0007 = 8;
  if ((DAT_000e & 0x10) != 0) {
    DAT_0007 = 9;
  }
  do {
    DAT_0002 = *(undefined1 *)((short)_DAT_0000 + (ushort)DAT_0005);
    DAT_0003 = *(undefined1 *)(_DAT_0010 + (ushort)DAT_0005);
    bStack0000 = 0xac;
    FUN_af1b();
    DAT_0017 = DAT_0017 + '\x02';
    DAT_0019 = DAT_0019 + '\x02';
    bStack0000 = 0xac;
    FUN_ac80();
    bStack0000 = DAT_0005 + 8;
    if (0x3f < bStack0000) {
      bStack0000 = bStack0000 & 7;
      FUN_aef3((char)DAT_000a);
      FUN_af0c(DAT_001a);
    }
    DAT_0006 = DAT_0006 + 1;
    DAT_0005 = bStack0000;
  } while (DAT_0006 < DAT_0007);
  _DAT_0000 = &DAT_0188;
  bStack0000 = 0xac;
  FUN_a8d3();
  DAT_007e = DAT_007e | 0x20;
  return;
}



/* 0xad9f FUN_ad9f */

/* WARNING: Globals starting with '_' overlap smaller symbols at the same address */

void FUN_ad9f(char param_1)

{
  byte bVar1;
  byte bVar2;
  undefined1 uStack0000;
  
  DAT_000c = DAT_008e + 4;
  DAT_000d = DAT_008f + (0xfb < DAT_008e);
  DAT_000e = DAT_0090;
  DAT_000f = DAT_0091;
  uStack0000 = 0xad;
  FUN_a604();
  uStack0000 = 0xad;
  DAT_000a._0_1_ = param_1;
  FUN_aef3();
  DAT_000a._0_1_ = *(undefined1 *)(DAT_00a8 + (ushort)(byte)((char)DAT_000a + 1));
  DAT_0006 = 0;
  DAT_0008._0_1_ = DAT_000c >> 5;
  DAT_0005 = ((DAT_000e & 0xe0) >> 2) + (byte)DAT_0008;
  uStack0000 = 0xad;
  FUN_b055();
  DAT_0007 = 8;
  if ((DAT_000c & 0x10) != 0) {
    DAT_0007 = 9;
  }
  do {
    DAT_0002 = *(undefined1 *)((short)_DAT_0000 + (ushort)DAT_0005);
    uStack0000 = 0xae;
    FUN_afb5();
    DAT_0016 = DAT_0016 + '\x02';
    DAT_0018 = DAT_0018 + '\x02';
    uStack0000 = 0xae;
    FUN_ae58();
    bVar1 = DAT_0005 + 1;
    bVar2 = DAT_0005 & 7;
    DAT_0005 = bVar1;
    if (bVar2 == 7) {
      uStack0000 = 0xae;
      FUN_aef3((char)DAT_000a);
      DAT_0005 = DAT_0005 - 1 & 0xf8;
    }
    DAT_0006 = DAT_0006 + 1;
  } while (DAT_0006 < DAT_0007);
  _DAT_0000 = &DAT_019c;
  uStack0000 = 0xae;
  FUN_a8d3();
  DAT_007e = DAT_007e | 0x10;
  return;
}



/* 0xae58 FUN_ae58 */

void FUN_ae58(byte param_1)

{
  if ((DAT_009c & 0x10) == 0) {
    if ((DAT_0006 == '\b') && ((DAT_000c & 0x10) != 0)) {
      DAT_019e = DAT_0002 & 0x33 | DAT_019e & 0xcc;
      return;
    }
    (&DAT_019e)[param_1] = DAT_0002;
    return;
  }
  if ((DAT_0006 == '\b') && ((DAT_000c & 0x10) != 0)) {
    DAT_019e = DAT_0002 & 0x33 | DAT_019e & 0xcc;
    return;
  }
  (&DAT_019e)[param_1] = DAT_0002;
  return;
}



/* 0xaeb5 FUN_aeb5 */

/* WARNING: Globals starting with '_' overlap smaller symbols at the same address */

void FUN_aeb5(char param_1)

{
  byte bVar1;
  byte bVar2;
  undefined1 uStack0000;
  
  DAT_000c = DAT_008e + 4;
  DAT_000d = DAT_008f + (0xfb < DAT_008e);
  DAT_000e = DAT_0090 + 0xa0;
  if ((DAT_0090 < 0x60) && (DAT_000e < 0xf0)) {
    DAT_000f = DAT_0091;
  }
  else {
    DAT_000e = DAT_0090 + 0xb0;
    DAT_000f = DAT_0091 + '\x01';
  }
  uStack0000 = 0xad;
  FUN_a604();
  uStack0000 = 0xad;
  DAT_000a._0_1_ = param_1;
  FUN_aef3();
  DAT_000a._0_1_ = *(undefined1 *)(DAT_00a8 + (ushort)(byte)((char)DAT_000a + 1));
  DAT_0006 = 0;
  DAT_0008._0_1_ = DAT_000c >> 5;
  DAT_0005 = ((DAT_000e & 0xe0) >> 2) + (byte)DAT_0008;
  uStack0000 = 0xad;
  FUN_b055();
  DAT_0007 = 8;
  if ((DAT_000c & 0x10) != 0) {
    DAT_0007 = 9;
  }
  do {
    DAT_0002 = *(undefined1 *)((short)_DAT_0000 + (ushort)DAT_0005);
    uStack0000 = 0xae;
    FUN_afb5();
    DAT_0016 = DAT_0016 + '\x02';
    DAT_0018 = DAT_0018 + '\x02';
    uStack0000 = 0xae;
    FUN_ae58();
    bVar1 = DAT_0005 + 1;
    bVar2 = DAT_0005 & 7;
    DAT_0005 = bVar1;
    if (bVar2 == 7) {
      uStack0000 = 0xae;
      FUN_aef3((char)DAT_000a);
      DAT_0005 = DAT_0005 - 1 & 0xf8;
    }
    DAT_0006 = DAT_0006 + 1;
  } while (DAT_0006 < DAT_0007);
  _DAT_0000 = &DAT_019c;
  uStack0000 = 0xae;
  FUN_a8d3();
  DAT_007e = DAT_007e | 0x10;
  return;
}



/* 0xaef0 FUN_aef0 */

void FUN_aef0(void)

{
  ushort uVar1;
  undefined1 uStack0000;
  
  DAT_0001 = (&DAT_a733)[(byte)(DAT_0000 << 1)];
  uVar1 = (ushort)DAT_0000;
  uStack0000 = 0xaf;
  DAT_0000 = (&DAT_a732)[(byte)(DAT_0000 << 1)];
  FUN_f25f((&DAT_a822)[uVar1]);
  return;
}



/* 0xaef3 FUN_aef3 */

void FUN_aef3(byte param_1)

{
  undefined1 uStack0000;
  
  DAT_0000 = (&DAT_a732)[(byte)(param_1 << 1)];
  DAT_0001 = (&DAT_a733)[(byte)(param_1 << 1)];
  uStack0000 = 0xaf;
  FUN_f25f((&DAT_a822)[param_1]);
  return;
}



/* 0xaf0c FUN_af0c */

void FUN_af0c(char param_1)

{
  DAT_0010 = (&DAT_a732)[(byte)(param_1 << 1)];
  DAT_0011 = (&DAT_a733)[(byte)(param_1 << 1)];
  return;
}



/* 0xaf1b FUN_af1b */

void FUN_af1b(void)

{
  undefined1 uStack0000;
  
  if ((DAT_000c + 8U & 0x10) != 0) {
    uStack0000 = 0xaf;
    FUN_af30();
    uStack0000 = 0xaf;
    FUN_af71();
    return;
  }
  uStack0000 = 0xaf;
  FUN_af30();
  return;
}



/* 0xaf30 FUN_af30 */

void FUN_af30(void)

{
  if (-1 < *(char *)(DAT_0019 + 0x680)) {
    DAT_0002 = DAT_0002 & 0xfc | 2;
  }
  if (-1 < *(char *)(DAT_0019 + 0x6a0)) {
    DAT_0002 = DAT_0002 & 0xf3 | 8;
  }
  if (-1 < *(char *)((byte)(DAT_0019 + 1) + 0x680)) {
    DAT_0002 = DAT_0002 & 0xcf | 0x20;
  }
  if (-1 < *(char *)((byte)(DAT_0019 + 1) + 0x6a0)) {
    DAT_0002 = DAT_0002 & 0x3f | 0x80;
  }
  return;
}



/* 0xaf71 FUN_af71 */

void FUN_af71(void)

{
  if (-1 < *(char *)(DAT_0019 + 0x6c0)) {
    DAT_0003 = DAT_0003 & 0xfc | 2;
  }
  if (-1 < *(char *)(DAT_0019 + 0x6e0)) {
    DAT_0003 = DAT_0003 & 0xf3 | 8;
  }
  if (-1 < *(char *)((byte)(DAT_0019 + 1) + 0x6c0)) {
    DAT_0003 = DAT_0003 & 0xcf | 0x20;
  }
  if (-1 < *(char *)((byte)(DAT_0019 + 1) + 0x6e0)) {
    DAT_0003 = DAT_0003 & 0x3f | 0x80;
  }
  DAT_0017 = DAT_0017 + -1;
  return;
}



/* 0xafb5 FUN_afb5 */

void FUN_afb5(void)

{
  if (-1 < *(char *)(DAT_0018 + 0x680)) {
    DAT_0002 = DAT_0002 & 0xfc | 2;
  }
  if (-1 < *(char *)(DAT_0018 + 0x6a0)) {
    DAT_0002 = DAT_0002 & 0xcf | 0x20;
  }
  if (-1 < *(char *)((byte)(DAT_0018 + 1) + 0x680)) {
    DAT_0002 = DAT_0002 & 0xf3 | 8;
  }
  if (-1 < *(char *)((byte)(DAT_0018 + 1) + 0x6a0)) {
    DAT_0002 = DAT_0002 & 0x3f | 0x80;
  }
  DAT_0017 = DAT_0017 + -1;
  return;
}



/* 0xaff9 FUN_aff9 */

void FUN_aff9(void)

{
  byte bVar1;
  char cVar2;
  undefined1 uStack0000;
  
  uStack0000 = 0xaf;
  FUN_b08f();
  bVar1 = 0x7f;
  do {
    *(undefined1 *)(bVar1 + 0x680) = 0xff;
    bVar1 = bVar1 - 1;
  } while (-1 < (char)bVar1);
  cVar2 = '\x13';
  do {
    uStack0000 = 0xb0;
    FUN_b00f();
    cVar2 = cVar2 + -1;
  } while (-1 < cVar2);
  return;
}



/* 0xb00f FUN_b00f */

void FUN_b00f(byte param_1)

{
  char cVar1;
  
  cVar1 = *(char *)(param_1 + 0x600);
  if (cVar1 == DAT_0018) {
    *(byte *)(*(byte *)(param_1 + 0x614) + 0x680) = param_1;
  }
  DAT_0018 = DAT_0018 + '\x01';
  if (cVar1 == DAT_0018) {
    *(byte *)(*(byte *)(param_1 + 0x614) + 0x6a0) = param_1;
  }
  if (cVar1 == DAT_0016) {
    *(byte *)(*(byte *)(param_1 + 0x614) + 0x6c0) = param_1;
  }
  DAT_0016 = DAT_0016 + '\x01';
  if (cVar1 == DAT_0016) {
    *(byte *)(*(byte *)(param_1 + 0x614) + 0x6e0) = param_1;
  }
  DAT_0016 = DAT_0016 + -1;
  DAT_0018 = DAT_0018 + -1;
  return;
}



/* 0xb055 FUN_b055 */

void FUN_b055(void)

{
  byte bVar1;
  char cVar2;
  undefined1 uStack0000;
  
  uStack0000 = 0xb0;
  FUN_b08f();
  bVar1 = 0x3f;
  do {
    *(undefined1 *)(bVar1 + 0x680) = 0xff;
    bVar1 = bVar1 - 1;
  } while (-1 < (char)bVar1);
  cVar2 = '\x13';
  do {
    uStack0000 = 0xb0;
    FUN_b06b();
    cVar2 = cVar2 + -1;
  } while (-1 < cVar2);
  return;
}



/* 0xb06b FUN_b06b */

void FUN_b06b(byte param_1)

{
  char cVar1;
  
  cVar1 = *(char *)(param_1 + 0x614);
  if (cVar1 == DAT_0019) {
    *(byte *)(*(byte *)(param_1 + 0x600) + 0x680) = param_1;
  }
  DAT_0019 = DAT_0019 + '\x01';
  if (cVar1 == DAT_0019) {
    *(byte *)(*(byte *)(param_1 + 0x600) + 0x6a0) = param_1;
  }
  DAT_0019 = DAT_0019 + -1;
  return;
}



/* 0xb08f FUN_b08f */

byte FUN_b08f(void)

{
  DAT_0018 = ((byte)(DAT_000c >> 1 | DAT_000d << 7) >> 4) << 1;
  DAT_0019 = ((byte)(DAT_000e >> 1 | DAT_000f << 7) >> 4) << 1;
  DAT_0016 = ((byte)(DAT_001c >> 1 | DAT_001d << 7) >> 4) << 1;
  DAT_0017 = ((byte)(DAT_000e >> 1 | DAT_000f << 7) >> 4) << 1;
  return DAT_000f >> 1;
}



/* 0xb100 FUN_b100 */

void FUN_b100(void)

{
  undefined1 uStack0000;
  
  DAT_6f44 = *(char *)(DAT_04aa + 0x4ab);
  if (DAT_6f44 < '\0') {
    DAT_6f44 = *(char *)((DAT_04aa ^ 1) + 0x4ab);
  }
  uStack0000 = 0xb1;
                    /* WARNING: Subroutine does not return */
  tail_dispatch_inline_table(DAT_04a8);
}



/* 0xd693 FUN_d693 */

void FUN_d693(void)

{
  undefined1 uStack0000;
  
  uStack0000 = 0xd6;
  FUN_f25f(0x26);
  uStack0000 = 0xd6;
                    /* WARNING: Subroutine does not return */
  tail_dispatch_inline_table(DAT_0541);
}



/* 0xde25 FUN_de25 */

void FUN_de25(void)

{
  undefined1 uStack0000;
  
  if ((DAT_0081 & 8) != 0) {
    DAT_0541 = 4;
    DAT_0115 = 0xf;
    DAT_0116 = 0xf;
    DAT_0117 = 0xf;
    return;
  }
  uStack0000 = 0xde;
                    /* WARNING: Subroutine does not return */
  tail_dispatch_inline_table(DAT_0541);
}



/* 0xdf15 FUN_df15 */

/* WARNING: Globals starting with '_' overlap smaller symbols at the same address */

void FUN_df15(void)

{
  _DAT_0000 = (undefined1 *)
              CONCAT11((&DAT_df4b)[(byte)(DAT_050e << 1)],(&DAT_df4a)[(byte)(DAT_050e << 1)]);
  DAT_00aa = *_DAT_0000;
  DAT_00ab = _DAT_0000[1];
  DAT_00ac = _DAT_0000[2];
  DAT_00ad = _DAT_0000[3];
  DAT_00a8._0_1_ = 0xaa;
  DAT_00a8._1_1_ = 0;
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
  thunk_FUN_b100();
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
  DAT_d000 = (&DAT_e567)[(byte)(bVar1 + 2)];
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
  DAT_d000 = 0xe0;
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
      bVar1 = thunk_FUN_a387();
      return bVar1;
    }
    if ((char)(DAT_007e << 5) < '\0') {
      DAT_007e = DAT_007e & 0xfb;
      bStack0000 = 0xee;
      FUN_f237(0x3d);
      bVar1 = thunk_FUN_a24e();
      return bVar1;
    }
    if ((char)(DAT_007e << 6) < '\0') {
      DAT_007e = DAT_007e & 0xfd;
      bStack0000 = 0xee;
      FUN_f237(0x3d);
      bVar1 = thunk_FUN_a61c();
      return bVar1;
    }
    if ((char)(DAT_007e << 7) < '\0') {
      bStack0000 = 0xee;
      FUN_f237(DAT_007e << 7,0x3d);
      bVar1 = bank23_entry_00();
      return bVar1;
    }
  }
  bVar1 = FUN_e70e();
  return bVar1;
}



/* 0xeee6 FUN_eee6 */

char FUN_eee6(void)

{
  char cVar1;
  
  if ((char)DAT_007e < '\0') {
    DAT_007e = DAT_007e & 0x7f;
    cVar1 = FUN_ef0b();
    return cVar1;
  }
  if ((char)(DAT_007e << 1) < '\0') {
    DAT_007e = DAT_007e & 0xbf;
    cVar1 = FUN_ef71();
    return cVar1;
  }
  if ((char)(DAT_007e << 2) < '\0') {
    DAT_007e = DAT_007e & 0xdf;
    cVar1 = FUN_efc0();
    return cVar1;
  }
  if (-1 < (char)(DAT_007e << 3)) {
    return DAT_007e << 3;
  }
  DAT_007e = DAT_007e & 0xef;
  cVar1 = FUN_f028();
  return cVar1;
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



/* 0xf206 FUN_f206 */

void FUN_f206(void)

{
  DAT_8000 = DAT_00ae;
  DAT_8800 = DAT_00af;
  DAT_9000 = DAT_00b0;
  DAT_9800 = DAT_00b1;
  bank23_entry_00 = DAT_00b2;
  DAT_a800 = DAT_00b3;
  FUN_aff9 = DAT_00b4;
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
  DAT_d000 = 0xe0;
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
  cRAM0050 = cRAM0050 + '\x01';
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
  thunk_FUN_a212();
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
  DAT_d000 = DAT_00e8;
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


